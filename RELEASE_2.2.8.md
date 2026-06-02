## 2.2.8

- Fix boss raid **0 damage** when players used `/fcdex boss` in a different channel than the announcement — raids are **guild-wide** in servers again (one active raid per server); DMs still use the DM channel id
- `AdminContext.scope_id` now uses `raid_scope_id()` so every button/modal reads the same scope as live interactions
- Join during **pick** phase (late registration before locking a card)
- **Resolve** explains zero damage (no joins, no locked cards, defend round, missing instances)
- **Defend round** labelled clearly in admin + resolve (flavour only — no boss HP loss)
- Player panel shows locked card id; server/DM scope hints in empty-state copy
- Announcement **Join** button falls back to live interaction scope

Install: `path = "fcdex_3_1"` · pin `@2.2.8`
