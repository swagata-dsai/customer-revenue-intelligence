#!/usr/bin/env python3
"""
forecasting.py
==============
Step 9 of the Customer Revenue Intelligence project: time-series forecasting of monthly revenue.

    >>> Works on the SYNTHETIC transaction data cleaned in Step 3. <<<

Forecasting design (decided from the data - see the EDA, ADF and split tables)
-----------------------------------------------------------------------------
    Forecasting unit   total company revenue (Delivered Sales, Rs) - same revenue rule as Steps 3-8
    Frequency          calendar month (36 complete months, 2023-01 .. 2025-12)
    Split              train 2023-01..2024-12 (24) | validation 2025-01..2025-06 (6) | test 2025-07..2025-12 (6)
    Horizon            6 months (2026-01 .. 2026-06) = the horizon actually evaluated on validation, test and backtest
    Selection rule     (fixed before modelling) lowest mean MAPE across the rolling-origin backtest, AND the model
                       must beat both the naive and seasonal-naive baselines on the test window; otherwise the best
                       baseline is kept. Within 5% of the best backtest MAPE, the simpler model wins.

Pipeline
--------
    load_sales_data()                  cleaned lines + data-quality summary
    aggregate_revenue_by_period()      monthly revenue, profit, quantity, orders, customers, AOV
    time_series_eda()                  trend, seasonality evidence, volatility, rolling statistics, decomposition
    check_stationarity()               ADF on level, log and differences
    create_train_test_split()          chronological 24 / 6 / 6
    naive_forecast() / seasonal_naive_forecast()
    exponential_smoothing_forecast()   SES, Holt, damped Holt, Holt-Winters (additive / multiplicative)
    arima_forecast()                   small ARIMA / SARIMA candidate set guided by ADF, ACF, PACF
    theta_forecast()                   optional statistical model (Theta method)
    evaluate_forecast()                MAE, RMSE, MAPE, sMAPE, WAPE, bias
    tune_on_validation()               best configuration per family (fit on train, score on validation)
    compare_models()                   validation + test table
    backtest_forecast()                expanding-window rolling origin, 6-month horizon
    select_final_model()               rule above
    generate_future_forecast()         refit on all 36 months, 6-month forecast with 80% / 95% intervals
    forecast_by_dimension()            category / region series, published only where accurate on test
    validate_forecasting()             quality-control checklist
    save_forecasting_outputs()

Main entry point:  python src/forecasting.py
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import statsmodels
from scipy import stats
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.forecasting.theta import ThetaModel
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import acf, adfuller, pacf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src.eda import inr  # noqa: E402

warnings.filterwarnings("ignore", module="statsmodels")

# ----------------------------------------------------------------------------- files
TS_FILE = config.PROCESSED_DIR / "monthly_sales_timeseries.csv"
FORECAST_FILE = config.PROCESSED_DIR / "revenue_forecast.csv"
FIG_DIR = config.FIGURES_DIR / "forecasting"
MODELS_DIR = config.PROJECT_ROOT / "models"
MODEL_FILE = MODELS_DIR / "forecasting_model.pkl"
METADATA_FILE = MODELS_DIR / "forecasting_metadata.json"
REPORT_FILE = config.REPORTS_DIR / "forecasting_methodology.md"

# ----------------------------------------------------------------------------- design
SEED = config.RANDOM_SEED
M = 12                                   # seasonal period (months)
N_TRAIN, N_VALID, N_TEST = 24, 6, 6
HORIZON = 6
BACKTEST_ORIGINS = list(range(N_TRAIN, N_TRAIN + N_VALID + N_TEST - HORIZON + 1))   # 24..30 -> 7 folds
SIMPLICITY_TOLERANCE = 0.05
DIMENSION_MAX_TEST_MAPE = 20.0           # publish a category/region forecast only if test MAPE <= 20% and beats naive
COMPLEXITY = {"Naive": 0, "Seasonal naive": 0, "Exponential smoothing": 1, "Theta": 1, "ARIMA / SARIMA": 2}

ETS_CANDIDATES = {
    "SES (A,N,N)": dict(error="add", trend=None, seasonal=None),
    "Holt (A,A,N)": dict(error="add", trend="add", seasonal=None),
    "Damped Holt (A,Ad,N)": dict(error="add", trend="add", damped_trend=True, seasonal=None),
    "Holt-Winters additive (A,A,A)": dict(error="add", trend="add", seasonal="add", seasonal_periods=M),
    "Holt-Winters damped additive (A,Ad,A)": dict(error="add", trend="add", damped_trend=True, seasonal="add",
                                                  seasonal_periods=M),
    "Holt-Winters multiplicative (A,Ad,M)": dict(error="add", trend="add", damped_trend=True, seasonal="mul",
                                                 seasonal_periods=M),
}
# Small, reasoned ARIMA set: d = 1 because the level is non-stationary and the first difference is stationary (ADF);
# low orders because ACF/PACF of the differenced series show at most one significant lag; seasonal variants use a
# seasonal difference (the recurring October peak) with no extra seasonal AR/MA terms (only 24 training months).
ARIMA_CANDIDATES = {
    "ARIMA(0,1,1)": dict(order=(0, 1, 1), seasonal_order=(0, 0, 0, 0), trend="n"),
    "ARIMA(1,1,0)": dict(order=(1, 1, 0), seasonal_order=(0, 0, 0, 0), trend="n"),
    "ARIMA(0,1,1) + drift": dict(order=(0, 1, 1), seasonal_order=(0, 0, 0, 0), trend="t"),
    "ARIMA(1,1,1) + drift": dict(order=(1, 1, 1), seasonal_order=(0, 0, 0, 0), trend="t"),
    "SARIMA(0,0,0)(0,1,0)12 + drift": dict(order=(0, 0, 0), seasonal_order=(0, 1, 0, M), trend="t"),
    "SARIMA(1,0,0)(0,1,0)12 + drift": dict(order=(1, 0, 0), seasonal_order=(0, 1, 0, M), trend="t"),
}
# statsmodels ARIMA class: with d = 1 (or D = 1) trend="t" is a linear trend in the LEVEL = constant drift in the
# differences. (SARIMAX's trend="t" would add a trend to the differenced series, i.e. a quadratic path in levels -
# found and rejected during development.)


# =============================================================================
# 1. DATA
# =============================================================================
def load_sales_data(path: Path = config.CLEAN_DATA_FILE) -> dict:
    """Load the cleaned order lines and produce a concise data-quality summary."""
    raw = pd.read_csv(path, encoding="utf-8-sig")
    tx = raw.copy()
    tx["Order_Date"] = pd.to_datetime(tx["Order_Date"], errors="coerce")
    need = ["Order_Date", "Sales", "Profit", "Quantity", "Customer_ID", "Product_ID", "Category", "Region"]
    d = tx[tx["Is_Delivered"]]
    days = pd.date_range(tx["Order_Date"].min(), tx["Order_Date"].max(), freq="D")
    per_day = tx.groupby(tx["Order_Date"].dt.normalize())["Order_ID"].nunique().reindex(days, fill_value=0)
    months = pd.period_range(tx["Order_Date"].min(), tx["Order_Date"].max(), freq="M")
    dm = d.groupby(d["Order_Date"].dt.to_period("M")).size().reindex(months, fill_value=0)
    q = pd.DataFrame([
        ("Required columns present", ", ".join(need), all(c in tx for c in need)),
        ("Missing values in required columns", int(tx[need].isna().sum().sum()), tx[need].notna().all().all()),
        ("Invalid (unparseable) Order_Date", int(tx["Order_Date"].isna().sum() - raw["Order_Date"].isna().sum()),
         tx["Order_Date"].notna().all()),
        ("Duplicate Order_Line_ID", int(tx["Order_Line_ID"].duplicated().sum()), not tx["Order_Line_ID"].duplicated().any()),
        ("Fully duplicated rows", int(tx.duplicated().sum()), not tx.duplicated().any()),
        ("Delivered lines with Sales <= 0", int((d["Sales"] <= 0).sum()), (d["Sales"] > 0).all()),
        ("Delivered lines with Quantity <= 0", int((d["Quantity"] <= 0).sum()), (d["Quantity"] > 0).all()),
        ("Date range", f"{tx['Order_Date'].min().date()} to {tx['Order_Date'].max().date()} ({len(days):,} days)", True),
        ("Calendar days with no order", int((per_day == 0).sum()), True),
        ("Months with no Delivered sales", int((dm == 0).sum()), (dm > 0).all()),
        ("Orders per day (mean / min / max)", f"{per_day.mean():.1f} / {per_day.min()} / {per_day.max()}", True),
        ("Delivered lines per month (min / max)", f"{dm.min()} / {dm.max()}", True),
        ("Lines by status", "; ".join(f"{k} {v:,}" for k, v in tx["Order_Status"].value_counts().items()), True),
    ], columns=["Check", "Result", "OK"])
    return {"tx": tx, "delivered": d.copy(), "quality": q}


def aggregate_revenue_by_period(delivered: pd.DataFrame, freq: str = "MS", by: str | None = None) -> pd.DataFrame:
    """Aggregate Delivered lines to calendar periods (month starts). Missing periods are NOT filled with zero:
    they are reported (none exist in this data) because a missing month is not the same as zero revenue."""
    key = [pd.Grouper(key="Order_Date", freq=freq)] + ([by] if by else [])
    g = delivered.groupby(key)
    ts = pd.DataFrame({"Revenue": g["Sales"].sum(), "Profit": g["Profit"].sum(), "Quantity": g["Quantity"].sum(),
                       "Orders": g["Order_ID"].nunique(), "Customers": g["Customer_ID"].nunique()})
    ts["Average_Order_Value"] = ts["Revenue"] / ts["Orders"]
    ts["Profit_Margin"] = ts["Profit"] / ts["Revenue"]
    ts = ts.reset_index().rename(columns={"Order_Date": "Month"})
    if by is None:
        full = pd.date_range(ts["Month"].min(), ts["Month"].max(), freq=freq)
        ts.attrs["missing_periods"] = int(len(full) - len(ts))
        ts = ts.set_index("Month").reindex(full)          # any gap would appear as NaN, never as 0
        ts.index.name = "Month"
        ts = ts.reset_index()
        ts["Year"] = ts["Month"].dt.year
        ts["Month_Number"] = ts["Month"].dt.month
        ts["Quarter"] = "Q" + ts["Month"].dt.quarter.astype(str)
        ts["Revenue_MoM_%"] = 100 * ts["Revenue"].pct_change()
        ts["Revenue_YoY_%"] = 100 * ts["Revenue"].pct_change(M)
    return ts


def series(ts: pd.DataFrame, col: str = "Revenue") -> pd.Series:
    s = ts.set_index("Month")[col].astype(float)
    s.index = pd.DatetimeIndex(s.index, freq="MS")
    return s


# =============================================================================
# 2. EDA + STATIONARITY
# =============================================================================
def time_series_eda(ts: pd.DataFrame) -> dict:
    """Trend, seasonality evidence, volatility, rolling statistics and STL decomposition."""
    y = series(ts)
    yr = ts.groupby("Year").agg(Revenue=("Revenue", "sum"), Months=("Revenue", "size"),
                                Mean_Month=("Revenue", "mean"), Std_Month=("Revenue", "std"),
                                Orders=("Orders", "sum"), Customers_Month_Avg=("Customers", "mean"))
    yr["YoY_Growth_%"] = 100 * yr["Revenue"].pct_change()
    yr["CV_%"] = 100 * yr["Std_Month"] / yr["Mean_Month"]
    q4 = ts.groupby(["Year", "Quarter"])["Revenue"].sum().unstack()
    yr["Q4_Share_%"] = 100 * q4["Q4"] / q4.sum(axis=1)
    t = np.arange(len(y))
    slope, intercept, r, p, se = stats.linregress(t, y.values)
    trend = {"slope_per_month": slope, "r2": r ** 2, "p_value": p,
             "first_12_mean": y.iloc[:12].mean(), "last_12_mean": y.iloc[-12:].mean()}
    # seasonal index: month revenue / that year's monthly mean (simple, transparent)
    idx = ts.assign(Index=ts["Revenue"] / ts.groupby("Year")["Revenue"].transform("mean"))
    si = idx.pivot(index="Month_Number", columns="Year", values="Index")
    si["Mean_Index"] = si.mean(axis=1)
    si["Min_Index"] = si[[c for c in si.columns if isinstance(c, (int, np.integer))]].min(axis=1)
    si["Max_Index"] = si[[c for c in si.columns if isinstance(c, (int, np.integer))]].max(axis=1)
    rank = idx.assign(Rank=idx.groupby("Year")["Revenue"].rank(ascending=False))
    top = rank[rank["Rank"] == 1][["Year", "Month_Number"]]
    kw = stats.kruskal(*[g["Index"].values for _, g in idx.groupby("Month_Number")])
    stl = STL(y, period=M, robust=True).fit()
    strength_seasonal = max(0.0, 1 - np.var(stl.resid) / np.var(stl.resid + stl.seasonal))
    strength_trend = max(0.0, 1 - np.var(stl.resid) / np.var(stl.resid + stl.trend))
    rolling = pd.DataFrame({"Month": y.index, "Revenue": y.values,
                            "Rolling_Mean_3M": y.rolling(3).mean().values, "Rolling_Std_3M": y.rolling(3).std().values,
                            "Rolling_Mean_12M": y.rolling(M).mean().values, "Rolling_Std_12M": y.rolling(M).std().values})
    rolling["Rolling_CV_12M_%"] = 100 * rolling["Rolling_Std_12M"] / rolling["Rolling_Mean_12M"]
    resid_z = (stl.resid - stl.resid.mean()) / stl.resid.std()
    unusual = pd.DataFrame({"Month": y.index, "Revenue": y.values, "STL_Trend": stl.trend.values,
                            "STL_Seasonal": stl.seasonal.values, "STL_Residual": stl.resid.values,
                            "Residual_Z": resid_z.values})
    unusual["Flag"] = np.where(unusual["Residual_Z"] >= 2, "unusually high", np.where(unusual["Residual_Z"] <= -2,
                                                                                         "unusually low", ""))
    mom = ts["Revenue_MoM_%"]
    return {"yearly": yr.reset_index(), "trend": trend, "seasonal_index": si.reset_index(), "peak_months": top,
            "kruskal": {"H": kw.statistic, "p": kw.pvalue}, "stl": stl,
            "strength": {"seasonal": strength_seasonal, "trend": strength_trend},
            "rolling": rolling, "decomposition": unusual,
            "volatility": {"mom_mean_abs_%": mom.abs().mean(), "mom_max_%": mom.max(), "mom_min_%": mom.min(),
                           "largest_rise": ts.loc[mom.idxmax(), "Month"], "largest_fall": ts.loc[mom.idxmin(), "Month"]}}


def check_stationarity(y: pd.Series) -> pd.DataFrame:
    """ADF test on the level, the log, the first difference and the seasonal difference."""
    rows = []
    for name, s in (("Revenue (level)", y), ("log(Revenue)", np.log(y)), ("First difference", y.diff()),
                    ("Seasonal difference (lag 12)", y.diff(M))):
        s = s.dropna()
        r = adfuller(s.values, autolag="AIC", regression="c", result_object=False)
        rows.append({"Series": name, "Observations": len(s), "ADF_Statistic": r[0], "p_value": r[1], "Lags_Used": r[2],
                     "Critical_5%": r[4]["5%"],
                     "Conclusion": "stationary (reject unit root at 5%)" if r[1] < 0.05 else
                     "non-stationary (cannot reject unit root at 5%)"})
    return pd.DataFrame(rows)


def acf_pacf_table(y: pd.Series, nlags: int = 12) -> pd.DataFrame:
    d = y.diff().dropna()
    a = acf(d, nlags=nlags, fft=False)
    p_ = pacf(d, nlags=nlags, method="ywm")
    ci = 1.96 / np.sqrt(len(d))
    return pd.DataFrame({"Lag": range(nlags + 1), "ACF_diff": a, "PACF_diff": p_, "Approx_95%_Bound": ci,
                         "ACF_Significant": np.abs(a) > ci, "PACF_Significant": np.abs(p_) > ci})


# =============================================================================
# 3. SPLIT + MODELS
# =============================================================================
def create_train_test_split(y: pd.Series) -> dict:
    """Strict chronological split: 24 train / 6 validation / 6 test months."""
    tr, va, te = y.iloc[:N_TRAIN], y.iloc[N_TRAIN:N_TRAIN + N_VALID], y.iloc[N_TRAIN + N_VALID:]
    summ = pd.DataFrame([(n, s.index[0].strftime("%Y-%m"), s.index[-1].strftime("%Y-%m"), len(s), s.sum())
                         for n, s in (("Train", tr), ("Validation", va), ("Test", te))],
                        columns=["Split", "Start", "End", "Months", "Revenue"])
    return {"train": tr, "valid": va, "test": te, "summary": summ}


def _future_index(history: pd.Series, h: int) -> pd.DatetimeIndex:
    return pd.date_range(history.index[-1] + pd.offsets.MonthBegin(1), periods=h, freq="MS")


def _frame(history, mean, lo80=None, hi80=None, lo95=None, hi95=None) -> pd.DataFrame:
    idx = _future_index(history, len(mean))
    f = pd.DataFrame({"Forecast": np.asarray(mean, float)}, index=idx)
    for k, v in (("Lower_80", lo80), ("Upper_80", hi80), ("Lower_95", lo95), ("Upper_95", hi95)):
        f[k] = np.nan if v is None else np.asarray(v, float)
    return f


def naive_forecast(history: pd.Series, h: int) -> dict:
    """Every future month = last observed month. Intervals: residual sigma x sqrt(k) (random-walk formula)."""
    sig = history.diff().dropna().std()
    mean = np.repeat(history.iloc[-1], h)
    k = np.arange(1, h + 1)
    return {"forecast": _frame(history, mean, mean - 1.2816 * sig * np.sqrt(k), mean + 1.2816 * sig * np.sqrt(k),
                               mean - 1.96 * sig * np.sqrt(k), mean + 1.96 * sig * np.sqrt(k)),
            "model": None, "params": {"sigma": sig}}


def seasonal_naive_forecast(history: pd.Series, h: int, m: int = M) -> dict:
    """Every future month = the same month one year earlier. Intervals: sigma x sqrt(floor((k-1)/m) + 1)."""
    sig = history.diff(m).dropna().std()
    mean = np.array([history.iloc[-m + ((k - 1) % m)] for k in range(1, h + 1)])
    k = np.floor((np.arange(1, h + 1) - 1) / m) + 1
    return {"forecast": _frame(history, mean, mean - 1.2816 * sig * np.sqrt(k), mean + 1.2816 * sig * np.sqrt(k),
                               mean - 1.96 * sig * np.sqrt(k), mean + 1.96 * sig * np.sqrt(k)),
            "model": None, "params": {"sigma": sig}}


def exponential_smoothing_forecast(history: pd.Series, h: int, spec: str) -> dict:
    """ETS state-space model (statsmodels ETSModel); smoothing parameters estimated by maximum likelihood.
    Prediction intervals: analytical for additive models, simulated (fixed seed) otherwise."""
    kw = ETS_CANDIDATES[spec]
    if kw.get("seasonal") and len(history) < 2 * M:
        raise ValueError("seasonal ETS needs >= 2 full years")
    res = ETSModel(history, initialization_method="estimated", **kw).fit(disp=False, maxiter=2000)
    start, end = len(history), len(history) + h - 1
    pr = res.get_prediction(start=start, end=end, method="simulated" if kw.get("seasonal") == "mul" else None,
                            simulate_repetitions=2000, rng=np.random.default_rng(SEED)) \
        if kw.get("seasonal") == "mul" else res.get_prediction(start=start, end=end)
    s80, s95 = pr.summary_frame(alpha=0.20), pr.summary_frame(alpha=0.05)
    return {"forecast": _frame(history, s80["mean"], s80["pi_lower"], s80["pi_upper"], s95["pi_lower"], s95["pi_upper"]),
            "model": res, "params": {k: float(v) for k, v in zip(res.param_names, res.params)
                                     if not k.startswith("initial")}, "aic": res.aic}


def arima_forecast(history: pd.Series, h: int, spec: str) -> dict:
    """ARIMA / SARIMA via statsmodels ARIMA (state-space, maximum likelihood). Intervals from the forecast variance."""
    kw = ARIMA_CANDIDATES[spec]
    res = ARIMA(history, order=kw["order"], seasonal_order=kw["seasonal_order"], trend=kw["trend"]).fit()
    fc = res.get_forecast(h)
    c80, c95 = fc.conf_int(alpha=0.20), fc.conf_int(alpha=0.05)
    return {"forecast": _frame(history, fc.predicted_mean, c80.iloc[:, 0], c80.iloc[:, 1], c95.iloc[:, 0], c95.iloc[:, 1]),
            "model": res, "params": {k: float(v) for k, v in res.params.items()}, "aic": res.aic}


def theta_forecast(history: pd.Series, h: int, spec: str = "Theta (seasonality auto-tested)") -> dict:
    """Theta method (Assimakopoulos & Nikolopoulos): SES + half the linear trend, on a seasonally adjusted
    series when a seasonality test says so."""
    res = ThetaModel(history, period=M, deseasonalize=True, use_test=True, method="auto").fit()
    mean = res.forecast(h)
    i80, i95 = res.prediction_intervals(h, alpha=0.20), res.prediction_intervals(h, alpha=0.05)
    params = {k: float(v) for k, v in res.params.items()}
    # the model's own seasonality test (ACF at lag 12) decides whether the series is seasonally adjusted first
    params["seasonality_detected_by_theta_test"] = bool(getattr(res.model, "_has_seasonality", False))
    return {"forecast": _frame(history, mean, i80["lower"], i80["upper"], i95["lower"], i95["upper"]),
            "model": res, "params": params}


FAMILIES = {
    "Naive": (lambda hist, h, spec: naive_forecast(hist, h), ["Naive (last month)"]),
    "Seasonal naive": (lambda hist, h, spec: seasonal_naive_forecast(hist, h), ["Seasonal naive (same month last year)"]),
    "Exponential smoothing": (exponential_smoothing_forecast, list(ETS_CANDIDATES)),
    "ARIMA / SARIMA": (arima_forecast, list(ARIMA_CANDIDATES)),
    "Theta": (theta_forecast, ["Theta (seasonality auto-tested)"]),
}


def run_spec(family: str, spec: str, history: pd.Series, h: int) -> dict:
    fn = FAMILIES[family][0]
    return fn(history, h, spec)


# =============================================================================
# 4. EVALUATION
# =============================================================================
def evaluate_forecast(actual, forecast) -> dict:
    """MAE, RMSE, MAPE (safe: monthly revenue is never 0 here), sMAPE, WAPE and bias."""
    a, f = np.asarray(actual, float), np.asarray(forecast, float)
    if (a == 0).any():
        mape = np.nan                                   # undefined with zero actuals -> use sMAPE / WAPE
    else:
        mape = 100 * np.mean(np.abs((a - f) / a))
    return {"MAE": np.mean(np.abs(a - f)), "RMSE": float(np.sqrt(np.mean((a - f) ** 2))), "MAPE_%": mape,
            "sMAPE_%": 100 * np.mean(2 * np.abs(a - f) / (np.abs(a) + np.abs(f))),
            "WAPE_%": 100 * np.abs(a - f).sum() / np.abs(a).sum(), "Bias_%": 100 * (f.sum() - a.sum()) / a.sum()}


def tune_on_validation(split: dict) -> pd.DataFrame:
    """Every candidate of every family: fit on TRAIN (24 months), forecast the 6 VALIDATION months."""
    rows = []
    for fam, (_, specs) in FAMILIES.items():
        for spec in specs:
            try:
                r = run_spec(fam, spec, split["train"], N_VALID)
                met = evaluate_forecast(split["valid"], r["forecast"]["Forecast"])
                rows.append({"Family": fam, "Specification": spec, **met, "AIC": r.get("aic", np.nan), "Status": "ok"})
            except Exception as e:                      # document failures instead of hiding them
                rows.append({"Family": fam, "Specification": spec, "Status": f"failed: {type(e).__name__}"})
    t = pd.DataFrame(rows)
    t["Best_in_Family"] = False
    for fam, g in t[t["Status"] == "ok"].groupby("Family"):
        t.loc[g["MAE"].idxmin(), "Best_in_Family"] = True
    return t


def compare_models(split: dict, tuning: pd.DataFrame) -> dict:
    """Validation (fit on train) and test (refit on train + validation) results for each family's chosen spec."""
    best = tuning[tuning["Best_in_Family"]].set_index("Family")["Specification"]
    trva = pd.concat([split["train"], split["valid"]])
    rows, fc_val, fc_test = [], {}, {}
    for fam, spec in best.items():
        rv = run_spec(fam, spec, split["train"], N_VALID)
        rt = run_spec(fam, spec, trva, N_TEST)
        mv = evaluate_forecast(split["valid"], rv["forecast"]["Forecast"])
        mt = evaluate_forecast(split["test"], rt["forecast"]["Forecast"])
        cov = ((split["test"].values >= rt["forecast"]["Lower_95"].values) &
               (split["test"].values <= rt["forecast"]["Upper_95"].values)).mean()
        rows.append({"Model": f"{fam}: {spec}", "Family": fam, "Specification": spec,
                     **{f"Val_{k}": v for k, v in mv.items()}, **{f"Test_{k}": v for k, v in mt.items()},
                     "Test_95%_Interval_Coverage_%": 100 * cov})
        fc_val[fam], fc_test[fam] = rv["forecast"], rt["forecast"]
    return {"table": pd.DataFrame(rows), "best_specs": best, "val_forecasts": fc_val, "test_forecasts": fc_test}


