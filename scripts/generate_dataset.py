#!/usr/bin/env python3
"""
generate_dataset.py
===================
Generates the SYNTHETIC e-commerce transaction dataset for the
"Customer Revenue Intelligence" project.

    >>> SYNTHETIC DATA — generated for academic demonstration only. <<<
    No real customers, companies or transactions are represented.
    Names are random combinations of common Indian first names and surnames.

What the script does
--------------------
1. Builds reference data: Indian geography, a 61-product catalogue, name lists.
2. Creates 2,000 customers. Each is secretly assigned a behavioural *persona*
   (high-value frequent, loyal, new, occasional, at-risk, low-value, inactive).
   The persona drives how often, when and what they buy, but it is NEVER
   written to the output, so segments must be rediscovered later with RFM and
   K-Means.
3. Places each customer's orders on a calendar that has a growth trend, a
   mid-2024 slowdown, monthly seasonality, weekend lift and Indian sale events
   (Republic Day, mid-year sale, Independence Day, the moving Diwali festive
   sale, year-end sale).
4. Fills each order with 1-3 products, prices, discounts, costs and statuses
   following explicit business rules (see docs/STEP2_Dataset_Design.md).
5. Injects a small, documented set of data-quality problems and logs exactly
   what was injected to data/raw/data_quality_injection_log.json.
6. Saves data/raw/customer_sales_raw.csv and prints shape, first 10 rows,
   dtypes and basic statistics.

Run from the project root:
    python scripts/generate_dataset.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# Make the project root importable so `import config` works from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402


# =============================================================================
# 1. REFERENCE DATA
# =============================================================================

# Region -> State -> [(City, City tier)]. Tier 1 = metro, 3 = smaller city.
# Every city belongs to exactly one state and every state to one region.
GEOGRAPHY: dict[str, dict[str, list[tuple[str, int]]]] = {
    "North": {
        "Delhi": [("New Delhi", 1)],
        "Haryana": [("Gurugram", 1)],
        "Uttar Pradesh": [("Lucknow", 2), ("Noida", 2), ("Kanpur", 2)],
        "Punjab": [("Ludhiana", 2), ("Amritsar", 2)],
        "Chandigarh": [("Chandigarh", 2)],
        "Rajasthan": [("Jaipur", 2)],
    },
    "South": {
        "Karnataka": [("Bengaluru", 1), ("Mysuru", 2)],
        "Tamil Nadu": [("Chennai", 1), ("Coimbatore", 2)],
        "Telangana": [("Hyderabad", 1)],
        "Kerala": [("Kochi", 2), ("Thiruvananthapuram", 2)],
        "Andhra Pradesh": [("Visakhapatnam", 2)],
    },
    "East": {
        "West Bengal": [("Kolkata", 1), ("Siliguri", 3)],
        "Odisha": [("Bhubaneswar", 2)],
        "Bihar": [("Patna", 2)],
        "Assam": [("Guwahati", 2)],
        "Jharkhand": [("Ranchi", 3)],
    },
    "West": {
        "Maharashtra": [("Mumbai", 1), ("Pune", 1), ("Nagpur", 2)],
        "Gujarat": [("Ahmedabad", 1), ("Surat", 2), ("Vadodara", 2)],
        "Goa": [("Panaji", 3)],
    },
    "Central": {
        "Madhya Pradesh": [("Indore", 2), ("Bhopal", 2), ("Jabalpur", 3)],
        "Chhattisgarh": [("Raipur", 3)],
    },
}

# Share of the customer base living in each region (assumption).
REGION_SHARE = {"North": 0.22, "South": 0.27, "East": 0.13,
                "West": 0.26, "Central": 0.12}

# How strongly each region's customer acquisition grows over the 3 years.
# f(t) with t in [0, 1] across the period. South/East grow, Central shrinks.
REGION_ACQUISITION_TREND = {
    "North":   lambda t: 1.00 + 0.05 * t,
    "South":   lambda t: 0.60 + 1.00 * t,
    "East":    lambda t: 0.80 + 0.50 * t,
    "West":    lambda t: 1.05 - 0.05 * t,
    "Central": lambda t: 1.30 - 0.70 * t,
}

CITY_TIER_WEIGHT = {1: 3.0, 2: 1.5, 3: 0.8}       # where customers live
CITY_TIER_PRICE_PREF = {1: 0.08, 2: 0.0, 3: -0.08}  # metros buy pricier items

# Product catalogue: (Name, Category, Sub_Category, base price INR,
#                     cost ratio = unit cost / list price, popularity weight)
# Cost ratio encodes margin: Electronics thin, Fashion/Beauty fat.
CATALOGUE: list[tuple[str, str, str, float, float, float]] = [
    # --- Electronics: high ticket, thin margin -----------------------------
    ("Nova X5 Smartphone 128GB", "Electronics", "Smartphones", 18999, 0.86, 0.9),
    ("Nova X7 Pro Smartphone 256GB", "Electronics", "Smartphones", 34999, 0.88, 0.4),
    ("Pulse Lite Smartphone 64GB", "Electronics", "Smartphones", 9999, 0.84, 1.0),
    ("AeroBook 14 Laptop", "Electronics", "Laptops", 52999, 0.87, 0.22),
    ("AeroBook Pro 16 Laptop", "Electronics", "Laptops", 84999, 0.91, 0.08),
    ("43-inch 4K Smart TV", "Electronics", "Televisions", 27999, 0.925, 0.25),
    ("Wireless Earbuds Air", "Electronics", "Audio", 1999, 0.62, 2.2),
    ("Noise-Cancelling Headphones", "Electronics", "Audio", 7999, 0.70, 0.9),
    ("Bluetooth Party Speaker", "Electronics", "Audio", 3499, 0.66, 0.8),
    ("FitPulse Smartwatch", "Electronics", "Wearables", 3999, 0.68, 1.4),
    ("Fitness Band Lite", "Electronics", "Wearables", 1799, 0.64, 1.0),
    ("65W Fast Charger", "Electronics", "Accessories", 1299, 0.45, 1.8),
    ("20000mAh Power Bank", "Electronics", "Accessories", 1499, 0.55, 1.5),
    # --- Fashion: high margin, high returns ---------------------------------
    ("Men's Cotton Casual Shirt", "Fashion", "Men's Clothing", 1299, 0.45, 2.0),
    ("Men's Slim Fit Jeans", "Fashion", "Men's Clothing", 1799, 0.48, 1.6),
    ("Women's Printed Kurta", "Fashion", "Women's Clothing", 1199, 0.42, 2.2),
    ("Women's Cotton Saree", "Fashion", "Women's Clothing", 2499, 0.50, 1.2),
    ("Women's Western Dress", "Fashion", "Women's Clothing", 1899, 0.46, 1.1),
    ("Running Shoes", "Fashion", "Footwear", 2999, 0.52, 1.4),
    ("Casual Sneakers", "Fashion", "Footwear", 2199, 0.50, 1.3),
    ("Leather Formal Shoes", "Fashion", "Footwear", 3499, 0.55, 0.6),
    ("Leather Wallet", "Fashion", "Fashion Accessories", 799, 0.38, 1.2),
    ("Analog Wrist Watch", "Fashion", "Fashion Accessories", 2499, 0.47, 0.7),
    ("Polarised Sunglasses", "Fashion", "Fashion Accessories", 1299, 0.40, 0.8),
    # --- Home & Kitchen: mid margin ----------------------------------------
    ("Mixer Grinder 750W", "Home & Kitchen", "Kitchen Appliances", 3499, 0.66, 1.2),
    ("Air Fryer 4L", "Home & Kitchen", "Kitchen Appliances", 5999, 0.68, 1.0),
    ("Induction Cooktop", "Home & Kitchen", "Kitchen Appliances", 2499, 0.64, 0.8),
    ("Microwave Oven 20L", "Home & Kitchen", "Kitchen Appliances", 7499, 0.73, 0.5),
    ("Non-Stick Cookware Set", "Home & Kitchen", "Cookware", 2299, 0.58, 1.1),
    ("Pressure Cooker 5L", "Home & Kitchen", "Cookware", 1899, 0.60, 1.3),
    ("Cotton Double Bedsheet", "Home & Kitchen", "Home Decor", 1099, 0.50, 1.6),
    ("Blackout Curtains (Set of 2)", "Home & Kitchen", "Home Decor", 1499, 0.52, 0.8),
    ("Decorative Table Lamp", "Home & Kitchen", "Home Decor", 1299, 0.55, 0.5),
    ("Steel Water Bottle Set", "Home & Kitchen", "Storage", 699, 0.52, 1.4),
    ("Airtight Container Set", "Home & Kitchen", "Storage", 899, 0.55, 1.0),
    # --- Beauty: low ticket, highest margin --------------------------------
    ("Vitamin C Face Serum", "Beauty", "Skincare", 649, 0.35, 2.0),
    ("SPF 50 Sunscreen", "Beauty", "Skincare", 499, 0.38, 1.8),
    ("Hydrating Face Moisturiser", "Beauty", "Skincare", 399, 0.40, 1.6),
    ("Argan Oil Shampoo", "Beauty", "Haircare", 449, 0.42, 1.5),
    ("Hair Dryer 1200W", "Beauty", "Haircare", 1499, 0.62, 0.7),
    ("Matte Lipstick", "Beauty", "Makeup", 599, 0.36, 1.2),
    ("Kajal & Eyeliner Combo", "Beauty", "Makeup", 349, 0.38, 1.1),
    ("Beard Trimmer", "Beauty", "Grooming", 1799, 0.60, 1.1),
    ("Perfume 100ml", "Beauty", "Grooming", 1299, 0.45, 0.9),
    # --- Sports: mid margin, a few slow movers ------------------------------
    ("Yoga Mat 6mm", "Sports", "Fitness Equipment", 799, 0.52, 1.6),
    ("Adjustable Dumbbell Set 20kg", "Sports", "Fitness Equipment", 3999, 0.66, 0.6),
    ("Resistance Bands Set", "Sports", "Fitness Equipment", 699, 0.50, 1.1),
    ("Hybrid Bicycle 21-Speed", "Sports", "Cycling", 14999, 0.78, 0.3),
    ("English Willow Cricket Bat", "Sports", "Team Sports", 4499, 0.60, 0.7),
    ("Football Size 5", "Sports", "Team Sports", 899, 0.55, 0.9),
    ("Badminton Racket Pair", "Sports", "Team Sports", 1299, 0.56, 0.9),
    ("Trekking Backpack 50L", "Sports", "Outdoor", 2199, 0.58, 0.6),
    ("Camping Tent 4-Person", "Sports", "Outdoor", 5499, 0.66, 0.25),
    # --- Books: low ticket, multi-unit baskets ------------------------------
    ("Contemporary Fiction Paperback", "Books", "Fiction", 399, 0.66, 1.8),
    ("Classic Literature Box Set", "Books", "Fiction", 1499, 0.70, 0.4),
    ("Business Strategy Hardcover", "Books", "Non-Fiction", 699, 0.64, 1.1),
    ("Self-Help Bestseller", "Books", "Non-Fiction", 349, 0.62, 1.6),
    ("Data Science Handbook", "Books", "Academic", 899, 0.68, 0.9),
    ("Competitive Exam Guide", "Books", "Academic", 549, 0.60, 1.3),
    ("Children's Illustrated Storybook", "Books", "Children", 299, 0.65, 1.0),
    ("Kids Activity Book Set", "Books", "Children", 499, 0.63, 0.7),
]

CATEGORY_CODE = {"Electronics": "ELE", "Fashion": "FAS", "Home & Kitchen": "HOM",
                 "Beauty": "BEA", "Sports": "SPO", "Books": "BOO"}

# Overall category demand (before age preferences).
CATEGORY_BASE_WEIGHT = {"Electronics": 0.75, "Fashion": 1.3, "Home & Kitchen": 1.0,
                        "Beauty": 1.0, "Sports": 0.6, "Books": 0.7}

# Category preference multipliers by age band.
AGE_CATEGORY_PREF = {
    "18-24": {"Electronics": 1.3, "Fashion": 1.5, "Home & Kitchen": 0.4,
              "Beauty": 1.2, "Sports": 1.0, "Books": 0.8},
    "25-34": {"Electronics": 1.3, "Fashion": 1.2, "Home & Kitchen": 0.9,
              "Beauty": 1.0, "Sports": 1.0, "Books": 0.6},
    "35-49": {"Electronics": 1.1, "Fashion": 0.9, "Home & Kitchen": 1.4,
              "Beauty": 0.8, "Sports": 0.8, "Books": 0.7},
    "50+":   {"Electronics": 0.8, "Fashion": 0.7, "Home & Kitchen": 1.5,
              "Beauty": 0.6, "Sports": 0.5, "Books": 1.2},
}

# Average discount by category when there is no sale running.
CATEGORY_BASE_DISCOUNT = {"Electronics": 0.08, "Fashion": 0.18, "Home & Kitchen": 0.12,
                          "Beauty": 0.12, "Sports": 0.12, "Books": 0.08}

# Units per order line: probabilities for quantity 1, 2, 3, 4.
CATEGORY_QTY_PROBS = {
    "Electronics":    [0.93, 0.06, 0.01, 0.00],
    "Fashion":        [0.75, 0.20, 0.05, 0.00],
    "Home & Kitchen": [0.85, 0.12, 0.03, 0.00],
    "Beauty":         [0.60, 0.28, 0.12, 0.00],
    "Sports":         [0.85, 0.13, 0.02, 0.00],
    "Books":          [0.55, 0.25, 0.12, 0.08],
}

# Probability a delivered-eligible line is returned.
CATEGORY_RETURN_RATE = {"Electronics": 0.045, "Fashion": 0.11, "Home & Kitchen": 0.035,
                        "Beauty": 0.02, "Sports": 0.035, "Books": 0.015}

PAYMENT_METHODS = config.VALID_PAYMENT_METHODS  # UPI, Card, COD, Net Banking, Wallet
PAYMENT_PROBS_BY_AGE = {
    "18-24": [0.55, 0.10, 0.15, 0.05, 0.15],
    "25-34": [0.50, 0.20, 0.12, 0.08, 0.10],
    "35-49": [0.38, 0.27, 0.17, 0.12, 0.06],
    "50+":   [0.25, 0.25, 0.28, 0.18, 0.04],
}

MALE_FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Karan", "Rahul", "Siddharth",
    "Ananya", "Vikram", "Amit", "Rajesh", "Suresh", "Manish", "Nikhil", "Pranav",
    "Harsh", "Kunal", "Sandeep", "Abhishek", "Deepak", "Gaurav", "Ishaan", "Kabir",
    "Mohit", "Nitin", "Prakash", "Rakesh", "Sanjay", "Tushar", "Varun", "Yash",
    "Arnab", "Sourav", "Debashish", "Subhajit", "Karthik", "Vignesh", "Sai", "Imran",
    "Farhan", "Gurpreet", "Harpreet", "Joseph", "Aniket", "Omkar", "Ritwik", "Tanmay",
]
MALE_FIRST_NAMES.remove("Ananya")  # keep lists gender-consistent
FEMALE_FIRST_NAMES = [
    "Ananya", "Diya", "Isha", "Kavya", "Meera", "Neha", "Pooja", "Priya", "Riya",
    "Sneha", "Shreya", "Tanvi", "Aditi", "Anjali", "Divya", "Kritika", "Lakshmi",
    "Nandini", "Pallavi", "Radhika", "Sakshi", "Swati", "Trisha", "Vaishnavi",
    "Aishwarya", "Bhavna", "Deepika", "Ishita", "Madhuri", "Nisha", "Payel",
    "Rimjhim", "Sayani", "Moumita", "Keerthana", "Divyashree", "Fatima", "Sana",
    "Simran", "Jasleen", "Mary", "Sneha", "Tanya", "Urvashi", "Zoya", "Ankita",
]
SURNAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Agarwal", "Mehta", "Shah",
    "Patel", "Desai", "Joshi", "Kulkarni", "Deshpande", "Patil", "Reddy", "Rao",
    "Naidu", "Iyer", "Iyengar", "Menon", "Nair", "Pillai", "Krishnan", "Banerjee",
    "Chatterjee", "Mukherjee", "Das", "Ghosh", "Bose", "Sen", "Dutta", "Roy",
    "Mishra", "Tiwari", "Pandey", "Yadav", "Chauhan", "Rathore", "Malhotra",
    "Kapoor", "Khanna", "Bhatia", "Sethi", "Gill", "Sandhu", "Khan", "Ahmed",
    "Qureshi", "Fernandes", "D'Souza", "Mohanty", "Panda", "Hazarika", "Saikia",
]


# =============================================================================
# 2. HIDDEN CUSTOMER PERSONAS  (never written to the output)
# =============================================================================
@dataclass(frozen=True)
class Persona:
    name: str
    share: float                    # fraction of the 2,000 customers
    orders: tuple[int, int]         # min/max orders over their lifetime
    start: tuple[str, str]          # window for the first purchase date
    last_gap_days: tuple[int, int]  # days between LAST order and END_DATE
    age_mu: float
    age_sd: float
    price_beta: float               # >0 prefers expensive items, <0 cheap ones
    discount_shift: float           # extra discount they typically get/seek
    sale_sensitivity: float         # exponent on calendar weight (>1 = buys in sales)
    basket_probs: tuple[float, float, float]  # P(1, 2, 3 lines per order)
    pre_existing_share: float       # share who were already customers before 2023


PERSONAS = [
    Persona("high_value_frequent", 0.06, (18, 30), ("2023-01-01", "2024-03-31"), (0, 40),
            36, 8, 0.20, -0.03, 1.0, (0.55, 0.30, 0.15), 0.70),
    Persona("loyal", 0.14, (8, 15), ("2023-01-01", "2024-09-30"), (0, 75),
            35, 9, 0.08, -0.01, 1.0, (0.65, 0.25, 0.10), 0.60),
    Persona("new", 0.12, (1, 3), ("2025-07-01", "2025-12-20"), (0, 0),
            28, 7, 0.0, 0.02, 1.2, (0.75, 0.19, 0.06), 0.00),
    Persona("occasional", 0.25, (3, 7), ("2023-01-01", "2025-03-31"), (20, 240),
            33, 10, 0.0, 0.0, 1.2, (0.75, 0.19, 0.06), 0.35),
    Persona("at_risk", 0.13, (6, 12), ("2023-01-01", "2024-12-31"), (120, 300),
            34, 9, 0.05, 0.02, 1.0, (0.72, 0.21, 0.07), 0.50),
    Persona("low_value", 0.18, (2, 5), ("2023-01-01", "2025-06-30"), (0, 300),
            27, 7, -0.35, 0.08, 1.8, (0.82, 0.15, 0.03), 0.30),
    Persona("inactive", 0.12, (1, 3), ("2023-01-01", "2024-06-30"), (430, 1000),
            33, 11, 0.0, 0.03, 1.2, (0.75, 0.19, 0.06), 0.40),
]
assert abs(sum(p.share for p in PERSONAS) - 1.0) < 1e-9


# =============================================================================
# 3. CALENDAR: trend x seasonality x weekday x sale events
# =============================================================================
# Month-level business trend (36 values, Jan-2023 .. Dec-2025).
# Growth through 2023, a slowdown in Apr-Jul 2024, recovery, then a flatter 2025.
MONTHLY_TREND = [
    1.00, 0.98, 1.02, 1.03, 1.04, 1.05, 1.07, 1.08, 1.09, 1.10, 1.11, 1.12,  # 2023
    1.14, 1.15, 1.16, 1.10, 1.03, 0.99, 1.01, 1.06, 1.12, 1.18, 1.21, 1.23,  # 2024
    1.24, 1.26, 1.27, 1.27, 1.26, 1.28, 1.29, 1.28, 1.30, 1.31, 1.31, 1.32,  # 2025
]
# Calendar-month seasonality (Jan..Dec). Oct/Nov are also boosted by the
# festive-sale window below, so these values are deliberately moderate.
MONTH_SEASONALITY = [0.95, 0.85, 0.95, 0.90, 0.88, 0.92, 1.02, 1.00, 1.02, 1.18, 1.12, 1.10]
WEEKDAY_FACTOR = [1.00, 0.97, 0.98, 1.00, 1.05, 1.12, 1.12]  # Mon..Sun

# Diwali dates (the festive sale runs ~3 weeks before Diwali, so the peak
# month moves between October and November from year to year).
DIWALI = {2023: "2023-11-12", 2024: "2024-11-01", 2025: "2025-10-20"}


def build_sale_events() -> list[tuple[pd.Timestamp, pd.Timestamp, float, str]]:
    """Return (start, end, demand multiplier, name) for every sale event."""
    events = []
    for year in (2023, 2024, 2025):
        diwali = pd.Timestamp(DIWALI[year])
        events += [
            (pd.Timestamp(f"{year}-01-18"), pd.Timestamp(f"{year}-01-26"), 1.30, "Republic Day Sale"),
            (pd.Timestamp(f"{year}-07-12"), pd.Timestamp(f"{year}-07-19"), 1.30, "Mid-Year Sale"),
            (pd.Timestamp(f"{year}-08-08"), pd.Timestamp(f"{year}-08-15"), 1.25, "Independence Day Sale"),
            (diwali - pd.Timedelta(days=24), diwali - pd.Timedelta(days=1), 1.60, "Festive Sale"),
            (pd.Timestamp(f"{year}-12-20"), pd.Timestamp(f"{year}-12-31"), 1.15, "Year-End Sale"),
        ]
    return events


def build_calendar() -> pd.DataFrame:
    """One row per day with a demand weight and a sale flag."""
    days = pd.date_range(config.START_DATE, config.END_DATE, freq="D")
    cal = pd.DataFrame({"date": days})
    month_idx = (cal["date"].dt.year - 2023) * 12 + cal["date"].dt.month - 1
    cal["weight"] = (np.array(MONTHLY_TREND)[month_idx]
                     * np.array(MONTH_SEASONALITY)[cal["date"].dt.month - 1]
                     * np.array(WEEKDAY_FACTOR)[cal["date"].dt.weekday])
    cal["sale_boost"] = 0.0  # extra discount available on that day
    for start, end, mult, name in build_sale_events():
        mask = cal["date"].between(start, end)
        cal.loc[mask, "weight"] *= mult
        cal.loc[mask, "sale_boost"] = 0.12 if name == "Festive Sale" else 0.07
    cal["t"] = np.linspace(0, 1, len(cal))  # position in the period, 0..1
    return cal


# =============================================================================
# 4. GENERATOR
# =============================================================================
def age_band(age: int) -> str:
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 50:
        return "35-49"
    return "50+"


class SyntheticSalesGenerator:
    """Builds the clean synthetic dataset; data-quality issues are added later."""

    def __init__(self, seed: int = config.RANDOM_SEED):
        self.rng = np.random.default_rng(seed)
        self.calendar = build_calendar()
        self.products = self._build_products()
        self.cities = self._build_cities()
        self._product_prob_cache: dict[tuple, np.ndarray] = {}

    # ---------------------------------------------------------------- products
    def _build_products(self) -> pd.DataFrame:
        df = pd.DataFrame(CATALOGUE, columns=["Product_Name", "Category", "Sub_Category",
                                              "Base_Price", "Cost_Ratio", "Popularity"])
        df["Product_ID"] = (df.groupby("Category").cumcount() + 1).astype(str).str.zfill(3)
        df["Product_ID"] = df["Category"].map(CATEGORY_CODE) + "-" + df["Product_ID"]
        return df

    # ------------------------------------------------------------------ cities
    def _build_cities(self) -> pd.DataFrame:
        rows = [(city, state, region, tier)
                for region, states in GEOGRAPHY.items()
                for state, cities in states.items()
                for city, tier in cities]
        return pd.DataFrame(rows, columns=["City", "State", "Region", "Tier"])

    # --------------------------------------------------------------- customers
    def build_customers(self, n: int = config.N_CUSTOMERS) -> pd.DataFrame:
        rng = self.rng
        counts = np.floor([p.share * n for p in PERSONAS]).astype(int)
        counts[0] += n - counts.sum()  # absorb rounding
        persona = np.repeat([p.name for p in PERSONAS], counts)
        rng.shuffle(persona)  # IDs must not reveal the persona

        regions = rng.choice(list(REGION_SHARE), size=n, p=list(REGION_SHARE.values()))
        genders = rng.choice(config.VALID_GENDERS, size=n, p=[0.52, 0.47, 0.01])
        records = []
        for i in range(n):
            p = next(x for x in PERSONAS if x.name == persona[i])
            age = int(np.clip(round(rng.normal(p.age_mu, p.age_sd)), 18, 65))
            region = regions[i]
            city_pool = self.cities[self.cities["Region"] == region]
            w = city_pool["Tier"].map(CITY_TIER_WEIGHT).to_numpy()
            city_row = city_pool.iloc[rng.choice(len(city_pool), p=w / w.sum())]
            gender = genders[i]
            if gender == "Male":
                first = rng.choice(MALE_FIRST_NAMES)
            elif gender == "Female":
                first = rng.choice(FEMALE_FIRST_NAMES)
            else:
                first = rng.choice(MALE_FIRST_NAMES + FEMALE_FIRST_NAMES)
            records.append({
                "Customer_ID": f"CUST-{i + 1:04d}",
                "Customer_Name": f"{first} {rng.choice(SURNAMES)}",
                "Customer_Age": age,
                "Gender": gender,
                "City": city_row["City"], "State": city_row["State"],
                "Region": region, "Tier": int(city_row["Tier"]),
                "hidden_persona": p.name,  # internal only, never saved
                "pre_existing": bool(rng.random() < p.pre_existing_share),  # internal only
            })
        return pd.DataFrame(records)

    # ------------------------------------------------------------ order dates
    def _order_dates(self, p: Persona, region: str, pre_existing: bool) -> list[pd.Timestamp]:
        rng, cal = self.rng, self.calendar
        end_all = pd.Timestamp(config.END_DATE)
        weight = cal["weight"].to_numpy() ** p.sale_sensitivity

        # First purchase: weighted by calendar demand and regional growth.
        s_lo, s_hi = pd.Timestamp(p.start[0]), pd.Timestamp(p.start[1])
        if pre_existing:
            # Already a customer before the data starts: their history in this
            # extract simply begins on START_DATE (no special "first" order).
            first = pd.Timestamp(config.START_DATE)
        in_start = cal["date"].between(s_lo, s_hi).to_numpy()
        acq_w = weight * REGION_ACQUISITION_TREND[region](cal["t"].to_numpy()) * in_start
        if not pre_existing:
            first_idx = rng.choice(len(cal), p=acq_w / acq_w.sum())
            first = cal["date"].iat[first_idx]

        n_orders = int(rng.integers(p.orders[0], p.orders[1] + 1))
        if p.name == "new":
            last = first + pd.Timedelta(days=int(rng.integers(0, (end_all - first).days + 1)))
        elif p.name == "inactive":
            gap = int(rng.integers(0, 200))
            last = min(first + pd.Timedelta(days=gap), end_all - pd.Timedelta(days=430))
            last = max(last, first)
        else:
            gap = int(rng.integers(p.last_gap_days[0], p.last_gap_days[1] + 1))
            last = max(end_all - pd.Timedelta(days=gap), first)

        if pre_existing:
            # All orders fall between START_DATE and their last order (forced),
            # placed by calendar demand.
            window = (cal["date"].between(first, last)).to_numpy()
            w = weight * window
            idx = rng.choice(len(cal), size=max(n_orders - 1, 0), replace=True, p=w / w.sum())
            return sorted([last] + list(cal["date"].iloc[idx]))
        if n_orders == 1:
            return [first]
        if last == first:
            return [first]  # same-day purchases collapse into one order
        # Remaining orders fall between first and last, weighted by demand.
        between = cal["date"].between(first, last).to_numpy()
        w = weight * between
        middle_n = max(n_orders - 2, 0)
        middle_idx = rng.choice(len(cal), size=middle_n, replace=True, p=w / w.sum())
        return sorted([first, last] + list(cal["date"].iloc[middle_idx]))

    # ------------------------------------------------------------ order lines
    def _choose_product(self, age: int, p: Persona, tier: int) -> pd.Series:
        """Product choice = popularity x category taste (age) x price taste (persona, city tier)."""
        key = (age_band(age), p.name, tier)
        if key not in self._product_prob_cache:
            prods = self.products
            cat_w = prods["Category"].map(lambda c: CATEGORY_BASE_WEIGHT[c]
                                          * AGE_CATEGORY_PREF[key[0]][c])
            beta = p.price_beta + CITY_TIER_PRICE_PREF[tier]
            price_w = (prods["Base_Price"] / 1500.0) ** beta
            w = (prods["Popularity"] * cat_w * price_w).to_numpy()
            self._product_prob_cache[key] = w / w.sum()
        probs = self._product_prob_cache[key]
        return self.products.iloc[self.rng.choice(len(self.products), p=probs)]

    def _discount(self, category: str, sale_boost: float, p: Persona) -> float:
        rng = self.rng
        if sale_boost == 0 and rng.random() < 0.30:
            return 0.0  # many non-sale purchases are at full price
        mean = CATEGORY_BASE_DISCOUNT[category] + sale_boost + p.discount_shift
        d = rng.normal(mean, 0.05)
        d = round(round(d / 0.05) * 0.05, 2)  # coupon tiers of 5%
        return float(np.clip(d, 0.0, config.MAX_DISCOUNT))

    def _quantity(self, category: str, discount: float) -> int:
        q = int(self.rng.choice([1, 2, 3, 4], p=CATEGORY_QTY_PROBS[category]))
        # Deep discounts nudge people to buy an extra unit (not for big-ticket tech).
        if discount >= 0.25 and category != "Electronics" and self.rng.random() < 0.15:
            q += 1
        return q

    def _payment(self, age: int, preferred: str, t: float) -> str:
        if self.rng.random() < 0.70:
            return preferred  # payment habit
        probs = np.array(PAYMENT_PROBS_BY_AGE[age_band(age)], dtype=float)
        probs[0] *= 1 + 0.4 * t    # UPI adoption rises over time
        probs[2] *= 1 - 0.35 * t   # COD declines over time
        return str(self.rng.choice(PAYMENT_METHODS, p=probs / probs.sum()))

    def build_transactions(self, customers: pd.DataFrame) -> pd.DataFrame:
        rng = self.rng
        cal = self.calendar.set_index("date")
        start = pd.Timestamp(config.START_DATE)
        span_days = (pd.Timestamp(config.END_DATE) - start).days
        rows = []
        for cust in customers.itertuples(index=False):
            p = next(x for x in PERSONAS if x.name == cust.hidden_persona)
            preferred = str(rng.choice(PAYMENT_METHODS,
                                       p=PAYMENT_PROBS_BY_AGE[age_band(cust.Customer_Age)]))
            # One order per customer per day: duplicate sampled dates are merged.
            for order_date in sorted(set(self._order_dates(p, cust.Region, cust.pre_existing))):
                t = (order_date - start).days / span_days
                sale_boost = float(cal.at[order_date, "sale_boost"])
                payment = self._payment(cust.Customer_Age, preferred, t)
                cancel_p = 0.035 + (0.03 if payment == "COD" else 0.0)
                cancelled = rng.random() < cancel_p
                n_lines = int(rng.choice([1, 2, 3], p=p.basket_probs))
                years = (order_date - start).days / 365.25
                for _ in range(n_lines):
                    prod = self._choose_product(cust.Customer_Age, p, cust.Tier)
                    disc = self._discount(prod["Category"], sale_boost, p)
                    qty = self._quantity(prod["Category"], disc)
                    # ~5% annual price inflation plus small listing variation.
                    price = round(prod["Base_Price"] * 1.05 ** years * (1 + rng.normal(0, 0.025)))
                    cost_ratio = prod["Cost_Ratio"] * (1 + rng.normal(0, 0.01))
                    gross = qty * price
                    sales = round(gross * (1 - disc), 2)
                    cost = round(gross * cost_ratio, 2)
                    if cancelled:
                        status = "Cancelled"
                    else:
                        ret_p = (CATEGORY_RETURN_RATE[prod["Category"]]
                                 + (0.02 if payment == "COD" else 0.0)
                                 + (0.02 if p.name == "low_value" else 0.0))
                        status = "Returned" if rng.random() < ret_p else "Delivered"
                    rows.append({
                        "Order_Date": order_date,
                        "Customer_ID": cust.Customer_ID,
                        "Customer_Name": cust.Customer_Name,
                        "Customer_Age": cust.Customer_Age,
                        "Gender": cust.Gender,
                        "City": cust.City, "State": cust.State, "Region": cust.Region,
                        "Product_ID": prod["Product_ID"], "Product_Name": prod["Product_Name"],
                        "Category": prod["Category"], "Sub_Category": prod["Sub_Category"],
                        "Quantity": qty, "Unit_Price": float(price), "Discount": disc,
                        "Sales": sales, "Cost": cost, "Profit": round(sales - cost, 2),
                        "Payment_Method": payment, "Order_Status": status,
                        "_order_key": (cust.Customer_ID, order_date),
                        "_pre_existing": cust.pre_existing,
                    })
        df = pd.DataFrame(rows)
        return self._assign_ids(df)

    @staticmethod
    def _assign_ids(df: pd.DataFrame) -> pd.DataFrame:
        """Chronological Order_IDs, line IDs and the derived Customer_Type."""
        df["_order_key"] = df["_order_key"].astype(str)
        df = df.sort_values(["Order_Date", "Customer_ID", "_order_key"], kind="stable")
        order_codes = pd.factorize(df["_order_key"])[0] + 1
        df["Order_ID"] = [f"ORD-{c:06d}" for c in order_codes]
        df = df.reset_index(drop=True)
        df["Order_Line_ID"] = [f"OL-{i + 1:07d}" for i in range(len(df))]
        first_order = df.groupby("Customer_ID")["Order_ID"].transform("min")
        # "New" = the customer's first-ever order. Customers who already bought
        # before 2023 are "Returning" even on their first order in this extract
        # (the source CRM knows their earlier history).
        is_first = (df["Order_ID"] == first_order) & ~df["_pre_existing"].astype(bool)
        df["Customer_Type"] = np.where(is_first, "New", "Returning")
        df["Order_Date"] = df["Order_Date"].dt.strftime("%Y-%m-%d")
        return df[config.EXPECTED_COLUMNS]


# =============================================================================
# 5. CONTROLLED DATA-QUALITY ISSUES
# =============================================================================
CATEGORY_VARIANTS = {
    "Electronics": ["electronics", "ELECTRONICS", " Electronics "],
    "Fashion": ["fashion", "FASHION", "Fashion "],
    "Home & Kitchen": ["Home and Kitchen", "home & kitchen", "Home & Kitchen "],
    "Beauty": ["beauty", "BEAUTY", " Beauty"],
    "Sports": ["sports", "SPORTS", "Sports "],
    "Books": ["books", "BOOKS", " Books"],
}
GENDER_VARIANTS = {"Male": ["M", "male", "MALE"], "Female": ["F", "female", "FEMALE"],
                   "Other": ["other", "O"]}
PAYMENT_VARIANTS = {"UPI": ["upi", "Upi"], "Card": ["card", "Credit/Debit Card"],
                    "COD": ["Cash on Delivery", "cod"], "Net Banking": ["NetBanking", "net banking"],
                    "Wallet": ["wallet", "E-Wallet"]}
OLD_CITY_NAMES = {"Bengaluru": "Bangalore", "Gurugram": "Gurgaon", "Mumbai": "Bombay",
                  "Kolkata": "Calcutta", "Thiruvananthapuram": "Trivandrum",
                  "Mysuru": "Mysore", "Visakhapatnam": "Vizag"}
STATE_VARIANTS = {"Odisha": "Orissa", "Tamil Nadu": "Tamilnadu", "Chhattisgarh": "Chattisgarh",
                  "Uttar Pradesh": "UP", "West Bengal": "W. Bengal"}


class DataQualityInjector:
    """Adds a small, logged amount of realistic mess to the clean data."""

    def __init__(self, seed: int):
        self.rng = np.random.default_rng(seed)
        self.log: list[dict] = []

    def _pick(self, df: pd.DataFrame, frac: float, mask: pd.Series | None = None) -> pd.Index:
        pool = df.index if mask is None else df.index[mask.to_numpy()]
        k = max(1, int(round(frac * len(df))))
        k = min(k, len(pool))
        return pd.Index(self.rng.choice(pool, size=k, replace=False))

    def _record(self, issue: str, column: str, idx, note: str) -> None:
        self.log.append({"issue_type": issue, "column": column,
                         "rows_affected": int(len(idx)), "description": note})

    def inject(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Columns that will receive text must be object dtype first.
        for col in ["Unit_Price", "Customer_Age", "Quantity", "Discount", "Sales"]:
            df[col] = df[col].astype(object)

        # --- A. Unusual / invalid numerical values ------------------------
        cheap = df["Unit_Price"].astype(float) < 3000  # bulk buys are gifts/supplies, not laptops
        idx = self._pick(df, 0.001, cheap)
        bulk = self.rng.integers(20, 51, size=len(idx))
        for i, q in zip(idx, bulk):   # genuine bulk orders: kept internally consistent
            gross = q * float(df.at[i, "Unit_Price"])
            ratio = float(df.at[i, "Cost"]) / (float(df.at[i, "Quantity"]) * float(df.at[i, "Unit_Price"]))
            df.at[i, "Quantity"] = int(q)
            df.at[i, "Sales"] = round(gross * (1 - float(df.at[i, "Discount"])), 2)
            df.at[i, "Cost"] = round(gross * ratio, 2)
            df.at[i, "Profit"] = round(float(df.at[i, "Sales"]) - float(df.at[i, "Cost"]), 2)
        self._record("outlier", "Quantity", idx,
                     "Genuine bulk orders (20-50 units); Sales/Cost/Profit recomputed, so values are valid but extreme.")

        idx = self._pick(df, 0.0005)
        df.loc[idx, "Quantity"] = -1
        self._record("invalid_value", "Quantity", idx,
                     "Quantity entered as -1 (data-entry error); Sales left unchanged, so the row fails the revenue check.")

        idx = self._pick(df, 0.001)
        df.loc[idx, "Customer_Age"] = self.rng.choice([0, 5, 150, 999], size=len(idx))
        self._record("invalid_value", "Customer_Age", idx,
                     "Impossible ages (0, 5, 150, 999); the true age exists on the customer's other rows.")

        idx = self._pick(df, 0.002, df["Discount"].astype(float) > 0)
        df.loc[idx, "Discount"] = (df.loc[idx, "Discount"].astype(float) * 100).round(0)
        self._record("invalid_value", "Discount", idx,
                     "Discount stored as a percentage (e.g. 15 instead of 0.15).")

        idx = self._pick(df, 0.0005)
        df.loc[idx, "Unit_Price"] = df.loc[idx, "Unit_Price"].astype(float) * 10
        self._record("invalid_value", "Unit_Price", idx,
                     "Unit price with an extra zero (x10 typo); Sales unchanged, so the row fails the revenue check.")

        # --- B. Missing values ---------------------------------------------
        for col, frac, note in [
            ("Customer_Age", 0.015, "Recoverable from the same customer's other rows."),
            ("Gender", 0.010, "Recoverable from the same customer's other rows."),
            ("City", 0.008, "State and Region still present; recoverable from the customer's other rows."),
            ("Payment_Method", 0.010, "Not recoverable; to be labelled 'Unknown'."),
            ("Discount", 0.005, "Recoverable from Sales / (Quantity x Unit_Price)."),
            ("Sales", 0.003, "Recoverable from Quantity x Unit_Price x (1 - Discount)."),
        ]:
            idx = self._pick(df, frac)
            df.loc[idx, col] = np.nan
            self._record("missing_value", col, idx, note)

        # --- C. Inconsistent categorical values -----------------------------
        def vary(col: str, frac: float, variants: dict, note: str) -> None:
            mask = df[col].isin(list(variants))
            idx = self._pick(df, frac, mask)
            df.loc[idx, col] = [
                (lambda v: v if isinstance(v, str) else self.rng.choice(v))(variants[x])
                for x in df.loc[idx, col]
            ]
            self._record("inconsistent_category", col, idx, note)

        vary("Category", 0.015, CATEGORY_VARIANTS, "Case, whitespace and '&' vs 'and' variants.")
        vary("Gender", 0.010, GENDER_VARIANTS, "Abbreviations and case variants (M/F/male...).")
        vary("Payment_Method", 0.010, PAYMENT_VARIANTS, "Alternative spellings and case variants.")
        vary("City", 0.005, OLD_CITY_NAMES, "Old city names (Bangalore, Bombay, Gurgaon...).")
        vary("State", 0.004, STATE_VARIANTS, "Old or informal state names (Orissa, UP...).")
        region_variants = {r: [r.lower(), r.upper(), f" {r}"] for r in config.VALID_REGIONS}
        vary("Region", 0.008, region_variants, "Case and whitespace variants.")

        # --- D. Formatting issues --------------------------------------------
        idx = self._pick(df, 0.020)
        df.loc[idx, "Order_Date"] = pd.to_datetime(df.loc[idx, "Order_Date"]).dt.strftime("%d-%m-%Y")
        self._record("format", "Order_Date", idx, "Date written as DD-MM-YYYY instead of YYYY-MM-DD.")
        remaining = df["Order_Date"].str.match(r"^\d{4}-\d{2}-\d{2}$")
        idx = self._pick(df, 0.010, remaining)
        df.loc[idx, "Order_Date"] = pd.to_datetime(df.loc[idx, "Order_Date"]).dt.strftime("%d/%m/%Y")
        self._record("format", "Order_Date", idx, "Date written as DD/MM/YYYY.")

        numeric_price = df["Unit_Price"].map(lambda v: isinstance(v, (int, float)))
        idx = self._pick(df, 0.005, numeric_price)
        df.loc[idx, "Unit_Price"] = [f"₹{float(v):,.0f}" for v in df.loc[idx, "Unit_Price"]]
        self._record("format", "Unit_Price", idx, "Price stored as text with rupee symbol and comma, e.g. '₹1,299'.")

        idx = self._pick(df, 0.005)
        df.loc[idx, "Customer_Name"] = [
            f"  {n.upper()} " if k % 2 == 0 else f"{n.lower()}  "
            for k, n in enumerate(df.loc[idx, "Customer_Name"])
        ]
        self._record("format", "Customer_Name", idx, "Upper/lower case and leading/trailing spaces.")

        # --- E. Duplicate rows -------------------------------------------------
        idx = self._pick(df, 0.008)
        dupes = df.loc[idx].copy()
        df = pd.concat([df, dupes]).sort_values("Order_Line_ID", kind="stable").reset_index(drop=True)
        self._record("duplicate", "ALL", idx, "Exact duplicate rows (double ingestion), including Order_Line_ID.")
        return df


# =============================================================================
# 6. MAIN
# =============================================================================
def main() -> None:
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"*** {config.DATASET_LABEL} ***")
    print(f"Seed = {config.RANDOM_SEED} | Period = {config.START_DATE} to {config.END_DATE}\n")

    gen = SyntheticSalesGenerator(seed=config.RANDOM_SEED)
    customers = gen.build_customers()
    clean = gen.build_transactions(customers)

    injector = DataQualityInjector(seed=config.RANDOM_SEED + 1)
    raw = injector.inject(clean)

    raw.to_csv(config.RAW_DATA_FILE, index=False, encoding="utf-8-sig")
    with open(config.INJECTION_LOG_FILE, "w", encoding="utf-8") as fh:
        json.dump({"dataset": config.DATASET_LABEL, "seed": config.RANDOM_SEED,
                   "clean_rows_before_injection": int(len(clean)),
                   "raw_rows_after_injection": int(len(raw)),
                   "issues": injector.log}, fh, indent=2, ensure_ascii=False)

    # ---- Required console output -------------------------------------------
    df = pd.read_csv(config.RAW_DATA_FILE, encoding="utf-8-sig")
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print(f"Saved: {config.RAW_DATA_FILE.relative_to(config.PROJECT_ROOT)}")
    print(f"Saved: {config.INJECTION_LOG_FILE.relative_to(config.PROJECT_ROOT)}\n")
    print("=== 1. DATASET SHAPE ===")
    print(f"{df.shape[0]:,} rows x {df.shape[1]} columns\n")
    print("=== 2. FIRST 10 ROWS ===")
    print(df.head(10).to_string(), "\n")
    print("=== 3. DATA TYPES (as read from CSV) ===")
    print(df.dtypes.to_string(), "\n")
    print("=== 4. BASIC STATISTICS (numeric columns) ===")
    print(df.describe().round(2).to_string(), "\n")
    print("=== 5. BASIC STATISTICS (categorical columns) ===")
    print(df.describe(include=["object", "string"]).T[["count", "unique", "top", "freq"]].to_string(), "\n")
    print("=== 6. INJECTED DATA-QUALITY ISSUES ===")
    print(pd.DataFrame(injector.log)[["issue_type", "column", "rows_affected"]].to_string(index=False))


if __name__ == "__main__":
    main()
