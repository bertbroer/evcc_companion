import json, os, re, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit

OPTIONS='/data/options.json'
ASSETS={'/manifest.webmanifest':'application/manifest+json','/icon.svg':'image/svg+xml','/apple-touch-icon.png':'image/png'}
def settings():
    try:
        with open(OPTIONS) as f: return json.load(f)
    except (OSError, ValueError): return {'evcc_url':'http://hass.nummer63.nl:7070','api_key':'','timezone':'Europe/Amsterdam'}

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, ctype='application/json'):
        body=data if isinstance(data,bytes) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers(); self.wfile.write(body)
    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')
    def handle_request(self,method):
        path=urlsplit(self.path).path
        if path in ASSETS and method=='GET':
            with open('/app/www'+path,'rb') as f: self.reply(200,f.read(),ASSETS[path])
            return
        if path in ('/','/index.html') and method=='GET':
            with open('/app/www/index.html','rb') as f: self.reply(200,f.read(),'text/html; charset=utf-8')
            return
        if path=='/app-config' and method=='GET':
            self.reply(200,{'timezone':settings().get('timezone','Europe/Amsterdam')}); return
        if not path.startswith('/proxy/'):
            self.reply(404,{'error':'Not found'}); return
        endpoint=path[len('/proxy/'):]
        # Strict allowlist: never expose arbitrary evcc endpoints or URLs.
        allowed=(method=='GET' and endpoint=='state') or (method=='POST' and (
            re.fullmatch(r'loadpoints/[1-9][0-9]*/mode/(off|smart|now)',endpoint) or
            re.fullmatch(r'vehicles/[A-Za-z0-9_.:-]+/plan/repeating',endpoint)))
        if not allowed:
            self.reply(403,{'error':'Endpoint not permitted'}); return
        payload=None
        if method=='POST':
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
            req=urllib.request.Request(base+'/api/'+endpoint,data=payload,headers=headers,method=method)
            with urllib.request.urlopen(req,timeout=12) as res:
                self.reply(res.status,res.read(),res.headers.get('Content-Type','application/json'))
        except urllib.error.HTTPError as e:
            self.reply(e.code,{'error':e.read().decode(errors='replace')[:300]})
        except Exception as e:
            self.reply(502,{'error':'Cannot reach evcc: '+str(e)[:200]})

ThreadingHTTPServer(('0.0.0.0',8099),Handler).serve_forever()