def backtest_forecast(y: pd.Series, best_specs: pd.Series, origins=BACKTEST_ORIGINS, h: int = HORIZON) -> dict:
    """Expanding-window rolling-origin backtest: for each origin t, fit on months 1..t and forecast t+1..t+h.
    Origins 24..30 give 7 folds; every 2025 month is forecast by at least one fold."""
    rows, detail = [], []
    for o in origins:
        hist, act = y.iloc[:o], y.iloc[o:o + h]
        for fam, spec in best_specs.items():
            f = run_spec(fam, spec, hist, h)["forecast"]["Forecast"]
            met = evaluate_forecast(act, f)
            rows.append({"Origin": hist.index[-1].strftime("%Y-%m"), "Train_Months": o,
                         "Forecast_Window": f"{act.index[0]:%Y-%m}..{act.index[-1]:%Y-%m}", "Family": fam, **met})
            for i, (ix, a, ff) in enumerate(zip(act.index, act.values, f.values), start=1):
                detail.append({"Origin": hist.index[-1].strftime("%Y-%m"), "Family": fam, "Month": ix, "Horizon": i,
                               "Actual": a, "Forecast": ff, "APE_%": 100 * abs(a - ff) / a})
    folds = pd.DataFrame(rows)
    summ = folds.groupby("Family").agg(Folds=("MAE", "size"), Mean_MAE=("MAE", "mean"), Mean_RMSE=("RMSE", "mean"),
                                       Mean_MAPE_pct=("MAPE_%", "mean"), Std_MAPE_pct=("MAPE_%", "std"),
                                       Worst_MAPE_pct=("MAPE_%", "max"), Mean_WAPE_pct=("WAPE_%", "mean"),
                                       Mean_Bias_pct=("Bias_%", "mean"))
    wins = folds.loc[folds.groupby("Origin")["MAPE_%"].idxmin()].groupby("Family").size()
    summ["Folds_Won"] = wins.reindex(summ.index).fillna(0).astype(int)
    by_h = pd.DataFrame(detail).groupby(["Family", "Horizon"])["APE_%"].mean().unstack()
    return {"folds": folds, "summary": summ.sort_values("Mean_MAPE_pct").reset_index(), "detail": pd.DataFrame(detail),
            "by_horizon": by_h.reset_index()}


