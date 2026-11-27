# Installation acceptance — 0.2.1 preview
No hardware acceptance is claimed. Use a disposable test project only.
- [ ] Exact-head CI unit tests and AMD64/ARM64 image smoke pass.
- [ ] Add repository to Home Assistant store and confirm app appears.
- [ ] Install on HAOS ARM64, start and open Ingress without a standalone token.
- [ ] Create two test projects; add a Cyrillic record; verify search and project isolation.
- [ ] Restart app; confirm data persists; test HA backup and restore on disposable data.
- [ ] Verify no host port exposed, no privileged permissions, and direct non-Supervisor requests denied.
- [ ] Observe RSS/container memory and swap before/after idle and search; target 256 MiB or less, not yet measured.
- [ ] Confirm stop/restart; collect only redacted logs, HAOS version and tested commit.
- [ ] Record tested SHA, date and source. CI is not evidence of physical acceptance.
Do not expose a preview to the public internet. Remote agent access is a separate milestone.
