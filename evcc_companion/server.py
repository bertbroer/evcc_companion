import json, os, re, threading, time, urllib.request, urllib.error
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, unquote, quote

# Overridable for local testing; the defaults are the paths inside the add-on.
OPTIONS=os.environ.get('EVCC_COMPANION_OPTIONS','/data/options.json')
WWW=os.path.realpath(os.environ.get('EVCC_COMPANION_WWW','/app/www'))
PORT=int(os.environ.get('EVCC_COMPANION_PORT','8099'))
DATA=os.environ.get('EVCC_COMPANION_DATA','/data')
SOH_FILE=os.path.join(DATA,'soh.json')
SOH_INTERVAL=int(os.environ.get('EVCC_COMPANION_SOH_INTERVAL','60'))
# Static files: anything in www with one of these extensions is served.
TYPES={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8',
       '.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp',
       '.ico':'image/x-icon','.woff2':'font/woff2','.webmanifest':'application/manifest+json','.json':'application/json'}
def settings():
    try:
        with open(OPTIONS) as f: return json.load(f)
    except (OSError, ValueError): return {'evcc_url':'http://hass.nummer63.nl:7070','api_key':'','timezone':'Europe/Amsterdam'}

def static_file(path):
    """Resolve a request path to a file inside WWW, or None. Refuses traversal and hidden files."""
    rel=unquote(path).lstrip('/') or 'index.html'
    if any(part.startswith('.') for part in rel.split('/')): return None
    full=os.path.realpath(os.path.join(WWW,rel))
    if not full.startswith(WWW+os.sep) or not os.path.isfile(full): return None
    ctype=TYPES.get(os.path.splitext(full)[1].lower())
    return (full,ctype) if ctype else None

def evcc_get(endpoint):
    cfg=settings(); base=cfg.get('evcc_url','').rstrip('/')
    headers={'Accept':'application/json'}
    if cfg.get('api_key'): headers['Authorization']='Bearer '+cfg['api_key']
    with urllib.request.urlopen(urllib.request.Request(base+'/api/'+endpoint,headers=headers),timeout=12) as res:
        data=json.loads(res.read())
    return data.get('result',data) if isinstance(data,dict) else data

# --- State of Health -------------------------------------------------------
# evcc's session history has no state of charge, so the add-on records it itself:
# for every connection of a known vehicle it notes the first and last SoC and the
# energy charged (loadpoint sessionEnergy, Wh). Capacity estimate per session:
#   energy_kWh * charging_efficiency / (SoC gained / 100)
SOH_LOCK=threading.Lock()
MIN_SOC_GAIN=15      # % SoC; smaller sessions are too noisy to use
MIN_ENERGY=5.0       # kWh

def soh_load():
    try:
        with open(SOH_FILE) as f: data=json.load(f)
        if isinstance(data,dict): return {'measurements':data.get('measurements',[]),'active':data.get('active',{})}
    except (OSError,ValueError): pass
    return {'measurements':[],'active':{}}

def soh_save(data):
    os.makedirs(DATA,exist_ok=True)
    tmp=SOH_FILE+'.tmp'
    with open(tmp,'w') as f: json.dump(data,f)
    os.replace(tmp,SOH_FILE)

def num(v):
    return v if isinstance(v,(int,float)) and not isinstance(v,bool) else None

def soh_finish(data,key,run):
    gain=(run.get('socLast') or 0)-(run.get('socFirst') or 0)
    energy=((run.get('energyLast') or 0)-(run.get('energyFirst') or 0))/1000
    if gain>=MIN_SOC_GAIN and energy>=MIN_ENERGY:
        data['measurements'].append({'start':run['start'],'end':run.get('seen',run['start']),'vehicle':run['vehicle'],
            'title':run.get('title') or run['vehicle'],'socStart':round(run['socFirst'],1),'socEnd':round(run['socLast'],1),
            'energy':round(energy,2)})
        data['measurements']=data['measurements'][-500:]
    data['active'].pop(key,None)

def soh_step(state):
    now=datetime.now(timezone.utc).isoformat(timespec='seconds')
    with SOH_LOCK:
        data=soh_load(); changed=False
        for i,lp in enumerate(state.get('loadpoints') or []):
            key=str(i+1); run=data['active'].get(key)
            vehicle=lp.get('vehicleName') or ''
            soc=num(lp.get('vehicleSoc')); energy=num(lp.get('sessionEnergy'))
            if run and (not lp.get('connected') or (vehicle and vehicle!=run['vehicle']) or (energy is not None and energy+50<(run.get('energyLast') or 0))):
                soh_finish(data,key,run); run=None; changed=True
            if not lp.get('connected') or not vehicle or soc is None or energy is None: continue
            if not run:
                run=data['active'][key]={'vehicle':vehicle,'title':lp.get('vehicleTitle'),'start':now,'socFirst':soc,'energyFirst':energy}
            # Only write when something changed, to spare the SD card.
            if run.get('socLast')!=soc or run.get('energyLast')!=energy:
                run.update(socLast=soc,energyLast=energy,seen=now); changed=True
        if changed: soh_save(data)

def soh_loop():
    while True:
        try: soh_step(evcc_get('state'))
        except Exception as e: print('SoH: evcc state not read:',str(e)[:200],flush=True)
        time.sleep(SOH_INTERVAL)

