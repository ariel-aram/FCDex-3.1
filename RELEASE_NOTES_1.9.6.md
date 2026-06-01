## Tournament match flow

- **`/tournament start`** — open group stage with Manage Server (creates round-robin matches).
- **Start group stage** button on `/tournament view` and `/tournament match` for admins while registration is open and requirements are met.
- **Single-group starts** — only groups with ≥2 players get matches; empty Legacy no longer blocks Main-only tournaments.
- **Clearer messaging** — registration hub explains per-group minimums and start paths.

## Install

```toml
fcdex-3-0 = { git = "https://github.com/ariel-aram/FCDex-3.0.git", tag = "1.9.6" }
```
