# SafePath mobile

React Native + Expo SDK 58 Android prototype. Reuses the existing FastAPI/Neon/Geoapify services and Vijayawada configuration. The existing Next.js app is retained.

## Implemented

- Native MapLibre dark map with selected and alternate walking routes.
- Debounced location search, route comparison, distance and travel time.
- Small category-coloured map dots for shops, petrol bunks, pharmacies, hospitals and police stations, with category filters and place details.
- Single foreground position reading on explicit request, permission-denial handling and pilot-area validation. No background tracking.
- Cached lighting coverage notice, unverified opening-hours notice, partial-result and network-error handling.
- Cancellation of obsolete searches, route and place requests; provider secrets remain on FastAPI.

Safety scoring, time-aware business availability, live turn instructions, SOS and trusted-contact sharing are future milestones. No route is currently assessed for safety.

## Development on an Android phone

MapLibre is a native module, so this app uses an Expo **development build**, not Expo Go. The Android JavaScript export is not an APK.

1. Start the existing services from the project root: `npm run dev`.
2. In `mobile`, install packages with `npm ci` and copy `.env.example` to `.env.local` for USB testing. Never copy the root `.env`: it contains backend secrets.
3. Create and install a development APK using Expo EAS:
   ```bash
   npx eas-cli@latest login
   npx eas-cli@latest build --platform android --profile development
   ```
   EAS may ask to register this app project and generate an Android signing key. Keep signing credentials private. Install the APK using the resulting link on your phone.
4. Enable Android USB debugging, connect your phone, and accept the device's authorization prompt. With Android Platform Tools installed on your computer:
   ```bash
   adb devices
   adb reverse tcp:8000 tcp:8000
   adb reverse tcp:8081 tcp:8081
   ```
   This forwards the backend and Metro ports through USB; no public backend or database port is needed. Forwarding must be reapplied after reconnecting the phone.
5. Run `npm start -- --localhost` from `mobile`. Open the installed SafePath development app and connect to `http://127.0.0.1:8081`. The development profile uses `http://127.0.0.1:8000` for the backend.
6. Try the Vijayawada Junction Railway Station → Rajiv Gandhi Park sample, compare both routes, filter place categories and open a place's details. Test both denied and granted location permission. Outside the pilot area the sample journey still works.

Alternative local native build (requires Android SDK and a compatible JDK): set `SAFEPATH_DEV_HTTP=1`, then run `npm run android -- --device`. Cloud builds do not need a local Android SDK.

## Release settings

`EXPO_PUBLIC_API_URL` is a public backend URL baked into the bundle. Set an HTTPS backend URL in EAS preview/production environment settings before making those builds. The development HTTP exemption is enabled only by `SAFEPATH_DEV_HTTP=1`. Preview and production profiles leave it off. The backend must be deployed for journeys to work away from your development computer.

City settings are imported directly from `../frontend/src/config/cities.json`. Metro watches that public configuration directory. Run EAS from this `mobile` directory within the repository so the shared file is included in the monorepo archive.

## Checks

```bash
npm run typecheck
npm run lint
npm test
SAFEPATH_DEV_HTTP=1 npm run prebuild:android
npm run export:android
```

Generated native folders and bundles are ignored. Configure native behaviour in `app.json`/`app.config.ts`, then regenerate with prebuild. Do not edit generated native files.

A successful export validates JavaScript compilation, not native map rendering, APK compilation, or device location. Those require the installed Android build and a real phone. See `docs/mobile-validation.md` at the repository root for the latest results.
