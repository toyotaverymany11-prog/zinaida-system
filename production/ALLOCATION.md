# Bounded allocation and one prepared job

Only a trusted server operator invokes these modules. There is no billable HTTP route.
`allocation.json` binds a unique zina-video UUID name, pinned image, one compute type,
temporary disk, exact region and original absolute deadline to an approved dollar budget.
Check current catalog pricing/availability before preparing it. The hourly figure is a
conservative bound, not a provider-enforced price cap; mismatched or overpriced resources
are immediately torn down. No queued creation, persistent volumes or hardware fallback.

Start `launch_allocation` and observe `watcher_ready` before `allocate_once`. The supervisor
is independent of the caller and starts before the POST. A durable create intent permits
at most one POST, including after lost replies and process crashes. The watcher paginates
the provider list by exact unique name, binds ID/name/provider timestamp, then delegates
to the existing independent lease guard. The original deadline is not renewed.
A crash between the intent write and POST can remain unresolved rather than double-rent.
Absent results after bounded reconciliation remain unknown, never permission to resubmit.
Host/network failure or a resource appearing after the finite reconciliation window still
requires operator reconciliation; this is not a provider-side hard spending cap.

`production.guarded_job` takes root, bundle, intake, request-file, credential and ssh-key.
Prepare scoped per-file model URLs and the pinned runtime bundle before invoking it.
The intent must include the exact prepared request_sha256. The entrypoint checks the
current accepted plan and prerequisites, arms allocation, creates once, waits for the
live resource guard and invokes the existing bounded GPU runner. It then creates the
editable scene and portable review package. No result is marked artistically accepted.
A repeated completed request verifies the result and package without touching the cloud.
The finally block signals the independent allocation watcher to reconcile and clean up.

Qualification 2026-11-17: a real CPU3c 2-vCPU Pod in EU-RO-1 at observed $0.06/hour
was created with a deliberately lost response. A second caller did not repeat POST.
The original caller exited; independent monitoring found the Pod and deleted it at the
original approximately 90-second deadline, with one DELETE and confirmed absence.
Resource tgm48jjc30xb3o, evidence allocation-live-stage36. This validates lifecycle,
not GPU inference. Complete automatic GPU qualification is tracked separately.

Official contract checked: https://api.runpod.io/v2/openapi.json (2026-11-17).
GET /v2/pods uses cursor pagination. POST returns 201 with a Pod; 202 is queued creation
only with queue, which this allocator disallows. The documented retry suggestion for 5xx
is intentionally not used for ambiguous mutations; local reconciliation prevents duplicates.
