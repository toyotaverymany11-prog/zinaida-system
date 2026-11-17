# First-frame generation qualification

This route extends the same reviewed-order and guarded-allocation lifecycle.
It is not video editing, face replacement, body replacement or artistic acceptance.

## Preparation

`prepare_shot` accepts the usual exact request fields plus `image_asset_id`.
The approved `new_video` order must contain exactly that one static reference
and no character images. Unresolved plan questions and source-video scenes
remain blocked. The initial pinned recipe requires the 1280:704 aspect ratio;
it never silently crops a different composition.

Preparation verifies the uploaded asset digest, applies EXIF orientation,
converts to RGB PNG without cropping, and records both source and derived SHA.
The PNG filename is its SHA. Prepared request reuse checks the existing bytes;
a corrupted derivative is not silently regenerated. The official graph binds
that filename, prompt and both noise seeds to the saved workflow hash.

## Execution and review

The canonical request and approved plan are checked before allocation. The
operator runner transfers only the exact PNG into ComfyUI's input directory
and verifies the remote SHA before inference. Account credentials remain on
the controller. Allocation uses the existing single-create journal, original
absolute deadline and independent cleanup watcher.

Output delivery rechecks the source order and prepared PNG. A quality decision
must explicitly include `first_frame_match` in addition to the five existing
criteria. Even an accepted scene does not release a finished film. Reference
identity preservation needs separate qualification and is not inferred from
a successful simple-object test.

## Evidence

The upstream workflow is pinned in `workflows/ltx25-i2v.lock.json`. CPU export
verified all 50 upstream node types; the executable graph retains 45 ancestors
of SaveVideo after removing the optional prompt enhancer. It reuses the five
verified model files, with no partner API nodes.

The static-reference regression test checks actual image pixels, source-file
delivery and corrupt-input rejection. Shot tests cover exact asset binding,
implicit-crop refusal, repeat preparation and the extra quality requirement.
Live GPU outcome is recorded in `qualification/i2v-live-20261117.json`: one
121-frame 1280x704 clip, full browser playback, exact reference visible,
editable project, confirmed Pod absence and repeat without cloud construction.
First-frame SSIM was 0.990795; this measures decoded-pixel similarity only.
Five sampled frames preserved the cube, table and window with forward camera
movement. Audio semantics, faces and final artistic quality remain unqualified.
