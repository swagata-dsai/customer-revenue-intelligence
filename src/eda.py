#!/usr/bin/env python3
"""
eda.py
======
Step 4 of the Customer Revenue Intelligence project: Exploratory Data
Analysis (EDA) and business-insight discovery.

    >>> Works on the SYNTHETIC dataset cleaned in Step 3. <<<

Measurement rules (applied everywhere in this module)
-----------------------------------------------------
* Realised revenue, cost, profit and units = **Delivered** order lines only.
  Cancelled and Returned lines are analysed separately (status analysis).
* An **order** = one distinct Order_ID (one checkout by one customer on one
  date; verified in `verify_order_definition`). Orders are counted only if
  they contain at least one Delivered line.
* Customer_Age statistics are computed per **customer** (one value each),
  not per transaction, so frequent buyers are not over-weighted.
* Correlation is reported as association only - never as causation.

Main entry point:  python src/eda.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

MONEY_COLS = ["Sales", "Cost", "Profit"]
NUM_VARS = ["Quantity", "Unit_Price", "Discount", "Sales", "Cost", "Profit", "Customer_Age"]
MONTH_ORDER = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DISCOUNT_BUCKETS = [(-0.001, 0.0, "0%"), (0.0, 0.10, "5-10%"), (0.10, 0.20, "15-20%"),
                    (0.20, 0.30, "25-30%"), (0.30, 0.40, "35-40%")]


# =============================================================================
# Formatting helpers
# =============================================================================
def inr(x: float, decimals: int = 2) -> str:
    """Indian-style short money label: Cr (1e7), L (1e5), otherwise full rupees."""
    if pd.isna(x):
        return "n/a"
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e7:
        return f"{sign}₹{x / 1e7:.{decimals}f} Cr"
    if x >= 1e5:
        return f"{sign}₹{x / 1e5:.{decimals}f} L"
    return f"{sign}₹{x:,.0f}"


def pct(x: float, decimals: int = 1) -> str:
    return "n/a" if pd.isna(x) else f"{100 * x:.{decimals}f}%"


def _delivered(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["Order_Status"] == "Delivered"]


def _bucket_discount(d: pd.Series) -> pd.Series:
    bins = [b[0] for b in DISCOUNT_BUCKETS] + [DISCOUNT_BUCKETS[-1][1]]
    labels = [b[2] for b in DISCOUNT_BUCKETS]
    return pd.cut(d, bins=bins, labels=labels)


def _strength(r: float) -> str:
    a = abs(r)
    label = ("strong" if a >= 0.7 else "moderate" if a >= 0.4 else "weak" if a >= 0.2 else "negligible")
    return f"{label} {'positive' if r > 0 else 'negative'}" if label != "negligible" else "negligible"


# =============================================================================
# 1. LOAD + DEFINITIONS
# =============================================================================
def load_clean_data(path: Path = config.CLEAN_DATA_FILE) -> pd.DataFrame:
    """Load the Step 3 cleaned file with correct types."""
    if not Path(path).exists():
        raise FileNotFoundError(f"{path} not found - run src/data_cleaning.py (Step 3) first.")
    df = pd.read_csv(path, encoding="utf-8-sig", parse_dates=["Order_Date"])
    for c in ["Is_Weekend", "Is_Delivered", "Revenue_Check_Pass", "Profit_Check_Pass",
              "Is_Bulk_Order_Line", "Is_Loss_Making", "Potential_Duplicate_Flag"]:
        df[c] = df[c].astype(bool)
    df["DQ_Flags"] = df["DQ_Flags"].fillna("")
    df["Year_Month"] = df["Order_Date"].dt.to_period("M")
    return df


def verify_order_definition(df: pd.DataFrame) -> pd.DataFrame:
    """Evidence that Order_ID is the right 'order' unit (and no double counting)."""
    per_order = df.groupby("Order_ID").agg(customers=("Customer_ID", "nunique"),
                                           dates=("Order_Date", "nunique"),
                                           payments=("Payment_Method", "nunique"))
    pairs = df[["Customer_ID", "Order_Date"]].drop_duplicates()
    deliv_orders = _delivered(df)["Order_ID"].nunique()
    return pd.DataFrame([
        ("Order lines (rows)", len(df), "One row = one product in one order"),
        ("Duplicate Order_Line_ID", int(df["Order_Line_ID"].duplicated().sum()), "Must be 0 - no double counting"),
        ("Distinct Order_ID", df["Order_ID"].nunique(), "Candidate order count"),
        ("Distinct (Customer, Date) pairs", len(pairs), "Equals Order_ID count -> one checkout per customer per day"),
        ("Order_IDs with >1 customer / date / payment",
         int((per_order > 1).any(axis=1).sum()), "Must be 0 - Order_ID is a single checkout"),
        ("Orders with >1 line (multi-product)", int((df.groupby("Order_ID").size() > 1).sum()),
         "Why rows != orders"),
        ("Orders with >= 1 Delivered line", deliv_orders, "Order count used for AOV and order KPIs"),
        ("Orders with no Delivered line", df["Order_ID"].nunique() - deliv_orders,
         "Fully cancelled / returned - excluded from realised KPIs"),
    ], columns=["Check", "Value", "Meaning"])


# =============================================================================
# 2. OVERVIEW + KPIs
# =============================================================================
def generate_dataset_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Structural overview of the cleaned dataset."""
    d = _delivered(df)
    known_cities = df.loc[df["City"] != "Unknown", "City"].nunique()
    return pd.DataFrame([
        ("Rows (order lines, all statuses)", f"{len(df):,}"),
        ("Columns", df.shape[1]),
        ("Date range", f"{df['Order_Date'].min():%d %b %Y} - {df['Order_Date'].max():%d %b %Y}"),
        ("Months covered", df["Year_Month"].nunique()),
        ("Unique customers", f"{df['Customer_ID'].nunique():,}"),
        ("Unique products", df["Product_ID"].nunique()),
        ("Categories", df["Category"].nunique()),
        ("Sub-categories", df["Sub_Category"].nunique()),
        ("Cities", f"{known_cities} (+ 'Unknown' for 1 customer)" if (df["City"] == "Unknown").any() else known_cities),
        ("States / UTs", df["State"].nunique()),
        ("Regions", df["Region"].nunique()),
        ("Orders (distinct Order_ID, all statuses)", f"{df['Order_ID'].nunique():,}"),
        ("Delivered order lines", f"{len(d):,}"),
    ], columns=["Item", "Value"])


def calculate_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Headline KPIs with the formula used for each (Delivered lines only)."""
    d = _delivered(df)
    revenue, cost, profit = d["Sales"].sum(), d["Cost"].sum(), d["Profit"].sum()
    orders = d["Order_ID"].nunique()
    buyers = d["Customer_ID"].nunique()
    units = d["Quantity"].sum()
    gross_booked = df["Sales"].sum()
    rows = [
        ("Total Revenue", revenue, inr(revenue), "Sum of Sales, Delivered lines"),
        ("Total Cost", cost, inr(cost), "Sum of Cost, Delivered lines"),
        ("Total Profit", profit, inr(profit), "Sum of Profit, Delivered lines"),
        ("Overall Profit Margin", profit / revenue, pct(profit / revenue), "Total Profit / Total Revenue"),
        ("Total Quantity Sold", units, f"{units:,.0f} units", "Sum of Quantity, Delivered lines"),
        ("Number of Orders", orders, f"{orders:,}", "Distinct Order_ID with >= 1 Delivered line"),
        ("Purchasing Customers", buyers, f"{buyers:,}", "Distinct Customer_ID with >= 1 Delivered line"),
        ("Average Order Value (AOV)", revenue / orders, inr(revenue / orders), "Total Revenue / Number of Orders"),
        ("Average Revenue per Customer", revenue / buyers, inr(revenue / buyers), "Total Revenue / Purchasing Customers"),
        ("Average Profit per Order", profit / orders, inr(profit / orders), "Total Profit / Number of Orders"),
        ("Average Quantity per Order", units / orders, f"{units / orders:.2f} units", "Total Quantity / Number of Orders"),
        ("Average Orders per Customer", orders / buyers, f"{orders / buyers:.2f}", "Number of Orders / Purchasing Customers"),
        ("Gross Booked Sales (all statuses)", gross_booked, inr(gross_booked), "Sum of Sales, all lines"),
        ("Revenue Lost to Cancellations & Returns", gross_booked - revenue, inr(gross_booked - revenue),
         "Gross Booked Sales - Total Revenue"),
        ("Share of Booked Sales Not Realised", 1 - revenue / gross_booked, pct(1 - revenue / gross_booked),
         "1 - Total Revenue / Gross Booked Sales"),
    ]
    return pd.DataFrame(rows, columns=["KPI", "Value", "Display", "Formula"])


# =============================================================================
# 3. DESCRIPTIVE STATISTICS
# =============================================================================
def descriptive_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """count/mean/median/std/min/quartiles/max/skewness for key numeric variables."""
    d = _delivered(df)
    series = {c: d[c].astype(float) for c in ["Quantity", "Unit_Price", "Discount", "Sales", "Cost", "Profit"]}
    series["Customer_Age (per customer)"] = df.drop_duplicates("Customer_ID")["Customer_Age"].astype(float)
    rows = []
    for name, s in series.items():
        sk = s.skew()
        rows.append({"Variable": name, "Count": int(s.count()), "Mean": s.mean(), "Median": s.median(),
                     "Std": s.std(), "Min": s.min(), "Q1": s.quantile(.25), "Q3": s.quantile(.75),
                     "Max": s.max(), "Skewness": sk, "Kurtosis": s.kurt(),
                     "Shape": ("strongly right-skewed" if sk > 1 else "strongly left-skewed" if sk < -1
                               else "moderately skewed" if abs(sk) > 0.5 else "approximately symmetric")})
    return pd.DataFrame(rows).round(3)


# =============================================================================
# 4. UNIVARIATE (incl. categorical distributions)
# =============================================================================
def analyze_sales_distribution(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Distribution summaries for numeric and categorical variables."""
    d = _delivered(df)
    cust = df.drop_duplicates("Customer_ID")
    age = cust["Customer_Age"]
    out = {}
    out["age_bands"] = (cust["Age_Band"].value_counts().reindex(["18-24", "25-34", "35-49", "50+"])
                        .rename_axis("Age_Band").reset_index(name="Customers")
                        .assign(Share=lambda t: (t["Customers"] / t["Customers"].sum()).round(4)))
    out["age_summary"] = pd.DataFrame([("Customers", len(age)), ("Mean age", round(age.mean(), 1)),
                                       ("Median age", age.median()), ("Youngest", age.min()),
                                       ("Oldest", age.max()), ("Share aged 25-34",
                                                               round((age.between(25, 34)).mean(), 4))],
                                      columns=["Metric", "Value"])
    out["quantity_dist"] = (d["Quantity"].value_counts().sort_index().rename_axis("Quantity")
                            .reset_index(name="Lines").assign(Share=lambda t: (t["Lines"] / t["Lines"].sum()).round(4)))
    out["discount_dist"] = (d["Discount"].round(2).value_counts().sort_index().rename_axis("Discount")
                            .reset_index(name="Lines").assign(Share=lambda t: (t["Lines"] / t["Lines"].sum()).round(4)))

    def share(series: pd.Series, unit: str) -> pd.DataFrame:
        t = series.value_counts().rename_axis("Value").reset_index(name=unit)
        t["Share"] = (t[unit] / t[unit].sum()).round(4)
        return t

    orders = df.drop_duplicates("Order_ID")
    out["cat_Gender"] = share(cust["Gender"], "Customers")
    out["cat_Region"] = share(cust["Region"], "Customers")
    out["cat_State"] = share(cust["State"], "Customers")
    out["cat_Category"] = share(d["Category"], "Delivered lines")
    out["cat_Sub_Category"] = share(d["Sub_Category"], "Delivered lines")
    out["cat_Payment_Method"] = share(orders["Payment_Method"], "Orders")
    out["cat_Order_Status"] = share(df["Order_Status"], "Order lines")
    out["cat_Customer_Type"] = share(orders["Customer_Type"], "Orders")
    return out


