# Limitations

Honest constraints of the current Creo integration (per instruction §0 — no
fabricated behavior):

## Requires a licensed Creo host
- The Java bridge's real extraction path (`CreoSession.extract`) is **not yet
  implemented** — the scaffold verifies environment variables and toolkit jars but
  does not yet open a Creo session. Implement it against the locally installed
  Object TOOLKIT Java API (see `creo-bridge/.../CreoSession.java` placeholder).
- Until then every conversion runs through the **mock sample** (synthetic motor);
  the conversion report lists this under `missingDependencies`.

## Tessellation fidelity
- Mock geometry is procedural cylinders/boxes. Real Creo extraction must use the
  toolkit's mesh/tessellation API; chord-height/angle quality settings exist only
  conceptually until the real bridge lands.

## Mechanisms / constraints
- Imported mechanisms map to joints with `requiresReview: true` and a confidence
  score — axes/limits are best-effort from metadata, not solver-grade kinematics.
  Review them in the Mechanism dock before animating.

## Exploded states
- Only per-occurrence linear offsets (`direction`/`distance`) are preserved;
  rotate-explode and per-stage camera moves from Creo are not modeled yet.

## Materials
- Alias table covers common steels/copper/aluminum/brass; unknown names fall back
  to a generic gray and are listed in the report's `missingDependencies`. Placeholder
  materials (`-x-`, `PTC_SYSTEM_MTRL_PROPS`) abort resolution deliberately.

## Security scope
- The FastAPI backend is a **local tool** (open CORS, no auth). Do not expose it to
  untrusted networks without adding authentication and tightening CORS origins.

## Units
- The canonical schema normalizes source→runtime units once; mock mode is mm→mm.
  The real bridge must report `sourceLength` correctly for inch-based models.