def soh_report():
    cfg=settings()
    try: efficiency=float(cfg.get('charging_efficiency') or 0.9)
    except (TypeError,ValueError): efficiency=0.9
    efficiency=min(1.0,max(0.5,efficiency))
    with SOH_LOCK: data=soh_load()
    rows=[]
    for m in data['measurements']:
        gain=m['socEnd']-m['socStart']
        if gain>0: rows.append({**m,'capacity':round(m['energy']*efficiency/(gain/100),1)})
    try: nominal=float(cfg.get('battery_capacity') or 0) or None
    except (TypeError,ValueError): nominal=None
    active=[{'vehicle':r['vehicle'],'title':r.get('title'),'start':r['start'],'socStart':r.get('socFirst'),'socNow':r.get('socLast'),
             'energy':round(((r.get('energyLast') or 0)-(r.get('energyFirst') or 0))/1000,2)} for r in data['active'].values()]
    return {'measurements':rows,'active':active,'nominal':nominal,'efficiency':efficiency,'minSocGain':MIN_SOC_GAIN,'minEnergy':MIN_ENERGY}

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, ctype='application/json', cache='no-store'):
        body=data if isinstance(data,bytes) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control',cache)
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers(); self.wfile.write(body)
    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')
    def do_DELETE(self): self.handle_request('DELETE')
    def handle_request(self,method):
        path=urlsplit(self.path).path
        if path=='/app-config' and method=='GET':
            self.reply(200,{'timezone':settings().get('timezone','Europe/Amsterdam')}); return
        if path=='/soh' and method=='GET':
            self.reply(200,soh_report()); return
        if not path.startswith('/proxy/'):
            found=static_file(path) if method=='GET' else None
            if not found: self.reply(404,{'error':'Not found'}); return
            full,ctype=found
            with open(full,'rb') as f: body=f.read()
            # The page itself is never cached, so updates show up at once; assets may be cached briefly.
            self.reply(200,body,ctype,'no-store' if ctype.startswith('text/html') else 'public, max-age=3600')
            return
        # Decode first: the app URL-encodes vehicle names, and evcc names vehicles
        # configured in its UI 'db:<id>', which arrives as 'db%3A<id>'.
        endpoint=unquote(path[len('/proxy/'):])
        # Strict allowlist: never expose arbitrary evcc endpoints or URLs.
        vehicle=r'vehicles/(?!\.+/)[A-Za-z0-9_.:-]+'
        timestamp=r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{1,3})?(Z|[+-]\d\d:\d\d)'
        allowed=(method=='GET' and endpoint in ('state','sessions')) or (method=='POST' and (
            re.fullmatch(r'loadpoints/[1-9][0-9]*/mode/(off|smart|now)',endpoint) or
            re.fullmatch(vehicle+r'/plan/repeating',endpoint) or
            re.fullmatch(vehicle+r'/plan/soc/(100|[1-9][0-9]?)/'+timestamp,endpoint))) or (
            method=='DELETE' and re.fullmatch(vehicle+r'/plan/soc',endpoint))
        if not allowed:
            self.reply(403,{'error':'Endpoint not permitted'}); return
        payload=None
        if method in ('POST','DELETE'):
            length=int(self.headers.get('Content-Length','0'))
            if length>20000: self.reply(413,{'error':'Request too large'}); return
            payload=self.rfile.read(length)
            if endpoint.endswith('/plan/repeating'):
                try:
                    plans=json.loads(payload)
                    assert isinstance(plans,list) and len(plans)<=7
                    for p in plans:
                        assert isinstance(p,dict) and set(p)=={'weekdays','time','tz','soc','active'}
                        assert isinstance(p['weekdays'],list) and all(isinstance(d,int) and 0<=d<=6 for d in p['weekdays'])
                        assert re.fullmatch(r'([01][0-9]|2[0-3]):[0-5][0-9]',p['time'])
                        assert isinstance(p['soc'],int) and 1<=p['soc']<=100
                        assert p['active'] is True and isinstance(p['tz'],str) and len(p['tz'])<100
                except (ValueError,AssertionError,TypeError,KeyError):
                    self.reply(400,{'error':'Invalid weekly plan'}); return
        cfg=settings(); base=cfg.get('evcc_url','').rstrip('/')
        if not base.startswith(('http://','https://')):
            self.reply(500,{'error':'Invalid evcc URL'}); return
        headers={'Accept':'application/json'}
        if payload is not None: headers['Content-Type']='application/json'
        if cfg.get('api_key'): headers['Authorization']='Bearer '+cfg['api_key']
        try:
            req=urllib.request.Request(base+'/api/'+quote(endpoint,safe='/:'),data=payload,headers=headers,method=method)
            with urllib.request.urlopen(req,timeout=12) as res:
                self.reply(res.status,res.read(),res.headers.get('Content-Type','application/json'))
        except urllib.error.HTTPError as e:
            self.reply(e.code,{'error':e.read().decode(errors='replace')[:300]})
        except Exception as e:
            self.reply(502,{'error':'Cannot reach evcc: '+str(e)[:200]})

threading.Thread(target=soh_loop,daemon=True).start()
ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
