# 10 — Non-Functional Requirements

**Version:** 1.0  

---

## 1. Performance

| ID | Requirement | Target | Actual / notes |
|---|---|---|---|
| NFR-01 | Full ETL pipeline (phases 0–5) completes on standard laptop | < 2 hours | ~30–60 min typical (phase4 depends on sample size) |
| NFR-02 | Phase 0 merge on 3M rows | < 10 min | Met with Parquet write optimization |
| NFR-03 | Model training (900K sample, 2 cores) | < 30 min | Met; full 2.97M retrain recommended |
| NFR-04 | Dashboard data refresh (phase5 export) | < 15 min | Met |
| NFR-05 | Power BI report load time | < 10 sec per page | Depends on local machine / import mode |

---

## 2. Scalability

| ID | Requirement | Approach |
|---|---|---|
| NFR-06 | Support 54 stores × 33 families × daily grain | Single-machine pandas; Parquet columnar storage |
| NFR-07 | Extensible to additional stores/categories | Star schema design; ETL parameterized by file paths |
| NFR-08 | Future warehouse migration | SQL scripts in `sql/` for BigQuery/PostgreSQL |

---

## 3. Reliability & reproducibility

| ID | Requirement | Implementation |
|---|---|---|
| NFR-09 | All outputs regenerable from raw CSVs | Documented pipeline in `docs/pipeline.md` |
| NFR-10 | Deterministic feature engineering | Shared `etl/features.py` for train and test |
| NFR-11 | Model versioning | `lightgbm_model.txt` saved with training run |
| NFR-12 | Row-count sanity checks after every join | Phase 0 dedup fix; automated tests |
| NFR-12b | Environment reproducible via container | `Dockerfile` pins Python 3.10-slim + exact `requirements.txt`; data volume-mounted at runtime, not baked into the image |

---

## 4. Maintainability

| ID | Requirement | Implementation |
|---|---|---|
| NFR-13 | One script per pipeline phase | `etl/phase0` through `phase5` |
| NFR-14 | Shared utilities in single module | `etl/features.py` |
| NFR-15 | Code documented with business rationale | Docstrings in each phase script |
| NFR-16 | Project documentation in `docs/` | 18-document pack |
| NFR-17 | CI on every push | `.gitlab-ci.yml` runs pytest, then builds and runs the same suite inside a Docker image (`docker-build` stage) |

---

## 5. Security & compliance

| ID | Requirement | Implementation |
|---|---|---|
| NFR-18 | No raw data in version control | `.gitignore` on `data/raw/*.csv` |
| NFR-19 | Kaggle competition license compliance | README download instructions only |
| NFR-20 | No PII in dataset or outputs | Aggregate store-level sales only |
| NFR-21 | Secrets not in repo | N/A for batch offline project |

---

## 6. Usability

| ID | Requirement | Implementation |
|---|---|---|
| NFR-22 | Business case readable by non-technical stakeholders | `reports/business_case.md` |
| NFR-23 | Dashboard self-service filtering | Slicers: year, city, type, category group |
| NFR-24 | Step-by-step Power BI build guide | `dashboard/POWERBI_GUIDE.md` (Persian) |
| NFR-25 | KPI definitions documented | `06_KPI_Definition.md` |

---

## 7. Compatibility

| ID | Requirement | Target |
|---|---|---|
| NFR-26 | Python version | 3.10+ |
| NFR-27 | Power BI Desktop | Latest version (Parquet import supported) |
| NFR-28 | GitLab CI runner | `python:3.10-slim` Docker image |
| NFR-29 | OS | Windows / Linux / macOS (cross-platform paths via `os.path`) |

---

## 8. Availability & deployment (v1 scope)

| ID | Requirement | v1 status |
|---|---|---|
| NFR-30 | Batch pipeline (not real-time) | ✅ By design |
| NFR-31 | Local execution only | ✅ No cloud deployment in v1 |
| NFR-32 | Scheduled refresh | Future: GitLab scheduled pipeline or cron |

---

## 9. Related documents

- [09_Functional_Requirements.md](09_Functional_Requirements.md)
- [12_Assumptions_Constraints.md](12_Assumptions_Constraints.md)
- [13_Risk_Assessment.md](13_Risk_Assessment.md)
