# FCDex 3.0 — BallsDex V3 Extra Package

Official **FCDex 3.0** feature pack for [BallsDex V3](https://github.com/Ballsdex-Team/BallsDex-DiscordBot). Adds tournaments, clubball battles, achievements, and merging — built as a pip-installable Django extra with Discord.py Components v2 UI.

## Features

### ⚔️ Battle System

Challenge friends to clubball matches. Pick lineups from the match panel, lock in, and watch live commentary.

| Command | Description |
| ------- | ----------- |
| `/battle challenge @user` | Start a match (Components v2 panel) |
| `/battle card` | Add or remove a specific clubball from your lineup |

Lineup buttons on the match panel: **Random**, **Strongest**, **Clear**, **Lock Selection**, **Cancel Match**.

### 🏟️ Tournaments

Legacy & Main group tournaments with battle-verified matches, bounties, betting, and bracket progression.

Points are earned only from verified match wins (**+3** each). Hosts advance rounds once all bracket matches are complete.

Registration stays open until the host **starts group stage** in `/tournament manage` (or scheduled end passes) — a passed scheduled start does not close signup.

| Command | Description |
| ------- | ----------- |
| `/tournament manage` | Ephemeral admin hub — create, edit, host, bounty vault, delete, announce |
| `/tournament view` | Player hub — overview (rules & betting), standings, bracket, join |
| `/tournament match` | Pending matches — **Start battle**, verify win, claim bounties |
| `/tournament bet` | Wager coins on a match participant |

### 📊 Rarity system

Live **BallsDex spawn weights** from the dex bot (`Ball.rarity` / balls cache). Lower value = rarer.

| Command | Description |
| ------- | ----------- |
| `/fcdex rarity` | Hub — spawnable overview, distribution, browse tabs |
| `/fcdex rarity clubball:<card>` | Look up one clubball's spawn weight and stats |
| `/fcdex rarity rarity:<value>` | All spawnable clubballs at spawn weight **value** |

Categories: **Spawnable** (enabled in dex) and **Unspawnable** (disabled).

Use `/fcdex menu` for a single hub listing every FCDex command group.

### 🏅 Achievements

Player achievements with progress tracking and claimable rewards (coins / clubballs).

| Command | Description |
| ------- | ----------- |
| `/achievement menu` | Hub — catalog, progress, claim |

Configure achievements in the **admin panel** under FCDex 3.0.

### 🏆 Leaderboard

Feel like **#1 on your server**, then flip to **Global** for the reality check.

| Command | Description |
| ------- | ----------- |
| `/fcdex leaderboard` | Paginated rankings — **This server** (clubballs caught here) or **Global** |
| `/fcdex leaderboard sort:<metric>` | Rank by clubballs, battles won, merges, or tournament wins (global stats) |
| `/fcdex leaderboard top:20` | Show top 10 (default) or top 20 |

Server scope ranks **clubballs caught in that Discord server** only. Global scope adds FCDex stats from `PlayerStats`. In DMs, rankings are always global.

### ✨ Merge forge

Sacrifice **matching clubballs** through **7 forge tiers** to craft a **FCDex Merge** special (custom background from the extra’s merge card art). Every input must be the **same clubball type** — the result keeps that club.

| Level | Inputs | Result stats |
| ----- | ------ | ------------ |
| **1** | 10× common (same club) | +15% ATK / +15% HP |
| **2** | 8× forge L1 | +35% / +35% |
| **3** | 6× forge L2 | +60% / +60% |
| **4** | 5× forge L3 | +90% / +90% |
| **5** | 4× forge L4 | +125% / +125% |
| **6** | 3× forge L5 | +165% / +165% |
| **7** | 2× forge L6 | +210% / +210% |

**Level 1** only accepts plain **common** copies (lowest spawn rarity). Higher tiers consume the previous forge level of the same club. **Level 7** is max tier and cannot be merged again. Legacy pre-1.9 merge cards cannot be used in the tiered forge.

**Limits:** **5 merges per player per calendar week** (resets Monday).

| Command | Description |
| ------- | ----------- |
| `/fcdex menu` | Directory of all FCDex 3.0 features |
| `/merge` | Pick 2–10 matching clubballs (count sets tier) → confirm → forged card |

On install, the extra **creates or repairs** the merge special in your database and reloads the BallsDex cache automatically.

## Installation

This package uses the [BallsDex V3 extras system](https://wiki.ballsdex.com/dev/custom-package/).

### 1 — Configure `extra.toml`

Add to `config/extra.toml` in your BallsDex directory:

```toml
[[ballsdex.packages]]
location = "git+https://github.com/ariel-aram/FCDex-3.0.git@1.9.4"
path = "fcdex_3_0"
enabled = true
```

**Local development** (with Docker):

```toml
[[ballsdex.packages]]
location = "/code/extra/FCDex-3.0"
path = "fcdex_3_0"
enabled = true
editable = true
```

### 2 — Rebuild and migrate

```bash
docker compose build
docker compose up -d
```

Migrations run automatically via the migration service.

Apply through **`0007`** if upgrading from an earlier 1.8.x install (merge log tier fields).

### 3 — Configure achievements (optional)

Open the admin panel and create `Achievement` entries under **FCDex 3.0**. Set type, required count, and rewards.

## Requirements

- BallsDex **V3** (3.0.0+) — must already be installed; this extra does not pull `ballsdex` from PyPI
- Python **3.12+**

## Development

```bash
python -m pip install -e ".[dev]"
python -m ruff check fcdex_3_0 tests
python -m ruff format fcdex_3_0 tests
python -m pytest tests -q
python -m pyright fcdex_3_0
```

## License

MIT — credits to the original BallsDex authors must not be removed when distributing.
