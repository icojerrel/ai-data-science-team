# BUSINESS SCIENCE UNIVERSITY
# AI DATA SCIENCE TEAM
# ***
# * Tools: Survival Analysis Tools

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import warnings

warnings.filterwarnings("ignore")


def get_survival_data_summary(
    data: pd.DataFrame,
    time_column: str,
    event_column: str,
    n_sample: int = 10,
) -> str:
    """
    Generate a summary of survival data for LLM prompts.

    Parameters
    ----------
    data : pd.DataFrame
        The survival dataset
    time_column : str
        Name of the time-to-event column
    event_column : str
        Name of the event indicator column (1=event occurred, 0=censored)
    n_sample : int
        Number of sample rows to include

    Returns
    -------
    str
        Formatted summary string
    """
    summary = []
    summary.append("# Survival Data Summary")
    summary.append(f"Total observations: {len(data)}")

    # Check if columns exist
    if time_column not in data.columns:
        summary.append(f"⚠️  Time column '{time_column}' not found!")
        return "\n".join(summary)

    if event_column not in data.columns:
        summary.append(f"⚠️  Event column '{event_column}' not found!")
        return "\n".join(summary)

    # Event summary
    event_counts = data[event_column].value_counts()
    n_events = event_counts.get(1, 0)
    n_censored = event_counts.get(0, 0)
    event_rate = (n_events / len(data) * 100) if len(data) > 0 else 0

    summary.append(f"\nEvent Statistics:")
    summary.append(f"  - Events: {n_events} ({event_rate:.1f}%)")
    summary.append(f"  - Censored: {n_censored} ({100-event_rate:.1f}%)")

    # Time summary
    time_data = data[time_column].dropna()
    if len(time_data) > 0:
        summary.append(f"\nTime-to-Event Statistics:")
        summary.append(f"  - Min: {time_data.min():.2f}")
        summary.append(f"  - Median: {time_data.median():.2f}")
        summary.append(f"  - Max: {time_data.max():.2f}")
        summary.append(f"  - Mean: {time_data.mean():.2f}")
        summary.append(f"  - Std: {time_data.std():.2f}")

    # Feature summary
    other_cols = [
        col for col in data.columns if col not in [time_column, event_column]
    ]
    if other_cols:
        summary.append(f"\nCovariates ({len(other_cols)} features):")
        for col in other_cols[:10]:  # Limit to 10
            dtype = data[col].dtype
            missing = data[col].isna().sum()
            missing_pct = (missing / len(data) * 100) if len(data) > 0 else 0
            summary.append(f"  - {col}: {dtype}, missing: {missing} ({missing_pct:.1f}%)")

    # Sample data
    summary.append(f"\nSample Data (first {n_sample} rows):")
    sample_df = data.head(n_sample)
    summary.append(sample_df.to_string(max_cols=10, max_rows=n_sample))

    return "\n".join(summary)


def validate_survival_data(
    data: pd.DataFrame,
    time_column: str,
    event_column: str,
) -> Tuple[bool, List[str]]:
    """
    Validate survival analysis data.

    Parameters
    ----------
    data : pd.DataFrame
        The dataset to validate
    time_column : str
        Name of the time column
    event_column : str
        Name of the event column

    Returns
    -------
    Tuple[bool, List[str]]
        (is_valid, list_of_issues)
    """
    issues = []

    # Check if columns exist
    if time_column not in data.columns:
        issues.append(f"Time column '{time_column}' not found in data")

    if event_column not in data.columns:
        issues.append(f"Event column '{event_column}' not found in data")

    if issues:
        return False, issues

    # Check time column
    if not pd.api.types.is_numeric_dtype(data[time_column]):
        issues.append(f"Time column '{time_column}' must be numeric")

    if (data[time_column] < 0).any():
        issues.append(f"Time column '{time_column}' contains negative values")

    # Check event column
    unique_events = data[event_column].dropna().unique()
    if not set(unique_events).issubset({0, 1, True, False}):
        issues.append(
            f"Event column '{event_column}' must contain only 0/1 or True/False values"
        )

    # Check for sufficient data
    if len(data) < 10:
        issues.append("Dataset too small (< 10 observations)")

    event_counts = data[event_column].value_counts()
    if event_counts.get(1, 0) < 2:
        issues.append("Too few events (< 2) for survival analysis")

    return len(issues) == 0, issues


def format_survival_function_output(
    result: Any,
    function_type: str,
) -> Dict[str, Any]:
    """
    Format the output from a survival analysis function.

    Parameters
    ----------
    result : Any
        The output from the survival function
    function_type : str
        Type of analysis ('kaplan_meier', 'cox', 'risk_prediction', etc.)

    Returns
    -------
    Dict[str, Any]
        Formatted results
    """
    output = {
        "function_type": function_type,
        "success": True,
    }

    if isinstance(result, pd.DataFrame):
        output["data"] = result.to_dict()
        output["summary"] = f"Generated {len(result)} rows of {function_type} results"
    elif isinstance(result, dict):
        output.update(result)
    else:
        output["result"] = str(result)

    return output


def get_survival_analysis_best_practices() -> str:
    """
    Return best practices for survival analysis code generation.

    Returns
    -------
    str
        Best practices text
    """
    return """
# Survival Analysis Best Practices:

1. **Data Preparation**:
   - Ensure time column is numeric and non-negative
   - Event column must be binary (0/1 or True/False)
   - Handle missing values appropriately
   - Check for proportional hazards assumption in Cox models

2. **Common Libraries**:
   - Use `from lifelines import KaplanMeierFitter, CoxPHFitter` for survival analysis
   - Use `from lifelines.statistics import logrank_test` for group comparisons
   - Use `import matplotlib.pyplot as plt` for survival curve plotting
   - Use `import pandas as pd` and `import numpy as np` for data manipulation

3. **Kaplan-Meier Analysis**:
   - Always check censoring proportions
   - Use confidence intervals (default 95%)
   - Include at-risk tables when plotting
   - Compare groups with log-rank test

4. **Cox Proportional Hazards**:
   - Check proportional hazards assumption
   - Standardize continuous variables
   - Handle categorical variables with proper encoding
   - Report hazard ratios with confidence intervals

5. **Risk Prediction**:
   - Validate with C-index (concordance index)
   - Use cross-validation for model selection
   - Report calibration metrics
   - Consider competing risks if applicable

6. **Plotting**:
   - Always return plotly figures for interactivity
   - Include confidence intervals in survival curves
   - Use meaningful colors for groups
   - Add proper labels and titles

7. **Error Handling**:
   - Check for convergence issues in Cox models
   - Handle small sample sizes gracefully
   - Warn about sparse data in subgroups
   - Validate input data before analysis
"""
