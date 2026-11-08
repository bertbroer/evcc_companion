# EVCC Companion v0.4 — Home Assistant custom app

A mobile-friendly evcc dashboard with Off / Smart / Now controls and a seven-day recurring planner.

## Updating from v0.3

1. Extract the ZIP and copy its contents into your public GitHub repository, keeping `repository.yaml` in the root and the `evcc_companion` folder intact. Commit the changes.
2. Home Assistant → Settings → Apps → App Store → ⋮ → Check for updates / Reload.
3. Open EVCC Companion and update to **0.4.0**. If necessary restart it.
4. Remove the old `companion_password` setting if it remains in the app's saved configuration. Version 0.3 does not use a login.
5. In the app's **Network** section, map `8099/tcp` to host port `8099` and restart. Visit `http://<HOME_ASSISTANT_LAN_IP>:8099/` while on your home Wi-Fi.

## Power readings

- **House total** is calculated as evcc `homePower` plus the sum of all loadpoints' `chargePower`. This assumes evcc `homePower` excludes EV charging (the standard evcc convention). If either source is missing, a dash is shown instead of guessing.
- **EV charger** displays the sum of all loadpoints' `chargePower`.
- **L1/L2/L3** use `chargeCurrents` (or compatible current fields) of the selected loadpoint. A dash indicates missing measurements, not zero amps.
- Power values are shown in W below 1,000 W and kW at or above 1,000 W. Amperes are shown to one decimal place. kWh is an energy unit and is not used for instantaneous power.

## Security

**No authentication is built into v0.4.** Anyone who can reach the app can change charging modes and recurring plans. **Never expose port 8099 directly to the internet.** Keep it restricted to a trusted local network or use a secured VPN / authenticated HTTPS reverse proxy for remote access. Avoid port forwarding on your router.

evcc credentials, if configured, stay on the server. Saving the weekly plan replaces existing repeating plans for the selected vehicle. This prototype has not been tested against your live evcc instance.

For an iPhone home-screen shortcut, open the standalone address in Safari and choose Share → Add to Home Screen. Reliable standalone PWA installation generally requires HTTPS.

## v0.4: Forecast and load balancing

- Forecast displays `loadpoints[].plan` intervals on a time-scaled chart, including their `value` as €/kWh, with a dashed departure marker from `effectivePlanTime`. `planActive: false` is clearly labeled as forecast-only. The chart does **not** imply the car is actively charging.
- Grid phase currents are taken from `grid.currents`, with 23 A as the fallback limit and `circuits[].maxCurrent` preferred. The minimum remaining headroom is computed from the largest absolute grid phase current. Grid currents are **net** at the P1 connection, not total household phase loads when solar generation is present.
- Charger phase currents come from the selected loadpoint's `chargeCurrents`. These are not added to grid phase currents, since the grid readings already include the charger.
- If `effectiveMaxCurrent` is lower than `maxCurrent` while charging, the UI reports **Charging limited · cause unconfirmed**, not definitive load balancing. No authoritative reason code was supplied by the example API state.
- No login. Keep port 8099 on trusted LAN/VPN only.
