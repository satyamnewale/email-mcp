import pytest
from server import _validate_max_results, _validate_date


@pytest.mark.parametrize("value", [1, 5, 10, 50])
def test_valid_max_results(value):
    assert _validate_max_results(value) == value


@pytest.mark.parametrize("value", [0, 51, -1, True, 1.5])
def test_invalid_max_results(value):
    with pytest.raises(ValueError):
        _validate_max_results(value)


def test_valid_date():
    assert _validate_date("2026-10-28", "start_date") == "2026-10-28"


@pytest.mark.parametrize("value", ["2026-02-30", "28-10-2026", ""])
def test_invalid_date(value):
    with pytest.raises(ValueError):
        _validate_date(value, "start_date")