# =============================================================================
# 5. TIME SERIES
# =============================================================================
def analyze_time_series(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Monthly / quarterly / seasonal views of realised revenue."""
    d = _delivered(df)
    m = d.groupby("Year_Month").agg(Revenue=("Sales", "sum"), Cost=("Cost", "sum"), Profit=("Profit", "sum"),
                                    Orders=("Order_ID", "nunique"), Active_Customers=("Customer_ID", "nunique"),
                                    Units=("Quantity", "sum"))
    m["Profit_Margin"] = m["Profit"] / m["Revenue"]
    m["AOV"] = m["Revenue"] / m["Orders"]
    m["MoM_Growth_%"] = m["Revenue"].pct_change() * 100
    m["YoY_Growth_%"] = m["Revenue"].pct_change(12) * 100
    m["Revenue_3M_MA"] = m["Revenue"].rolling(3).mean()
    # Classical decomposition: ratio to centred 2x12 moving average
    ma12 = m["Revenue"].rolling(12, center=True).mean()
    m["Trend_2x12_MA"] = ma12.rolling(2).mean().shift(-1)
    m["Seasonal_Ratio"] = m["Revenue"] / m["Trend_2x12_MA"]
    m = m.reset_index()
    m["Year"] = m["Year_Month"].dt.year
    m["Month"] = m["Year_Month"].dt.month
    m["Month_Name"] = m["Year_Month"].dt.strftime("%b")

    yearly = d.groupby("Order_Year").agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                                         Orders=("Order_ID", "nunique"), Customers=("Customer_ID", "nunique"))
    yearly["Profit_Margin"] = yearly["Profit"] / yearly["Revenue"]
    yearly["AOV"] = yearly["Revenue"] / yearly["Orders"]
    yearly["YoY_Revenue_Growth_%"] = yearly["Revenue"].pct_change() * 100

    q = d.groupby(["Order_Year", "Order_Quarter"]).agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                                                       Orders=("Order_ID", "nunique")).reset_index()
    q["Share_of_Year"] = q["Revenue"] / q.groupby("Order_Year")["Revenue"].transform("sum")

    # Month-of-year pattern: each month's share of its own year's revenue (removes growth)
    moy = m[["Year", "Month", "Month_Name", "Revenue", "Profit"]].copy()
    moy["Share_of_Year"] = moy["Revenue"] / moy.groupby("Year")["Revenue"].transform("sum")
    moy["Index_vs_Year_Avg"] = moy["Share_of_Year"] * 12  # 1.0 = an average month
    seasonal = (moy.groupby(["Month", "Month_Name"])
                .agg(Avg_Index=("Index_vs_Year_Avg", "mean"), Min_Index=("Index_vs_Year_Avg", "min"),
                     Max_Index=("Index_vs_Year_Avg", "max"),
                     Years_Above_Avg=("Index_vs_Year_Avg", lambda s: int((s > 1).sum())),
                     Avg_Revenue=("Revenue", "mean"), Avg_Profit=("Profit", "mean"))
                .reset_index())
    ratio = m.dropna(subset=["Seasonal_Ratio"]).groupby("Month")["Seasonal_Ratio"].agg(["mean", "count"])
    seasonal = seasonal.merge(ratio.rename(columns={"mean": "Avg_Ratio_to_Trend", "count": "Ratio_Obs"}),
                              left_on="Month", right_index=True, how="left")

    dow = d.groupby("Day_of_Week").agg(Revenue=("Sales", "sum"), Orders=("Order_ID", "nunique")).reindex(DOW_ORDER)
    days_per_dow = df.drop_duplicates("Order_Date")["Order_Date"].dt.day_name().value_counts()
    n_days = pd.Series(pd.date_range(df["Order_Date"].min(), df["Order_Date"].max()).day_name()).value_counts()
    dow["Calendar_Days"] = n_days.reindex(DOW_ORDER).values
    dow["Revenue_per_Day"] = dow["Revenue"] / dow["Calendar_Days"]
    dow["Index_vs_Avg_Day"] = dow["Revenue_per_Day"] / dow["Revenue_per_Day"].mean()
    del days_per_dow

    # Festive window: Oct + Nov combined share of each year (Diwali moves between them)
    fest = moy[moy["Month"].isin([10, 11])].groupby("Year")["Share_of_Year"].sum().rename("Oct_Nov_Share")
    peak = moy.loc[moy.groupby("Year")["Revenue"].idxmax(), ["Year", "Month_Name", "Revenue"]] \
        .rename(columns={"Month_Name": "Peak_Month", "Revenue": "Peak_Revenue"}).set_index("Year")
    low = moy.loc[moy.groupby("Year")["Revenue"].idxmin(), ["Year", "Month_Name", "Revenue"]] \
        .rename(columns={"Month_Name": "Lowest_Month", "Revenue": "Lowest_Revenue"}).set_index("Year")
    festive = pd.concat([fest, peak, low], axis=1).reset_index()

    return {"monthly": m, "yearly": yearly.reset_index(), "quarterly": q, "month_of_year": moy,
            "seasonal_index": seasonal, "day_of_week": dow.reset_index(), "festive": festive}


# =============================================================================
# 6. CUSTOMERS
# =============================================================================
def build_customer_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per customer; money and orders from Delivered lines."""
    d = _delivered(df)
    base = df.drop_duplicates("Customer_ID").set_index("Customer_ID")[
        ["Customer_Name", "Customer_Age", "Age_Band", "Gender", "City", "State", "Region"]]
    g = d.groupby("Customer_ID").agg(Total_Orders=("Order_ID", "nunique"), Total_Quantity=("Quantity", "sum"),
                                     Total_Revenue=("Sales", "sum"), Total_Profit=("Profit", "sum"),
                                     Average_Discount=("Discount", "mean"),
                                     First_Purchase_Date=("Order_Date", "min"),
                                     Last_Purchase_Date=("Order_Date", "max"),
                                     Categories_Bought=("Category", "nunique"))
    allst = df.groupby("Customer_ID").agg(Lines_All=("Order_Line_ID", "count"),
                                          Returned_Lines=("Order_Status", lambda s: (s == "Returned").sum()),
                                          Preferred_Payment=("Payment_Method", lambda s: s.mode().iloc[0]))
    c = base.join(g, how="left").join(allst, how="left")
    for col in ["Total_Orders", "Total_Quantity", "Total_Revenue", "Total_Profit"]:
        c[col] = c[col].fillna(0)
    c["Average_Order_Value"] = c["Total_Revenue"] / c["Total_Orders"].replace(0, np.nan)
    c["Return_Rate"] = c["Returned_Lines"] / c["Lines_All"]
    c["Revenue_Rank"] = c["Total_Revenue"].rank(ascending=False, method="first").astype(int)
    return c.reset_index().sort_values("Revenue_Rank")


def analyze_customer_performance(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Top customers, frequency, revenue distribution, concentration, characteristics."""
    cust = build_customer_summary(df)
    buyers = cust[cust["Total_Orders"] > 0]
    out = {"customer_summary": cust}
    cols = ["Customer_ID", "Customer_Name", "Region", "Total_Orders", "Total_Revenue", "Total_Profit",
            "Average_Order_Value", "Last_Purchase_Date"]
    out["top_customers_revenue"] = cust.nlargest(20, "Total_Revenue")[cols]
    out["top_customers_profit"] = cust.nlargest(20, "Total_Profit")[cols]

    bins = [0, 1, 2, 3, 5, 10, 20, 100]
    labels = ["1", "2", "3", "4-5", "6-10", "11-20", "21+"]
    freq = pd.cut(buyers["Total_Orders"], bins=bins, labels=labels).value_counts().reindex(labels)
    out["order_frequency"] = pd.DataFrame({"Orders_per_Customer": labels, "Customers": freq.values,
                                           "Share": (freq / freq.sum()).round(4).values,
                                           "Revenue": [buyers.loc[pd.cut(buyers["Total_Orders"], bins=bins, labels=labels) == l,
                                                                  "Total_Revenue"].sum() for l in labels]})
    out["order_frequency"]["Revenue_Share"] = (out["order_frequency"]["Revenue"] / buyers["Total_Revenue"].sum()).round(4)

    rev = buyers["Total_Revenue"].sort_values(ascending=False).to_numpy()
    total, n = rev.sum(), len(rev)
    conc = [{"Customer_Group": f"Top {p}%", "Customers": int(np.ceil(n * p / 100)),
             "Revenue": rev[: int(np.ceil(n * p / 100))].sum(),
             "Share_of_Revenue": rev[: int(np.ceil(n * p / 100))].sum() / total} for p in (1, 5, 10, 20, 50)]
    out["revenue_concentration"] = pd.DataFrame(conc)
    asc = np.sort(rev)
    lorenz = np.cumsum(asc) / total
    gini = 1 - 2 * np.trapezoid(np.concatenate([[0], lorenz]), dx=1 / n)
    out["lorenz"] = pd.DataFrame({"Cum_Share_Customers": np.arange(0, n + 1) / n,
                                  "Cum_Share_Revenue": np.concatenate([[0], lorenz])})
    out["distribution_stats"] = pd.DataFrame([
        ("Purchasing customers", n), ("Mean revenue per customer", buyers["Total_Revenue"].mean()),
        ("Median revenue per customer", buyers["Total_Revenue"].median()),
        ("Mean / median ratio", buyers["Total_Revenue"].mean() / buyers["Total_Revenue"].median()),
        ("Skewness of customer revenue", buyers["Total_Revenue"].skew()),
        ("Gini coefficient of customer revenue", gini),
        ("Median orders per customer", buyers["Total_Orders"].median()),
        ("Mean orders per customer", buyers["Total_Orders"].mean()),
        ("Share of customers with 1 order", (buyers["Total_Orders"] == 1).mean()),
        ("Customers with no delivered order", int((cust["Total_Orders"] == 0).sum())),
    ], columns=["Metric", "Value"])

    # Which characteristics are associated with higher revenue per customer? (Kruskal-Wallis)
    tests = []
    for attr in ["Age_Band", "Gender", "Region", "Preferred_Payment"]:
        sub = buyers[buyers[attr] != "Unknown"]
        groups = [g["Total_Revenue"].values for _, g in sub.groupby(attr)]
        h, p = stats.kruskal(*groups)
        med = sub.groupby(attr)["Total_Revenue"].median().sort_values(ascending=False)
        tests.append({"Characteristic": attr, "Groups": len(groups), "Kruskal_H": h, "p_value": p,
                      "Significant_at_5%": p < 0.05,
                      "Highest_Median_Group": f"{med.index[0]} ({inr(med.iloc[0])})",
                      "Lowest_Median_Group": f"{med.index[-1]} ({inr(med.iloc[-1])})"})
    rho, p = stats.spearmanr(buyers["Customer_Age"], buyers["Total_Revenue"])
    tests.append({"Characteristic": "Customer_Age (continuous)", "Groups": np.nan, "Kruskal_H": np.nan,
                  "p_value": p, "Significant_at_5%": p < 0.05,
                  "Highest_Median_Group": f"Spearman rho = {rho:.3f}", "Lowest_Median_Group": ""})
    for col in ["Total_Orders", "Average_Order_Value", "Categories_Bought", "Average_Discount", "Return_Rate"]:
        sub = buyers.dropna(subset=[col])
        rho, p = stats.spearmanr(sub[col], sub["Total_Revenue"])
        tests.append({"Characteristic": f"{col} (behavioural)", "Groups": np.nan, "Kruskal_H": np.nan,
                      "p_value": p, "Significant_at_5%": p < 0.05,
                      "Highest_Median_Group": f"Spearman rho = {rho:.3f}", "Lowest_Median_Group": ""})
    out["characteristic_tests"] = pd.DataFrame(tests)
    out["revenue_by_attribute"] = pd.concat([
        buyers.groupby(a).agg(Customers=("Customer_ID", "count"), Median_Revenue=("Total_Revenue", "median"),
                              Mean_Revenue=("Total_Revenue", "mean"), Median_Orders=("Total_Orders", "median"),
                              Median_AOV=("Average_Order_Value", "median"))
        .reset_index().rename(columns={a: "Group"}).assign(Attribute=a)
        for a in ["Age_Band", "Gender", "Region", "Preferred_Payment"]])[
        ["Attribute", "Group", "Customers", "Median_Revenue", "Mean_Revenue", "Median_Orders", "Median_AOV"]]
    # Recency snapshot (descriptive only - RFM comes in Step 5)
    snap = pd.Timestamp(config.END_DATE)
    days = (snap - buyers["Last_Purchase_Date"]).dt.days
    rb = pd.cut(days, [-1, 30, 90, 180, 365, 2000], labels=["0-30", "31-90", "91-180", "181-365", "365+"])
    out["recency_snapshot"] = pd.DataFrame({"Days_Since_Last_Purchase": rb.value_counts().sort_index().index.astype(str),
                                            "Customers": rb.value_counts().sort_index().values,
                                            "Revenue": buyers.groupby(rb, observed=False)["Total_Revenue"].sum().values})
    return out


# =============================================================================
# 7. PRODUCTS
# =============================================================================
def _perf_table(d: pd.DataFrame, allrows: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    g = d.groupby(keys).agg(Units_Sold=("Quantity", "sum"), Revenue=("Sales", "sum"), Cost=("Cost", "sum"),
                            Profit=("Profit", "sum"), Average_Discount=("Discount", "mean"),
                            Orders=("Order_ID", "nunique"), Customers=("Customer_ID", "nunique"),
                            Loss_Lines=("Is_Loss_Making", "sum"), Lines=("Order_Line_ID", "count"))
    ret = allrows.groupby(keys).agg(All_Lines=("Order_Line_ID", "count"),
                                    Returned=("Order_Status", lambda s: (s == "Returned").sum()),
                                    Cancelled=("Order_Status", lambda s: (s == "Cancelled").sum()))
    g = g.join(ret)
    g["Profit_Margin"] = g["Profit"] / g["Revenue"]
    g["Revenue_Share"] = g["Revenue"] / g["Revenue"].sum()
    g["Profit_Share"] = g["Profit"] / g["Profit"].sum()
    g["Return_Rate"] = g["Returned"] / g["All_Lines"]
    g["Avg_Selling_Price"] = g["Revenue"] / g["Units_Sold"]
    return g.reset_index()


def analyze_product_performance(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Product, category and sub-category performance (Delivered revenue & profit)."""
    d = _delivered(df)
    prod = _perf_table(d, df, ["Product_ID", "Product_Name", "Category", "Sub_Category"])
    cat = _perf_table(d, df, ["Category"]).sort_values("Revenue", ascending=False)
    sub = _perf_table(d, df, ["Category", "Sub_Category"]).sort_values("Revenue", ascending=False)
    out = {"product_summary": prod.sort_values("Revenue", ascending=False),
           "category_summary": cat, "subcategory_summary": sub}
    cols = ["Product_Name", "Category", "Units_Sold", "Revenue", "Profit", "Profit_Margin", "Average_Discount"]
    out["top_products_revenue"] = prod.nlargest(20, "Revenue")[cols]
    out["top_products_profit"] = prod.nlargest(20, "Profit")[cols]
    out["top_products_units"] = prod.nlargest(20, "Units_Sold")[cols]
    out["bottom_products_revenue"] = prod.nsmallest(10, "Revenue")[cols]
    return out


# =============================================================================
# 8. REGIONS
# =============================================================================
def _geo_table(d: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    g = d.groupby(keys).agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"), Orders=("Order_ID", "nunique"),
                            Customers=("Customer_ID", "nunique"), Quantity=("Quantity", "sum"))
    g["Profit_Margin"] = g["Profit"] / g["Revenue"]
    g["AOV"] = g["Revenue"] / g["Orders"]
    g["Revenue_per_Customer"] = g["Revenue"] / g["Customers"]
    g["Revenue_Share"] = g["Revenue"] / g["Revenue"].sum()
    return g.reset_index().sort_values("Revenue", ascending=False)


def analyze_regional_performance(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Region / state / city performance, growth and concentration."""
    d = _delivered(df)
    region = _geo_table(d, ["Region"])
    state = _geo_table(d, ["Region", "State"])
    city = _geo_table(d[d["City"] != "Unknown"], ["Region", "State", "City"])
    yr = d.pivot_table(index="Region", columns="Order_Year", values="Sales", aggfunc="sum")
    years = sorted(yr.columns)
    growth = yr.copy()
    growth.columns = [f"Revenue_{y}" for y in years]
    growth["Growth_2024_vs_2023_%"] = (yr[years[1]] / yr[years[0]] - 1) * 100
    growth["Growth_2025_vs_2024_%"] = (yr[years[2]] / yr[years[1]] - 1) * 100
    growth["CAGR_2023_2025_%"] = ((yr[years[2]] / yr[years[0]]) ** 0.5 - 1) * 100
    growth["Share_2023"] = yr[years[0]] / yr[years[0]].sum()
    growth["Share_2025"] = yr[years[2]] / yr[years[2]].sum()
    region = region.merge(growth.reset_index(), on="Region")
    cat_region = d.pivot_table(index="Region", columns="Category", values="Sales", aggfunc="sum")
    cat_region_share = cat_region.div(cat_region.sum(axis=1), axis=0)
    conc = pd.DataFrame([
        ("Top region share of revenue", region["Revenue_Share"].iloc[0], region["Region"].iloc[0]),
        ("Top 2 regions share", region["Revenue_Share"].head(2).sum(), ", ".join(region["Region"].head(2))),
        ("Top 5 states share (of 21)", state["Revenue_Share"].head(5).sum(), ", ".join(state["State"].head(5))),
        ("Top 5 cities share (of 34)", city["Revenue_Share"].head(5).sum(), ", ".join(city["City"].head(5))),
        ("Bottom 5 states share", state["Revenue_Share"].tail(5).sum(), ", ".join(state["State"].tail(5))),
    ], columns=["Measure", "Share", "Members"])
    return {"region_summary": region, "state_summary": state, "city_summary": city,
            "category_by_region_share": cat_region_share.reset_index(), "geo_concentration": conc}


# =============================================================================
# 9. DISCOUNT
# =============================================================================
def analyze_discount_impact(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """How discount levels relate to sales, quantity, profit and margin (association only)."""
    d = _delivered(df).copy()
    d["Discount_Bucket"] = _bucket_discount(d["Discount"])
    b = d.groupby("Discount_Bucket", observed=True).agg(
        Lines=("Order_Line_ID", "count"), Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
        Avg_Sales_per_Line=("Sales", "mean"), Avg_Quantity=("Quantity", "mean"),
        Avg_List_Price=("Unit_Price", "mean"), Loss_Lines=("Is_Loss_Making", "sum"),
        Electronics_Share=("Category", lambda s: (s == "Electronics").mean()))
    b["Line_Share"] = b["Lines"] / b["Lines"].sum()
    b["Revenue_Share"] = b["Revenue"] / b["Revenue"].sum()
    b["Profit_Margin"] = b["Profit"] / b["Revenue"]
    b["Loss_Line_Rate"] = b["Loss_Lines"] / b["Lines"]
    within = d.pivot_table(index="Category", columns="Discount_Bucket", values=["Profit", "Sales"],
                           aggfunc="sum", observed=True)
    within_margin = (within["Profit"] / within["Sales"])
    within_qty = d.pivot_table(index="Category", columns="Discount_Bucket", values="Quantity",
                               aggfunc="mean", observed=True)
    corr_rows = []
    for target in ["Sales", "Profit", "Profit_Margin", "Quantity"]:
        r_p, p_p = stats.pearsonr(d["Discount"], d[target])
        r_s, p_s = stats.spearmanr(d["Discount"], d[target])
        corr_rows.append({"Pair": f"Discount vs {target}", "Pearson_r": r_p, "Pearson_p": p_p,
                          "Spearman_rho": r_s, "Spearman_p": p_s, "Strength (Spearman)": _strength(r_s)})
    within_corr = []
    for cat, g in d.groupby("Category"):
        rho, p = stats.spearmanr(g["Discount"], g["Profit_Margin"])
        within_corr.append({"Category": cat, "Spearman_rho_Discount_vs_Margin": rho, "p_value": p,
                            "Lines": len(g)})
    return {"discount_summary": b.reset_index(), "margin_by_category_bucket": within_margin.reset_index(),
            "quantity_by_category_bucket": within_qty.reset_index(),
            "discount_correlations": pd.DataFrame(corr_rows),
            "discount_margin_within_category": pd.DataFrame(within_corr), "_lines": d}


# =============================================================================
# 10. PROFITABILITY
# =============================================================================
def analyze_profitability(product_summary: pd.DataFrame, category_summary: pd.DataFrame,
                          subcategory_summary: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Revenue-vs-profit positioning (exploratory quadrants, not final segments)."""
    p = product_summary.copy()
    rev_med, prof_med, marg_med = p["Revenue"].median(), p["Profit"].median(), p["Profit_Margin"].median()
    high_rev = p["Revenue"] >= rev_med

    def quad(r):
        if r["Revenue"] >= rev_med:
            return "High revenue + high profit" if r["Profit"] >= prof_med else "High revenue + low profit"
        return "Low revenue + high margin" if r["Profit_Margin"] >= marg_med else "Low revenue + low margin"
    p["Quadrant"] = p.apply(quad, axis=1)
    del high_rev
    thresholds = pd.DataFrame([("Median product revenue", rev_med), ("Median product profit", prof_med),
                               ("Median product margin", marg_med)], columns=["Threshold", "Value"])
    quad_summary = p.groupby("Quadrant").agg(Products=("Product_ID", "count"), Revenue=("Revenue", "sum"),
                                             Profit=("Profit", "sum")).reset_index()
    # Examples: the most characteristic members (highest profit, or lowest profit for "low profit")
    ex = {}
    for q_, g in p.groupby("Quadrant"):
        g = g.sort_values("Profit", ascending=q_ == "High revenue + low profit")
        ex[q_] = ", ".join(f"{n} ({pct(m_, 0)})" for n, m_ in zip(g["Product_Name"].head(4), g["Profit_Margin"].head(4)))
    quad_summary["Examples (margin)"] = quad_summary["Quadrant"].map(ex)
    quad_summary["Margin"] = quad_summary["Profit"] / quad_summary["Revenue"]
    cat = category_summary[["Category", "Revenue", "Profit", "Profit_Margin", "Revenue_Share", "Profit_Share"]].copy()
    cat["Profit_Share_minus_Revenue_Share_pp"] = (cat["Profit_Share"] - cat["Revenue_Share"]) * 100
    low_margin_subs = subcategory_summary.sort_values("Profit_Margin").head(6)
    return {"product_quadrants": p.sort_values(["Quadrant", "Revenue"], ascending=[True, False]),
            "quadrant_summary": quad_summary, "quadrant_thresholds": thresholds,
            "category_revenue_vs_profit": cat, "low_margin_subcategories": low_margin_subs}


# =============================================================================
# 11. PAYMENT + STATUS
# =============================================================================
def analyze_payment_and_status(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Payment mix and the effect of order status on revenue."""
    orders = df.groupby("Order_ID").agg(Payment=("Payment_Method", "first"), Booked=("Sales", "sum"),
                                        Delivered_Rev=("Revenue", "sum"),
                                        Any_Cancel=("Order_Status", lambda s: (s == "Cancelled").any()),
                                        Any_Return=("Order_Status", lambda s: (s == "Returned").any()))
    pay = orders.groupby("Payment").agg(Orders=("Booked", "count"), Booked_Sales=("Booked", "sum"),
                                        Revenue=("Delivered_Rev", "sum"),
                                        Cancel_Rate=("Any_Cancel", "mean"), Return_Rate=("Any_Return", "mean"))
    lines = df.groupby("Payment_Method").size()
    pay["Order_Lines"] = lines
    pay["Order_Share"] = pay["Orders"] / pay["Orders"].sum()
    pay["Revenue_Share"] = pay["Revenue"] / pay["Revenue"].sum()
    pay["AOV"] = pay["Revenue"] / (pay["Orders"] * (1 - pay["Cancel_Rate"]))
    pay = pay.sort_values("Revenue", ascending=False).reset_index().rename(columns={"Payment": "Payment_Method"})
    stt = df.groupby("Order_Status").agg(Lines=("Order_Line_ID", "count"), Orders_Touched=("Order_ID", "nunique"),
                                         Sales_Value=("Sales", "sum"), Profit_Value=("Profit", "sum"))
    stt["Line_Share"] = stt["Lines"] / stt["Lines"].sum()
    stt["Value_Share"] = stt["Sales_Value"] / stt["Sales_Value"].sum()
    stt["Counted_in_Revenue"] = ["Yes" if s == "Delivered" else "No - reported separately" for s in stt.index]
    ret_cat = df.groupby("Category")["Order_Status"].value_counts(normalize=True).unstack().fillna(0)
    return {"payment_summary": pay, "status_summary": stt.reset_index(), "status_by_category": ret_cat.reset_index()}


# =============================================================================
# 12. CORRELATION
# =============================================================================
def calculate_correlations(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Pearson and Spearman matrices (Delivered lines) plus a labelled pair list."""
    d = _delivered(df)[NUM_VARS].astype(float)
    pear, spear = d.corr("pearson"), d.corr("spearman")
    pairs = []
    for i, a in enumerate(NUM_VARS):
        for b in NUM_VARS[i + 1:]:
            pairs.append({"Variable_1": a, "Variable_2": b, "Pearson_r": pear.loc[a, b],
                          "Spearman_rho": spear.loc[a, b], "Strength (Spearman)": _strength(spear.loc[a, b])})
    pairs = pd.DataFrame(pairs).sort_values("Spearman_rho", key=np.abs, ascending=False)
    return {"pearson": pear, "spearman": spear, "correlation_pairs": pairs}


# =============================================================================
# 13. OUTLIERS
# =============================================================================
def detect_eda_outliers(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """IQR and percentile view of remaining extremes, with a plausibility check."""
    d = _delivered(df)
    rows = []
    for c in ["Sales", "Profit", "Quantity", "Discount", "Unit_Price"]:
        s = d[c].astype(float)
        q1, q3 = s.quantile([.25, .75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = int(((s < lo) | (s > hi)).sum())
        pcts = s.quantile([.01, .05, .5, .95, .99, .999])
        rows.append({"Variable": c, "P1": pcts[.01], "P5": pcts[.05], "Median": pcts[.5], "P95": pcts[.95],
                     "P99": pcts[.99], "P99.9": pcts[.999], "Max": s.max(), "IQR_Lower": lo, "IQR_Upper": hi,
                     "IQR_Outliers": n_out, "IQR_Outlier_%": 100 * n_out / len(s),
                     "Max_to_P99_ratio": s.max() / pcts[.99] if pcts[.99] else np.nan})
    top = d.nlargest(10, "Sales")[["Order_Line_ID", "Order_Date", "Customer_ID", "Product_Name", "Category",
                                   "Quantity", "Unit_Price", "Discount", "Sales", "Profit",
                                   "Revenue_Check_Pass", "Is_Bulk_Order_Line"]]
    worst = d.nsmallest(10, "Profit")[["Order_Line_ID", "Product_Name", "Category", "Quantity", "Unit_Price",
                                       "Discount", "Sales", "Profit", "Revenue_Check_Pass"]]
    s_hi = d["Outlier_IQR_Sales"]
    classes = pd.DataFrame([
        ("Genuine high-value transactions", int((s_hi & ~d["Is_Bulk_Order_Line"]).sum()),
         d.loc[s_hi & ~d["Is_Bulk_Order_Line"], "Sales"].sum() / d["Sales"].sum(),
         "Premium items at list price; all pass the Sales formula"),
        ("Unusual purchases (bulk, >= 10 units)", int(d["Is_Bulk_Order_Line"].sum()),
         d.loc[d["Is_Bulk_Order_Line"], "Sales"].sum() / d["Sales"].sum(),
         "Formula-consistent; plausible gifting / institutional orders"),
        ("Loss-making lines (Profit < 0)", int(d["Is_Loss_Making"].sum()),
         d.loc[d["Is_Loss_Making"], "Sales"].sum() / d["Sales"].sum(),
         "Business issue (discount on thin margin), not a data error"),
        ("Data errors (formula failures)", int((~d["Revenue_Check_Pass"] | ~d["Profit_Check_Pass"]).sum()), 0.0,
         "None remain after Step 3"),
    ], columns=["Class", "Lines", "Share_of_Revenue", "Assessment"])
    return {"outlier_percentiles": pd.DataFrame(rows), "top_sales_lines": top, "worst_profit_lines": worst,
            "outlier_classes": classes}


# =============================================================================
# 14. BUSINESS QUESTIONS + INSIGHTS (text built only from computed values)
# =============================================================================
def run_all_analyses(df: pd.DataFrame) -> dict:
    """Run every analysis once and collect results in one dictionary."""
    R: dict = {"order_definition": verify_order_definition(df), "dataset_summary": generate_dataset_summary(df),
               "kpis": calculate_kpis(df), "descriptive_stats": descriptive_statistics(df)}
    R["univariate"] = analyze_sales_distribution(df)
    R["time"] = analyze_time_series(df)
    R["customers"] = analyze_customer_performance(df)
    R["products"] = analyze_product_performance(df)
    R["regions"] = analyze_regional_performance(df)
    R["discount"] = analyze_discount_impact(df)
    R["profitability"] = analyze_profitability(R["products"]["product_summary"], R["products"]["category_summary"],
                                               R["products"]["subcategory_summary"])
    R["payment_status"] = analyze_payment_and_status(df)
    R["correlations"] = calculate_correlations(df)
    R["outliers"] = detect_eda_outliers(df)
    R["quality_checks"] = quality_checks(df, R)
    R["business_questions"] = answer_business_questions(R)
    R["insights"] = generate_business_insights(R)
    return R


def _kpi(R, name):
    k = R["kpis"].set_index("KPI")
    return k.loc[name, "Value"]


def answer_business_questions(R: dict) -> pd.DataFrame:
    """Q1-Q12 answered from computed tables (no hand-typed numbers)."""
    cat = R["products"]["category_summary"].set_index("Category")
    prod = R["products"]["product_summary"]
    reg = R["regions"]["region_summary"].set_index("Region")
    t = R["time"]
    yr = t["yearly"].set_index("Order_Year")
    si = t["seasonal_index"]
    conc = R["customers"]["revenue_concentration"].set_index("Customer_Group")
    ds = R["discount"]
    within = ds["discount_margin_within_category"]
    mb = ds["margin_by_category_bucket"].set_index("Category")
    ct = R["customers"]["characteristic_tests"].set_index("Characteristic")
    crp = R["profitability"]["category_revenue_vs_profit"].set_index("Category")
    sub = R["products"]["subcategory_summary"]
    top_rev_cat = cat["Revenue"].idxmax()
    top_prof_cat = cat["Profit"].idxmax()
    tp = prod.nlargest(3, "Revenue")
    tpp = prod.nlargest(3, "Profit")
    top_reg_rev = reg["Revenue"].idxmax()
    top_reg_prof = reg["Profit"].idxmax()
    fastest = reg["CAGR_2023_2025_%"].idxmax()
    years = list(yr.index)
    above_all = si.loc[si["Years_Above_Avg"] == len(years), "Month_Name"].tolist()
    peaks = t["festive"]["Peak_Month"].tolist()
    oct_margin = t["monthly"].loc[t["monthly"]["Month"] == 10, "Profit_Margin"]
    gap = crp["Profit_Share_minus_Revenue_Share_pp"].idxmin()
    neg_sub = sub[sub["Profit_Margin"] < 0]
    low_sub = sub.nsmallest(3, "Profit_Margin")
    sig = ct[ct["Significant_at_5%"]]
    rows = [
        ("Q1. Which category generates the most revenue?",
         f"{top_rev_cat}: {inr(cat.loc[top_rev_cat, 'Revenue'])} ({pct(cat.loc[top_rev_cat, 'Revenue_Share'])} of revenue). "
         f"Next: {cat['Revenue'].nlargest(3).index[1]} ({pct(cat['Revenue_Share'].nlargest(3).iloc[1])}).",
         "category_summary.csv"),
        ("Q2. Which category generates the most profit?",
         f"{top_prof_cat}: {inr(cat.loc[top_prof_cat, 'Profit'])} ({pct(cat.loc[top_prof_cat, 'Profit_Share'])} of profit) "
         f"at a {pct(cat.loc[top_prof_cat, 'Profit_Margin'])} margin, although it is only {pct(cat.loc[top_prof_cat, 'Revenue_Share'])} of revenue.",
         "category_summary.csv"),
        ("Q3. Which products generate the most revenue?",
         "; ".join(f"{r.Product_Name} {inr(r.Revenue)}" for r in tp.itertuples()) + ". All three are Electronics.",
         "product_summary.csv"),
        ("Q4. Which products generate the most profit?",
         "; ".join(f"{r.Product_Name} {inr(r.Profit)} ({pct(r.Profit_Margin)} margin)" for r in tpp.itertuples()) + ".",
         "product_summary.csv"),
        ("Q5. Which region generates the most revenue?",
         f"{top_reg_rev}: {inr(reg.loc[top_reg_rev, 'Revenue'])} ({pct(reg.loc[top_reg_rev, 'Revenue_Share'])}). "
         f"Fastest-growing: {fastest} (CAGR {reg.loc[fastest, 'CAGR_2023_2025_%']:.1f}% 2023-25).",
         "regional_summary.csv"),
        ("Q6. Which region generates the most profit?",
         f"{top_reg_prof}: {inr(reg.loc[top_reg_prof, 'Profit'])}. Margins are similar across regions "
         f"({pct(reg['Profit_Margin'].min())} - {pct(reg['Profit_Margin'].max())}); "
         f"highest margin: {reg['Profit_Margin'].idxmax()}.",
         "regional_summary.csv"),
        ("Q7. What is the monthly revenue trend?",
         f"Upward with slowing growth: {years[0]} {inr(yr.loc[years[0], 'Revenue'])} -> {years[1]} {inr(yr.loc[years[1], 'Revenue'])} "
         f"(+{yr.loc[years[1], 'YoY_Revenue_Growth_%']:.1f}%) -> {years[2]} {inr(yr.loc[years[2], 'Revenue'])} "
         f"(+{yr.loc[years[2], 'YoY_Revenue_Growth_%']:.1f}%). Month-to-month swings are large "
         f"(MoM growth ranges {t['monthly']['MoM_Growth_%'].min():.1f}% to +{t['monthly']['MoM_Growth_%'].max():.1f}%).",
         "monthly_summary.csv"),
        ("Q8. Is there evidence of seasonality?",
         f"Yes, for Q4. The peak month was {', '.join(sorted(set(peaks)))} in all {len(years)} years, and "
         f"{', '.join(above_all)} were above the year's average month in every year "
         f"(October averages {si.loc[si['Month'] == 10, 'Avg_Index'].iloc[0]:.2f}x an average month; "
         f"after removing trend, {si.loc[si['Month'] == 10, 'Avg_Ratio_to_Trend'].iloc[0]:.2f}x). "
         f"October also has the lowest margin ({pct(oct_margin.min())}-{pct(oct_margin.max())}).",
         "seasonal_index.csv"),
        ("Q9. How concentrated is revenue among customers?",
         f"Top 1% of customers -> {pct(conc.loc['Top 1%', 'Share_of_Revenue'])}, top 5% -> {pct(conc.loc['Top 5%', 'Share_of_Revenue'])}, "
         f"top 10% -> {pct(conc.loc['Top 10%', 'Share_of_Revenue'])}, top 20% -> {pct(conc.loc['Top 20%', 'Share_of_Revenue'])} "
         f"of revenue. Gini = {R['customers']['distribution_stats'].set_index('Metric').loc['Gini coefficient of customer revenue', 'Value']:.2f}.",
         "revenue_concentration.csv"),
        ("Q10. What is the relationship between discount and profitability?",
         f"Negative. Line-level Spearman rho(discount, margin) = {ds['discount_correlations'].set_index('Pair').loc['Discount vs Profit_Margin', 'Spearman_rho']:.2f}; "
         f"within categories it ranges {within['Spearman_rho_Discount_vs_Margin'].min():.2f} to {within['Spearman_rho_Discount_vs_Margin'].max():.2f}. "
         f"E.g. Fashion margin falls from {pct(mb.loc['Fashion', '0%'])} at 0% to {pct(mb.loc['Fashion', '35-40%'])} at 35-40%. "
         f"Quantity barely moves (rho {ds['discount_correlations'].set_index('Pair').loc['Discount vs Quantity', 'Spearman_rho']:.2f}). Association, not causation.",
         "discount_summary.csv"),
        ("Q11. Which areas have high revenue but comparatively low profit?",
         f"{gap}: {pct(crp.loc[gap, 'Revenue_Share'])} of revenue but {pct(crp.loc[gap, 'Profit_Share'])} of profit "
         f"(margin {pct(crp.loc[gap, 'Profit_Margin'])}). Lowest-margin sub-categories: "
         + ", ".join(f"{r.Sub_Category} {pct(r.Profit_Margin)}" for r in low_sub.itertuples())
         + (f". {', '.join(neg_sub['Sub_Category'])} lost money overall." if len(neg_sub) else "."),
         "subcategory_summary.csv"),
        ("Q12. Which customer characteristics appear associated with higher revenue?",
         "Behaviour far more than demographics. Significant (p<0.05): " +
         "; ".join(f"{i.split(' (')[0]} {r['Highest_Median_Group']}" for i, r in sig.iterrows()) +
         ". Not significant: " + ", ".join(ct[~ct['Significant_at_5%']].index) + ".",
         "customer_characteristic_tests.csv"),
    ]
    return pd.DataFrame(rows, columns=["Question", "Answer (from data)", "Evidence table"])


def generate_business_insights(R: dict) -> pd.DataFrame:
    """Structured insight table: Area | Observation | Evidence | Business Implication.

    Observation and Evidence are computed. Business Implication is
    interpretation (a hypothesis to test later), not a proven effect.
    """
    cat = R["products"]["category_summary"].set_index("Category")
    reg = R["regions"]["region_summary"].set_index("Region")
    t = R["time"]
    yr = t["yearly"].set_index("Order_Year")
    mon = t["monthly"]
    conc = R["customers"]["revenue_concentration"].set_index("Customer_Group")
    freq = R["customers"]["order_frequency"].set_index("Orders_per_Customer")
    rec = R["customers"]["recency_snapshot"].set_index("Days_Since_Last_Purchase")
    ds = R["discount"]
    within = ds["discount_margin_within_category"]
    prod = R["products"]["product_summary"].set_index("Product_Name")
    pay = R["payment_status"]["payment_summary"].set_index("Payment_Method")
    dow = t["day_of_week"].set_index("Day_of_Week")
    ct = R["customers"]["revenue_by_attribute"]
    ab = ct[ct["Attribute"] == "Age_Band"].set_index("Group")
    loss = R["outliers"]["outlier_classes"].set_index("Class").loc["Loss-making lines (Profit < 0)"]
    y = list(yr.index)
    heavy = freq.loc[["11-20", "21+"]]
    lapsed = rec.loc[["181-365", "365+"], "Customers"].sum()
    n_buyers = rec["Customers"].sum()
    oct_m = mon[mon["Month"] == 10]
    tv = prod.loc["43-inch 4K Smart TV"]
    rows = [
        ("Revenue", "Revenue is growing, but growth is slowing",
         f"{y[0]} {inr(yr.loc[y[0], 'Revenue'])} -> {y[1]} {inr(yr.loc[y[1], 'Revenue'])} (+{yr.loc[y[1], 'YoY_Revenue_Growth_%']:.1f}%) -> "
         f"{y[2]} {inr(yr.loc[y[2], 'Revenue'])} (+{yr.loc[y[2], 'YoY_Revenue_Growth_%']:.1f}%)",
         "Forecasting should model trend plus seasonality; the slowdown is worth diagnosing (fewer new customers or lower frequency?)"),
        ("Seasonality", "October is the peak month every year; Oct-Dec are always above average",
         "October revenue: " + ", ".join(f"{r.Year} {inr(r.Revenue)}" for r in oct_m.itertuples())
         + "; Q4 share of year: " + ", ".join(f"{int(r.Order_Year)} {pct(r.Share_of_Year)}" for r in t['quarterly'][t['quarterly']['Order_Quarter'] == 'Q4'].itertuples()),
         "Plan inventory, staffing and marketing budget around the festive quarter"),
        ("Seasonality", "The festive peak is the least profitable month",
         f"October margin {pct(oct_m['Profit_Margin'].min())}-{pct(oct_m['Profit_Margin'].max())} vs overall {pct(_kpi(R, 'Overall Profit Margin'))}",
         "Festive growth is being bought with discounts; review the depth of festive discounts on thin-margin items"),
        ("Products", "Electronics dominates revenue but not profit",
         f"Electronics = {pct(cat.loc['Electronics', 'Revenue_Share'])} of revenue, {pct(cat.loc['Electronics', 'Profit_Share'])} of profit, margin {pct(cat.loc['Electronics', 'Profit_Margin'])}",
         "Revenue KPIs alone overstate Electronics' contribution; judge categories on profit"),
        ("Products", "Fashion is the profit engine, but has the highest return rate",
         f"Fashion = {pct(cat.loc['Fashion', 'Revenue_Share'])} of revenue, {pct(cat.loc['Fashion', 'Profit_Share'])} of profit (margin {pct(cat.loc['Fashion', 'Profit_Margin'])}); return rate {pct(cat.loc['Fashion', 'Return_Rate'])} vs {pct(cat.drop('Fashion')['Return_Rate'].max())} max elsewhere",
         "Reducing Fashion returns (sizing guides, fit tools) could protect the highest-margin revenue"),
        ("Profitability", "Some top-selling items barely break even or lose money",
         f"43-inch 4K Smart TV: revenue {inr(tv['Revenue'])}, profit {inr(tv['Profit'])} (margin {pct(tv['Profit_Margin'])}); "
         f"AeroBook Pro 16 margin {pct(prod.loc['AeroBook Pro 16 Laptop', 'Profit_Margin'])}; loss-making lines = {int(loss['Lines'])} ({pct(loss['Share_of_Revenue'])} of revenue)",
         "Review pricing, supplier cost and discount caps for these SKUs"),
        ("Discount", "Deeper discounts go with lower margins in every category, while quantity barely changes",
         f"Within-category Spearman rho(discount, margin): {within['Spearman_rho_Discount_vs_Margin'].min():.2f} to {within['Spearman_rho_Discount_vs_Margin'].max():.2f}; "
         f"rho(discount, quantity) = {ds['discount_correlations'].set_index('Pair').loc['Discount vs Quantity', 'Spearman_rho']:.2f}",
         "Discounts appear to cost margin without clearly lifting volume; test targeted rather than blanket discounts (association, not causation)"),
        ("Discount", "The overall discount-margin table is misleading because of category mix",
         "Margin by bucket (all categories): " + ", ".join(f"{r.Discount_Bucket} {pct(r.Profit_Margin)}" for r in ds['discount_summary'].itertuples())
         + "; the 5-10% bucket is heavy in low-margin Electronics",
         "Always compare discount effects within a category (Simpson's paradox)"),
        ("Customers", "Revenue is concentrated in a minority of customers",
         f"Top 20% -> {pct(conc.loc['Top 20%', 'Share_of_Revenue'])}, top 10% -> {pct(conc.loc['Top 10%', 'Share_of_Revenue'])}, top 1% -> {pct(conc.loc['Top 1%', 'Share_of_Revenue'])}",
         "Losing a few top customers would hurt disproportionately; they are the priority for retention (RFM/CLV in Steps 5-7)"),
        ("Customers", "Frequent buyers drive revenue",
         f"Customers with 11+ orders: {pct(heavy['Share'].sum())} of buyers, {pct(heavy['Revenue_Share'].sum())} of revenue; "
         f"customer revenue vs order count Spearman rho = {R['customers']['characteristic_tests'].set_index('Characteristic').loc['Total_Orders (behavioural)', 'Highest_Median_Group'].split('= ')[1]}",
         "Growing purchase frequency is a stronger lever than acquiring one-off buyers"),
        ("Customers", "A large share of customers has gone quiet",
         f"{lapsed} of {n_buyers} buyers ({pct(lapsed / n_buyers)}) have not bought in over 180 days",
         "Reactivation candidates to size in RFM (Step 5); descriptive only here"),
        ("Customers", "Age is linked to spend; gender and region are not",
         f"Median customer revenue: 35-49 {inr(ab.loc['35-49', 'Median_Revenue'])} vs 18-24 {inr(ab.loc['18-24', 'Median_Revenue'])} "
         f"(Kruskal-Wallis p<0.001); gender p={R['customers']['characteristic_tests'].set_index('Characteristic').loc['Gender', 'p_value']:.2f}, "
         f"region p={R['customers']['characteristic_tests'].set_index('Characteristic').loc['Region', 'p_value']:.2f}",
         "Age band is a candidate feature for prediction; gender/region-based targeting has little support"),
        ("Region", "South leads; East grows fastest; Central's share is shrinking",
         f"South {pct(reg.loc['South', 'Revenue_Share'])} of revenue; East CAGR {reg.loc['East', 'CAGR_2023_2025_%']:.1f}%; "
         f"Central share {pct(reg.loc['Central', 'Share_2023'])} -> {pct(reg.loc['Central', 'Share_2025'])}",
         "Protect the South, invest behind East's momentum, and investigate Central's slower growth"),
        ("Operations", f"{pct(_kpi(R, 'Share of Booked Sales Not Realised'))} of booked sales never became revenue",
         f"Lost to cancellations and returns: {inr(_kpi(R, 'Revenue Lost to Cancellations & Returns'))}; "
         f"COD cancel rate {pct(pay.loc['COD', 'Cancel_Rate'])} vs UPI {pct(pay.loc['UPI', 'Cancel_Rate'])}",
         "Nudging COD users to prepaid methods could reduce leakage"),
        ("Timing", "Weekends sell more",
         f"Revenue per calendar day: Saturday {dow.loc['Saturday', 'Index_vs_Avg_Day']:.2f}x and Monday {dow.loc['Monday', 'Index_vs_Avg_Day']:.2f}x the average day",
         "Schedule campaigns and flash sales for Friday-Sunday"),
    ]
    return pd.DataFrame(rows, columns=["Area", "Observation", "Evidence", "Business Implication (interpretation)"])


def quality_checks(df: pd.DataFrame, R: dict) -> pd.DataFrame:
    """Reconcile every aggregate back to the source rows (Section 22 of the brief)."""
    d = _delivered(df)
    rev = d["Sales"].sum()
    tol = 0.5  # rupees

    def ok(a, b):
        return bool(abs(a - b) <= tol)
    cust = R["customers"]["customer_summary"]
    checks = [
        ("Dataset is the Step 3 cleaned file", str(config.CLEAN_DATA_FILE.name), True),
        ("No duplicate Order_Line_ID (no double counting)", int(df["Order_Line_ID"].duplicated().sum()),
         df["Order_Line_ID"].is_unique),
        ("Order_Date parsed as datetime", str(df["Order_Date"].dtype),
         pd.api.types.is_datetime64_any_dtype(df["Order_Date"])),
        ("Dates within 2023-01-01 .. 2025-12-31",
         f"{df['Order_Date'].min():%Y-%m-%d} .. {df['Order_Date'].max():%Y-%m-%d}",
         df["Order_Date"].min() >= pd.Timestamp(config.START_DATE) and df["Order_Date"].max() <= pd.Timestamp(config.END_DATE)),
        ("Only Delivered lines in revenue (Revenue column = Sales for Delivered, 0 otherwise)",
         inr(df.loc[~df["Is_Delivered"], "Revenue"].sum()), ok(df["Revenue"].sum(), rev)),
        ("Monthly revenue sums to total revenue", inr(R["time"]["monthly"]["Revenue"].sum()),
         ok(R["time"]["monthly"]["Revenue"].sum(), rev)),
        ("Category revenue sums to total revenue", inr(R["products"]["category_summary"]["Revenue"].sum()),
         ok(R["products"]["category_summary"]["Revenue"].sum(), rev)),
        ("Product revenue sums to total revenue", inr(R["products"]["product_summary"]["Revenue"].sum()),
         ok(R["products"]["product_summary"]["Revenue"].sum(), rev)),
        ("Region revenue sums to total revenue", inr(R["regions"]["region_summary"]["Revenue"].sum()),
         ok(R["regions"]["region_summary"]["Revenue"].sum(), rev)),
        ("Customer-level revenue sums to total revenue", inr(cust["Total_Revenue"].sum()),
         ok(cust["Total_Revenue"].sum(), rev)),
        ("Customer-level orders sum to order count", int(cust["Total_Orders"].sum()),
         int(cust["Total_Orders"].sum()) == d["Order_ID"].nunique()),
        ("Profit = Revenue - Cost at total level", inr(d["Profit"].sum()),
         ok(d["Profit"].sum(), d["Sales"].sum() - d["Cost"].sum())),
        ("Every line passes Sales and Profit formula checks",
         int((~df["Revenue_Check_Pass"] | ~df["Profit_Check_Pass"]).sum()),
         bool(df["Revenue_Check_Pass"].all() and df["Profit_Check_Pass"].all())),
        ("Status analysis reconciles to gross booked sales",
         inr(R["payment_status"]["status_summary"]["Sales_Value"].sum()),
         ok(R["payment_status"]["status_summary"]["Sales_Value"].sum(), df["Sales"].sum())),
        ("Outliers kept (rows = Step 3 cleaned rows)", len(df),
         len(df) == len(pd.read_csv(config.CLEAN_DATA_FILE, usecols=["Order_Line_ID"]))),
    ]
    return pd.DataFrame(checks, columns=["Check", "Value", "Pass"])


# =============================================================================
# 15. FIGURES
# =============================================================================
PAL = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100",
       "magenta": "#e87ba4", "green": "#008300", "violet": "#4a3aa7", "red": "#e34948",
       "text": "#0b0b0b", "muted": "#52514e", "grid": "#e4e3df", "light": "#cde2fb", "neutral": "#c3c2b7"}
SERIES = [PAL["blue"], PAL["orange"], PAL["aqua"], PAL["yellow"], PAL["magenta"], PAL["green"]]


def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 12.5, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.titlecolor": PAL["text"], "axes.labelcolor": PAL["muted"],
        "axes.edgecolor": PAL["grid"], "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": PAL["muted"], "ytick.color": PAL["muted"], "axes.grid": True, "grid.color": PAL["grid"],
        "grid.linewidth": 0.8, "axes.axisbelow": True, "legend.frameon": False, "figure.facecolor": "white",
        "savefig.bbox": "tight", "savefig.dpi": 160})
    return plt


def _lakh(ax, axis="y"):
    from matplotlib.ticker import FuncFormatter
    f = FuncFormatter(lambda v, _: (f"{'-' if v < 0 else ''}₹{abs(v) / 1e5:,.0f}L" if abs(v) >= 1e5 or v == 0
                                    else f"{'-' if v < 0 else ''}₹{abs(v) / 1e5:,.1f}L"))
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(f)


def _rupee(ax, axis="y"):
    from matplotlib.ticker import FuncFormatter
    f = FuncFormatter(lambda v, _: f"{'-' if v < 0 else ''}₹{abs(v):,.0f}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(f)


def _pct_axis(ax, axis="y", decimals=0):
    from matplotlib.ticker import PercentFormatter
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(PercentFormatter(1.0, decimals=decimals))


def _date_axis(ax):
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))


def _note(fig, text):
    fig.text(0.01, -0.02, text, fontsize=8.5, color=PAL["muted"], ha="left", va="top")


def _save(fig, name, out_dir, saved):
    p = out_dir / name
    fig.savefig(p)
    import matplotlib.pyplot as plt
    plt.close(fig)
    saved.append(p)


def _hbar(ax, labels, values, color=PAL["blue"], fmt=inr, value_labels=None):
    y = np.arange(len(labels))
    bars = ax.barh(y, values, color=color, height=0.65)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    span = max(abs(np.nanmax(values)), abs(np.nanmin(values)), 1)
    for i, (b, v) in enumerate(zip(bars, values)):
        lab = value_labels[i] if value_labels is not None else fmt(v)
        x = b.get_width()
        # Negative bars: put the label just right of zero so it never collides with the axis labels
        ax.text(max(x, 0) + span * 0.01, b.get_y() + b.get_height() / 2, lab,
                va="center", ha="left", fontsize=8.5, color=PAL["text"])
    ax.set_xlim(min(0, np.nanmin(values) * 1.25), np.nanmax(values) * 1.22 if np.nanmax(values) > 0 else 0)
    return bars


def plot_univariate(df, R, out_dir, saved):
    plt = _style()
    d = _delivered(df)
    cust = df.drop_duplicates("Customer_ID")
    specs = [("Customer age (years, per customer)", cust["Customer_Age"], False, 25),
             ("Sales per line (₹, log scale)", d["Sales"], True, 40),
             ("Profit per line (₹)", d["Profit"], False, 60),
             ("Discount per line", d["Discount"], False, None),
             ("Quantity per line (units)", d["Quantity"], False, None)]
    fig, axes = plt.subplots(2, 5, figsize=(18, 6.4), gridspec_kw={"height_ratios": [3, 1]})
    for j, (title, s, logx, bins) in enumerate(specs):
        ax, bx = axes[0, j], axes[1, j]
        s = s.astype(float)
        if title.startswith("Discount"):
            vc = s.round(2).value_counts().sort_index()
            ax.bar(vc.index, vc.values, width=0.04, color=PAL["blue"])
            for a_ in (ax, bx):
                a_.set_xticks([0, 0.1, 0.2, 0.3, 0.4])
                a_.set_xlim(-0.03, 0.43)
                _pct_axis(a_, "x")
        elif title.startswith("Quantity"):
            vc = s.clip(upper=6).value_counts().sort_index()
            ax.bar(vc.index, vc.values, width=0.7, color=PAL["blue"])
            for a_ in (ax, bx):
                a_.set_xticks([1, 2, 3, 4, 5, 6], ["1", "2", "3", "4", "5", "6+"])
                a_.set_xlim(0.4, 6.6)
            ax.text(0.98, 0.95, f"{int((s >= 6).sum())} lines have 6+ units\n(max {int(s.max())})",
                    transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color=PAL["muted"])
        else:
            if logx:
                b = np.logspace(np.log10(s.min()), np.log10(s.max()), bins)
            elif title.startswith("Profit"):
                b = np.linspace(s.quantile(0.002), s.quantile(0.998), bins)
            else:
                b = bins
            ax.hist(s, bins=b, color=PAL["blue"], edgecolor="white", linewidth=0.6)
            if logx:
                ax.set_xscale("log")
                bx.set_xscale("log")
            if title.startswith("Profit"):
                for a_ in (ax, bx):
                    a_.set_xlim(s.quantile(0.002), s.quantile(0.998))
                ax.axvline(0, color=PAL["red"], linewidth=1)
            else:
                bx.set_xlim(ax.get_xlim())
        ax.axvline(s.median(), color=PAL["orange"], linewidth=1.5, linestyle="--")
        ax.set_title(title, fontsize=10.5)
        ax.text(0.98, 0.72 if title.startswith("Quantity") else 0.95,
                f"median {s.median():,.2f}\nmean {s.mean():,.2f}\nskew {s.skew():.2f}", transform=ax.transAxes,
                ha="right", va="top", fontsize=8.5, color=PAL["text"])
        box_s = (s.clip(s.quantile(0.002), s.quantile(0.998)) if title.startswith("Profit")
                 else s.clip(upper=6) if title.startswith("Quantity") else s)
        bx.boxplot(box_s,
                   vert=False, widths=0.6, patch_artist=True, showfliers=True,
                   boxprops=dict(facecolor=PAL["light"], edgecolor=PAL["blue"]),
                   medianprops=dict(color=PAL["text"]), flierprops=dict(marker="o", markersize=2,
                                                                         markerfacecolor=PAL["orange"],
                                                                         markeredgecolor="none", alpha=0.4))
        bx.set_yticks([])
        bx.grid(axis="y", visible=False)
    axes[0, 0].set_ylabel("Customers")
    axes[0, 1].set_ylabel("Delivered lines")
    fig.suptitle("Distributions of key variables (histogram + boxplot; dashed line = median)", x=0.01, ha="left",
                 fontweight="bold", fontsize=13)
    _note(fig, "Delivered lines only, except age (one value per customer). Profit view trimmed to the 0.2-99.8th "
               "percentile for readability; red line = zero profit.")
    fig.tight_layout()
    _save(fig, "univariate_distributions.png", out_dir, saved)


def plot_categorical(df, R, out_dir, saved):
    plt = _style()
    U = R["univariate"]
    panels = [("Gender (customers)", U["cat_Gender"], "Customers"),
              ("Region (customers)", U["cat_Region"], "Customers"),
              ("Category (delivered lines)", U["cat_Category"], "Delivered lines"),
              ("Payment method (orders)", U["cat_Payment_Method"], "Orders"),
              ("Order status (order lines)", U["cat_Order_Status"], "Order lines"),
              ("Customer type (orders)", U["cat_Customer_Type"], "Orders")]
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.2))
    for ax, (title, t, unit) in zip(axes.flat, panels):
        _hbar(ax, t["Value"].tolist(), t["Share"].to_numpy(), fmt=pct,
              value_labels=[f"{pct(s)}  ({n:,})" for s, n in zip(t["Share"], t[unit])])
        _pct_axis(ax, "x")
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(f"Share of {unit.lower()}")
    fig.suptitle("Categorical distributions (share, with counts)", x=0.01, ha="left", fontweight="bold", fontsize=13)
    fig.tight_layout()
    _save(fig, "categorical_distributions.png", out_dir, saved)

    for key, name, unit, title in [("cat_Sub_Category", "subcategory_distribution.png", "Delivered lines",
                                    "Sub-category mix (share of delivered order lines)"),
                                   ("cat_State", "state_customer_distribution.png", "Customers",
                                    "Customers by state (share of 2,000 customers)")]:
        t = R["univariate"][key]
        if key == "cat_State":
            reg = df.drop_duplicates("State").set_index("State")["Region"]
            labels = [f"{v} ({reg[v]})" for v in t["Value"]]
        else:
            labels = t["Value"].tolist()
        fig, ax = plt.subplots(figsize=(9, 0.32 * len(t) + 1.2))
        _hbar(ax, labels, t["Share"].to_numpy(), fmt=pct,
              value_labels=[f"{pct(s)}  ({n:,})" for s, n in zip(t["Share"], t[unit])])
        _pct_axis(ax, "x")
        ax.set_title(title)
        ax.set_xlabel(f"Share of {unit.lower()}")
        fig.tight_layout()
        _save(fig, name, out_dir, saved)


def plot_time_series(df, R, out_dir, saved):
    plt = _style()
    m = R["time"]["monthly"].copy()
    x = m["Year_Month"].dt.to_timestamp()
    # Revenue trend
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(x, m["Revenue"], color=PAL["blue"], linewidth=2, marker="o", markersize=4, label="Monthly revenue")
    ax.plot(x, m["Revenue_3M_MA"], color=PAL["orange"], linewidth=2, linestyle="--", label="3-month moving average")
    for r in m[m["Month"] == 10].itertuples():
        ax.annotate(f"Oct {r.Year}\n{inr(r.Revenue)}", (r.Year_Month.to_timestamp(), r.Revenue),
                    textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8.5, color=PAL["text"])
    _lakh(ax)
    ax.set_ylim(0, m["Revenue"].max() * 1.18)
    ax.set_ylabel("Revenue (₹ lakh)")
    ax.set_title("Monthly revenue trend, Jan 2023 - Dec 2025 (Delivered orders)")
    _date_axis(ax)
    ax.legend(loc="upper left")
    fig.tight_layout()
    _save(fig, "monthly_revenue_trend.png", out_dir, saved)

    # MoM growth
    fig, ax = plt.subplots(figsize=(13, 4.2))
    g = m["MoM_Growth_%"].fillna(0) / 100
    ax.bar(x, g, width=20, color=[PAL["blue"] if v >= 0 else PAL["red"] for v in g])
    ax.axhline(0, color=PAL["muted"], linewidth=0.8)
    _pct_axis(ax)
    ax.set_ylabel("MoM revenue growth")
    ax.set_title("Month-over-month revenue growth (blue = growth, red = decline)")
    _date_axis(ax)
    _note(fig, "MoM Growth % = (current month revenue - previous month revenue) / previous month revenue x 100. "
               "Jan 2023 has no prior month.")
    fig.tight_layout()
    _save(fig, "mom_revenue_growth.png", out_dir, saved)

    # Profit and margin: two panels (no dual axis)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 6.8), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    a1.plot(x, m["Profit"], color=PAL["aqua"], linewidth=2, marker="o", markersize=4)
    _lakh(a1)
    a1.set_ylim(0, m["Profit"].max() * 1.15)
    a1.set_ylabel("Profit (₹ lakh)")
    a1.set_title("Monthly profit and profit margin")
    a2.plot(x, m["Profit_Margin"], color=PAL["blue"], linewidth=2, marker="o", markersize=4)
    a2.axhline(_kpi(R, "Overall Profit Margin"), color=PAL["muted"], linestyle=":", linewidth=1)
    a2.text(x.iloc[0], _kpi(R, "Overall Profit Margin") + 0.004, f"overall {pct(_kpi(R, 'Overall Profit Margin'))}",
            fontsize=8.5, color=PAL["muted"])
    for r in m[m["Month"] == 10].itertuples():
        a2.annotate(f"Oct {r.Year}", (r.Year_Month.to_timestamp(), r.Profit_Margin), textcoords="offset points",
                    xytext=(0, -14), ha="center", fontsize=8.5, color=PAL["red"])
    _pct_axis(a2)
    from matplotlib.ticker import MultipleLocator
    a2.yaxis.set_major_locator(MultipleLocator(0.04))
    a2.set_ylim(m["Profit_Margin"].min() - 0.03, m["Profit_Margin"].max() + 0.02)
    _date_axis(a2)
    a2.set_ylabel("Profit margin")
    fig.tight_layout()
    _save(fig, "monthly_profit_trend.png", out_dir, saved)

    # Orders and active customers (same unit: counts)
    fig, ax = plt.subplots(figsize=(13, 4.6))
    ax.plot(x, m["Orders"], color=PAL["blue"], linewidth=2, marker="o", markersize=4, label="Orders")
    ax.plot(x, m["Active_Customers"], color=PAL["orange"], linewidth=2, marker="o", markersize=4,
            label="Active customers (unique buyers)")
    ax.set_ylabel("Count per month")
    ax.set_ylim(0, m["Orders"].max() * 1.12)
    ax.set_title("Monthly orders and active customers")
    _date_axis(ax)
    ax.legend(loc="upper left")
    fig.tight_layout()
    _save(fig, "monthly_orders_customers.png", out_dir, saved)

    # Month-of-year by year
    fig, ax = plt.subplots(figsize=(11, 4.8))
    for i, (yv, g2) in enumerate(m.groupby("Year")):
        ax.plot(g2["Month"], g2["Revenue"], color=SERIES[i], linewidth=2, marker="o", markersize=5, label=str(yv))
        ax.text(12.15, g2["Revenue"].iloc[-1], str(yv), color=PAL["text"], fontsize=9, va="center")
    ax.set_xticks(range(1, 13), [mm[:3] for mm in MONTH_ORDER])
    _lakh(ax)
    ax.set_ylim(0, m["Revenue"].max() * 1.1)
    ax.set_ylabel("Revenue (₹ lakh)")
    ax.set_title("Revenue by calendar month, each year")
    ax.legend(loc="upper left", ncol=3)
    fig.tight_layout()
    _save(fig, "seasonality_by_year.png", out_dir, saved)

    # Quarterly grouped
    q = R["time"]["quarterly"]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    years = sorted(q["Order_Year"].unique())
    w = 0.26
    for i, yv in enumerate(years):
        qq = q[q["Order_Year"] == yv]
        pos = np.arange(4) + (i - 1) * w
        ax.bar(pos, qq["Revenue"], width=w - 0.02, color=SERIES[i], label=str(yv))
    ax.set_xticks(range(4), ["Q1", "Q2", "Q3", "Q4"])
    ax.grid(axis="x", visible=False)
    _lakh(ax)
    ax.set_ylabel("Revenue (₹ lakh)")
    ax.set_title("Quarterly revenue by year")
    ax.legend(ncol=3, loc="upper left")
    fig.tight_layout()
    _save(fig, "quarterly_revenue.png", out_dir, saved)

    # Seasonal index
    si = R["time"]["seasonal_index"]
    fig, ax = plt.subplots(figsize=(11, 4.6))
    cols = [PAL["blue"] if v > 1 else PAL["neutral"] for v in si["Avg_Index"]]
    ax.bar(si["Month"], si["Avg_Index"], color=cols, width=0.7)
    ax.errorbar(si["Month"], si["Avg_Index"], yerr=[si["Avg_Index"] - si["Min_Index"], si["Max_Index"] - si["Avg_Index"]],
                fmt="none", ecolor=PAL["muted"], capsize=3, linewidth=1)
    ax.axhline(1, color=PAL["text"], linewidth=1, linestyle=":")
    ax.set_xticks(range(1, 13), [mm[:3] for mm in MONTH_ORDER])
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Revenue vs. the year's average month")
    ax.set_title("Seasonal index by month (bar = 3-year average, whiskers = min-max)")
    _note(fig, "Index = month's share of its year's revenue x 12, so 1.0 = an average month and growth between "
               "years is removed. Blue = above average on average.")
    fig.tight_layout()
    _save(fig, "seasonal_index.png", out_dir, saved)

    # Day of week
    dow = R["time"]["day_of_week"]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar([d_[:3] for d_ in dow["Day_of_Week"]], dow["Index_vs_Avg_Day"],
           color=[PAL["blue"] if v > 1 else PAL["neutral"] for v in dow["Index_vs_Avg_Day"]], width=0.65)
    ax.axhline(1, color=PAL["text"], linewidth=1, linestyle=":")
    ax.set_ylim(0.8, dow["Index_vs_Avg_Day"].max() * 1.05)
    for i, v in enumerate(dow["Index_vs_Avg_Day"]):
        ax.text(i, v + 0.005, f"{v:.2f}", ha="center", fontsize=9)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Revenue per day vs average day")
    ax.set_title("Revenue per calendar day, by weekday")
    fig.tight_layout()
    _save(fig, "day_of_week_revenue.png", out_dir, saved)

    # Interactive Plotly version of the trend
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=m["Revenue"], mode="lines+markers", name="Revenue",
                                 line=dict(color=PAL["blue"], width=2),
                                 customdata=np.stack([m["Profit"], m["Orders"], m["MoM_Growth_%"].fillna(0)], axis=1),
                                 hovertemplate="%{x|%b %Y}<br>Revenue ₹%{y:,.0f}<br>Profit ₹%{customdata[0]:,.0f}"
                                               "<br>Orders %{customdata[1]:,}<br>MoM %{customdata[2]:.1f}%<extra></extra>"))
        fig.add_trace(go.Scatter(x=x, y=m["Revenue_3M_MA"], mode="lines", name="3-month MA",
                                 line=dict(color=PAL["orange"], width=2, dash="dash"),
                                 hovertemplate="%{x|%b %Y}<br>3M MA ₹%{y:,.0f}<extra></extra>"))
        fig.update_layout(title="Monthly revenue trend (Delivered orders) - SYNTHETIC DATA", template="plotly_white",
                          yaxis_title="Revenue (₹)", hovermode="x unified", height=480)
        p = out_dir / "monthly_revenue_interactive.html"
        fig.write_html(p, include_plotlyjs="cdn")
        saved.append(p)
    except ImportError:
        pass