def select_final_model(comp: dict, bt: dict) -> dict:
    """Rule fixed in advance: lowest mean backtest MAPE; must beat BOTH baselines on test MAE; within 5% of the best
    backtest MAPE the simpler family (lower COMPLEXITY) wins."""
    s = bt["summary"].set_index("Family")
    t = comp["table"].set_index("Family")
    base_mae = min(t.loc["Naive", "Test_MAE"], t.loc["Seasonal naive", "Test_MAE"])
    tab = s[["Mean_MAPE_pct", "Std_MAPE_pct", "Mean_MAE"]].join(t[["Specification", "Val_MAPE_%", "Test_MAPE_%", "Test_MAE"]])
    tab["Beats_Both_Baselines_on_Test"] = (tab["Test_MAE"] < base_mae) | tab.index.isin(["Naive", "Seasonal naive"])
    tab["Complexity"] = tab.index.map(COMPLEXITY)
    elig = tab[tab["Beats_Both_Baselines_on_Test"]]
    best = elig["Mean_MAPE_pct"].min()
    tab["Within_5%_of_Best_Backtest_MAPE"] = tab["Mean_MAPE_pct"] <= best * (1 + SIMPLICITY_TOLERANCE)
    cand = tab[tab["Beats_Both_Baselines_on_Test"] & tab["Within_5%_of_Best_Backtest_MAPE"]]
    chosen = cand.sort_values(["Complexity", "Mean_MAPE_pct"]).index[0]
    tab["Selected"] = tab.index == chosen
    return {"table": tab.reset_index().sort_values("Mean_MAPE_pct"), "family": chosen,
            "spec": comp["best_specs"][chosen]}


def generate_future_forecast(y: pd.Series, family: str, spec: str, h: int = HORIZON) -> dict:
    """Refit the selected model on all 36 months and forecast the next h months with 80% / 95% intervals."""
    r = run_spec(family, spec, y, h)
    f = r["forecast"].copy()
    f.index.name = "Month"
    return {"forecast": f, "result": r}


# =============================================================================
# 5. BY DIMENSION
# =============================================================================
def forecast_by_dimension(delivered: pd.DataFrame, family: str, spec: str) -> dict:
    """Category and region monthly series: evaluate the selected model vs naive / seasonal naive on the test window
    (refit on train+validation), and publish a 6-month forecast only if test MAPE <= 20% AND it beats both baselines."""
    rows, fcs = [], []
    for dim in ("Category", "Region"):
        m = aggregate_revenue_by_period(delivered, by=dim).pivot(index="Month", columns=dim, values="Revenue")
        m.index = pd.DatetimeIndex(m.index, freq="MS")
        for lvl in m.columns:
            y = m[lvl].astype(float)
            if y.isna().any() or len(y) < N_TRAIN + N_VALID + N_TEST or (y <= 0).any():
                rows.append({"Dimension": dim, "Level": lvl, "Status": "skipped: gaps or zero months"})
                continue
            trva, te = y.iloc[:N_TRAIN + N_VALID], y.iloc[N_TRAIN + N_VALID:]
            res = {}
            for name, fam, sp in (("Selected", family, spec), ("Naive", "Naive", None),
                                  ("Seasonal naive", "Seasonal naive", None)):
                try:
                    res[name] = evaluate_forecast(te, run_spec(fam, sp, trva, N_TEST)["forecast"]["Forecast"])
                except Exception as e:
                    res[name] = {"MAPE_%": np.nan, "MAE": np.nan, "err": type(e).__name__}
            ok = (res["Selected"]["MAPE_%"] <= DIMENSION_MAX_TEST_MAPE and
                  res["Selected"]["MAE"] < min(res["Naive"]["MAE"], res["Seasonal naive"]["MAE"]))
            rows.append({"Dimension": dim, "Level": lvl, "Monthly_Mean_Revenue": y.mean(),
                         "CV_%": 100 * y.std() / y.mean(), "Selected_Test_MAPE_%": res["Selected"]["MAPE_%"],
                         "Naive_Test_MAPE_%": res["Naive"]["MAPE_%"],
                         "Seasonal_Naive_Test_MAPE_%": res["Seasonal naive"]["MAPE_%"],
                         "Selected_Test_MAE": res["Selected"]["MAE"], "Naive_Test_MAE": res["Naive"]["MAE"],
                         "Seasonal_Naive_Test_MAE": res["Seasonal naive"]["MAE"],
                         "Published": ok, "Status": "forecast published" if ok else
                         "not published: test MAPE > 20% or does not beat both baselines"})
            if ok:
                f = run_spec(family, spec, y, HORIZON)["forecast"]
                fcs.append(f.assign(Dimension=dim, Level=lvl).reset_index().rename(columns={"index": "Month"}))
    return {"evaluation": pd.DataFrame(rows), "forecasts": pd.concat(fcs, ignore_index=True) if fcs else pd.DataFrame()}


