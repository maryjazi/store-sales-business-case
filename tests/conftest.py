"""Shared pytest fixtures."""
import os
import sys

import pandas as pd
import pytest

# Allow `from features import ...` when running tests from repo root
ETL_DIR = os.path.join(os.path.dirname(__file__), "..", "etl")
sys.path.insert(0, ETL_DIR)

# Allow `import cockpit_data` - the cockpit's data layer is deliberately Streamlit-free so
# it can be tested here without a browser
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard")
sys.path.insert(0, DASHBOARD_DIR)


@pytest.fixture
def sample_sales_df():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2017-01-01", "2017-01-15", "2017-01-31"]),
            "store_nbr": [1, 1, 1],
            "sales": [10.0, 0.0, 25.0],
        }
    )
