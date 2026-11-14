# EVCC Companion v0.13 — Home Assistant custom app

A mobile-friendly evcc dashboard with Off / Smart / Now controls and a seven-day recurring planner.

## Updating

1. Extract the ZIP and copy its contents into your public GitHub repository, keeping `repository.yaml` in the root and the `evcc_companion` folder intact. Commit the changes.
2. Home Assistant → Settings → Apps → App Store → ⋮ → Check for updates / Reload.
3. Open EVCC Companion and update to **0.13.0**. If necessary restart it.
4. Remove the old `companion_password` setting if it remains in the app's saved configuration. Version 0.3 does not use a login.
5. In the app's **Network** section, map `8099/tcp` to host port `8099` and restart. Visit `http://<HOME_ASSISTANT_LAN_IP>:8099/` while on your home Wi-Fi.

## Power readings

- **House total** is calculated as evcc `homePower` plus the sum of all loadpoints' `chargePower`. This assumes evcc `homePower` excludes EV charging (the standard evcc convention). If either source is missing, a dash is shown instead of guessing.
- **EV charger** displays the sum of all loadpoints' `chargePower`.
- **L1/L2/L3** use `chargeCurrents` (or compatible current fields) of the selected loadpoint. A dash indicates missing measurements, not zero amps.
- Power values are shown in W below 1,000 W and kW at or above 1,000 W. Amperes are shown to one decimal place. kWh is an energy unit and is not used for instantaneous power.

## Security

**No authentication is built into this app.** Anyone who can reach the app can change charging modes and recurring plans. **Never expose port 8099 directly to the internet.** Keep it restricted to a trusted local network or use a secured VPN / authenticated HTTPS reverse proxy for remote access. Avoid port forwarding on your router.

evcc credentials, if configured, stay on the server. Saving the weekly plan replaces existing repeating plans for the selected vehicle. This prototype has not been tested against your live evcc instance.

For an iPhone home-screen shortcut, open the standalone address in Safari and choose Share → Add to Home Screen. Reliable standalone PWA installation generally requires HTTPS.

## v0.6: Forecast and load balancing

- Forecast displays `loadpoints[].plan` intervals on a time-scaled chart, including their `value` as €/kWh, with a dashed departure marker from `effectivePlanTime`. `planActive: false` is clearly labeled as forecast-only. The chart does **not** imply the car is actively charging.
- Grid phase currents are taken from `grid.currents`, with 23 A as the fallback limit and `circuits[].maxCurrent` preferred. The minimum remaining headroom is computed from the largest absolute grid phase current. Grid currents are **net** at the P1 connection, not total household phase loads when solar generation is present.
- Charger phase currents come from the selected loadpoint's `chargeCurrents`. These are not added to grid phase currents, since the grid readings already include the charger.
- If `effectiveMaxCurrent` is lower than `maxCurrent` while charging, the UI reports **Charging limited · cause unconfirmed**, not definitive load balancing. No authoritative reason code was supplied by the example API state.
- No login. Keep port 8099 on trusted LAN/VPN only.

## v0.7 interface

Rebuilt as an iOS-native web app, always in Dutch regardless of the device language: system font, iOS grouped lists, a floating tab bar (Laden, Planning, Energie), segmented control for the charging mode, native switches, and light/dark mode. Dates and numbers are formatted with `nl-NL`. Time and target selection use in-app wheels, because the iOS time picker and `confirm()` show their buttons in the device language. The Laden tab always fits on one screen. The charging mode now applies on tap, without confirmation. No change to evcc API operations.

## v0.8 interface

New, more modern look: light bento tiles on a soft grey-green background, one mint-green accent and Plus Jakarta Sans (loaded from Google Fonts, falls back to the system font when offline). Dark mode follows the device.

