## 2.2.3

- Fix boss admin on **servers** — raids now keyed by **channel id** (not stale guild snapshot); every button/modal re-reads live interaction context
- Remove "Boss admin requires a server" permanently; DMs still supported
- Boss admin: **Start by PK / name** + optional **reward clubball** field
- Shop/craft admin modals preserve navigation after submit (no more `channel_id=0` back button bug)
- Craft/shop modals stay within Discord’s 5-field limit; craft uses PK/country resolution
- Tournament bets use `remove_money` instead of invalid `add_money(-n)`
- Async-safe owner lookup and bet payout resolution

Install: `path = "fcdex_3_1"` · pin `@2.2.3`