# =============================================================================
# 6. ORCHESTRATION
# =============================================================================
def run_forecasting_analysis() -> dict:
    D = load_sales_data()
    ts = aggregate_revenue_by_period(D["delivered"])
    y = series(ts)
    R = {"data": D, "ts": ts, "y": y}
    R["eda"] = time_series_eda(ts)
    R["adf"] = check_stationarity(y)
    R["acf"] = acf_pacf_table(y)
    R["split"] = create_train_test_split(y)
    R["tuning"] = tune_on_validation(R["split"])
    R["comparison"] = compare_models(R["split"], R["tuning"])
    R["backtest"] = backtest_forecast(y, R["comparison"]["best_specs"])
    R["selection"] = select_final_model(R["comparison"], R["backtest"])
    R["future"] = generate_future_forecast(y, R["selection"]["family"], R["selection"]["spec"])
    R["dimension"] = forecast_by_dimension(D["delivered"], R["selection"]["family"], R["selection"]["spec"])
    R["forecast_table"] = build_forecast_table(R)
    R["insights"] = business_interpretation(R)
    R["qc"] = validate_forecasting(R)
    return R


def build_forecast_table(R: dict) -> pd.DataFrame:
    """One table: actuals, validation forecasts (fit on train), test forecasts (fit on train+validation) and the
    future forecast (fit on all data), for the selected model."""
    fam = R["selection"]["family"]
    y = R["y"]
    rows = [pd.DataFrame({"Month": y.index, "Actual_Revenue": y.values, "Type": "Historical actual"})]
    for fc, typ, act in ((R["comparison"]["val_forecasts"][fam], "Validation forecast (fit on train)", R["split"]["valid"]),
                         (R["comparison"]["test_forecasts"][fam], "Test forecast (fit on train + validation)",
                          R["split"]["test"])):
        rows.append(fc.assign(Actual_Revenue=act.values, Type=typ).reset_index().rename(columns={"index": "Month"}))
    fut = R["future"]["forecast"].reset_index().assign(Actual_Revenue=np.nan, Type="Future forecast (fit on all 36 months)")
    rows.append(fut)
    t = pd.concat(rows, ignore_index=True)
    t["Model"] = np.where(t["Type"] == "Historical actual", "", f"{fam}: {R['selection']['spec']}")
    t["Month"] = pd.to_datetime(t["Month"]).dt.strftime("%Y-%m")
    return t[["Month", "Type", "Actual_Revenue", "Forecast", "Lower_80", "Upper_80", "Lower_95", "Upper_95", "Model"]]


def business_interpretation(R: dict) -> pd.DataFrame:
    e, fut, y = R["eda"], R["future"]["forecast"], R["y"]
    yr = e["yearly"].set_index("Year")
    si = e["seasonal_index"].set_index("Month_Number")
    last6 = y.iloc[-6:].sum()
    same6 = y.iloc[-12:-6].sum()
    f6 = fut["Forecast"].sum()
    prev_h1 = y[(y.index.year == y.index[-1].year) & (y.index.month <= HORIZON)].sum()
    sel = R["selection"]["table"].set_index("Family").loc[R["selection"]["family"]]
    width = ((fut["Upper_95"] - fut["Lower_95"]) / fut["Forecast"]).mean()
    peaks = ", ".join(f"{int(r['Year'])}: month {int(r['Month_Number'])}" for _, r in e["peak_months"].iterrows())
    rows = [
        ("Revenue direction", f"Revenue grew {yr['YoY_Growth_%'].dropna().iloc[0]:.0f}% in "
                              f"{int(yr.index[1])} and {yr['YoY_Growth_%'].dropna().iloc[1]:.0f}% in {int(yr.index[2])}; "
                              f"the 6-month forecast totals {inr(f6)} vs {inr(prev_h1)} in the same months of "
                              f"{y.index[-1].year} ({100 * (f6 / prev_h1 - 1):+.0f}%).",
         "Plan for continued growth, but the forecast is a model extrapolation of 3 years of history."),
        ("Seasonality", f"Highest month each year: {peaks}. Mean seasonal index for October "
                        f"{si.loc[10, 'Mean_Index']:.2f} (range {si.loc[10, 'Min_Index']:.2f}-{si.loc[10, 'Max_Index']:.2f}); "
                        f"Q4 share of annual revenue " + ", ".join(f"{int(k)}: {v:.0f}%" for k, v in yr['Q4_Share_%'].items())
                        + f". Kruskal-Wallis across months p = {e['kruskal']['p']:.3f}.",
         "A recurring Q4/October peak is supported; other month-to-month differences are not consistent across years."),
        ("Volatility", f"Average absolute month-on-month change {e['volatility']['mom_mean_abs_%']:.0f}%; largest rise "
                       f"{e['volatility']['mom_max_%']:+.0f}% ({e['volatility']['largest_rise']:%Y-%m}), largest fall "
                       f"{e['volatility']['mom_min_%']:+.0f}% ({e['volatility']['largest_fall']:%Y-%m}).",
         "Single-month targets need buffers; quarterly totals are more stable."),
        ("Forecast accuracy", f"Selected model: backtest mean MAPE {sel['Mean_MAPE_pct']:.1f}% (7 folds), test MAPE "
                              f"{sel['Test_MAPE_%']:.1f}%.",
         "Expect monthly errors of roughly this size; use the intervals, not only the point forecast."),
        ("Uncertainty", f"The 95% interval is on average {100 * width:.0f}% of the point forecast wide.",
         "Useful for cash-flow and inventory buffers: plan ranges, not single numbers."),
        ("Planning implications", f"Last 6 actual months {inr(last6)} vs previous 6 {inr(same6)}.",
         "Inventory, staffing and marketing budgets can be phased to the forecast path and to the Q4 peak; "
         "specific actions are for the recommendation step."),
    ]
    return pd.DataFrame(rows, columns=["Area", "Evidence", "Planning interpretation"])


def validate_forecasting(R: dict) -> pd.DataFrame:
    y, sp = R["y"], R["split"]
    d = R["data"]["delivered"]
    ft = R["forecast_table"]
    rows = [
        ("Actual cleaned dataset used", str(config.CLEAN_DATA_FILE.relative_to(config.PROJECT_ROOT)), True),
        ("Correct date handling (all dates parsed; monthly index regular)", f"{len(y)} months, freq=MS",
         R["data"]["quality"].set_index("Check").loc["Invalid (unparseable) Order_Date", "OK"] and y.index.freqstr == "MS"),
        ("Monthly aggregation reconciles with Delivered sales", f"{inr(y.sum())} vs {inr(d['Sales'].sum())}",
         np.isclose(y.sum(), d["Sales"].sum())),
        ("No missing months (none filled with zero)", R["ts"].attrs.get("missing_periods", 0),
         R["ts"].attrs.get("missing_periods", 0) == 0 and y.notna().all()),
        ("No random split: train < validation < test in time",
         f"{sp['train'].index[-1]:%Y-%m} < {sp['valid'].index[0]:%Y-%m}; {sp['valid'].index[-1]:%Y-%m} < {sp['test'].index[0]:%Y-%m}",
         sp["train"].index[-1] < sp["valid"].index[0] and sp["valid"].index[-1] < sp["test"].index[0]),
        ("No leakage: validation fits use train only; test fits use train+validation only; backtest fits use data "
         "before each origin", "by construction (history slices)", True),
        ("Baselines implemented", "Naive, Seasonal naive", {"Naive", "Seasonal naive"} <= set(R["comparison"]["table"]["Family"])),
        ("Exponential smoothing tested", f"{len(ETS_CANDIDATES)} configurations",
         (R["tuning"]["Family"] == "Exponential smoothing").sum() == len(ETS_CANDIDATES)),
        ("ARIMA / SARIMA tested", f"{len(ARIMA_CANDIDATES)} configurations",
         (R["tuning"]["Family"] == "ARIMA / SARIMA").sum() == len(ARIMA_CANDIDATES)),
        ("Stationarity checked (ADF)", "level, log, first and seasonal differences", len(R["adf"]) == 4),
        ("Backtesting performed", f"{len(BACKTEST_ORIGINS)} expanding-window folds", len(R["backtest"]["folds"]) > 0),
        ("MAE, RMSE, MAPE, sMAPE, WAPE calculated", "no zero monthly actuals, so MAPE is defined",
         (y > 0).all() and R["comparison"]["table"][["Test_MAE", "Test_RMSE", "Test_MAPE_%"]].notna().all().all()),
        ("Final model selected by the pre-set rule", f"{R['selection']['family']}: {R['selection']['spec']}",
         R["selection"]["table"]["Selected"].sum() == 1),
        ("Future forecast generated with intervals", f"{HORIZON} months",
         len(R["future"]["forecast"]) == HORIZON and R["future"]["forecast"][["Lower_95", "Upper_95"]].notna().all().all()),
        ("Forecast values finite and intervals ordered", "lower <= forecast <= upper",
         np.isfinite(R["future"]["forecast"]["Forecast"]).all() and
         ((R["future"]["forecast"]["Lower_95"] <= R["future"]["forecast"]["Forecast"]) &
          (R["future"]["forecast"]["Forecast"] <= R["future"]["forecast"]["Upper_95"])).all()),
        ("Forecast table reconciles with actuals", f"{int(ft['Actual_Revenue'].notna().sum())} actual values",
         np.isclose(ft.loc[ft["Type"] == "Historical actual", "Actual_Revenue"].sum(), y.sum())),
    ]
    return pd.DataFrame(rows, columns=["Check", "Evidence", "Pass"])


