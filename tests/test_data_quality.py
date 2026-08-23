"""Lightweight data-quality checks (skip if processed data not present)."""
import os

import pandas as pd
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
MERGED = os.path.join(PROCESSED, "merged_train.parquet")
CLEANED = os.path.join(PROCESSED, "cleaned_train.parquet")

pytestmark = pytest.mark.skipif(
    not os.path.exists(MERGED),
    reason="Processed data not generated — run etl/phase0 first",
)


def test_merged_row_count():
    df = pd.read_parquet(MERGED)
    assert len(df) == 3_000_888


def test_merged_has_no_duplicate_ids():
    df = pd.read_parquet(MERGED)
    assert df["id"].is_unique


@pytest.mark.skipif(not os.path.exists(CLEANED), reason="cleaned_train not found")
def test_cleaned_has_engineered_columns():
    df = pd.read_parquet(CLEANED)
    for col in ("is_payday", "days_since_store_open", "is_holiday"):
        assert col in df.columns
