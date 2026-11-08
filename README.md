# EVCC Companion — Home Assistant app (prototype v0.1.0)

A mobile-first dashboard with Off / Smart / Now modes and a seven-day recurring charging planner. It reads the evcc REST API and saves schedules using the official vehicle repeating-plan endpoint.

## Installation on Home Assistant OS

Home Assistant custom app repositories are **Git repositories**, not ZIP uploads. This ZIP contains a ready-to-publish repository, but you must first publish its contents to your own GitHub repository (or use a locally managed add-on directory with filesystem access).

1. Create a GitHub repository, e.g. `evcc-companion-ha`, and upload the *contents* of `evcc-companion-repository` to its root.
2. In Home Assistant go to **Settings → Apps → App Store → ⋮ → Repositories** and add the URL of your GitHub repository.
3. Install **EVCC Companion** from the store.
4. In **Configuration**, set `evcc_url` to a URL reachable **from the add-on container**. The prefilled `http://hass.nummer63.nl:7070` may work if DNS and routing allow it. If evcc runs as another HA app, its internal hostname or HA host IP may be more reliable.
5. If evcc requires authentication, create an evcc API key and enter it as `api_key`. Do not put the key in the frontend.
6. Start the app, click **Open Web UI**, and optionally enable **Show in sidebar**.

## Notes and limitations

- The companion **does not alter evcc's charging algorithm**. `Smart` and `Now` are native evcc modes.
- Saving a weekly schedule **replaces all existing repeating plans for the selected vehicle**. Confirm before saving. One-off plans remain untouched.
- The first detected loadpoint/vehicle is used; multi-car selection is not yet implemented.
- No changes are made to evcc until a user explicitly confirms a mode change or clicks Save and confirms.
- The next-departure card uses browser-local time; use the same timezone as the evcc schedule.
- Ingress serves the interface through Home Assistant; no public port is opened.
- This is an initial prototype and has **not been tested against your live installation**.
