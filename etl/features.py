"""
Shared feature engineering used by both the training set and the test/forecast set,
so train and test always go through identical transformations.
"""
import pandas as pd


def add_time_features(df, date_col="date"):
    d = df[date_col]
    df["year"] = d.dt.year
    df["month"] = d.dt.month
    df["day"] = d.dt.day
    df["day_of_week"] = d.dt.dayofweek        # 0=Mon .. 6=Sun
    df["day_of_year"] = d.dt.dayofyear
    df["week_of_year"] = d.dt.isocalendar().week.astype(int)
    df["quarter"] = d.dt.quarter
    df["is_weekend"] = df["day_of_week"].isin([5, 6])
    df["is_month_start"] = d.dt.is_month_start
    df["is_month_end"] = d.dt.is_month_end
    # Ecuador-specific business rule (from the competition brief): public-sector wages are
    # paid on the 15th and on the last day of the month, which historically bumps retail sales.
    df["is_payday"] = (df["day"] == 15) | df["is_month_end"]
    return df


def add_store_lifecycle_features(df, sales_col="sales"):
    """Adds days_since_store_open, using the first date each store has ANY record
    (sales>0 or not) as a proxy for when it started operating/reporting."""
    first_active = (
        df[df[sales_col] > 0].groupby("store_nbr")["date"].min()
        if sales_col in df.columns
        else df.groupby("store_nbr")["date"].min()
    )
    df["store_first_active_date"] = df["store_nbr"].map(first_active)
    df["days_since_store_open"] = (df["date"] - df["store_first_active_date"]).dt.days
    df["days_since_store_open"] = df["days_since_store_open"].clip(lower=0)
    return df