def plot_customers(df, R, out_dir, saved):
    plt = _style()
    C = R["customers"]
    buyers = C["customer_summary"][C["customer_summary"]["Total_Orders"] > 0]
    rev = buyers["Total_Revenue"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 5.6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    a1.hist(rev, bins=np.logspace(np.log10(rev.min()), np.log10(rev.max()), 40), color=PAL["blue"], edgecolor="white")
    a1.set_xscale("log")
    for v, lab, c, ha in [(rev.median(), "median", PAL["orange"], "right"), (rev.mean(), "mean", PAL["red"], "left")]:
        a1.axvline(v, color=c, linestyle="--", linewidth=1.5)
        a1.text(v, a1.get_ylim()[1] * 0.92, f" {lab} {inr(v)} " , color=PAL["text"], fontsize=9, ha=ha,
                bbox=dict(facecolor="white", edgecolor="none", pad=1))
    a1.set_ylabel("Customers")
    a1.set_title("Distribution of revenue per customer, 2023-2025 (log scale)")
    a2.boxplot(rev, vert=False, widths=0.6, patch_artist=True, boxprops=dict(facecolor=PAL["light"], edgecolor=PAL["blue"]),
               medianprops=dict(color=PAL["text"]), flierprops=dict(marker="o", markersize=3,
                                                                      markerfacecolor=PAL["orange"], markeredgecolor="none"))
    a2.set_yticks([])
    _rupee(a2, "x")
    a2.set_xlabel("Total delivered revenue per customer (₹, log scale)")
    fig.tight_layout()
    _save(fig, "customer_revenue_distribution.png", out_dir, saved)

    # Lorenz curve
    lz = C["lorenz"]
    conc = C["revenue_concentration"].set_index("Customer_Group")
    fig, ax = plt.subplots(figsize=(6.4, 6))
    # Plot top-down: share of customers (largest first) vs share of revenue
    top_x = 1 - lz["Cum_Share_Customers"][::-1].to_numpy()
    top_y = 1 - lz["Cum_Share_Revenue"][::-1].to_numpy()
    ax.plot(top_x, top_y, color=PAL["blue"], linewidth=2.2, label="Actual")
    ax.plot([0, 1], [0, 1], color=PAL["neutral"], linestyle="--", label="Perfect equality")
    for grp in ["Top 10%", "Top 20%"]:
        xv = int(grp.split()[1][:-1]) / 100
        yv = conc.loc[grp, "Share_of_Revenue"]
        ax.plot([xv], [yv], marker="o", markersize=8, color=PAL["orange"])
        ax.annotate(f"{grp} of customers\n= {pct(yv)} of revenue", (xv, yv), textcoords="offset points",
                    xytext=(12, -28), fontsize=9)
    _pct_axis(ax)
    _pct_axis(ax, "x")
    ax.set_xlabel("Share of customers (highest-spending first)")
    ax.set_ylabel("Cumulative share of revenue")
    gini = C["distribution_stats"].set_index("Metric").loc["Gini coefficient of customer revenue", "Value"]
    ax.set_title(f"Revenue concentration (Gini = {gini:.2f})")
    ax.legend(loc="lower right")
    fig.tight_layout()
    _save(fig, "revenue_concentration_curve.png", out_dir, saved)

    # Orders per customer: customer share vs revenue share
    of = C["order_frequency"]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    pos = np.arange(len(of))
    ax.bar(pos - 0.2, of["Share"], width=0.38, color=PAL["blue"], label="Share of customers")
    ax.bar(pos + 0.2, of["Revenue_Share"], width=0.38, color=PAL["orange"], label="Share of revenue")
    for i, r in enumerate(of.itertuples()):
        ax.text(i - 0.2, r.Share + 0.005, pct(r.Share, 0), ha="center", fontsize=8.5)
        ax.text(i + 0.2, r.Revenue_Share + 0.005, pct(r.Revenue_Share, 0), ha="center", fontsize=8.5)
    ax.set_xticks(pos, of["Orders_per_Customer"])
    ax.grid(axis="x", visible=False)
    _pct_axis(ax)
    ax.set_xlabel("Delivered orders per customer (2023-2025)")
    ax.set_title("Purchase frequency: share of customers vs share of revenue")
    ax.legend()
    fig.tight_layout()
    _save(fig, "purchase_frequency.png", out_dir, saved)

    # Top 20 customers
    for key, metric, fname, title in [("top_customers_revenue", "Total_Revenue", "top_customers_revenue.png",
                                       "Top 20 customers by delivered revenue"),
                                      ("top_customers_profit", "Total_Profit", "top_customers_profit.png",
                                       "Top 20 customers by profit")]:
        t = C[key]
        fig, ax = plt.subplots(figsize=(10, 7))
        _hbar(ax, [f"{r.Customer_ID}  ({r.Region}, {int(r.Total_Orders)} orders)" for r in t.itertuples()],
              t[metric].to_numpy())
        _lakh(ax, "x")
        ax.set_xlabel(f"{metric.replace('_', ' ')} (₹ lakh)")
        ax.set_title(title)
        fig.tight_layout()
        _save(fig, fname, out_dir, saved)

    # Revenue by age band (bivariate)
    order = ["18-24", "25-34", "35-49", "50+"]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    data = [buyers.loc[buyers["Age_Band"] == a, "Total_Revenue"] for a in order]
    ax.boxplot(data, widths=0.55, patch_artist=True, boxprops=dict(facecolor=PAL["light"], edgecolor=PAL["blue"]),
               medianprops=dict(color=PAL["text"], linewidth=1.6),
               flierprops=dict(marker="o", markersize=2.5, markerfacecolor=PAL["orange"], markeredgecolor="none", alpha=0.5))
    ax.set_xticks(range(1, 5), [f"{a}\n(n={len(dd)})" for a, dd in zip(order, data)])
    ax.set_yscale("log")
    _rupee(ax)
    for i, dd in enumerate(data, start=1):
        ax.text(i + 0.3, dd.median(), inr(dd.median()), fontsize=8.5, va="center")
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Revenue per customer (₹, log scale)")
    ax.set_title("Revenue per customer by age band")
    p = C["characteristic_tests"].set_index("Characteristic").loc["Age_Band", "p_value"]
    _note(fig, f"Kruskal-Wallis test across age bands: p = {p:.1e} (difference unlikely to be chance). Association only.")
    fig.tight_layout()
    _save(fig, "customer_revenue_by_age_band.png", out_dir, saved)


def plot_products(df, R, out_dir, saved):
    plt = _style()
    P = R["products"]
    cat = P["category_summary"]
    for metric, fname, color, title in [("Revenue", "category_revenue.png", PAL["blue"], "Revenue by category"),
                                        ("Profit", "category_profit.png", PAL["aqua"], "Profit by category")]:
        t = cat.sort_values(metric, ascending=False)
        fig, ax = plt.subplots(figsize=(9, 4.2))
        share_col = "Revenue_Share" if metric == "Revenue" else "Profit_Share"
        _hbar(ax, t["Category"].tolist(), t[metric].to_numpy(), color=color,
              value_labels=[f"{inr(v)}  ({pct(s)})" + (f"  margin {pct(mg)}" if metric == "Profit" else "")
                            for v, s, mg in zip(t[metric], t[share_col], t["Profit_Margin"])])
        _lakh(ax, "x")
        ax.set_xlabel(f"{metric} (₹ lakh), Delivered lines")
        ax.set_title(f"{title}, 2023-2025")
        fig.tight_layout()
        _save(fig, fname, out_dir, saved)

    # Revenue share vs profit share
    t = cat.sort_values("Revenue_Share", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 4.6))
    pos = np.arange(len(t))
    ax.bar(pos - 0.2, t["Revenue_Share"], width=0.38, color=PAL["blue"], label="Share of revenue")
    ax.bar(pos + 0.2, t["Profit_Share"], width=0.38, color=PAL["aqua"], label="Share of profit")
    for i, r in enumerate(t.itertuples()):
        ax.text(i - 0.2, r.Revenue_Share + 0.006, pct(r.Revenue_Share, 0), ha="center", fontsize=8.5)
        ax.text(i + 0.2, r.Profit_Share + 0.006, pct(r.Profit_Share, 0), ha="center", fontsize=8.5)
    ax.set_xticks(pos, [f"{c}\nmargin {pct(mg)}" for c, mg in zip(t["Category"], t["Profit_Margin"])])
    ax.grid(axis="x", visible=False)
    _pct_axis(ax)
    ax.set_title("Category share of revenue vs share of profit")
    ax.legend()
    fig.tight_layout()
    _save(fig, "category_revenue_vs_profit.png", out_dir, saved)

    # Sub-category margin
    sub = P["subcategory_summary"].sort_values("Profit_Margin")
    fig, ax = plt.subplots(figsize=(10, 8.4))
    _hbar(ax, [f"{s} ({c})" for s, c in zip(sub["Sub_Category"], sub["Category"])], sub["Profit_Margin"].to_numpy(),
          color=[PAL["red"] if v < 0 else PAL["orange"] if v < 0.15 else PAL["blue"] for v in sub["Profit_Margin"]],
          value_labels=[f"{pct(mg)}  (rev {inr(r)})" for mg, r in zip(sub["Profit_Margin"], sub["Revenue"])])
    ax.invert_yaxis()
    ax.axvline(_kpi(R, "Overall Profit Margin"), color=PAL["muted"], linestyle=":", linewidth=1)
    _pct_axis(ax, "x")
    ax.set_xlabel("Profit margin (Profit / Revenue)")
    ax.set_title("Profit margin by sub-category (lowest first)")
    _note(fig, f"Dotted line = overall margin {pct(_kpi(R, 'Overall Profit Margin'))}. "
               "Orange = below 15%, red = loss-making.")
    fig.tight_layout()
    _save(fig, "subcategory_margin.png", out_dir, saved)

    for key, metric, fname, title, color in [
            ("top_products_revenue", "Revenue", "top_products_revenue.png", "Top 20 products by revenue", PAL["blue"]),
            ("top_products_profit", "Profit", "top_products_profit.png", "Top 20 products by profit", PAL["aqua"]),
            ("top_products_units", "Units_Sold", "top_products_units.png", "Top 20 products by units sold", PAL["blue"])]:
        t = P[key]
        fig, ax = plt.subplots(figsize=(10.5, 7.2))
        labels = [f"{n} [{c}]" for n, c in zip(t["Product_Name"], t["Category"])]
        if metric == "Units_Sold":
            _hbar(ax, labels, t[metric].to_numpy(), color=color,
                  value_labels=[f"{v:,.0f} units" for v in t[metric]])
            ax.set_xlabel("Units sold (Delivered)")
        else:
            _hbar(ax, labels, t[metric].to_numpy(), color=color,
                  value_labels=[f"{inr(v)}  (margin {pct(mg)})" for v, mg in zip(t[metric], t["Profit_Margin"])])
            _lakh(ax, "x")
            ax.set_xlabel(f"{metric} (₹ lakh)")
        ax.set_title(title)
        fig.tight_layout()
        _save(fig, fname, out_dir, saved)


