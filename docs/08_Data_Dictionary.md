# 08 — Data Dictionary

**Version:** 1.0  
**See also:** [data_dictionary.md](data_dictionary.md) (technical summary)

---

## 1. Raw tables (`data/raw/`)

### train.csv

| Column | Data type | Description | Example | PK/FK |
|---|---|---|---|---|
| id | integer | Unique record identifier | 0 | PK |
| date | date | Sales date | 2013-01-01 | |
| store_nbr | integer | Store number | 1 | FK → stores |
| family | string | Product category (33 values) | AUTOMOTIVE | |
| sales | float | Unit sales — a quantity, not currency (fractional for weighed goods; the dataset has no price column) | 0.0 – 124,717 | |
| onpromotion | integer | Items on promotion | 0 – 741 | |

**Grain:** one row per store × family × day  
**Rows:** 3,000,888  
**Missing values:** None

---

### test.csv

| Column | Data type | Description | Notes |
|---|---|---|---|
| id | integer | Unique record identifier | PK |
| date | date | Forecast date | 2017-08-16 → 2017-08-31 |
| store_nbr | integer | Store number | FK → stores |
| family | string | Product category | |
| onpromotion | integer | Items on promotion | Known at forecast time |

**Rows:** 28,512 (54 stores × 33 families × 16 days)

---

### stores.csv

| Column | Data type | Description | Example |
|---|---|---|---|
| store_nbr | integer | Store identifier | 1 | PK |
| city | string | City name | Quito |
| state | string | Province | Pichincha |
| type | string | Format: A, B, C, D | D |
| cluster | integer | Similar-store group | 13 |

**Rows:** 54

---

### oil.csv

| Column | Data type | Description | Notes |
|---|---|---|---|
| date | date | Trading day | Weekday entries only |
| dcoilwtico | float | WTI crude oil price (USD) | 43 missing → ffill/bfill |

---

### holidays_events.csv

| Column | Data type | Description | Notes |
|---|---|---|---|
| date | date | Event date | |
| type | string | Holiday, Event, Bridge, etc. | |
| locale | string | National, Regional, Local | Phase 0 uses National only |
| locale_name | string | Region/city name | |
| description | string | Event description | |
| transferred | boolean | Holiday moved to another date | Exclude when True |

---

### transactions.csv

| Column | Data type | Description | Notes |
|---|---|---|---|
| date | date | Transaction date | |
| store_nbr | integer | Store number | |
| transactions | integer | Customer transaction count | ~245K rows missing in merge |

---

## 2. Processed tables (`data/processed/`)

### merged_train.parquet (phase 0)

All train columns plus:

| Column | Type | Source / derivation |
|---|---|---|
| city, state, type, cluster | string/int | stores.csv |
| dcoilwtico | float | oil.csv (daily filled) |
| transactions | float | transactions.csv (nullable) |
| holiday_type, holiday_description | string | holidays_events.csv |
| is_holiday | boolean | holiday_type IS NOT NULL |

**Shape:** 3,000,888 × 15

---

### cleaned_train.parquet (phase 1)

Additional engineered columns:

| Column | Type | Definition |
|---|---|---|
| year, month, day | int | Calendar parts from date |
| day_of_week | int | 0=Mon … 6=Sun |
| day_of_year | int | 1–366 |
| week_of_year | int | ISO week |
| quarter | int | 1–4 |
| is_weekend | boolean | day_of_week ∈ {5, 6} |
| is_month_start | boolean | pandas is_month_start |
| is_month_end | boolean | pandas is_month_end |
| is_payday | boolean | day=15 OR is_month_end |
| store_first_active_date | date | First date with sales > 0 per store |
| days_since_store_open | int | date − first_active, clipped ≥ 0 |
| transactions_missing | boolean | Original transactions was null |
| sales_outlier_flag | boolean | sales > 99.9th pct within family |

**Shape:** 3,000,888 × 30

---

### prepared_test.parquet (phase 1)

Same features as cleaned_train except:
- No `sales` column
- No `transactions` column (leakage guard)
- No outlier flag (no sales to evaluate)

**Shape:** 28,512 × 26

---

## 3. Dashboard tables (`dashboard/data/`)

### fact_sales_actual

| Column | Type | Description |
|---|---|---|
| date | date | Sales date |
| store_nbr | int | Store |
| family | string | Category |
| sales | float | Actual sales |
| onpromotion | int | Promotion count |
| is_holiday | boolean | Holiday flag |
| is_payday | boolean | Payday flag |
| is_weekend | boolean | Weekend flag |

### fact_sales_forecast

| Column | Type | Description |
|---|---|---|
| date | date | Forecast date |
| store_nbr | int | Store |
| family | string | Category |
| forecast_sales | float | Model prediction |

### dim_store

| Column | Type |
|---|---|
| store_nbr, city, state, type, cluster |

### dim_date

| Column | Type |
|---|---|
| date, year, month, day, day_name, day_of_week, quarter, is_weekend, is_holiday, is_payday |

### dim_family

| Column | Type |
|---|---|
| family, family_group |

---

## 4. Related documents

- [07_Data_Requirements.md](07_Data_Requirements.md)
- [16_Data_Model.md](16_Data_Model.md)
- [11_Business_Rules.md](11_Business_Rules.md)