def save_forecasting_outputs(R: dict) -> list[Path]:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    ts = R["ts"].copy()
    ts["Month"] = ts["Month"].dt.strftime("%Y-%m-%d")
    ts.round(4).to_csv(TS_FILE, index=False, encoding="utf-8-sig")
    R["forecast_table"].round(2).to_csv(FORECAST_FILE, index=False, encoding="utf-8-sig")
    paths += [TS_FILE, FORECAST_FILE]
    e = R["eda"]
    tabs = {
        "forecast_data_quality.csv": R["data"]["quality"],
        "forecast_yearly_summary.csv": e["yearly"],
        "forecast_seasonal_index.csv": e["seasonal_index"],
        "forecast_rolling_statistics.csv": e["rolling"],
        "forecast_stl_decomposition.csv": e["decomposition"],
        "forecast_adf_tests.csv": R["adf"],
        "forecast_acf_pacf.csv": R["acf"],
        "forecast_split_summary.csv": R["split"]["summary"],
        "forecast_validation_tuning.csv": R["tuning"],
        "forecast_model_comparison.csv": R["comparison"]["table"],
        "forecast_backtest_folds.csv": R["backtest"]["folds"],
        "forecast_backtest_summary.csv": R["backtest"]["summary"],
        "forecast_backtest_by_horizon.csv": R["backtest"]["by_horizon"],
        "forecast_model_selection.csv": R["selection"]["table"],
        "forecast_future.csv": R["future"]["forecast"].reset_index().assign(Month=lambda d: d["Month"].dt.strftime("%Y-%m")),
        "forecast_by_dimension_evaluation.csv": R["dimension"]["evaluation"],
        "forecast_business_interpretation.csv": R["insights"],
        "forecast_quality_checklist.csv": R["qc"],
    }
    if len(R["dimension"]["forecasts"]):
        tabs["forecast_by_dimension.csv"] = R["dimension"]["forecasts"].assign(
            Month=lambda d: pd.to_datetime(d["Month"]).dt.strftime("%Y-%m"))
    for n, df in tabs.items():
        p = config.TABLES_DIR / n
        df = df.copy()
        for c in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                df[c] = df[c].dt.strftime("%Y-%m")
        df.round(4).to_csv(p, index=False, encoding="utf-8-sig")
        paths.append(p)
    res = R["future"]["result"]
    fam, spec = R["selection"]["family"], R["selection"]["spec"]
    artefact = {"family": fam, "specification": spec, "fitted_model": res["model"], "params": res["params"],
                "trained_on": [R["y"].index[0].strftime("%Y-%m"), R["y"].index[-1].strftime("%Y-%m")],
                "history": R["y"] if res["model"] is None else None,
                "note": "fitted statsmodels results object; for naive-type models the history is stored instead"}
    joblib.dump(artefact, MODEL_FILE)
    sel = R["selection"]["table"].set_index("Family").loc[fam]
    ct = R["comparison"]["table"].set_index("Family").loc[fam]
    meta = {
        "dataset": config.DATASET_LABEL, "target": "monthly Delivered revenue (Sales, Rs), company total",
        "model_type": f"{fam}: {spec}", "model_parameters": res["params"],
        "forecasting_frequency": "monthly (month start)", "forecast_horizon_months": HORIZON,
        "forecast_months": [d.strftime("%Y-%m") for d in R["future"]["forecast"].index],
        "training_period_final_fit": f"{R['y'].index[0]:%Y-%m} to {R['y'].index[-1]:%Y-%m} (36 months)",
        "evaluation_split": {"train": "2023-01..2024-12", "validation": "2025-01..2025-06", "test": "2025-07..2025-12"},
        "selection_rule": "lowest mean backtest MAPE; must beat naive and seasonal naive on test MAE; "
                          "within 5% -> simpler family",
        "metrics": {"validation": {k: round(float(ct[f"Val_{k}"]), 3) for k in ("MAE", "RMSE", "MAPE_%", "sMAPE_%", "WAPE_%")},
                    "test": {k: round(float(ct[f"Test_{k}"]), 3) for k in ("MAE", "RMSE", "MAPE_%", "sMAPE_%", "WAPE_%")},
                    "backtest_mean_MAPE_%": round(float(sel["Mean_MAPE_pct"]), 3)},
        "intervals": "80% and 95% prediction intervals from the model",
        "random_seed": SEED, "statsmodels_version": statsmodels.__version__, "created": date.today().isoformat(),
        "reload": "a = joblib.load('models/forecasting_model.pkl'); a['fitted_model'].forecast(6)",
    }
    METADATA_FILE.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    paths += [MODEL_FILE, METADATA_FILE]
    return paths


def verify_artefact(R: dict) -> bool:
    a = joblib.load(MODEL_FILE)
    if a["fitted_model"] is None:
        re = run_spec(a["family"], a["specification"], a["history"], HORIZON)["forecast"]["Forecast"]
    else:
        re = np.asarray(a["fitted_model"].forecast(HORIZON), float)
    return bool(np.allclose(re, R["future"]["forecast"]["Forecast"].values))


def run_forecasting(make_plots: bool = True, verbose: bool = True) -> dict:
    R = run_forecasting_analysis()
    R["saved"] = save_forecasting_outputs(R)
    ok = verify_artefact(R)
    R["qc"] = pd.concat([R["qc"], pd.DataFrame([
        ("Model artefact saved and reproduces the future forecast after reload", "models/forecasting_model.pkl", ok),
        ("Metadata saved", "models/forecasting_metadata.json", METADATA_FILE.exists())],
        columns=["Check", "Evidence", "Pass"])], ignore_index=True)
    R["qc"].to_csv(config.TABLES_DIR / "forecast_quality_checklist.csv", index=False, encoding="utf-8-sig")
    if make_plots:
        R["figures"] = plot_forecasting_figures(R)
    R["report"] = write_forecasting_report(R)
    if verbose:
        print(R["qc"][["Check", "Pass"]].to_string(index=False))
        print(f"\nSelected: {R['selection']['family']}: {R['selection']['spec']}")
        print(R["future"]["forecast"].round(0).to_string())
        print(f"Files saved: {len(R['saved'])} | figures: {len(R.get('figures', []))} | "
              f"report: {R['report'].relative_to(config.PROJECT_ROOT)}")
    return R


# =============================================================================
# 7. FIGURES
# =============================================================================
FAMILY_COLORS = {"Naive": "#8f8e87", "Seasonal naive": "#c3c2b7", "Exponential smoothing": "#1baf7a",
                 "ARIMA / SARIMA": "#4a3aa7", "Theta": "#eb6834"}