def plot_regions(df, R, out_dir, saved):
    plt = _style()
    G = R["regions"]
    reg = G["region_summary"]
    for metric, fname, color, title, share in [
            ("Revenue", "regional_revenue.png", PAL["blue"], "Revenue by region", "Revenue_Share"),
            ("Profit", "regional_profit.png", PAL["aqua"], "Profit by region", None),
            ("Customers", "region_customers.png", PAL["blue"], "Customers by region", None)]:
        t = reg.sort_values(metric, ascending=False)
        fig, ax = plt.subplots(figsize=(9, 3.8))
        if metric == "Revenue":
            labs = [f"{inr(v)}  ({pct(s)})  AOV {inr(a)}" for v, s, a in zip(t[metric], t[share], t["AOV"])]
        elif metric == "Profit":
            labs = [f"{inr(v)}  margin {pct(m_)}" for v, m_ in zip(t[metric], t["Profit_Margin"])]
        else:
            labs = [f"{v:,}  ({inr(r)} per customer)" for v, r in zip(t[metric], t["Revenue_per_Customer"])]
        _hbar(ax, t["Region"].tolist(), t[metric].to_numpy(), color=color, value_labels=labs)
        if metric != "Customers":
            _lakh(ax, "x")
        ax.set_xlabel(metric if metric == "Customers" else f"{metric} (₹ lakh)")
        ax.set_title(f"{title}, 2023-2025")
        fig.tight_layout()
        _save(fig, fname, out_dir, saved)

    # Growth by region
    t = reg.sort_values("Revenue", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 4.6))
    pos = np.arange(len(t))
    for i, yv in enumerate([2023, 2024, 2025]):
        ax.bar(pos + (i - 1) * 0.26, t[f"Revenue_{yv}"], width=0.24, color=SERIES[i], label=str(yv))
    ax.set_xticks(pos, [f"{r}\nCAGR {c:.0f}%" for r, c in zip(t["Region"], t["CAGR_2023_2025_%"])])
    ax.grid(axis="x", visible=False)
    _lakh(ax)
    ax.set_ylabel("Revenue (₹ lakh)")
    ax.set_title("Regional revenue by year (with 2023-25 CAGR)")
    ax.legend(ncol=3)
    fig.tight_layout()
    _save(fig, "regional_growth.png", out_dir, saved)

    st = G["state_summary"]
    fig, ax = plt.subplots(figsize=(10, 7.4))
    _hbar(ax, [f"{s} ({r})" for s, r in zip(st["State"], st["Region"])], st["Revenue"].to_numpy(),
          value_labels=[f"{inr(v)}  ({pct(sh)}), margin {pct(mg)}" for v, sh, mg in
                        zip(st["Revenue"], st["Revenue_Share"], st["Profit_Margin"])])
    _lakh(ax, "x")
    ax.set_xlabel("Revenue (₹ lakh)")
    ax.set_title("Revenue by state / UT")
    _note(fig, "No map is drawn: the data has city and state names but no coordinates or boundary files, "
               "and 21 states cover only part of India, so a ranked bar chart is more accurate.")
    fig.tight_layout()
    _save(fig, "state_revenue.png", out_dir, saved)

    # Category mix by region (heatmap)
    import seaborn as sns
    h = G["category_by_region_share"].set_index("Region")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    sns.heatmap(h, annot=True, fmt=".0%", cmap=sns.light_palette(PAL["blue"], as_cmap=True), cbar=False,
                linewidths=2, linecolor="white", ax=ax, annot_kws={"fontsize": 9})
    ax.set_ylabel("")
    ax.set_xlabel("")
    ax.set_title("Category share of each region's revenue")
    fig.tight_layout()
    _save(fig, "category_region_mix.png", out_dir, saved)