- **Laden:** a 10-segment battery with the target of the next departure drawn dashed, a "Klaar om" time (end of the last planned charging slot), tiles for charging power and price, a link tile to the next departure, and three large mode buttons (Uit / Slim / Nu).
- **Planning:** a mint "Volgend vertrek" card, the week schedule with time and target as chips, and the **Laadprognose** (moved here from Energie) with finish time, target, average planned price, a bar chart with the cheapest slot labelled and the departure marker.
- **Energie:** a dark summary card that splits total use into charger and rest of the house, grid phases as bars with the headroom as a chip, and the charger per phase.
- The tab bar is a dark floating pill; the active tab shows its label.

No change to evcc API operations.

## v0.9: Historie

A fourth tab, **Historie**, lists evcc's charging sessions (`GET /api/sessions`), newest first and grouped by month. Each row shows date and start–end time, energy charged (`chargedEnergy`, kWh) and total price (`price`, or `pricePerKWh × chargedEnergy` when `price` is missing). A session without an end time is shown as *bezig*. The card at the top totals kWh, cost and number of sessions for the current month. The proxy allowlist now also permits `GET sessions` (read-only).

v0.9 also fixes the car image from v0.8.1 not loading: the server did not serve `car.png`.

## v0.10

- **Eenmalig vertrek** on the Planning tab: set a one-off departure (day, time, target) next to the weekly schedule, applied to evcc immediately (`POST /api/vehicles/{name}/plan/soc/{soc}/{RFC3339 time}`) and removable (`DELETE /api/vehicles/{name}/plan/soc`). It is read back from the vehicle's `plan` in the evcc state. The home screen's next departure shows whichever comes first, weekly or one-off.
- The server now serves any file in `www` with a known web file type, instead of a fixed list. Paths outside `www` and hidden files are refused. The page is never cached; other files for one hour.
- The Plus Jakarta Sans font is bundled in `www/fonts` (SIL Open Font License, `fonts/OFL.txt`): no request to Google, and it works offline.
- `repository.yaml` points to this repository.
- For local testing, `EVCC_COMPANION_OPTIONS`, `EVCC_COMPANION_WWW` and `EVCC_COMPANION_PORT` override the options file, web folder and port.

## v0.11: guest vehicles

When a car is connected but evcc has not matched it to a configured vehicle (`connected: true` with an empty `vehicleName`), the Laden tab no longer falls back to your own car's data. While `vehicleDetectionActive` is true it shows *Auto herkennen…*; otherwise it shows *Andere auto*, without the car image, charge level, target or finish time, and instead the current session's energy (`sessionEnergy`, Wh) and price (`sessionPrice`). Charging power, price, mode and the weekly plan (which belongs to your own car) are unchanged.

## v0.12

- The battery card shows the car's range under the charge level (`vehicleRange`, km).
- The label top right is now the vehicle's charge limit (`vehicleLimitSoc`), shown as *Limiet 90%*, and the dashed segments of the meter run up to that limit. Previously both followed the target of the next departure. Both are hidden for guest vehicles.

## v0.13: State of Health

A fifth tab, **SoH** (*State of Health*), estimates the battery's usable capacity and health.

evcc's session history does not store the state of charge, so the add-on measures it itself: a background thread reads the evcc state every minute and, for each connection of a recognised vehicle, records the first and last `vehicleSoc` and the energy charged (`sessionEnergy`). When the car is unplugged, a session with at least 15% SoC gained and 5 kWh charged becomes a measurement:

    capacity ≈ kWh charged × charging_efficiency ÷ (SoC gained ÷ 100)

The tab shows the median of the last 10 estimates, as a percentage of the nominal capacity, a chart of all measurements with a trend line, and the list of measurements. Measurements are stored in `/data/soh.json` and survive updates. **They start from the moment this version runs**; there is no history to import.

New options:
- `charging_efficiency` (default `0.9`): share of grid energy that ends up in the battery. AC charging typically loses 8–12%.
- `battery_capacity` (optional, kWh): nominal usable capacity to compare against. Without it the app uses the vehicle's `capacity` from evcc, if set; otherwise it shows only the estimated kWh.

Treat it as a trend, not a lab measurement: SoC from the car's API is rounded and can lag, and charging losses vary with temperature and power.
