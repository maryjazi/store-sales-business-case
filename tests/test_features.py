"""Unit tests for etl/features.py."""
from features import add_store_lifecycle_features, add_time_features


def test_add_time_features_payday(sample_sales_df):
    df = add_time_features(sample_sales_df.copy())
    assert df.loc[0, "is_payday"] == False   # 1st
    assert df.loc[1, "is_payday"] == True    # 15th
    assert df.loc[2, "is_payday"] == True    # month end


def test_add_time_features_weekend(sample_sales_df):
    df = add_time_features(sample_sales_df.copy())
    assert "is_weekend" in df.columns
    assert "day_of_week" in df.columns


def test_add_store_lifecycle_features(sample_sales_df):
    df = add_store_lifecycle_features(sample_sales_df.copy())
    assert (df["days_since_store_open"] >= 0).all()
    assert df.loc[0, "days_since_store_open"] == 0
