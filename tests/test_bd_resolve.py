from __future__ import annotations

import pytest

from fcdex_3_1.fcdex_ext.bd_resolve import _normalize_token


@pytest.mark.parametrize(("raw", "expected"), [("42", "42"), ("#42", "42"), ("  #99 ", "99"), ("Brazil", "Brazil")])
def test_normalize_token(raw: str, expected: str) -> None:
    assert _normalize_token(raw) == expected