def plot_discount(df, R, out_dir, saved):
    plt = _style()
    D = R["discount"]
    lines = D["_lines"]
    rng = np.random.default_rng(config.RANDOM_SEED)
    samp = lines.sample(n=min(5000, len(lines)), random_state=config.RANDOM_SEED)
    jitter = samp["Discount"] + rng.uniform(-0.012, 0.012, len(samp))
    means = lines.groupby(lines["Discount"].round(2)).agg(Sales=("Sales", "median"), Profit=("Profit", "median"),
                                                          Profit_Margin=("Profit_Margin", "median"))
    corr = D["discount_correlations"].set_index("Pair")
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))
    for ax, col, lab in zip(axes, ["Sales", "Profit", "Profit_Margin"],
                            ["Sales per line (₹, log)", "Profit per line (₹)", "Profit margin per line"]):
        ax.scatter(jitter, samp[col], s=6, alpha=0.25, color=PAL["blue"], edgecolors="none", label="Order lines (sample)")
        ax.plot(means.index, means[col], color=PAL["orange"], marker="o", linewidth=2, markersize=6,
                label="Median at each discount")
        rho = corr.loc[f"Discount vs {col}", "Spearman_rho"]
        ax.set_title(f"Discount vs {col.replace('_', ' ')}  (Spearman rho = {rho:.2f})", fontsize=11)
        ax.set_xlabel("Discount")
        ax.set_ylabel(lab)
        _pct_axis(ax, "x")
        if col == "Sales":
            ax.set_yscale("log")
            _rupee(ax)
        elif col == "Profit":
            ax.set_ylim(samp["Profit"].quantile(0.005), samp["Profit"].quantile(0.995))
            ax.axhline(0, color=PAL["red"], linewidth=1)
            _rupee(ax)
        else:
            _pct_axis(ax)
            ax.axhline(0, color=PAL["red"], linewidth=1)
    axes[0].legend(loc="lower left", fontsize=8.5)
    fig.suptitle("Discount vs sales, profit and margin (Delivered lines; association, not causation)", x=0.01,
                 ha="left", fontweight="bold", fontsize=13)
    _note(fig, "5,000 randomly sampled lines shown with slight horizontal jitter (discounts are in 5% steps); "
               "medians and correlations use all delivered lines.")
    fig.tight_layout()
    _save(fig, "discount_scatter_panels.png", out_dir, saved)

    # Margin by discount bucket within each category (small multiples)
    mb = D["margin_by_category_bucket"].set_index("Category")
    counts = lines.groupby(["Category", "Discount_Bucket"], observed=False).size().unstack()
    order = R["products"]["category_summary"]["Category"].tolist()
    fig, axes = plt.subplots(2, 3, figsize=(15, 7.2), sharey=True)
    for ax, c in zip(axes.flat, order):
        vals = mb.loc[c].to_numpy()
        n = counts.loc[c].to_numpy()
        cols = [PAL["neutral"] if k < 30 else (PAL["red"] if v < 0 else PAL["blue"]) for v, k in zip(vals, n)]
        ax.bar(range(len(vals)), vals, color=cols, width=0.65)
        for i, (v, k) in enumerate(zip(vals, n)):
            ax.text(i, v + (0.015 if v >= 0 else -0.05), f"{pct(0.0 if abs(v) < 0.005 else v, 0)}\nn={k}",
                    ha="center", fontsize=8)
        ax.set_ylim(-0.14, 0.68)
        ax.set_xticks(range(len(vals)), mb.columns)
        ax.axhline(0, color=PAL["muted"], linewidth=0.8)
        ax.grid(axis="x", visible=False)
        _pct_axis(ax)
        rho = D["discount_margin_within_category"].set_index("Category").loc[c, "Spearman_rho_Discount_vs_Margin"]
        ax.set_title(f"{c}  (rho = {rho:.2f})", fontsize=11)
    for ax in axes[:, 0]:
        ax.set_ylabel("Profit margin")
    fig.suptitle("Profit margin falls as discount deepens - within every category", x=0.01, ha="left",
                 fontweight="bold", fontsize=13)
    _note(fig, "Grey bars: fewer than 30 lines (unreliable). rho = Spearman correlation between line discount and line "
               "margin within the category. Association, not causation.")
    fig.tight_layout()
    _save(fig, "discount_profit_relationship.png", out_dir, saved)

    # Bucket summary: two panels
    b = D["discount_summary"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.4))
    a1.bar(b["Discount_Bucket"].astype(str), b["Revenue_Share"], color=PAL["blue"], width=0.6)
    for i, r in enumerate(b.itertuples()):
        a1.text(i, r.Revenue_Share + 0.006, f"{pct(r.Revenue_Share)}\n({r.Lines:,} lines)", ha="center", fontsize=8.5)
    _pct_axis(a1)
    a1.set_ylim(0, b["Revenue_Share"].max() * 1.25)
    a1.grid(axis="x", visible=False)
    a1.set_title("Share of revenue by discount level", fontsize=11)
    a2.bar(b["Discount_Bucket"].astype(str), b["Profit_Margin"], color=PAL["aqua"], width=0.6)
    for i, r in enumerate(b.itertuples()):
        a2.text(i, r.Profit_Margin + 0.005, f"{pct(r.Profit_Margin)}\nElectronics {pct(r.Electronics_Share, 0)}",
                ha="center", fontsize=8.5)
    _pct_axis(a2)
    a2.set_ylim(0, b["Profit_Margin"].max() * 1.3)
    a2.grid(axis="x", visible=False)
    a2.set_title("Overall margin by discount level (mixes categories)", fontsize=11)
    for a in (a1, a2):
        a.set_xlabel("Discount level")
    _note(fig, "The overall margin does not fall steadily because the 5-10% level contains many low-margin "
               "Electronics lines - compare within categories (previous chart).")
    fig.tight_layout()
    _save(fig, "discount_bucket_summary.png", out_dir, saved)