def plot_forecasting_figures(R: dict, out_dir: Path = FIG_DIR) -> list[Path]:
    """Forecasting charts (PNG) + one interactive Plotly HTML of the final forecast."""
    from matplotlib.ticker import FuncFormatter
    from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
    from src.eda import PAL, _note, _save, _style
    plt = _style()
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    y, ts, e = R["y"], R["ts"], R["eda"]
    lfmt = FuncFormatter(lambda v, _: f"₹{v / 1e5:,.0f}L")
    YEARS = {2023: PAL["neutral"], 2024: PAL["blue"], 2025: PAL["orange"]}

    # 1 historical trend ---------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.plot(y.index, y.values, marker="o", markersize=4, color=PAL["blue"], linewidth=1.8, label="Monthly revenue")
    t = np.arange(len(y))
    tr = e["trend"]
    ax.plot(y.index, tr["slope_per_month"] * t + (y.values.mean() - tr["slope_per_month"] * t.mean()), color=PAL["text"],
            linestyle="--", linewidth=1, label=f"Linear trend (+{inr(tr['slope_per_month'])}/month, R² {tr['r2']:.2f})")
    ax.plot(y.index, y.rolling(M).mean(), color=PAL["orange"], linewidth=2, label="12-month rolling mean")
    for yr_, r in e["yearly"].set_index("Year").iterrows():
        ax.text(pd.Timestamp(f"{yr_}-06-15"), y.max() * 1.08, f"{yr_}: {inr(r['Revenue'])}"
                + ("" if pd.isna(r["YoY_Growth_%"]) else f" ({r['YoY_Growth_%']:+.0f}%)"), ha="center", fontsize=9,
                color=PAL["muted"])
    ax.set_ylim(0, y.max() * 1.18)
    ax.yaxis.set_major_formatter(lfmt)
    ax.set_title("Monthly Delivered revenue, 2023-2025")
    ax.legend(loc="lower right", fontsize=8.5)
    fig.tight_layout()
    _save(fig, "historical_revenue_trend.png", out_dir, saved)

    # 2 monthly pattern ------------------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    mn = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for yr_, g in ts.groupby("Year"):
        axes[0].plot(g["Month_Number"], g["Revenue"], marker="o", color=YEARS[yr_], linewidth=2, label=str(yr_))
    axes[0].set_xticks(range(1, 13), mn)
    axes[0].yaxis.set_major_formatter(lfmt)
    axes[0].set_title("Revenue by calendar month, one line per year")
    axes[0].legend()
    q = ts.groupby(["Year", "Quarter"])["Revenue"].sum().unstack()
    x = np.arange(4)
    for i, (yr_, r) in enumerate(q.iterrows()):
        axes[1].bar(x + (i - 1) * 0.27, r.values, 0.27, color=YEARS[yr_], label=str(yr_))
    axes[1].set_xticks(x, q.columns)
    axes[1].yaxis.set_major_formatter(lfmt)
    axes[1].set_title("Revenue by quarter")
    axes[1].grid(axis="x", visible=False)
    fig.suptitle("Monthly and quarterly revenue pattern", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, "monthly_revenue_pattern.png", out_dir, saved)

    # 3 rolling statistics ----------------------------------------------------------------------------
    ro = e["rolling"]
    fig, axes = plt.subplots(2, 1, figsize=(12, 6.4), sharex=True, gridspec_kw={"height_ratios": [2, 1.2]})
    axes[0].plot(ro["Month"], ro["Revenue"], color=PAL["neutral"], marker="o", markersize=3, label="Monthly revenue")
    axes[0].plot(ro["Month"], ro["Rolling_Mean_3M"], color=PAL["blue"], linewidth=1.6, label="3-month rolling mean")
    axes[0].plot(ro["Month"], ro["Rolling_Mean_12M"], color=PAL["orange"], linewidth=2.2, label="12-month rolling mean")
    axes[0].yaxis.set_major_formatter(lfmt)
    axes[0].legend(loc="upper left", fontsize=8.5)
    axes[0].set_title("Rolling mean")
    axes[1].plot(ro["Month"], ro["Rolling_Std_12M"], color=PAL["orange"], linewidth=2, label="12-month rolling std")
    ax2 = axes[1].twinx()
    ax2.plot(ro["Month"], ro["Rolling_CV_12M_%"], color=PAL["text"], linestyle=":", linewidth=1.5,
             label="12-month coefficient of variation (right)")
    ax2.set_ylabel("CV %")
    ax2.grid(False)
    axes[1].yaxis.set_major_formatter(lfmt)
    axes[1].set_title("Rolling volatility")
    h1, l1 = axes[1].get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    axes[1].legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8.5)
    fig.suptitle("Rolling statistics: rising level; absolute volatility up, relative volatility (CV) down", x=0.01, ha="left",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, "rolling_mean_std.png", out_dir, saved)

    # 4 seasonal pattern + STL -------------------------------------------------------------------------
    si = e["seasonal_index"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.1, 1]})
    ax = axes[0]
    ax.bar(si["Month_Number"], si["Mean_Index"], color=[PAL["orange"] if v >= 1.2 else PAL["blue"] for v in si["Mean_Index"]],
           width=0.65)
    ax.errorbar(si["Month_Number"], si["Mean_Index"], yerr=[si["Mean_Index"] - si["Min_Index"], si["Max_Index"] - si["Mean_Index"]],
                fmt="none", ecolor=PAL["text"], capsize=3, linewidth=1)
    ax.axhline(1, color=PAL["muted"], linewidth=0.8)
    ax.set_xticks(range(1, 13), mn)
    ax.set_title("Seasonal index (month / that year's monthly mean)")
    ax.text(0.01, 0.97, "bar = mean of 3 years, whisker = min-max", transform=ax.transAxes, fontsize=8, va="top",
            color=PAL["muted"])
    ax.grid(axis="x", visible=False)
    stl = e["stl"]
    ax = axes[1]
    ax.plot(y.index, stl.trend, color=PAL["text"], label="STL trend")
    ax.plot(y.index, stl.trend + stl.seasonal, color=PAL["orange"], label="Trend + seasonal")
    ax.scatter(y.index, y.values, s=12, color=PAL["blue"], label="Actual", zorder=3)
    ax.yaxis.set_major_formatter(lfmt)
    ax.set_title(f"STL decomposition (seasonal strength {e['strength']['seasonal']:.2f})")
    ax.tick_params(axis="x", labelrotation=30)
    ax.legend(fontsize=8.5, loc="upper left")
    fig.suptitle("Seasonality: a recurring October / Q4 peak; other months inconsistent", x=0.01, ha="left",
                 fontsize=13, fontweight="bold")
    _note(fig, "Only 3 years of data: seasonal estimates rest on 3 observations per calendar month.")
    fig.tight_layout()
    _save(fig, "seasonal_pattern.png", out_dir, saved)

    # 5 distribution --------------------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    axes[0].hist(y.values, bins=12, color=PAL["blue"], edgecolor="white")
    axes[0].axvline(y.mean(), color=PAL["text"], linestyle="--", linewidth=1)
    axes[0].text(y.mean(), axes[0].get_ylim()[1] * 0.92, f" mean {inr(y.mean())}", fontsize=8.5)
    axes[0].xaxis.set_major_formatter(lfmt)
    axes[0].set_title("Monthly revenue distribution (36 months)")
    axes[0].set_ylabel("Months")
    bp = axes[1].boxplot([ts.loc[ts["Year"] == yr_, "Revenue"] for yr_ in YEARS], patch_artist=True,
                         medianprops={"color": "#0b0b0b"})
    for b_, c_ in zip(bp["boxes"], YEARS.values()):
        b_.set(facecolor=c_, alpha=0.7)
    axes[1].set_xticks([1, 2, 3], [str(k) for k in YEARS])
    axes[1].yaxis.set_major_formatter(lfmt)
    axes[1].set_title("By year: the level shifts up each year")
    axes[1].grid(axis="x", visible=False)
    fig.tight_layout()
    _save(fig, "revenue_distribution.png", out_dir, saved)

    # 6 ACF / PACF --------------------------------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
    plot_acf(y, lags=18, ax=axes[0], title="ACF - revenue level")
    plot_acf(y.diff().dropna(), lags=12, ax=axes[1], title="ACF - first difference")
    plot_pacf(y.diff().dropna(), lags=12, ax=axes[2], method="ywm", title="PACF - first difference")
    for a_ in axes:
        a_.set_xlabel("Lag (months)")
    fig.suptitle("Autocorrelation: slow decay in the level (trend); differences: lag 1 clear, lags 6 and 12 borderline", x=0.01, ha="left",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, "acf_pacf.png", out_dir, saved)

    # 7 model comparison -------------------------------------------------------------------------------
    ct = R["comparison"]["table"].set_index("Family")
    bs = R["backtest"]["summary"].set_index("Family")
    fams = list(bs.index)
    sel = R["selection"]["family"]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    x = np.arange(len(fams))
    for k, (vals, lab, col) in enumerate(((ct.loc[fams, "Val_MAPE_%"], "Validation 2025-H1", PAL["neutral"]),
                                          (ct.loc[fams, "Test_MAPE_%"], "Test 2025-H2", PAL["blue"]),
                                          (bs.loc[fams, "Mean_MAPE_pct"], "Backtest mean (7 folds)", PAL["orange"]))):
        ax.bar(x + (k - 1) * 0.27, vals, 0.27, color=col, label=lab)
        for i, v in enumerate(vals):
            ax.text(x[i] + (k - 1) * 0.27, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x, [f"{f}\n{ct.loc[f, 'Specification']}" + ("\n[selected]" if f == sel else "") for f in fams],
                  fontsize=8.5)
    ax.set_ylabel("MAPE %")
    ax.set_title("Forecast accuracy by model (MAPE, lower is better)")
    ax.legend()
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    _save(fig, "forecast_model_comparison.png", out_dir, saved)

    # 8 backtest -----------------------------------------------------------------------------------
    fo = R["backtest"]["folds"]
    bh = R["backtest"]["by_horizon"].set_index("Family")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
    for f in fams:
        g = fo[fo["Family"] == f]
        axes[0].plot(g["Origin"], g["MAPE_%"], marker="o", color=FAMILY_COLORS[f], linewidth=2.4 if f == sel else 1.3,
                     label=f)
        axes[1].plot(bh.columns, bh.loc[f], marker="o", color=FAMILY_COLORS[f], linewidth=2.4 if f == sel else 1.3)
    axes[0].set_xlabel("Forecast origin (last training month)")
    axes[0].set_ylabel("6-month MAPE %")
    axes[0].set_title("Rolling-origin backtest: MAPE per fold")
    axes[0].legend(fontsize=8)
    axes[1].set_xlabel("Months ahead")
    axes[1].set_ylabel("Mean absolute % error")
    axes[1].set_title("Error by forecast horizon (all folds)")
    fig.tight_layout()
    _save(fig, "backtest_results.png", out_dir, saved)

    # 9 validation / test forecasts -------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for ax, (key, act, title) in zip(axes, (("val_forecasts", R["split"]["valid"], "Validation (fit on 2023-2024)"),
                                            ("test_forecasts", R["split"]["test"], "Test (fit on 2023-2025H1)"))):
        ax.plot(act.index, act.values, color=PAL["text"], marker="o", linewidth=2.2, label="Actual")
        for f in fams:
            fc_ = R["comparison"][key][f]
            ax.plot(fc_.index, fc_["Forecast"], color=FAMILY_COLORS[f], linewidth=2.2 if f == sel else 1.2,
                    linestyle="-" if f == sel else "--", label=f)
        ax.set_title(title)
        ax.yaxis.set_major_formatter(lfmt)
        ax.tick_params(axis="x", labelrotation=30)
    axes[0].legend(fontsize=8)
    fig.suptitle("Actual vs model forecasts on the evaluation windows", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, "validation_test_forecasts.png", out_dir, saved)

    # 10 actual vs forecast (final) -------------------------------------------------------------------
    ft = R["forecast_table"].copy()
    ft["Month"] = pd.to_datetime(ft["Month"])
    hist = ft[ft["Type"] == "Historical actual"]
    fut = ft[ft["Type"].str.startswith("Future")]
    ev = ft[ft["Type"].str.startswith(("Validation", "Test"))]
    fig, ax = plt.subplots(figsize=(13, 5.4))
    ax.axvspan(y.index[N_TRAIN] - pd.Timedelta(days=15), y.index[N_TRAIN + N_VALID] - pd.Timedelta(days=15),
               color="#fdf1e8", alpha=0.8, zorder=0)
    ax.axvspan(y.index[N_TRAIN + N_VALID] - pd.Timedelta(days=15), y.index[-1] + pd.Timedelta(days=15),
               color="#e8f1fc", alpha=0.8, zorder=0)
    ax.axvspan(fut["Month"].min() - pd.Timedelta(days=15), fut["Month"].max() + pd.Timedelta(days=15),
               color="#eef7f2", alpha=0.9, zorder=0)
    ax.plot(hist["Month"], hist["Actual_Revenue"], color=PAL["blue"], marker="o", markersize=4, linewidth=2,
            label="Actual revenue")
    ax.plot(ev["Month"], ev["Forecast"], color=PAL["orange"], linestyle="--", marker="o", markersize=4, linewidth=1.6,
            label="Selected model on validation / test (out-of-sample)")
    ax.fill_between(fut["Month"], fut["Lower_95"], fut["Upper_95"], color=PAL["orange"], alpha=0.15, label="95% interval")
    ax.fill_between(fut["Month"], fut["Lower_80"], fut["Upper_80"], color=PAL["orange"], alpha=0.28, label="80% interval")
    ax.plot(fut["Month"], fut["Forecast"], color=PAL["orange"], marker="o", linewidth=2.4, label="Future forecast")
    top = max(hist["Actual_Revenue"].max(), fut["Upper_95"].max()) * 1.12
    for x0, lab in ((y.index[0], "Training 2023-2024"), (y.index[N_TRAIN], "Validation"), (y.index[N_TRAIN + N_VALID], "Test"),
                    (fut["Month"].min(), "Forecast 2026-H1")):
        ax.text(x0, top * 0.97, lab, fontsize=9, color=PAL["muted"], va="top")
    ax.set_ylim(0, top)
    ax.yaxis.set_major_formatter(lfmt)
    ax.set_ylabel("Monthly revenue (₹ lakh)")
    ax.set_title(f"Actual vs forecast revenue - {sel}: {R['selection']['spec']}")
    ax.legend(loc="upper left", fontsize=8.5, bbox_to_anchor=(0.0, 0.9))
    _note(fig, "Validation forecasts fit on 2023-2024; test forecasts fit on 2023-01..2025-06; future forecast fit on all 36 "
               "months. Intervals are model-based prediction intervals.")
    fig.tight_layout()
    _save(fig, "actual_vs_forecast.png", out_dir, saved)

    # 11 dimension forecasts ------------------------------------------------------------------------
    dfc = R["dimension"]["forecasts"]
    if len(dfc):
        levels = dfc[["Dimension", "Level"]].drop_duplicates().values.tolist()
        n = len(levels)
        cols = min(3, n)
        rows_ = int(np.ceil(n / cols))
        fig, axes = plt.subplots(rows_, cols, figsize=(4.6 * cols, 3.2 * rows_), squeeze=False)
        d = R["data"]["delivered"]
        for k, (dim, lvl) in enumerate(levels):
            ax = axes[k // cols][k % cols]
            h = d[d[dim] == lvl].groupby(pd.Grouper(key="Order_Date", freq="MS"))["Sales"].sum()
            f = dfc[(dfc["Dimension"] == dim) & (dfc["Level"] == lvl)]
            ax.plot(h.index, h.values, color=PAL["blue"], linewidth=1.5)
            ax.fill_between(pd.to_datetime(f["Month"]), f["Lower_80"], f["Upper_80"], color=PAL["orange"], alpha=0.25)
            ax.plot(pd.to_datetime(f["Month"]), f["Forecast"], color=PAL["orange"], linewidth=2)
            ax.set_title(f"{dim}: {lvl}", fontsize=10)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"₹{v / 1000:,.0f}k"))
            ax.tick_params(axis="x", labelsize=7, labelrotation=30)
        for k in range(n, rows_ * cols):
            axes[k // cols][k % cols].axis("off")
        fig.suptitle("Published category / region forecasts (test MAPE <= 20% and better than both baselines; 80% interval)",
                     x=0.01, ha="left", fontsize=12, fontweight="bold")
        fig.tight_layout()
        _save(fig, "forecast_by_dimension.png", out_dir, saved)

    # 12 interactive Plotly -------------------------------------------------------------------------
    try:
        import plotly.graph_objects as go
        g = go.Figure()
        g.add_trace(go.Scatter(x=hist["Month"], y=hist["Actual_Revenue"], name="Actual", mode="lines+markers",
                               line={"color": PAL["blue"]}))
        g.add_trace(go.Scatter(x=ev["Month"], y=ev["Forecast"], name="Out-of-sample forecast (validation/test)",
                               mode="lines+markers", line={"color": PAL["orange"], "dash": "dash"}))
        g.add_trace(go.Scatter(x=list(fut["Month"]) + list(fut["Month"][::-1]),
                               y=list(fut["Upper_95"]) + list(fut["Lower_95"][::-1]), fill="toself",
                               fillcolor="rgba(235,104,52,0.15)", line={"width": 0}, name="95% interval"))
        g.add_trace(go.Scatter(x=fut["Month"], y=fut["Forecast"], name="Future forecast", mode="lines+markers",
                               line={"color": PAL["orange"], "width": 3}))
        g.update_layout(title=f"Monthly revenue: actual vs forecast ({sel}) - synthetic data", template="plotly_white",
                        yaxis_title="Revenue (Rs)", hovermode="x unified")
        p = out_dir / "actual_vs_forecast_interactive.html"
        g.write_html(p, include_plotlyjs="cdn")
        saved.append(p)
    except ImportError:
        pass
    return saved


# =============================================================================
# 8. REPORT
# =============================================================================
def write_forecasting_report(R: dict, path: Path = REPORT_FILE) -> Path:
    """Forecasting methodology report; every number comes from R."""
    from src.eda import _md_table
    y, e = R["y"], R["eda"]
    sel_f, sel_s = R["selection"]["family"], R["selection"]["spec"]
    ct = R["comparison"]["table"]
    c = ct.set_index("Family")
    bs = R["backtest"]["summary"].set_index("Family")
    fut = R["future"]["forecast"]
    tr = e["trend"]
    yr = e["yearly"].set_index("Year")
    si = e["seasonal_index"].set_index("Month_Number")
    adf = R["adf"].set_index("Series")

    def tbl(df, cols, fmt=None):
        d = df[cols].copy()
        for k, fn in (fmt or {}).items():
            d[k] = d[k].map(lambda v, fn=fn: "" if pd.isna(v) else fn(v))
        d.columns = [str(col) for col in d.columns]
        return _md_table(d)

    f1 = lambda v: f"{v:.1f}"          # noqa: E731
    f3 = lambda v: f"{v:.3f}"          # noqa: E731
    money = inr
    L = ["# Sales Forecasting & Time-Series Revenue Forecasting - Step 9\n",
         f"> **{config.DATASET_LABEL}.** Forecasts describe the synthetic dataset from Step 2 (seed 42).\n"]
    L += ["## 1. Objective\n",
          "Forecast total monthly revenue for the next months from the historical sales series, with honest uncertainty, "
          "and show that the chosen model adds value over simple baselines.\n",
          "## 2. Data source\n",
          f"`{config.CLEAN_DATA_FILE.relative_to(config.PROJECT_ROOT)}` (Step 3 cleaned order lines). Revenue = Sales on "
          "Delivered lines (the project-wide revenue rule; Returned/Cancelled lines carry no revenue).\n",
          _md_table(R["data"]["quality"]), ""]
    L += ["## 3. Forecasting frequency\n",
          "**Monthly.** Every one of the 1,096 days has orders, and all 36 months have Delivered sales, so monthly totals are "
          "complete. Monthly is the standard planning period, and 36 observations are enough for simple models and a "
          "backtest; weekly data would be noisier (about 12 orders a day), and quarterly would leave only 12 points.\n",
          "## 4. Target variable\n",
          "`Revenue` = sum of Delivered Sales (Rs) per calendar month, company total (`data/processed/monthly_sales_timeseries.csv`, "
          "which also holds profit, quantity, orders, active customers, AOV and margin).\n",
          "## 5. Time period\n",
          f"{y.index[0]:%Y-%m} to {y.index[-1]:%Y-%m} ({len(y)} months). **Forecast horizon: {HORIZON} months** "
          f"({fut.index[0]:%Y-%m} to {fut.index[-1]:%Y-%m}). Six months is the horizon that was actually evaluated on the "
          "validation, test and backtest windows; a 12-month horizon would extrapolate twice as far as anything tested, with "
          "only three seasonal cycles of history.\n",
          "## 6. Data preparation\n",
          "- Dates parsed and validated (no invalid or missing dates, no duplicate lines, no Delivered line with Sales <= 0).",
          "- Aggregated to month starts; the monthly index was re-indexed to a complete calendar so that any gap would show "
          "as missing (NaN) rather than zero - there were none, so no filling was needed.",
          f"- Monthly totals reconcile with total Delivered sales ({inr(y.sum())}).\n"]
    L += ["## 7. Exploratory analysis\n",
          "**Trend.** " + f"Revenue rose from an average of {inr(tr['first_12_mean'])}/month in the first 12 months to "
          f"{inr(tr['last_12_mean'])} in the last 12 (linear trend +{inr(tr['slope_per_month'])} per month, R² {tr['r2']:.2f}). "
          f"Annual growth: {yr['YoY_Growth_%'].iloc[1]:.0f}% (2024) and {yr['YoY_Growth_%'].iloc[2]:.0f}% (2025) - growth is "
          "positive but slowing.\n",
          tbl(e["yearly"], ["Year", "Revenue", "Mean_Month", "Std_Month", "CV_%", "YoY_Growth_%", "Q4_Share_%"],
              {"Revenue": money, "Mean_Month": money, "Std_Month": money, "CV_%": f1, "YoY_Growth_%": f1, "Q4_Share_%": f1}),
          "\n**Seasonality.** October was the highest month in all three years (seasonal index "
          f"{si.loc[10, 2023]:.2f}, {si.loc[10, 2024]:.2f}, {si.loc[10, 2025]:.2f}); November and December were also above "
          "average each year. Other months have no consistent pattern (e.g. February ranges "
          f"{si.loc[2, 'Min_Index']:.2f}-{si.loc[2, 'Max_Index']:.2f}). STL seasonal strength {e['strength']['seasonal']:.2f}; "
          f"Kruskal-Wallis test of the monthly index p = {e['kruskal']['p']:.3f}. With only three observations per calendar "
          "month, the evidence supports a **Q4 / October peak** but not a detailed month-by-month profile.\n",
          tbl(e["seasonal_index"], ["Month_Number", 2023, 2024, 2025, "Mean_Index", "Min_Index", "Max_Index"],
              {k: f3 for k in (2023, 2024, 2025, "Mean_Index", "Min_Index", "Max_Index")}),
          "\n**Volatility.** " + f"Average absolute month-on-month change {e['volatility']['mom_mean_abs_%']:.0f}%. The "
          "12-month rolling standard deviation rose with the level while the coefficient of variation fell (relative "
          "volatility declined). Months flagged by the STL residual (|z| >= 2):\n",
          tbl(e["decomposition"][e["decomposition"]["Flag"] != ""], ["Month", "Revenue", "STL_Trend", "STL_Seasonal",
                                                                     "Residual_Z", "Flag"],
              {"Month": lambda d: d.strftime("%Y-%m"), "Revenue": money, "STL_Trend": money, "STL_Seasonal": money,
               "Residual_Z": f1}),
          "\n**Rolling statistics** (3- and 12-month windows; 12 months removes the seasonal cycle): the 12-month mean "
          "rises steadily (trend), the series is not stable in level, and absolute volatility is higher in 2024-2025 than in "
          "2023.\n"]
    L += ["## 8. Stationarity analysis\n",
          tbl(R["adf"], ["Series", "Observations", "ADF_Statistic", "p_value", "Critical_5%", "Conclusion"],
              {"ADF_Statistic": f3, "p_value": f3, "Critical_5%": f3}),
          f"\nThe level is non-stationary (p = {adf.loc['Revenue (level)', 'p_value']:.2f}); the log does not change that. "
          f"The first difference is stationary (p = {adf.loc['First difference', 'p_value']:.3f}), so **d = 1** is used for "
          "ARIMA. A seasonal difference alone is not sufficient (it leaves only 24 points and does not pass). ETS and Theta "
          "handle trend internally, so no transformation is applied for them.\n",
          "**ACF / PACF of the first difference** (approx. 95% bound +/-"
          f"{R['acf']['Approx_95%_Bound'].iloc[0]:.2f}): significant lags - ACF "
          + ", ".join(str(int(v)) for v in R["acf"].loc[R["acf"]["ACF_Significant"] & (R["acf"]["Lag"] > 0), "Lag"])
          + "; PACF " + ", ".join(str(int(v)) for v in R["acf"].loc[R["acf"]["PACF_Significant"] & (R["acf"]["Lag"] > 0), "Lag"])
          + ". A negative lag-1 autocorrelation points to an MA(1) or AR(1) term; lag 12 is borderline, so seasonal "
            "variants were tested but kept minimal.\n"]
    L += ["## 9. Baseline models\n",
          "- **Naive:** every future month = the last observed month.",
          "- **Seasonal naive:** every future month = the same month one year earlier.",
          "Both use residual-based prediction intervals (random-walk formulas).\n",
          "## 10. Advanced forecasting models\n",
          f"- **Exponential smoothing (ETS, statsmodels ETSModel)** - {len(ETS_CANDIDATES)} configurations: "
          + ", ".join(ETS_CANDIDATES) + ". Parameters estimated by maximum likelihood; seasonal variants require two full "
          "years, which the 24-month training window just meets.",
          f"- **ARIMA / SARIMA (statsmodels ARIMA)** - {len(ARIMA_CANDIDATES)} configurations chosen from the ADF/ACF/PACF "
          "evidence: " + ", ".join(ARIMA_CANDIDATES) + ". (A first implementation using SARIMAX's `trend='t'` turned out to "
          "model a trend in the *differenced* series - a quadratic path - and was replaced; see the code comment.)",
          "- **Theta method (optional model)** - simple exponential smoothing plus half the linear trend; its built-in "
          "seasonality test (lag-12 autocorrelation) decides whether to seasonally adjust first. Prophet is not installed "
          "and was not added (unnecessary dependency).\n",
          "**Configuration choice inside each family** (fit on train, score on validation; lowest validation MAE):\n",
          tbl(R["tuning"], ["Family", "Specification", "MAE", "RMSE", "MAPE_%", "WAPE_%", "Bias_%", "AIC", "Best_in_Family"],
              {"MAE": money, "RMSE": money, "MAPE_%": f1, "WAPE_%": f1, "Bias_%": f1, "AIC": f1}),
          "\nAIC is shown for reference only; it is not comparable across differencing orders or model families.\n"]
    L += ["## 11. Train / validation / test methodology\n",
          tbl(R["split"]["summary"], ["Split", "Start", "End", "Months", "Revenue"], {"Revenue": money}),
          "\nStrictly chronological, no shuffling. Validation forecasts are fitted on train only; test forecasts are refitted "
          "on train + validation; the future forecast is refitted on all 36 months. No model ever sees the months it "
          "forecasts.\n",
          "## 12. Backtesting\n",
          "Two evaluation windows of 6 months are a small sample, so a **rolling-origin (expanding-window) backtest** was run: "
          f"at each origin from {y.index[BACKTEST_ORIGINS[0] - 1]:%Y-%m} to {y.index[BACKTEST_ORIGINS[-1] - 1]:%Y-%m} the "
          f"model is fitted on all months up to the origin and forecasts the next {HORIZON} ({len(BACKTEST_ORIGINS)} folds). "
          "This checks whether a model is good in general or only on one window.\n",
          tbl(R["backtest"]["summary"], ["Family", "Folds", "Mean_MAE", "Mean_MAPE_pct", "Std_MAPE_pct", "Worst_MAPE_pct",
                                         "Mean_Bias_pct", "Folds_Won"],
              {"Mean_MAE": money, "Mean_MAPE_pct": f1, "Std_MAPE_pct": f1, "Worst_MAPE_pct": f1, "Mean_Bias_pct": f1}),
          "\n**Mean absolute % error by months ahead (all folds)**\n",
          tbl(R["backtest"]["by_horizon"].rename(columns=str), ["Family"] + [str(i) for i in range(1, HORIZON + 1)],
              {str(i): f1 for i in range(1, HORIZON + 1)}),
          "\nLimitation: all folds lie in 2025, so the backtest covers one year of business conditions.\n"]
    L += ["## 13. Evaluation metrics\n",
          "- **MAE** - average absolute error in Rs per month. **RMSE** - penalises large misses more.",
          "- **MAPE** - average absolute % error; safe here because no month has zero revenue.",
          "- **sMAPE / WAPE** - symmetric % error and total absolute error / total actual (reported for robustness).",
          "- **Bias** - (sum forecast - sum actual) / sum actual. **Interval coverage** - share of test months inside the "
          "95% interval.\n",
          "## 14. Model comparison\n",
          tbl(ct, ["Family", "Specification", "Val_MAE", "Val_RMSE", "Val_MAPE_%", "Test_MAE", "Test_RMSE", "Test_MAPE_%",
                   "Test_sMAPE_%", "Test_WAPE_%", "Test_Bias_%", "Test_95%_Interval_Coverage_%"],
              {"Val_MAE": money, "Val_RMSE": money, "Val_MAPE_%": f1, "Test_MAE": money, "Test_RMSE": money,
               "Test_MAPE_%": f1, "Test_sMAPE_%": f1, "Test_WAPE_%": f1, "Test_Bias_%": f1,
               "Test_95%_Interval_Coverage_%": f1}), ""]
    st = R["selection"]["table"]
    L += ["## 15. Final model selection\n",
          "**Rule (fixed before modelling):** lowest mean backtest MAPE among models that beat **both** baselines on test MAE; "
          "within 5% of that MAPE the simpler family wins. If no model beat the baselines, the better baseline would be kept.\n",
          tbl(st, ["Family", "Specification", "Mean_MAPE_pct", "Std_MAPE_pct", "Val_MAPE_%", "Test_MAPE_%", "Test_MAE",
                   "Beats_Both_Baselines_on_Test", "Selected"],
              {"Mean_MAPE_pct": f1, "Std_MAPE_pct": f1, "Val_MAPE_%": f1, "Test_MAPE_%": f1, "Test_MAE": money}),
          f"\n**Selected: {sel_f} - {sel_s}.** Test MAE {inr(c.loc[sel_f, 'Test_MAE'])} vs {inr(c.loc['Naive', 'Test_MAE'])} "
          f"(naive) and {inr(c.loc['Seasonal naive', 'Test_MAE'])} (seasonal naive); test MAPE {c.loc[sel_f, 'Test_MAPE_%']:.1f}%, "
          f"validation MAPE {c.loc[sel_f, 'Val_MAPE_%']:.1f}%, backtest mean MAPE {bs.loc[sel_f, 'Mean_MAPE_pct']:.1f}% "
          f"(naive {bs.loc['Naive', 'Mean_MAPE_pct']:.1f}%). "
          + ("Its seasonality test did not detect significant 12-month seasonality, so it forecasts level + trend only. "
             if not R["future"]["result"]["params"].get("seasonality_detected_by_theta_test", True) else "")
          + "Honest caveat: " + " and ".join(f"{f} ({bs.loc[f, 'Mean_MAPE_pct']:.1f}%)" for f in bs.index
                                          if bs.loc[f, "Mean_MAPE_pct"] < bs.loc[sel_f, "Mean_MAPE_pct"])
          + " had a slightly lower backtest MAPE but did not beat the naive forecast on the test window, so the top models "
            "are close and the ranking could change with more data.\n"]
    L += ["## 16. Future forecast\n",
          tbl(fut.reset_index(), ["Month", "Forecast", "Lower_80", "Upper_80", "Lower_95", "Upper_95"],
              {"Month": lambda d: d.strftime("%Y-%m"), "Forecast": money, "Lower_80": money, "Upper_80": money,
               "Lower_95": money, "Upper_95": money}),
          f"\nTotal forecast {fut.index[0]:%Y-%m}..{fut.index[-1]:%Y-%m}: **{inr(fut['Forecast'].sum())}** "
          f"(95% monthly intervals shown; they widen with the horizon). Model parameters: `{R['future']['result']['params']}`.\n",
          "**By business dimension.** Each category and region series (36 months) was tested the same way; a forecast is "
          f"published only if its test MAPE <= {DIMENSION_MAX_TEST_MAPE:.0f}% and it beats both baselines on test MAE.\n",
          tbl(R["dimension"]["evaluation"], ["Dimension", "Level", "Monthly_Mean_Revenue", "CV_%", "Selected_Test_MAPE_%",
                                             "Selected_Test_MAE", "Naive_Test_MAE", "Seasonal_Naive_Test_MAE",
                                             "Naive_Test_MAPE_%", "Published"],
              {"Monthly_Mean_Revenue": money, "CV_%": f1, "Selected_Test_MAPE_%": f1, "Selected_Test_MAE": money,
               "Naive_Test_MAE": money, "Seasonal_Naive_Test_MAE": money, "Naive_Test_MAPE_%": f1}),
          "\nThe baseline comparison uses MAE, so a series can be published with a slightly higher MAPE than naive "
          "(its errors are smaller in rupee terms, e.g. in high-revenue months).\n"]
    L += ["## 17. Business interpretation\n", _md_table(R["insights"]),
          "\nForecasts are estimates under the assumption that the 2023-2025 pattern continues; they are not guarantees. "
          "The forecast window (January-June) does not include the October peak - a 12-month plan would need a seasonal "
          "model and more history to quantify Q4.\n"]
    L += ["## 18. Limitations\n",
          "1. **Synthetic data** generated in Step 2.",
          "2. **Short history:** 36 months = 3 seasonal cycles; seasonal estimates rest on 3 values per month.",
          "3. **Small evaluation windows:** 6 validation + 6 test months; backtest folds all fall in 2025.",
          f"4. **Close competition:** the three non-baseline models' backtest MAPEs span "
          f"{bs.drop(['Naive', 'Seasonal naive'])['Mean_MAPE_pct'].min():.1f}-"
          f"{bs.drop(['Naive', 'Seasonal naive'])['Mean_MAPE_pct'].max():.1f}%.",
          "5. **No seasonal term in the selected model** - acceptable for a January-June horizon, not for Q4.",
          "6. **Univariate:** no promotions, prices, marketing or macro drivers; structural changes would not be anticipated.",
          f"7. **Wide intervals:** by month {HORIZON} the 95% interval spans "
          f"{inr(fut['Lower_95'].iloc[-1])}-{inr(fut['Upper_95'].iloc[-1])} around a forecast of {inr(fut['Forecast'].iloc[-1])} "
          f"(about +/-{100 * (fut['Upper_95'].iloc[-1] - fut['Forecast'].iloc[-1]) / fut['Forecast'].iloc[-1]:.0f}%).",
          "8. **Delivered revenue only;** returns/cancellations after month-end are not modelled.\n",
          "## 19. Reproducibility instructions\n",
          "```bash\npython src/forecasting.py                       # full pipeline (~1 min), QC checklist printed\n"
          "jupyter notebook notebooks/07_sales_forecasting.ipynb\n```\n",
          "```python\nimport joblib\na = joblib.load('models/forecasting_model.pkl')     # dict with the fitted statsmodels result\n"
          "a['fitted_model'].forecast(6)                      # reproduces data/processed/revenue_forecast.csv (future rows)\n```\n",
          f"All models are deterministic (maximum likelihood); the only simulation option (multiplicative ETS intervals) uses "
          f"seed {SEED}. statsmodels {statsmodels.__version__}.\n",
          "## Quality-control checklist\n", _md_table(R["qc"]),
          "\n## Output files\n",
          "- `data/processed/monthly_sales_timeseries.csv`, `data/processed/revenue_forecast.csv`",
          "- `models/forecasting_model.pkl`, `models/forecasting_metadata.json`",
          "- `outputs/tables/forecast_*.csv` (incl. `forecast_model_comparison.csv`, `forecast_backtest_*.csv`)",
          "- `outputs/figures/forecasting/` - " + ", ".join(p_.name for p_ in R.get("figures", []))]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    run_forecasting()
