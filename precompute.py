"""
Precompute real agent-pipeline results for every brand in the catalog and
write dist_data.json — consumed by the static Netlify demo site (build_dist.py).

Resumable: saves to dist_data_partial.json after every brand, so an
interrupted run picks up where it left off.

Run:  python precompute.py
"""

import json
import os
import sys
import time
from datetime import date

from agents import load_data, run_pipeline

QTY = 20_000
TARGET_MARGIN = 45.0
RETRIES = 3
PARTIAL = "dist_data_partial.json"

data = load_data()
brands = data["brands"]

results = {}
if os.path.exists(PARTIAL):
    with open(PARTIAL) as f:
        results = json.load(f)
    print(f"Resuming: {len(results)} brands already done", flush=True)

t0 = time.time()
for i, brand in enumerate(brands["brand"], 1):
    if brand in results:
        continue
    for attempt in range(1, RETRIES + 1):
        try:
            r = run_pipeline(data, brand, QTY, TARGET_MARGIN)
            results[brand] = {k: v for k, v in r.items() if k != "brand_row"}
            with open(PARTIAL, "w") as f:
                json.dump(results, f, default=float)
            print(f"[{i}/{len(brands)}] {brand}: {r['decision']['decision']} "
                  f"qty={r['decision']['recommended_qty']:,} "
                  f"({time.time() - t0:.0f}s elapsed)", flush=True)
            break
        except Exception as e:
            wait = 15 * attempt
            print(f"[{i}/{len(brands)}] {brand}: attempt {attempt} failed ({e}); "
                  f"retrying in {wait}s", file=sys.stderr, flush=True)
            if attempt == RETRIES:
                raise
            time.sleep(wait)

payload = {
    "generated": date.today().isoformat(),
    "params": {"requested_qty": QTY, "target_margin_pct": TARGET_MARGIN},
    "brands": brands.to_dict(orient="records"),
    "tariffs": {
        cat: g[["country", "base_tariff_pct", "current_tariff_pct"]]
             .sort_values("current_tariff_pct").to_dict(orient="records")
        for cat, g in data["tariffs"].groupby("category")
    },
    "trends": {
        cat: g.tail(12)[["month", "demand_index", "social_buzz_score"]]
             .to_dict(orient="records")
        for cat, g in data["trends"].groupby("category")
    },
    "results": results,
}

with open("dist_data.json", "w") as f:
    json.dump(payload, f, default=float)
print(f"\nWrote dist_data.json ({len(results)} brands)", flush=True)
