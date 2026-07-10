"""
Synthetic data generator for the Ross Stores Agentic Procurement Advisor.

Generates six datasets under ./data :
  1. brand_catalog.csv       - candidate brands, origin country, FOB cost, MOQ, lead time
  2. tariff_schedule.csv     - US import tariff rates by country x category (base vs current)
  3. trade_agreements.csv    - status of trade deals / agreements per country
  4. geopolitical_events.csv - news-style event feed with risk impact scores
  5. market_trends.csv       - 24 months of demand & social-buzz indices per category
  6. sales_history.csv       - Ross's own 24-month sales per category

All data is synthetic but calibrated to be directionally realistic (mid-2026 view).
Run:  python data_gen.py
"""

import os
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
os.makedirs("data", exist_ok=True)

CATEGORIES = ["Apparel", "Footwear", "Home Goods", "Accessories", "Beauty"]
COUNTRIES = ["China", "Vietnam", "Bangladesh", "India", "Mexico", "Turkey", "Indonesia", "Italy"]

# ---------------------------------------------------------------- 1. brands
BRANDS = [
    # brand, country, category, fob_cost, moq, lead_days, quality(1-10)
    ("Lunara Apparel",      "China",      "Apparel",     6.20, 5000, 38, 7),
    ("MeiTex Garments",     "China",      "Apparel",     5.10, 8000, 40, 6),
    ("SaigonWear Co",       "Vietnam",    "Apparel",     6.80, 4000, 34, 7),
    ("Hanoi Threads",       "Vietnam",    "Apparel",     7.40, 3000, 36, 8),
    ("DhakaKnit Ltd",       "Bangladesh", "Apparel",     4.60, 10000, 48, 6),
    ("BengalWeave",         "Bangladesh", "Apparel",     4.90, 8000, 46, 6),
    ("IndiCotton Mills",    "India",      "Apparel",     5.70, 6000, 42, 7),
    ("MonteVerde Moda",     "Mexico",     "Apparel",     8.90, 2000, 14, 7),
    ("Anatolia Textiles",   "Turkey",     "Apparel",     7.90, 2500, 22, 8),
    ("StepOne Footwear",    "China",      "Footwear",   11.50, 4000, 42, 7),
    ("DaNang Soles",        "Vietnam",    "Footwear",   12.80, 3000, 38, 8),
    ("Chennai Leatherworks","India",      "Footwear",   13.60, 2500, 44, 8),
    ("Bandung Kicks",       "Indonesia",  "Footwear",   12.10, 3500, 40, 7),
    ("Firenze Passo",       "Italy",      "Footwear",   34.00, 800,  28, 10),
    ("Casa Loma Living",    "Mexico",     "Home Goods", 9.80,  1500, 12, 7),
    ("Yiwu HomeStyle",      "China",      "Home Goods", 6.40,  6000, 44, 6),
    ("Jaipur Artisan Co",   "India",      "Home Goods", 8.20,  2000, 46, 8),
    ("Izmir Ceramics",      "Turkey",     "Home Goods", 10.50, 1200, 24, 9),
    ("Guangzhou Trims",     "China",      "Accessories", 3.10, 10000, 36, 6),
    ("Mumbai Adornments",   "India",      "Accessories", 3.80, 6000, 40, 7),
    ("Jakarta Style Lab",   "Indonesia",  "Accessories", 3.50, 7000, 42, 6),
    ("GlowEast Cosmetics",  "China",      "Beauty",      2.90, 12000, 34, 6),
    ("K-Seoul Beauty*",     "Vietnam",    "Beauty",      4.10, 6000, 32, 8),
    ("Veneto Skincare",     "Italy",      "Beauty",      9.60, 1500, 26, 9),
]
brand_catalog = pd.DataFrame(
    BRANDS,
    columns=["brand", "country", "category", "fob_unit_cost_usd",
             "moq_units", "lead_time_days", "quality_score"],
)
# ocean/land freight per unit by origin (synthetic)
FREIGHT = {"China": 0.85, "Vietnam": 0.80, "Bangladesh": 0.95, "India": 0.90,
           "Mexico": 0.35, "Turkey": 1.10, "Indonesia": 0.88, "Italy": 1.40}
brand_catalog["freight_per_unit_usd"] = brand_catalog["country"].map(FREIGHT)
brand_catalog.to_csv("data/brand_catalog.csv", index=False)

