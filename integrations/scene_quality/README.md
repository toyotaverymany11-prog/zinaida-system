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

Tests: `python -m unittest discover -s integrations/scene_quality/tests -v`.
They check consequential failures: stale reviews, self-approval, missing actual
modalities, critical findings hidden by a passing verdict, and replacement of
the frozen source audio. They are not a live critic evaluation.

The graph data derives from the existing MIT Comfy-Org workflow pinned in
`workflows/ltx25-i2v.lock.json`. Model weights and runtime retain their separate
licenses. The Lightricks A2V graph was inspected as a reference; its full source
is not redistributed here. No new weights, GPU or external service is implied
by installing this package. Publication remains disabled.