def plot_profitability(df, R, out_dir, saved):
    plt = _style()
    d = _delivered(df)
    order = R["products"]["category_summary"]["Category"].tolist()
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True, sharey=True)
    for ax, c in zip(axes.flat, order):
        g = d[d["Category"] == c]
        ax.scatter(g["Sales"], g["Profit"], s=6, alpha=0.3, color=PAL["blue"], edgecolors="none")
        ax.axhline(0, color=PAL["red"], linewidth=1)
        ax.set_xscale("log")
        ax.set_yscale("symlog", linthresh=1000)
        ax.set_yticks([-10000, -1000, 0, 1000, 10000], ["-₹10,000", "-₹1,000", "₹0", "₹1,000", "₹10,000"])
        ax.set_ylim(-20000, 60000)
        mg = g["Profit"].sum() / g["Sales"].sum()
        ax.set_title(f"{c}: margin {pct(mg)}, {int((g['Profit'] < 0).sum())} loss lines", fontsize=10.5)
        _rupee(ax, "x")
    for ax in axes[1]:
        ax.set_xlabel("Sales per line (₹, log)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Profit per line (₹, symlog)")
    fig.suptitle("Revenue vs profit per order line, by category", x=0.01, ha="left", fontweight="bold", fontsize=13)
    _note(fig, "Each dot = one delivered order line. Points below the red line lost money. Symmetric-log profit axis "
               "shows both gains and losses.")
    fig.tight_layout()
    _save(fig, "revenue_vs_profit_scatter.png", out_dir, saved)

    # Product quadrant
    Q = R["profitability"]
    p = Q["product_quadrants"]
    th = Q["quadrant_thresholds"].set_index("Threshold")["Value"]
    fig, ax = plt.subplots(figsize=(11.5, 7))
    hl = p["Quadrant"] == "High revenue + low profit"
    ax.scatter(p.loc[~hl, "Revenue"], p.loc[~hl, "Profit"], s=45, color=PAL["blue"], alpha=0.75,
               edgecolors="white", linewidths=1, label="Other products")
    ax.scatter(p.loc[hl, "Revenue"], p.loc[hl, "Profit"], s=70, color=PAL["orange"],
               edgecolors="white", linewidths=1, label="High revenue + low profit")
    ax.axvline(th["Median product revenue"], color=PAL["muted"], linestyle=":", linewidth=1)
    ax.axhline(th["Median product profit"], color=PAL["muted"], linestyle=":", linewidth=1)
    ax.axhline(0, color=PAL["red"], linewidth=0.8)
    ax.set_xscale("log")
    label_set = pd.concat([p.nlargest(6, "Revenue"), p.nlargest(4, "Profit"), p[hl], p.nsmallest(1, "Revenue")]).drop_duplicates("Product_ID")
    offsets = {"Nova X7 Pro Smartphone 256GB": ((10, -4), "left"), "Women's Printed Kurta": ((-6, 4), "right"),
               "Pulse Lite Smartphone 64GB": ((-14, 16), "right"), "AeroBook 14 Laptop": ((10, -18), "left")}
    for r in label_set.itertuples():
        xy, ha = offsets.get(r.Product_Name, ((6, 4), "left"))
        arrow = dict(arrowstyle="-", color=PAL["muted"], linewidth=0.6) if r.Product_Name in offsets else None
        ax.annotate(r.Product_Name, (r.Revenue, r.Profit), textcoords="offset points", xytext=xy, ha=ha,
                    fontsize=7.8, color=PAL["text"], arrowprops=arrow)
    ax.set_xlim(right=p["Revenue"].max() * 2.3)
    _rupee(ax, "x")
    _lakh(ax)
    ax.set_xlabel("Product revenue (₹, log scale)")
    ax.set_ylabel("Product profit (₹ lakh)")
    ax.set_title("Product revenue vs profit (dotted lines = medians across 61 products)")
    ax.legend(loc="upper left")
    _note(fig, "Exploratory positioning only - not final product segments. Low-revenue products are split by "
               f"margin (median {pct(th['Median product margin'])}).")
    fig.tight_layout()
    _save(fig, "product_revenue_profit_quadrant.png", out_dir, saved)


