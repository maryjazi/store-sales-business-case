"""
Phase 4 - Forecasting Models

Validation design: since the competition's true test labels are private, we hold out
the LAST 16 days of the training data (2017-07-31 to 2017-08-15) as a validation set --
same horizon length as the actual test.csv -- and train on everything before that.

Models compared, all scored with RMSLE (the competition's own metric):
  A. Naive last-value per (store, family)
  B. Same-weekday average of the last 4 occurrences in train
  C. 28-day moving average per (store, family)
  D. LightGBM gradient-boosted trees on engineered features (log1p(sales) target)

Educational goal: show *why* a baseline matters -- a model is only "good" relative to
how hard the naive alternatives are to beat.
"""
import os
import json
import time
import shutil
import numpy as np
import pandas as pd
import lightgbm as lgb

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED = os.path.join(ROOT, "data", "processed")
REPORTS = os.path.join(ROOT, "reports")

VAL_START = pd.Timestamp("2017-07-31")
LAST_TRAIN_DATE = pd.Timestamp("2017-07-30")

FEATURES = [
    "store_nbr", "family", "city", "state", "type", "cluster",
    "onpromotion", "dcoilwtico", "is_holiday",
    "year", "month", "day", "day_of_week", "day_of_year", "week_of_year", "quarter",
    "is_weekend", "is_month_start", "is_month_end", "is_payday",
    "days_since_store_open",
]
CATEGORICAL = ["store_nbr", "family", "city", "state", "type", "cluster"]


def rmsle(y_true, y_pred):
    y_pred = np.clip(y_pred, 0, None)
    return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))


def main():
    t0 = time.time()
    df = pd.read_parquet(f"{PROCESSED}/cleaned_train.parquet")
    print("loaded:", time.time() - t0, df.shape)

    train_full = df[df["date"] <= LAST_TRAIN_DATE].copy()
    val = df[df["date"] >= VAL_START].copy()

    # Compute-budget decision: this project runs on a 2-core sandbox, so we train on a
    # random 900k-row sample of the ~2.97M available training rows rather than the full
    # set. This keeps fit time reasonable while still covering every store/family
    # combination many times over. On a normal machine, drop `SAMPLE_SIZE` and fit on
    # `train_full` directly for a small additional accuracy gain.
    SAMPLE_SIZE = 900_000
    train = train_full.sample(n=SAMPLE_SIZE, random_state=42)

    for col in CATEGORICAL:
        train[col] = train[col].astype("category")
        val[col] = val[col].astype("category").cat.set_categories(train[col].cat.categories)

    X_train, y_train = train[FEATURES], np.log1p(train["sales"])
    X_val, y_val = val[FEATURES], val["sales"]

    model = lgb.LGBMRegressor(
        n_estimators=200,
        num_leaves=63,
        learning_rate=0.08,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=2,
        verbosity=-1,
    )
    t1 = time.time()
    model.fit(X_train, y_train, categorical_feature=CATEGORICAL)
    print("fit time:", time.time() - t1)

    pred = np.expm1(model.predict(X_val))
    rmsle_lgb = rmsle(y_val.values, pred)
    print("RMSLE LightGBM:", rmsle_lgb)

    # ---- Load baseline results computed earlier ----
    with open("/tmp/baseline_results.json") as f:
        baselines = json.load(f)

    results = {
        "Naive last-value": baselines["naive"],
        "Same-weekday avg (4wk)": baselines["dow_avg_4wk"],
        "28-day moving average": baselines["ma28"],
        "LightGBM (engineered features)": rmsle_lgb,
    }
    print("\n=== MODEL COMPARISON (RMSLE, lower=better) ===")
    for k, v in sorted(results.items(), key=lambda kv: kv[1]):
        print(f"  {k}: {v:.4f}")

    # ---- Feature importance ----
    importance = pd.DataFrame({
        "feature": FEATURES,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)

    # ---- Save everything locally first ----
    local_dir = "/tmp/phase4_out"
    os.makedirs(local_dir, exist_ok=True)
    model.booster_.save_model(f"{local_dir}/lightgbm_model.txt")
    importance.to_csv(f"{local_dir}/feature_importance.csv", index=False)
    with open(f"{local_dir}/model_comparison.json", "w") as f:
        json.dump(results, f, indent=2)

    val_out = val[["date", "store_nbr", "family", "sales"]].copy()
    val_out["pred_lightgbm"] = pred
    val_out.to_parquet(f"{local_dir}/val_predictions.parquet", index=False)

    # ---- Copy to mount ----
    dest_reports = REPORTS
    dest_processed = PROCESSED
    shutil.copyfile(f"{local_dir}/model_comparison.json", f"{dest_reports}/model_comparison.json")
    shutil.copyfile(f"{local_dir}/feature_importance.csv", f"{dest_reports}/feature_importance.csv")
    shutil.copyfile(f"{local_dir}/lightgbm_model.txt", f"{dest_processed}/lightgbm_model.txt")
    shutil.copyfile(f"{local_dir}/val_predictions.parquet", f"{dest_processed}/val_predictions.parquet")

    print("\nSaved model, feature importance, comparison, and validation predictions.")
    print("Total time:", time.time() - t0)


if __name__ == "__main__":
    main()
