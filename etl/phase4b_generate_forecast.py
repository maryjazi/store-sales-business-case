"""
Phase 4b - Generate the Forward Forecast

Loads the model trained by phase4_forecasting.py and scores it on prepared_test.parquet
(the actual Kaggle competition test window, Aug 16-31 2017) to produce:
  - reports/forecast_submission.csv   (id, sales — Kaggle submission format)
  - data/processed/forecast_detail.parquet (date, store, family, sales — for the dashboard)

This is a separate script from phase4_forecasting.py because it reuses an already-trained
model rather than retraining. Run phase4_forecasting.py first.

(Note: this step was originally run as a one-off command and not saved as a script —
fixed here so the full pipeline is reproducible end-to-end from etl/, as the README claims.)
"""
import os
import shutil
import numpy as np
import pandas as pd
import lightgbm as lgb

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
REPORTS = os.path.join(ROOT, "reports")

FEATURES = [
    "store_nbr", "family", "city", "state", "type", "cluster",
    "onpromotion", "dcoilwtico", "is_holiday",
    "year", "month", "day", "day_of_week", "day_of_year", "week_of_year", "quarter",
    "is_weekend", "is_month_start", "is_month_end", "is_payday",
    "days_since_store_open",
]
CATEGORICAL = ["store_nbr", "family", "city", "state", "type", "cluster"]


def main():
    booster = lgb.Booster(model_file=f"{PROCESSED}/lightgbm_model.txt")

    test = pd.read_parquet(f"{PROCESSED}/prepared_test.parquet")
    train = pd.read_parquet(f"{PROCESSED}/cleaned_train.parquet")

    # Categories must match exactly what the model was trained on.
    for col in CATEGORICAL:
        cats = train[col].astype("category").cat.categories
        test[col] = pd.Categorical(test[col], categories=cats)

    pred = np.expm1(booster.predict(test[FEATURES]))
    pred = np.clip(pred, 0, None)
    test["sales"] = pred

    submission = test[["id", "sales"]].sort_values("id")
    detail = test[["id", "date", "store_nbr", "family", "sales"]]

    local_dir = "/tmp/phase4b_out"
    os.makedirs(local_dir, exist_ok=True)
    submission.to_csv(f"{local_dir}/forecast_submission.csv", index=False)
    detail.to_parquet(f"{local_dir}/forecast_detail.parquet", index=False)

    shutil.copyfile(f"{local_dir}/forecast_submission.csv", f"{REPORTS}/forecast_submission.csv")
    shutil.copyfile(f"{local_dir}/forecast_detail.parquet", f"{PROCESSED}/forecast_detail.parquet")

    print(f"Forecast rows: {len(submission)}")
    print(f"Total forecast sales (16 days, all stores): {submission['sales'].sum():,.0f}")
    print("Saved reports/forecast_submission.csv and data/processed/forecast_detail.parquet")


if __name__ == "__main__":
    main()
