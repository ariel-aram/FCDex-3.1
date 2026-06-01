## FCDex 3.1 (2.0.0)

Major release — rebrand from FCDex 3.0 to **FCDex 3.1** with new systems:

- **Packs** — `/pack daily`, `/pack weekly`, `/pack mascot`
- **Craft (SBC)** — `/craft menu`, `/craft complete` (configure recipes in admin)
- **Battles** — `/battle random` (instant 5v5), `/battle all` (full roster, skip commentary)
- **List regime** — `/fcdex list regime:<key>`
- **Admin owners** — `/fcdex owners clubball:<card>`
- **Boss** — `/fcdex boss`
- **Shiny** — `/fcdex shiny`
- **Daily quests** — `/fcdex quests`, `/fcdex quest claim`
- **Tournament bet** (existing), **leave tournament** (existing), **Legacy vs Main** final (existing)

Run migration **0008** after upgrade.

```toml
[[ballsdex.packages]]
location = "git+https://github.com/ariel-aram/FCDex-3.0.git@2.0.0"
path = "fcdex_3_1"
enabled = true
```