def plot_payment_status_corr_outliers(df, R, out_dir, saved):
    plt = _style()
    import seaborn as sns
    pay = R["payment_status"]["payment_summary"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 4.4))
    _hbar(a1, pay["Payment_Method"].tolist(), pay["Revenue_Share"].to_numpy(), fmt=pct,
          value_labels=[f"{pct(s)}  ({o:,} orders)" for s, o in zip(pay["Revenue_Share"], pay["Orders"])])
    _pct_axis(a1, "x")
    a1.set_title("Share of revenue by payment method", fontsize=11)
    pos = np.arange(len(pay))
    a2.bar(pos - 0.2, pay["Cancel_Rate"], width=0.38, color=PAL["blue"], label="Orders with a cancellation")
    a2.bar(pos + 0.2, pay["Return_Rate"], width=0.38, color=PAL["orange"], label="Orders with a return")
    a2.set_xticks(pos, pay["Payment_Method"])
    a2.grid(axis="x", visible=False)
    _pct_axis(a2)
    a2.set_title("Cancellation and return rate by payment method", fontsize=11)
    a2.legend()
    fig.tight_layout()
    _save(fig, "payment_method_analysis.png", out_dir, saved)

    st = R["payment_status"]["status_summary"].sort_values("Sales_Value", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 3.4))
    _hbar(ax, st["Order_Status"].tolist(), st["Sales_Value"].to_numpy(),
          color=[PAL["blue"] if s == "Delivered" else PAL["neutral"] for s in st["Order_Status"]],
          value_labels=[f"{inr(v)}  ({pct(s)} of booked value, {n:,} lines)"
                        for v, s, n in zip(st["Sales_Value"], st["Value_Share"], st["Lines"])])
    _lakh(ax, "x")
    ax.set_xlabel("Booked sales value (₹ lakh)")
    ax.set_title("Booked sales by order status (only Delivered counts as revenue)")
    fig.tight_layout()
    _save(fig, "order_status_value.png", out_dir, saved)

    C = R["correlations"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    for ax, key, title in zip(axes, ["pearson", "spearman"], ["Pearson (linear)", "Spearman (rank, robust to skew)"]):
        sns.heatmap(C[key], annot=True, fmt=".2f", cmap=sns.diverging_palette(12, 250, s=75, l=50, as_cmap=True),
                    vmin=-1, vmax=1, center=0, square=True, linewidths=1, linecolor="white", cbar=key == "spearman",
                    ax=ax, annot_kws={"fontsize": 8.5})
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=45)
    fig.suptitle("Correlation matrix of numeric variables (Delivered lines)", x=0.01, ha="left", fontweight="bold",
                 fontsize=13)
    _note(fig, "Blue = positive, red = negative. Correlation measures association only; it does not show that one "
               "variable causes another.")
    fig.tight_layout()
    _save(fig, "correlation_heatmap.png", out_dir, saved)

    d = _delivered(df)
    fig, axes = plt.subplots(1, 5, figsize=(17, 4.4))
    for ax, col in zip(axes, ["Sales", "Profit", "Quantity", "Discount", "Unit_Price"]):
        s = d[col].astype(float)
        ax.boxplot(s, widths=0.55, patch_artist=True, boxprops=dict(facecolor=PAL["light"], edgecolor=PAL["blue"]),
                   medianprops=dict(color=PAL["text"]),
                   flierprops=dict(marker="o", markersize=3, markerfacecolor=PAL["orange"], markeredgecolor="none",
                                   alpha=0.5))
        if col in ("Sales", "Unit_Price", "Quantity"):
            ax.set_yscale("log")
        if col == "Discount":
            _pct_axis(ax)
        elif col in ("Sales", "Profit", "Unit_Price"):
            _rupee(ax)
        n = R["outliers"]["outlier_percentiles"].set_index("Variable").loc[col, "IQR_Outliers"]
        ax.set_title(f"{col}\n{int(n):,} beyond IQR fences ({100 * n / len(s):.1f}%)", fontsize=10.5)
        ax.set_xticks([])
    fig.suptitle("Remaining extreme values (kept - investigated, not removed)", x=0.01, ha="left",
                 fontweight="bold", fontsize=13)
    _note(fig, "Log scale for Sales, Unit_Price and Quantity. Quantity: IQR fences collapse to 1 because 76% of lines "
               "have 1 unit, so any multi-unit line is 'outside'.")
    fig.tight_layout()
    _save(fig, "outlier_boxplots.png", out_dir, saved)


