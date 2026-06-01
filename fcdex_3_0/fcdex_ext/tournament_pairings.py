from __future__ import annotations

import itertools


def planned_group_stage_match_count(*group_sizes: int) -> int:
    """Round-robin match count per group with at least two players."""
    total = 0
    for size in group_sizes:
        if size >= 2:
            total += len(list(itertools.combinations(range(size), 2)))
    return total
