"""Tests for pickle-based persistence utilities."""

from datetime import datetime, timezone

from src.utils.persistence import _convert_to_timestamp, load_data, save_data


def test_convert_to_timestamp_converts_datetime_values():
    now = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)
    result = _convert_to_timestamp({"posted_at": now, "url": "https://example.com"})
    assert result == {"posted_at": now.isoformat(), "url": "https://example.com"}


def test_convert_to_timestamp_leaves_non_datetime_values_untouched():
    data = {"count": 3, "name": "test"}
    assert _convert_to_timestamp(data) == data


def test_save_and_load_data_roundtrip(tmp_path):
    filename = str(tmp_path / "data.pkl")
    save_data({"a": 1, "b": [1, 2, 3]}, filename)
    assert load_data(filename) == {"a": 1, "b": [1, 2, 3]}


def test_save_data_converts_nested_datetime_dicts(tmp_path):
    filename = str(tmp_path / "data.pkl")
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    save_data({"match1": {"posted_at": now, "score": "1-0"}}, filename)
    assert load_data(filename) == {"match1": {"posted_at": now.isoformat(), "score": "1-0"}}


def test_load_data_returns_default_when_file_missing(tmp_path):
    filename = str(tmp_path / "missing.pkl")
    assert load_data(filename, default={"empty": True}) == {"empty": True}


def test_load_data_returns_none_default_by_default(tmp_path):
    filename = str(tmp_path / "missing.pkl")
    assert load_data(filename) is None


def test_load_data_returns_default_on_corrupt_file(tmp_path):
    filename = str(tmp_path / "corrupt.pkl")
    with open(filename, "wb") as f:
        f.write(b"not a valid pickle")
    assert load_data(filename, default="fallback") == "fallback"


def test_save_data_does_not_raise_on_unwritable_path():
    save_data({"a": 1}, "/nonexistent-dir/data.pkl")
