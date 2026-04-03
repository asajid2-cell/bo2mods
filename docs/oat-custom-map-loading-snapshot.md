# OAT Custom Map Loading Snapshot

This branch preserves the OpenAssetTools custom-map loading state that could not
be pushed directly to the upstream OAT remote.

- Local OAT repo: `z:\Games\pluto_t6_full_game\_external\OpenAssetTools-src`
- Local branch: `snapshot/t6-custom-map-loading-20260403`
- Local commit: `c4829ab67bf2741e67af91b5e2f37288f3e4a0e8`
- Upstream remote: `https://github.com/Laupetin/OpenAssetTools.git`
- Push result: denied with `403` for user `asajid2-cell`

The exact committed OAT delta is exported here:

- `docs/oat-t6-custom-map-loading-snapshot.patch`

That patch can be applied onto the matching OAT base to recreate the exact
loader-side snapshot that existed when this branch was pushed.
