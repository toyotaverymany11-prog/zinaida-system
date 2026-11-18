# Owner film draft preview

Owners can view an existing film while candidate quality review remains pending.
Imported films are separate immutable artifacts, never relabeled shot revisions.
Existing candidate catalog, video, project and quality acceptance remain unchanged.

The web integration needs owner_imported_draft_preview=true; the trusted producer
order maps owner_imported_drafts artifact IDs to private manifest paths. Browser
input cannot configure file paths or opt itself in. Registration uses
video_imported_draft.py with explicit source SHA, duration, project and provenance.
It checks the actual current task/active owner binding read-only, verifies the
media and writes a root-private immutable copy; DB and configuration stay unchanged.

Separate /video/imported-drafts catalog and video routes require the real owner
session before and after reads. No employee, agent or different owner may use
them. Responses bind current task, artifact ID and exact bytes and always say
draft, ready_for_owner=false, finished_video_accepted=false and publication=false.
Files and manifest are rechecked after reading; range responses support inline
playback and use private/no-store caching.

owner-imported-ui.patch adds a labeled inline player to the existing videoPanel.
Apply only after comparing its live baseline; preserve existing polling/playback
guards and the application video hook. A candidate QA error must not hide the
separate imported preview. Its player uses controls, playsInline and metadata preload.

The new tests use real session-check logic and synthetic SQLite/media fixtures.
They prove authentication, source and byte guards, not an actual owner login,
physical iPad playback or artistic approval. No renderer, model, rent or publication
is triggered by this feature.
