# Video orders in the existing Megamozg workboard

Status: isolated integration verified; not installed in the shared service.

The common pult owns coordination, identity and assignment. The video project
owns orders, assets, scene plans, attempts and production decisions. GPT/Codex
and Hermes remain replaceable permitted execution routes. Reading a card never
starts a model, a renderer, a paid request or a second queue.

`production.pult_link.collect` reads a single bound order using SQLite `mode=ro`
and `query_only`. Do not use `Intake` to read real production data: its constructor
creates directories, tables and migrations. The projection includes only stage
states, observation time, plan revision and a limited recorded review status.
No source brief, paths, tokens, output URLs or review notes are returned.

`video_routes.install(app, store, bindings, loader)` adds one GET endpoint beside
the existing workboard task. It reuses the real session/identity checks before
source access and after the read. Only the bound human owner is admitted in this
phase; employee and agent paths are denied. A task revision change invalidates
the link. A future trusted rebind operation must distinguish changed requirements
from routine progress, without accepting a caller-supplied source root.

`video_panel.js` is inserted into the existing workboard closure before `open`;
call `await videoPanel(t,root,generation)` before `attachmentPanel`. It uses the
existing card generation guard, so a delayed response cannot replace a new card.
There is no standalone competing web application.

The loader is a trusted dependency. Production should consume a bounded,
privately exported metadata file instead of granting the web service access to
the whole source directory. One in-flight read is allowed; after an HTTP timeout
its slot remains occupied until the actual read finishes. This prevents growing
queues of filesystem threads, but does not promise to terminate an OS I/O hang.
No scheduled exporter, shared permission change or authentication bridge is
installed by this patch. These are prerequisites to a production installation.

Recorded plan acceptance is explicitly unverified: this projection does not
rehash all current evidence or authenticate the original local reviewer. It
cannot mark a shot or film accepted. Age above 180 seconds is shown as stale;
missing, changed and unavailable sources remain distinct from a successful read.

## Verified scope

12 contract tests pass on the local workspace and server. The probe uses a copy
of the installed pult, an empty disposable state, synthetic identities, real
loopback HTTPS and Chromium at 1024/390 px. 26 assertions cover authentication,
foreign owner/staff denial, revoked sessions during reads, stale task bindings,
expired/unavailable snapshots, single-flight timeout behavior, visible card,
reload, mobile width, unchanged video DB and no model or execution jobs.

Run the probe only on an isolated stage containing `source` and a source-only
`pult` copy with the panel inserted. Never point it at production state:

```bash
python3 -m unittest production.tests.test_pult_link -v
python3 integrations/tests/probe_pult_video.py /absolute/isolated/stage
```

The probe's temporary certificate and fake login apply only to its random
loopback listener. It does not modify any deployed authentication or service.

## Next acceptance

1. Reviewed metadata export and explicit owner binding on a real task; verify
   installed-file admission manifests before changing shared pult code.
2. Protected exact-version MP4 playback/download with current task and project
   permissions, size limits, hashes, range requests and revocation. Existing
   pult attachment support for TXT/PDF/images up to 2 MiB is insufficient.
3. One CPU video order, one targeted revision, repeat login and human review.
4. Separate Grok capability qualification using the actual subscribed account;
   CLI OAuth/billing does not establish video support. Do not silently switch
   to metered API or give employees the owner's account.

The other development chat retains GPU allocation, throughput and rental code.
This branch adds files only and must not move its active PR head.
