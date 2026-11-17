# Video production in Megamozg

Status: owner route installed and verified at the public pult on17November2026.
Read DEPLOYMENT.md for exact files, limits, rollout, rollback and evidence.

The pult owns identity, assignments and tasks. Video production owns source
materials, scene versions, render attempts and artistic review. The web process
has no access to source directories: a private Unix producer returns current
metadata or verified immutable media. Each request runs in one bounded child;
only the pult OS UID can connect. Web authorization is rechecked after reads.

Supported: bound order status, plan revision, exact-version video playback and
byte-range delivery, editable ZIP download, owner or currently assigned human
employee, revoked assignment/session/task-version rejection. Media access never
renders or starts a model. Task revision changes deliberately require a reviewed
rebind. This does not automatically approve a scene or a finished film.

Grok subscription generation is separately qualified by one actual OAuth request
and verified MP4. grok_subscription.py is an operator-only no-repeat wrapper;
API-key fallback and durable public storage are absent. Employee account use
and automatic inference from the card are not enabled by this qualification.

Evidence:32 contract tests locally/server;44 isolated real HTTPS/Chromium checks;
3 additional Grok no-repeat/auth tests. Public browser: standard login, same card
after reload, actual3-second CPU revision played to ended=true, ZIP SHA matched.
Physical iPad and a real employee account remain independent acceptance work.

Before edits read /opt/zinaida/coordination/README.md and registry.json. PR2 owns
GPU, allocation, scene edits and packages. This branch owns the portal adapter.
Do not move PR2 or restart Hermes. The common entry point and workboard script
were changed only after recorded reconciliation and backups. The original49
admission pins and model flags passed unchanged. No background developer runs;
the enabled read-only producer is an ordinary bounded-operation service.
