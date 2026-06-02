from fcdex_3_1.fcdex_ext.boss_raid import raid_scope_id


def test_raid_scope_uses_guild_id_in_servers():
    assert raid_scope_id(999, 12345) == 999


def test_raid_scope_uses_channel_id_in_dm():
    assert raid_scope_id(None, 67890) == 67890