# ---------------------------------------------------------------- 2. tariffs
# base = pre-2025 MFN-style rate; current = mid-2026 rate after tariff actions
TARIFF_BASE = {  # by country: (base_pct, current_pct_multiplier_note)
    "China":      {"Apparel": (16.5, 46.5), "Footwear": (20.0, 50.0), "Home Goods": (8.4, 38.4),
                   "Accessories": (11.0, 41.0), "Beauty": (6.5, 36.5)},
    "Vietnam":    {"Apparel": (16.5, 26.5), "Footwear": (20.0, 30.0), "Home Goods": (8.4, 18.4),
                   "Accessories": (11.0, 21.0), "Beauty": (6.5, 16.5)},
    "Bangladesh": {"Apparel": (16.5, 31.5), "Footwear": (20.0, 35.0), "Home Goods": (8.4, 23.4),
                   "Accessories": (11.0, 26.0), "Beauty": (6.5, 21.5)},
    "India":      {"Apparel": (16.5, 24.5), "Footwear": (20.0, 28.0), "Home Goods": (8.4, 16.4),
                   "Accessories": (11.0, 19.0), "Beauty": (6.5, 14.5)},
    "Mexico":     {"Apparel": (16.5, 0.0),  "Footwear": (20.0, 0.0),  "Home Goods": (8.4, 0.0),
                   "Accessories": (11.0, 0.0), "Beauty": (6.5, 0.0)},
    "Turkey":     {"Apparel": (16.5, 21.5), "Footwear": (20.0, 25.0), "Home Goods": (8.4, 13.4),
                   "Accessories": (11.0, 16.0), "Beauty": (6.5, 11.5)},
    "Indonesia":  {"Apparel": (16.5, 29.5), "Footwear": (20.0, 33.0), "Home Goods": (8.4, 21.4),
                   "Accessories": (11.0, 24.0), "Beauty": (6.5, 19.5)},
    "Italy":      {"Apparel": (16.5, 26.5), "Footwear": (20.0, 30.0), "Home Goods": (8.4, 18.4),
                   "Accessories": (11.0, 21.0), "Beauty": (6.5, 16.5)},
}
rows = []
for country, cats in TARIFF_BASE.items():
    for cat, (base, cur) in cats.items():
        rows.append({
            "country": country, "category": cat,
            "base_tariff_pct": base, "current_tariff_pct": cur,
            "effective_date": "2026-04-01",
            "trend": ("rising" if cur > base + 15 else
                      "elevated" if cur > base else
                      "duty-free" if cur == 0 else "stable"),
        })
tariffs = pd.DataFrame(rows)
tariffs.to_csv("data/tariff_schedule.csv", index=False)

# ---------------------------------------------------- 3. trade agreements
trade_agreements = pd.DataFrame([
    {"country": "China", "agreement": "US-China Phase One (lapsed)", "status": "Suspended",
     "tariff_relief": "None", "outlook": "Escalation risk high; Section 301 tariffs expanded Apr-2026; talks stalled."},
    {"country": "Vietnam", "agreement": "US-Vietnam Reciprocal Trade Framework", "status": "Active",
     "tariff_relief": "Partial (10pt reduction on textiles pending ratification)",
     "outlook": "Constructive; reciprocal deal signed 2025, ratification vote expected Q4-2026."},
    {"country": "Bangladesh", "agreement": "GSP (US) - not restored", "status": "Under negotiation",
     "tariff_relief": "None currently", "outlook": "Labor-standards review ongoing; possible relief in 2027."},
    {"country": "India", "agreement": "US-India Bilateral Trade Agreement (Tranche 1)", "status": "Active",
     "tariff_relief": "Partial (textiles & leather goods carve-out)",
     "outlook": "Improving; tranche-2 talks include footwear duty reduction."},
    {"country": "Mexico", "agreement": "USMCA", "status": "Active",
     "tariff_relief": "Full (duty-free if rules-of-origin met)",
     "outlook": "Stable; 2026 joint review passed. Nearshoring incentives strong."},
    {"country": "Turkey", "agreement": "US-Turkey Trade Framework", "status": "Active",
     "tariff_relief": "Limited", "outlook": "Stable but currency volatility raises supplier risk."},
    {"country": "Indonesia", "agreement": "US-Indonesia CEPA (draft)", "status": "Under negotiation",
     "tariff_relief": "None currently", "outlook": "Deal 70% negotiated; nickel/minerals chapters are the blocker."},
    {"country": "Italy", "agreement": "US-EU trade truce", "status": "Active",
     "tariff_relief": "Capped at 15% ceiling for most goods",
     "outlook": "Stable under 2025 framework; luxury goods demand-driven, not tariff-driven."},
])
trade_agreements.to_csv("data/trade_agreements.csv", index=False)

