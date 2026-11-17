# Bound GPU shots

The local review page can prepare one five-second T2V scene from the current
accepted plan. It never rents a Pod or authorizes spending. References, character
identity, source editing and unresolved plan questions are rejected by this
recipe rather than silently discarded. All files remain in the order root.

A trusted operator supplies an existing exclusive lease, its live independent
guard, protected Runpod credential and a per-shot JSON grant:

```json
{
  "approved": true,
  "request_sha256": "prepared request digest",
  "lease_sha256": "canonical production.core.object_digest of lease",
  "endpoint": "http://127.0.0.1:8188",
  "max_runtime_seconds": 300,
  "budget_usd": 0.5
}
```

The endpoint must be the operator-established tunnel to this exclusive rental.
The endpoint-to-Pod mapping is a trusted operator responsibility, not proven by
the grant hash. Runtime and budget must fit the original rental, including the
separate rental cleanup reserve. The public HTTP handler cannot submit grants.

```bash
python -m production.shots --root /path/to/intake \
  --order-id ORDER_UUID --request-id SHOT_UUID \
  --grant /private/shot-grant.json --lease /private/lease.json \
  --guard-root /private/guard --credential-file /private/runpod.key \
  --execute-authorized
```

Do not run without the verified recipe models, pinned ComfyUI runtime, and an
independent live rental guard. The CLI checks the current accepted plan before
submission, during polling and before publishing. It records exact workflow,
grant and lease hashes before submission. A durable attempt lock and existing
Executor receipt prevent automatic duplicate POSTs. Unknown outcomes require
reconciliation. A completed request reuses verified media without another GPU
submission. A changed request needs a new request ID and explicit grant.

On completion or execution failure the CLI invokes ownership-checked rental
cleanup. The independent guard remains the backstop if the process dies. Host or
network loss can still prevent provider cleanup; this is not a hard billing cap.
Inspect rental-cleanup.json for confirmed provider absence, independently from
result.json. A generated file is not proof that billing stopped.

The local window exposes verified media only while its accepted plan remains
current. Acceptance requires all five explicit quality checks and the exact
output hash. A shot decision never sets finished_video_accepted. The local
reviewer is not an authenticated external client; no public access is enabled.

Qualification: six new controller tests, 123 passing production tests, and
Chromium playback/quality/revocation checks on a clearly synthetic clip. The
separate real H100 pilot proves recipe execution but failed object geometry.
The order binding subsequently passed a real H100/AP-IN-1 run: exact prepared order, verified weights, guarded submission, download, full decode, browser playback, confirmed Pod deletion and reuse without another submission. Artistic acceptance remains pending. See qualification/bound-live-20261117.json.


## Editable scene preview

`python -m production.shot_edit --root INTAKE --order-id ORDER --request-id SHOT --output NEW_EDIT_FOLDER` copies the verified original, builds a manifest, renders a review copy and writes an editable OpenTimelineIO timeline. The original GPU output is preserved. Reuse checks source, manifest and render hashes. These single-scene previews cannot be released as finished films. The on-server timeline references the control host. Add `--package` to create a portable ZIP with relative timeline links, unchanged source assets, a rendered preview and integrity checks. It remains an unreleased single-scene preview.

The operator qualification runner prepares an existing guarded Pod and invokes the bound shot: `python -m production.qualification.bound_pilot_runner --help`. It does not allocate a Pod. The transfer allowance is derived from the original lease with inference and cleanup reserve. The first 64 MiB estimate is conservative, not a throughput guarantee; final full-file SHA checks remain mandatory. Stop the dedicated guard service after confirmed Pod deletion if it is still watching.
