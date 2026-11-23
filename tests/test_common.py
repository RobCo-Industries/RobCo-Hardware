import uuid

import pytest

from common import GridError, check_grid, g, on_grid, snap, stable_uuid


def test_stable_uuid_repeats():
    assert stable_uuid("toy", "symbol", "R1") == stable_uuid("toy", "symbol", "R1")


def test_stable_uuid_depends_on_seed_and_path():
    base = stable_uuid("toy", "symbol", "R1")
    assert stable_uuid("toy2", "symbol", "R1") != base
    assert stable_uuid("toy", "symbol", "R2") != base
    assert uuid.UUID(base).version == 5


def test_known_value():
    # Pinned so a change to the scheme shows up as a test failure.
    assert stable_uuid("toy", "sch", "root") == "8f8bf3ee-d2a9-50f6-9dc1-d95e364a64e8"


def test_grid_helpers():
    assert g(2) == 2.54
    assert g(-3) == -3.81
    assert on_grid(101.6)
    assert not on_grid(101.0)
    assert snap(101.0) == 101.6
    check_grid("ok", 0, 1.27, 63.5)
    with pytest.raises(GridError, match="not on the 1.27 mm grid"):
        check_grid("label", 2.0)