# ------------------------------------------------- 4. geopolitical events
geo_events = pd.DataFrame([
    {"date": "2026-06-28", "country": "China", "event": "New 10% tariff tranche announced on apparel & footwear HS codes",
     "risk_impact": 9, "direction": "negative"},
    {"date": "2026-06-15", "country": "China", "event": "Port of Shanghai congestion; average vessel wait +6 days",
     "risk_impact": 6, "direction": "negative"},
    {"date": "2026-06-20", "country": "Vietnam", "event": "Textile tariff-relief ratification moved up to October vote",
     "risk_impact": 3, "direction": "positive"},
    {"date": "2026-05-30", "country": "Vietnam", "event": "Rules-of-origin audits tightened on transshipped Chinese fabric",
     "risk_impact": 5, "direction": "negative"},
    {"date": "2026-06-10", "country": "Bangladesh", "event": "Garment-sector minimum wage strike resolved after 2 weeks",
     "risk_impact": 4, "direction": "neutral"},
    {"date": "2026-06-25", "country": "India", "event": "Tranche-2 talks: US signals footwear duty cut to 12% by 2027",
     "risk_impact": 2, "direction": "positive"},
    {"date": "2026-06-18", "country": "Mexico", "event": "New cross-dock capacity at Laredo cuts border dwell time 30%",
     "risk_impact": 1, "direction": "positive"},
    {"date": "2026-05-12", "country": "Turkey", "event": "Lira depreciates 8% in 30 days; suppliers re-quoting in EUR",
     "risk_impact": 5, "direction": "negative"},
    {"date": "2026-06-05", "country": "Indonesia", "event": "CEPA negotiation round ends without textile chapter agreement",
     "risk_impact": 4, "direction": "negative"},
    {"date": "2026-06-22", "country": "Italy", "event": "EU-US 15% tariff ceiling reaffirmed at G7 summit",
     "risk_impact": 2, "direction": "positive"},
    {"date": "2026-07-02", "country": "China", "event": "Retaliatory export-licensing review for synthetic-fiber inputs",
     "risk_impact": 7, "direction": "negative"},
    {"date": "2026-06-30", "country": "Mexico", "event": "USMCA 2026 joint review concluded; apparel rules unchanged",
     "risk_impact": 1, "direction": "positive"},
])
geo_events.to_csv("data/geopolitical_events.csv", index=False)

# ---------------------------------------------------- 5. market trends
months = pd.date_range("2024-08-01", periods=24, freq="MS").strftime("%Y-%m")
trend_rows = []
BASE_DEMAND = {"Apparel": 100, "Footwear": 90, "Home Goods": 80, "Accessories": 70, "Beauty": 60}
GROWTH = {"Apparel": 0.4, "Footwear": 0.9, "Home Goods": -0.3, "Accessories": 0.2, "Beauty": 1.2}
RETAIL = {"Apparel": 14.99, "Footwear": 29.99, "Home Goods": 19.99, "Accessories": 9.99, "Beauty": 8.99}
for cat in CATEGORIES:
    for i, m in enumerate(months):
        season = 12 * np.sin(2 * np.pi * (i + 3) / 12)          # holiday peak
        demand = BASE_DEMAND[cat] + GROWTH[cat] * i + season + rng.normal(0, 3)
        buzz = 50 + GROWTH[cat] * 14 * (i / 24) * 10 + rng.normal(0, 5)
        trend_rows.append({
            "month": m, "category": cat,
            "demand_index": round(max(demand, 20), 1),
            "social_buzz_score": round(min(max(buzz, 10), 100), 1),
            "avg_retail_price_usd": RETAIL[cat],
        })
market_trends = pd.DataFrame(trend_rows)
market_trends.to_csv("data/market_trends.csv", index=False)

# ---------------------------------------------------- 6. sales history
sales_rows = []
BASE_UNITS = {"Apparel": 420_000, "Footwear": 260_000, "Home Goods": 310_000,
              "Accessories": 180_000, "Beauty": 120_000}
for cat in CATEGORIES:
    for i, m in enumerate(months):
        season = 0.18 * np.sin(2 * np.pi * (i + 3) / 12)
        units = BASE_UNITS[cat] * (1 + GROWTH[cat] * i / 100) * (1 + season) * rng.normal(1, 0.03)
        units = int(max(units, 10_000))
        sales_rows.append({
            "month": m, "category": cat, "units_sold": units,
            "revenue_usd": round(units * RETAIL[cat] * rng.normal(0.97, 0.01), 2),
        })
sales_history = pd.DataFrame(sales_rows)
sales_history.to_csv("data/sales_history.csv", index=False)

print("Generated datasets:")
for f in sorted(os.listdir("data")):
    df = pd.read_csv(f"data/{f}")
    print(f"  data/{f:28s} {df.shape[0]:>4} rows x {df.shape[1]} cols")
