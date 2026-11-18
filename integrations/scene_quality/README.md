# Scene quality development

Isolated implementation of the producer/director and audio-driven scene work in
`Hermes_Video_Direction.md` (VD01-VD30). It does not replace the existing Intake,
the shared pult, or the active PR2 writer.

`contracts.py` validates explicit scene decisions, exact cast and voice bindings,
versioned review evidence and bounded corrective tasks. These structural checks
do not measure dramatic quality. A text-only or uncalibrated reviewer cannot
grant readiness to show an owner. Technical decode success is insufficient.

`workflow.py` adapts the pinned I2V Comfy graph to frozen-audio generation. Both
sampler stages receive the original audio latent with a zero noise mask. The
output uses the original trimmed waveform instead of generated speech. At this
commit the graph is prepared but has not passed a GPU or audiovisual quality test.

`model_client.py` uses only the existing Z.AI Coding Plan endpoint. It journals a
request before submission and never automatically repeats an unknown outcome.
The first producer request timed out; the route is not qualified by that attempt.
No secret is stored in this repository.

`preflight.py` adds conservative cold-start timing before the trial runner can
allocate a disposable GPU. It includes all pinned weight bytes, measured transfer
rate, bootstrap, inference, review and cleanup within the original aggregate
grant. It never renews an expired grant. A current `cold-start-plan.json` is now
required; a missing or infeasible plan prevents POST.

`supervisor.py` makes an immutable copy of the exact movie, decodes every frame,
preserves the owner's rejection and builds an internal review job. Its delivery
guard checks the current SHA again. Trusted runner receipts bind model revision,
perception capabilities and actual coverage separately from model-written
findings. Corrections name the source SHA, stage, interval and recheck condition.
New versions require fresh reviews and have a two-round lineage limit.

The live owner-rejected bouquet film is an integration control, never a new
delivery. No calibrated audiovisual reviewer is registered by this package.
The review path therefore remains closed for real films until that reviewer
is qualified. Simulated passing capabilities occur only in unit-test fixtures.
The pult's private producer now calls `release.guard` before cataloguing or
reading a movie or project and again after loading its bytes. A missing quality
job is closed by default. Internal files remain available to the private reviewer;
they are not exposed as finished owner candidates. This does not intercept
unrelated legacy writers or grant public-service deployment by itself.

`qualification.py` measures held-out controls separately for casting, story,
camera, editing, speech, sound, anatomy and brand. Related source variants cannot
cross development/holdout splits. Missing responses count as abstentions. A
critical false pass cannot be averaged away. Counts and95%Wilson upper bounds
remain visible: a tiny green test set is not a broad reliability guarantee.

`release.py` binds the exact movie and project to the current physical reference
files, casting manifest, camera rules and creative context before independent
review. Reference copies are frozen in the review job. The release check
recomputes calibration, checks its date and route, validates actual coverage,
re-reads the owner's rejection ledger and rejects mutated evidence. CLI guards
exit3 when delivery is not permitted, so shell callers cannot interpret a JSON
denial as success. A candidate is never publication permission or owner approval.

Private producer configuration may set `quality_root` and `quality_ledger` for
each order. Defaults are `ROOT/quality` and its `owner-rejections.json`. These
paths are administrator configuration; browser input cannot choose them.
Policy and calibration files must be supplied by the trusted runner, not copied
from a model-written answer. No live reviewer is qualified merely by installation.

Lifecycle, with real reference/cast files and a structurally validated plan:

```bash
python -m integrations.scene_quality.supervisor prepare --job QUALITY/VIDEO_SHA --video MOVIE --ledger LEDGER
python -m integrations.scene_quality.release bind --root QUALITY --video MOVIE --project PROJECT --context PLAN --ledger LEDGER
# An independently qualified runner then records exact inputs, execution and findings.
python -m integrations.scene_quality.release guard --root QUALITY --video MOVIE --project PROJECT --ledger LEDGER
```

`intake_app.py` preserves the existing Intake HTTP interface and CPU controller.
Its pinned compatibility read model binds preparation receipts to the stored
order before derived analysis/status fields are added. A changed backend requires
requalification. It does not edit the peer PR2 source, bypass its token or create
a separate queue. Launch an isolated operator instance with
`python -m integrations.scene_quality.intake_app --root ORDER_ROOT --port PORT`.
The normal UI template must be present in that source checkout; the read-only
pult adapter distribution intentionally omits it. The browser qualification uses
synthetic media and never proves artistic acceptance or authorizes generation.

The Grok subscription client now sends an explicit reasoning effort, defaulting
to `low` for finite service tasks. Provider documentation states that omitting it
defaults to `high`. Effort is part of request identity; a timed-out older request
is never silently resubmitted. Receipts record actual response model IDs,
fingerprints and timing. Raw reasoning is not treated as an editorial verdict.

`vimax_bridge.py` reuses the installed ViMax shot schema while preserving an
explicit sidecar for canonical cast, exact 9:16 geometry and frozen source
speech. The stock text-audio interface fails the executor preflight; a schema
conversion never silently authorizes generation. The first bundle remains an
internal one-shot proposal. Its framing and audio-driven executor are not live
qualified. Review of 124 upstream materials is documented in the research report.

Tests: `python -m unittest discover -s integrations/scene_quality/tests -v`.
They check consequential failures: stale reviews, self-approval, missing actual
modalities, critical findings hidden by a passing verdict, and replacement of
the frozen source audio. They are not a live critic evaluation.

The graph data derives from the existing MIT Comfy-Org workflow pinned in
`workflows/ltx25-i2v.lock.json`. Model weights and runtime retain their separate
licenses. The Lightricks A2V graph was inspected as a reference; its full source
is not redistributed here. No new weights, GPU or external service is implied
by installing this package. Publication remains disabled.
