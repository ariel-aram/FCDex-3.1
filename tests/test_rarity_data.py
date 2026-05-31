from __future__ import annotations

from fcdex_3_0.fcdex_ext.rarity_data import (
    RarityCategory,
    entries_for_category,
    entries_for_tier,
    normalize_rarity_name,
    obtainable_tiers,
    resolve_entry,
)


def test_obtainable_count_matches_official_list():
    rows = entries_for_category(RarityCategory.OBTAINABLE)
    assert len(rows) == 101


def test_tier_one_is_rarest_obtainable():
    tier_one = entries_for_tier(1)
    names = {row.name for row in tier_one}
    assert names == {"Team Shaolin", "Team Hurakan"}


def test_icon_pele_weight():
    entry = resolve_entry("Pele")
    assert entry is not None
    assert entry.category == RarityCategory.ICON
    assert entry.tier == 1
    assert entry.weight == 0.001


def test_goat_icon_messi():
    entry = resolve_entry("Lionel Messi")
    assert entry is not None
    assert entry.category == RarityCategory.GOAT_ICON


def test_eid_custom_weight():
    entry = resolve_entry("Nash X")
    assert entry is not None
    assert entry.category == RarityCategory.EID
    assert entry.weight == 0.05


def test_normalize_matches_punctuation():
    assert normalize_rarity_name("FC Barcelona") == normalize_rarity_name("fc barcelona")


def test_obtainable_tiers_span():
    tiers = obtainable_tiers()
    assert tiers[0] == 1
    assert tiers[-1] == 91
    assert len(tiers) >= 20
