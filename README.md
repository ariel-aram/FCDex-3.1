# FCDex 3.1 — BallsDex V3 Extra Package

Official **FCDex 3.1** feature pack for [BallsDex V3](https://github.com/Ballsdex-Team/BallsDex-DiscordBot). Packs, SBC crafting, coin shop, battles, tournaments, quests, shiny conversion, boss raids, and more — Components v2 UI.

Use `/fcdex menu` for the full command directory.

## Features

### 📦 Packs

| Command | Description |
| ------- | ----------- |
| `/pack daily` | Daily pack — coins + clubball (24h cooldown) |
| `/pack weekly` | Weekly pack — better rewards (7d cooldown) |
| `/pack mascot` | Mascot pack (7d cooldown) |

### 🛒 Shop

Buy admin-configured bundles with **Player coin balance** (BallsDex V3 economy).

| Command | Description |
| ------- | ----------- |
| `/fcdex shop` | Browse bundles · purchase via select menu |
| `/shop browse` | Same shop panel (standalone group) |
| `/fcdex shop-admin` | Create bundles, add items, enable/disable (Manage Server) |

Configure bundles in the admin panel under **FCDex 3.1 → Shop bundles**.

### 🧪 Craft (SBC)

Squad Building Challenges — no tickets needed. Configure recipes in admin.

| Command | Description |
| ------- | ----------- |
| `/craft menu` | List active SBC recipes |
| `/craft complete name:<SBC>` | Submit required clubballs and claim the reward |

### ⚔️ Battles

| Command | Description |
| ------- | ----------- |
| `/battle challenge @user` | Lineup panel (max 5) — **Random 5**, Strongest, Lock |
| `/battle random @user` | Instant random 5v5 (no panel) |
| `/battle all @user` | Uses **every** clubball you own · `skip_commentary:true` for quick results |
| `/battle card` | Add/remove a card from your active lineup |

### 🏟️ Tournaments

Legacy & Main groups · grand final is **Legacy vs Main** semifinal winners.

| Command | Description |
| ------- | ----------- |
| `/tournament view` | Hub — join, leave (while registration open), standings, bracket |
| `/tournament start` | Open group stage (Manage Server) |
| `/tournament match` | Pending matches · **Start battle** · claim |
| `/tournament bet` | Wager on match outcomes |

### ✨ Merge · 🏅 Achievements · 📊 Rarity · 🏆 Leaderboard

- **Merge** — 7-tier forge, same clubball only (`/merge`)
- **Achievements** — `/achievement menu`
- **Rarity** — live dex spawn weights (`/fcdex rarity`)
- **Leaderboard** — server vs global (`/fcdex leaderboard`)

### 📋 List regime · 👑 Boss · ✨ Shiny · 📜 Quests

| Command | Description |
| ------- | ----------- |
| `/fcdex list regime:<key>` | Clubballs by regime (UCL, Premier League, etc.) |
| `/fcdex boss` | Raid boss with your top 5 clubballs |
| `/fcdex shiny clubball:<card>` | 2 copies → 1 shiny (+25% ATK/HP) |
| `/fcdex quests` | Daily quest progress |
| `/fcdex quest claim:<key>` | Claim quest coins |

### 🛡️ Admin

| Command | Description |
| ------- | ----------- |
| `/fcdex owners clubball:<card>` | Who owns a rare card (Manage Server) |
| `/fcdex shop-admin` | Manage coin shop bundles (Manage Server) |

Configure **SBC recipes**, **shop bundles**, achievements, and tournaments in the admin panel under **FCDex 3.1**.

## Installation

```toml
[[ballsdex.packages]]
location = "git+https://github.com/ariel-aram/FCDex-3.0.git@2.1.0"
path = "fcdex_3_1"
enabled = true
```

```bash
docker compose build && docker compose up -d
```

### Upgrading from FCDex 3.0 (`fcdex_3_0`)

- Change `path` to **`fcdex_3_1`** and pin **`@2.1.0`** (see snippet above).
- Rebuild/restart so migrations run through **`0009`** (shop bundles).
- The Django app **label stays `fcdex_3_0`** for database compatibility — no `django_migrations` rename needed.
- Existing tournament/achievement/pack data is preserved.

### Fresh installs

Use `path = "fcdex_3_1"` as shown. Economy uses core `bd_models.Player` (`money`, `add_money`, `remove_money`).

## Requirements

- BallsDex **V3** (3.0.0+)
- Python **3.12+**
- Core **`players`** package loaded (coin balance — default in BallsDex V3)

## License

MIT
