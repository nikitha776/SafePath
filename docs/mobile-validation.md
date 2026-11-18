# Mobile prototype validation — 2026-10-22

Project: `mobile/`, Expo SDK 58 / React Native 0.88 / MapLibre React Native 11.5. Android is the first device target. Vijayawada is loaded from the shared public city configuration.

## Passed

- TypeScript (`npm run typecheck`).
- Expo lint (`npm run lint`).
- Five automated tests: disconnected-route bounds; backend request payload with no provider credentials; provider error messages; aborting obsolete fetches; useful network-error handling.
- Expo Doctor: **20/20 checks passed**.
- `SAFEPATH_DEV_HTTP=1 npm run prebuild:android`: generated native Android project with MapLibre and foreground location configuration.
- `npm run export:android`: Metro compiled the Android Hermes JavaScript bundle.
- Existing Vijayawada API previously verified through the running web app: location search, two walking routes, route-corridor places, and 503 cached OSM roads. The local OSM sample contains no mapped lamp nodes; missing lighting is unknown.

## Pending / limitations

- APK compilation and installation: local Android SDK/platform tools/JDK were not found. Expo device sign-in completed. The app is linked to `@nikitha776/safepath-mobile` (project `d659c522-2e55-4621-ac56-2e97d6a73661`). Android signing credentials were created remotely and the development build was uploaded. Build `a41935b9-b628-40ab-9695-34f81b60a1b8` is in progress.
- No native runtime/device claim: the map, taps, actual location permissions, denied permissions, USB connectivity, app resume and device performance still need validation on the installed APK. JavaScript export and prebuild do not verify those behaviours.
- Backend runs locally. The development APK needs USB port forwarding to reach it. An HTTPS backend deployment is needed for use away from the computer.
- `npm audit` reports 20 high-severity entries, propagated mainly from the upstream `braces` and `node-forge` advisories through Expo/Metro. A compatible `npm audit fix` was attempted; these remain. Its suggested forced fix downgrades Expo to SDK 44 and was not applied. Recheck upstream patches before a production release. Expo Doctor's compatibility check does not replace a security audit.
- Background tracking, SOS, trusted-contact sharing, turn-by-turn instructions and route safety scoring are not implemented in this first mobile milestone.

## Phone acceptance checks

1. Install the development APK; start Metro and forward ports 8000/8081 over USB.
2. Verify Vijayawada dark map and attribution, then search two precise local places.
3. Compare both sample routes; ensure selection changes the highlighted geometry and places.
4. Open a small place marker and a list row. Verify name, category colour, address, scheduled-hours uncertainty and distance.
5. Toggle categories. Change the selected route rapidly and edit an endpoint while loading; stale results must disappear.
6. Deny location permission, then grant it. Manual search must remain available; no background permission should be requested. Outside Vijayawada, explain pilot coverage and retain manual journey planning.
7. Disconnect the backend: show an actionable error without hiding all app controls. Restore it and retry.