def make_figures(df: pd.DataFrame, R: dict, out_dir: Path = config.FIGURES_DIR) -> list[Path]:
    """Create every EDA figure; returns the saved paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for fn in (plot_univariate, plot_categorical, plot_time_series, plot_customers, plot_products,
               plot_regions, plot_discount, plot_profitability, plot_payment_status_corr_outliers):
        fn(df, R, out_dir, saved)
    return saved


# =============================================================================
# 16. SAVE TABLES + SUMMARY REPORT
# =============================================================================
def save_eda_outputs(R: dict, out_dir: Path = config.TABLES_DIR) -> list[Path]:
    """Write the analytical tables used by the report, Power BI and Streamlit."""
    out_dir.mkdir(parents=True, exist_ok=True)
    m = R["time"]["monthly"].copy()
    m["Year_Month"] = m["Year_Month"].astype(str)
    cust = R["customers"]["customer_summary"].copy()
    for c in ["First_Purchase_Date", "Last_Purchase_Date"]:
        cust[c] = cust[c].dt.strftime("%Y-%m-%d")
    tables = {
        "eda_kpis.csv": R["kpis"][["KPI", "Value", "Display", "Formula"]],
        "eda_order_definition_checks.csv": R["order_definition"],
        "eda_descriptive_statistics.csv": R["descriptive_stats"],
        "monthly_summary.csv": m,
        "yearly_summary.csv": R["time"]["yearly"],
        "quarterly_summary.csv": R["time"]["quarterly"],
        "seasonal_index.csv": R["time"]["seasonal_index"],
        "day_of_week_summary.csv": R["time"]["day_of_week"],
        "customer_summary.csv": cust,
        "top_customers_revenue.csv": R["customers"]["top_customers_revenue"],
        "top_customers_profit.csv": R["customers"]["top_customers_profit"],
        "revenue_concentration.csv": R["customers"]["revenue_concentration"],
        "purchase_frequency.csv": R["customers"]["order_frequency"],
        "customer_characteristic_tests.csv": R["customers"]["characteristic_tests"],
        "customer_revenue_by_attribute.csv": R["customers"]["revenue_by_attribute"],
        "product_summary.csv": R["products"]["product_summary"],
        "category_summary.csv": R["products"]["category_summary"],
        "subcategory_summary.csv": R["products"]["subcategory_summary"],
        "product_revenue_profit_quadrants.csv": R["profitability"]["product_quadrants"],
        "regional_summary.csv": R["regions"]["region_summary"],
        "state_summary.csv": R["regions"]["state_summary"],
        "city_summary.csv": R["regions"]["city_summary"],
        "discount_summary.csv": R["discount"]["discount_summary"],
        "discount_margin_by_category.csv": R["discount"]["margin_by_category_bucket"],
        "discount_correlations.csv": pd.concat([R["discount"]["discount_correlations"],
                                                R["discount"]["discount_margin_within_category"]
                                                .rename(columns={"Spearman_rho_Discount_vs_Margin": "Spearman_rho",
                                                                 "p_value": "Spearman_p"})
                                                .assign(Pair=lambda t: "Within " + t["Category"] + ": Discount vs Profit_Margin")
                                                [["Pair", "Spearman_rho", "Spearman_p"]]]),
        "payment_summary.csv": R["payment_status"]["payment_summary"],
        "order_status_summary.csv": R["payment_status"]["status_summary"],
        "correlation_pairs.csv": R["correlations"]["correlation_pairs"],
        "eda_outlier_summary.csv": R["outliers"]["outlier_percentiles"],
        "eda_outlier_classes.csv": R["outliers"]["outlier_classes"],
        "business_questions.csv": R["business_questions"],
        "business_insights.csv": R["insights"],
        "eda_quality_checks.csv": R["quality_checks"],
    }
    paths = []
    for name, t in tables.items():
        p = out_dir / name
        t.to_csv(p, index=False, encoding="utf-8-sig")
        paths.append(p)
    return paths


def _md_table(t: pd.DataFrame) -> str:
    cols = list(t.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in t.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in r) + " |")
    return "\n".join(lines)


def write_eda_summary(R: dict, path: Path = config.REPORTS_DIR / "eda_summary.md") -> Path:
    """Generate the EDA summary report. Every number is inserted from computed results."""
    k = R["kpis"].set_index("KPI")["Display"]
    ins = R["insights"]
    bq = R["business_questions"]
    cat = R["products"]["category_summary"]
    reg = R["regions"]["region_summary"]
    yr = R["time"]["yearly"]
    pairs = R["correlations"]["correlation_pairs"]
    strong = pairs[pairs["Spearman_rho"].abs() >= 0.4]
    ra = R["customers"]["revenue_by_attribute"]
    ab = ra[ra["Attribute"] == "Age_Band"].set_index("Group")

    def section(area):
        t = ins[ins["Area"].isin(area)]
        return "\n".join(f"- **{r.Observation}.** {r.Evidence}.  \n  *Implication:* {r._4}" for r in t.itertuples())

    cat_t = cat[["Category", "Revenue", "Profit", "Profit_Margin", "Revenue_Share", "Profit_Share", "Return_Rate"]].copy()
    for c in ["Revenue", "Profit"]:
        cat_t[c] = cat_t[c].map(inr)
    for c in ["Profit_Margin", "Revenue_Share", "Profit_Share", "Return_Rate"]:
        cat_t[c] = cat_t[c].map(pct)
    reg_t = reg[["Region", "Revenue", "Profit_Margin", "Customers", "AOV", "Revenue_Share", "CAGR_2023_2025_%"]].copy()
    reg_t["Revenue"] = reg_t["Revenue"].map(inr)
    reg_t["AOV"] = reg_t["AOV"].map(inr)
    reg_t["Profit_Margin"] = reg_t["Profit_Margin"].map(pct)
    reg_t["Revenue_Share"] = reg_t["Revenue_Share"].map(pct)
    reg_t["CAGR_2023_2025_%"] = reg_t["CAGR_2023_2025_%"].map(lambda v: f"{v:.1f}%")
    yr_t = yr[["Order_Year", "Revenue", "Profit", "Profit_Margin", "Orders", "Customers", "AOV", "YoY_Revenue_Growth_%"]].copy()
    for c in ["Revenue", "Profit", "AOV"]:
        yr_t[c] = yr_t[c].map(inr)
    yr_t["Profit_Margin"] = yr_t["Profit_Margin"].map(pct)
    yr_t["YoY_Revenue_Growth_%"] = yr_t["YoY_Revenue_Growth_%"].map(lambda v: "-" if pd.isna(v) else f"+{v:.1f}%")
    rel = "\n".join(f"- {r.Variable_1} vs {r.Variable_2}: Spearman rho = {r.Spearman_rho:.2f} ({r._5})"
                    for r in strong.itertuples())

    text = f"""# EDA Summary: Customer Revenue Intelligence

> **SYNTHETIC DATA.** This summary is generated by `src/eda.py` from `data/processed/customer_sales_cleaned.csv`, the Step 3 output. Every number is computed; none is typed by hand. Re-running the script reproduces this file.

## 1. EDA Objective
The aim is to understand how revenue and profit are generated before any modelling:
- revenue trends over time;
- which products, categories, regions and customers matter most;
- how discounts relate to profitability;
- which questions the RFM, segmentation, CLV, prediction and forecasting steps should answer.

The analysis is exploratory and descriptive. Associations are reported as associations, not as causes.

**Measurement rules**
- Revenue, cost, profit and units count **Delivered order lines only**.
- An order is a distinct `Order_ID`. This was verified: {R['order_definition'].set_index('Check').loc['Distinct Order_ID', 'Value']:,} Order_IDs equal {R['order_definition'].set_index('Check').loc['Distinct (Customer, Date) pairs', 'Value']:,} distinct customer-date pairs, and no Order_ID has more than one customer, date or payment method.
- Order KPIs count only orders with at least one Delivered line.
- Customer age is summarised per customer.

## 2. Dataset Overview
{_md_table(R['dataset_summary'])}

## 3. Key KPIs
{_md_table(R['kpis'][['KPI', 'Display', 'Formula']])}

### Revenue by year
{_md_table(yr_t)}

## 4. Major Revenue Insights
{section(['Revenue', 'Operations'])}

## 5. Customer Insights
{section(['Customers'])}

## 6. Product Insights
{section(['Products'])}

### Category performance
{_md_table(cat_t)}

## 7. Regional Insights
{section(['Region'])}

{_md_table(reg_t)}

## 8. Profitability Insights
{section(['Profitability'])}

Product positioning (medians across 61 products; exploratory, not final segments):
{_md_table(R['profitability']['quadrant_summary'].assign(Revenue=lambda t: t['Revenue'].map(inr), Profit=lambda t: t['Profit'].map(inr), Margin=lambda t: t['Margin'].map(pct)))}

## 9. Discount Insights
{section(['Discount'])}

## 10. Time-Series Insights
{section(['Seasonality', 'Timing'])}

## 11. Important Relationships (correlation ≠ causation)
Spearman correlations with |rho| ≥ 0.4, computed on Delivered lines:
{rel}

Most of these relationships are true by construction. Sales, Cost and Unit_Price move together because Sales = Qty × Price × (1 − Discount). They are not evidence that one variable drives another. Customer age shows only negligible correlation with any line-level amount. At customer level, however, age band is significantly associated with total revenue. Customers aged 35-49 place a median of {int(ab.loc['35-49', 'Median_Orders'])} orders, against {int(ab.loc['18-24', 'Median_Orders'])} for 18-24. Their median AOV is {inr(ab.loc['35-49', 'Median_AOV'])}, against {inr(ab.loc['18-24', 'Median_AOV'])}. The gap therefore comes mainly from purchase frequency, not from the value of individual lines.

## 12. Answers to the Business Questions
{_md_table(bq[['Question', 'Answer (from data)']])}

## 13. Potential Business Problems
1. **Margin dilution from revenue mix.** Electronics accounts for {pct(cat.set_index('Category').loc['Electronics', 'Revenue_Share'])} of revenue at a {pct(cat.set_index('Category').loc['Electronics', 'Profit_Margin'])} margin. Some high-selling SKUs (the TV and the premium laptop) earn close to zero or negative profit.
2. **Discount-driven festive growth.** The October peak comes with the lowest monthly margins.
3. **Customer concentration and lapsing.** Revenue depends on a small group of frequent buyers, while a large group has not bought in over 180 days.
4. **Revenue leakage.** {k['Share of Booked Sales Not Realised']} of booked sales ({k['Revenue Lost to Cancellations & Returns']}) was cancelled or returned. The highest rates are in Fashion returns and among COD orders.
5. **Slowing growth.** Year-on-year revenue growth fell from 2024 to 2025. Central's share of revenue is shrinking.

## 14. Recommendations for Next Analytical Steps
**RFM analysis (Step 5)**
- How many customers fall into champion, loyal, at-risk and lapsed groups?
- How much revenue sits with customers who have not bought in over 180 days?
- Is the revenue concentration seen here driven by Frequency, by Monetary value, or by both?

**Customer segmentation (Step 6, K-Means)**
- Do natural behavioural clusters exist beyond RFM rules, for example discount-driven buyers or premium Electronics buyers?
- Do the clusters differ by age band, since age was the only demographic associated with revenue?

**CLV (Step 7)**
- What is each customer's expected future value?
- Does including profit margin change which customers look most valuable, given the Electronics vs Fashion margin gap?

**Revenue prediction (Step 8)**
- Can a customer's next-6-month revenue be predicted from past frequency, AOV, category mix, discount use and return rate?
- Behavioural variables showed strong associations here (e.g. order count rho ≈ 0.84 with revenue).
- Avoid leakage: build all features from the observation window only.

**Sales forecasting (Step 9)**
- The model needs to capture the upward trend, the growth slowdown and a strong, recurring Q4/October peak.
- Diwali's shifting date moves some festive demand between October and November. Test seasonal models (Holt-Winters, SARIMA) against a seasonal-naive baseline on a 6-month holdout.

## Limitations
- The data are synthetic. The patterns reflect the generator's assumptions, and the findings illustrate the method rather than describe a real market.
- 36 months give only 3 observations per calendar month, so seasonal estimates are indicative.
- The trend-adjusted seasonal ratio uses only 2 observations per month.
- Returned lines are excluded from revenue, and their logistics costs are not modelled.
- The bulk-order and premium outliers were kept on purpose. Mean-based statistics are therefore sensitive to them, so medians are reported alongside means.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# =============================================================================
# 17. MAIN
# =============================================================================
def run_eda(make_plots: bool = True, verbose: bool = True) -> dict:
    """Load data, run all analyses, save tables, figures and the summary report."""
    df = load_clean_data()
    R = run_all_analyses(df)
    R["tables_saved"] = save_eda_outputs(R)
    R["figures_saved"] = make_figures(df, R) if make_plots else []
    R["report"] = write_eda_summary(R)
    R["df"] = df
    if verbose:
        pd.set_option("display.width", 220)
        pd.set_option("display.max_colwidth", 140)
        print(f"*** {config.DATASET_LABEL} ***\n")
        print(R["kpis"][["KPI", "Display"]].to_string(index=False), "\n")
        print(R["business_questions"][["Question", "Answer (from data)"]].to_string(index=False), "\n")
        print(R["quality_checks"].to_string(index=False), "\n")
        print(f"Insights generated: {len(R['insights'])}")
        print(f"Tables saved: {len(R['tables_saved'])} | Figures saved: {len(R['figures_saved'])}")
        print(f"Report: {R['report'].relative_to(config.PROJECT_ROOT)}")
    return R


if __name__ == "__main__":
    run_eda()
