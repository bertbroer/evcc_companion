# EVCC Companion v0.2 — Home Assistant custom app

Mobile-friendly dashboard and seven-day recurring charging planner for evcc. Charging modes: **Off / Smart / Now**.

## Install / update

1. Copy the contents of this repository to your **public** GitHub repository. The root must contain `repository.yaml` and the `evcc_companion/` folder.
2. In Home Assistant OS: **Settings → Apps → App Store → ⋮ → Repositories**; add your GitHub repository URL. If already added, refresh the store and update the app.
3. In the EVCC Companion app **Configuration** tab, set `evcc_url` to your evcc URL and set a long, unique `companion_password` before enabling the standalone port. `api_key` is optional if your evcc requires one.
4. In the app **Network** section, assign **8099** to the `8099/tcp` container port, save, then restart the app. If the port is already in use, choose a different host port.
5. On your home Wi-Fi, open `http://<HOME_ASSISTANT_LAN_IP>:8099/` in Safari. If asked for credentials, use username `companion` and the password you set. Use your Home Assistant machine's **LAN IP**, not the evcc port 7070.
6. For iPhone **Add to Home Screen**, use the direct standalone URL in Safari, not the Home Assistant ingress URL. The app includes a web manifest and icon.

## Security — important

- **Do not forward port 8099 on your router or expose it publicly.** This prototype uses HTTP Basic authentication, which **does not encrypt passwords or traffic over HTTP**. Use only on a trusted LAN for testing. For remote access, put it behind a properly configured **HTTPS reverse proxy with authentication**, or use a trusted VPN with HTTPS. Do not use an insecure public HTTP endpoint.
- The standalone port is **disabled by default** (`8099/tcp: null`). Set a strong `companion_password` before enabling it. The password is required for both ingress and standalone requests in v0.2.
- evcc API credentials stay on the server and are never sent to the browser.
- Saving a weekly schedule **replaces all existing repeating plans** for the selected vehicle. Confirm before saving. This is an early prototype: test with care.
- iOS may show browser-style home-screen behavior over HTTP. For a reliable standalone PWA experience, serve the direct app URL over HTTPS with a valid certificate.

## App layout

`repository.yaml` at repository root; `evcc_companion/config.yaml`, `Dockerfile`, `server.py`, and `www/` inside app folder.
