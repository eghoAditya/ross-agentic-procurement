"""
Agentic core for the Ross Stores Procurement Advisor.

Five cooperating agents, each with a narrow mandate and its own data slice:

  1. TariffAgent      - import duty exposure & landed-cost impact
  2. GeopoliticsAgent - trade-deal status & country risk from an event feed
  3. TrendAgent       - demand / social-buzz trajectory for the category
  4. FinanceAgent     - landed cost, margin math, viability vs. target margin
  5. DecisionAgent    - synthesizes all findings into YES / PARTIAL / NO,
                        a recommended quantity, and order timing

Hard numbers (landed cost, margins, forecasts) are computed deterministically
in Python; Gemini is used for judgment, risk interpretation and the final
structured decision, so the pipeline is both auditable and adaptive.
"""

import json
import os
import re

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL_CANDIDATES = ["gemini-2.5-flash", "gemini-2.0-flash"]

_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set. Add it to a .env file.")
        _client = genai.Client(api_key=api_key)
    return _client


def ask_gemini_json(system: str, prompt: str) -> dict:
    """Call Gemini and parse a JSON object out of the response."""
    client = get_client()
    last_err = None
    for model in MODEL_CANDIDATES:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    temperature=0.2,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            text = resp.text or ""
            match = re.search(r"\{.*\}", text, re.DOTALL)
            return json.loads(match.group(0) if match else text)
        except Exception as e:  # try next model
            last_err = e
    raise RuntimeError(f"Gemini call failed on all models: {last_err}")


# ------------------------------------------------------------------ data

def load_data(data_dir: str = "data") -> dict:
    return {
        "brands": pd.read_csv(f"{data_dir}/brand_catalog.csv"),
        "tariffs": pd.read_csv(f"{data_dir}/tariff_schedule.csv"),
        "agreements": pd.read_csv(f"{data_dir}/trade_agreements.csv"),
        "events": pd.read_csv(f"{data_dir}/geopolitical_events.csv"),
        "trends": pd.read_csv(f"{data_dir}/market_trends.csv"),
        "sales": pd.read_csv(f"{data_dir}/sales_history.csv"),
    }


# ------------------------------------------------------------ finance math

def landed_cost_breakdown(brand_row: pd.Series, tariff_pct: float) -> dict:
    fob = float(brand_row["fob_unit_cost_usd"])
    duty = fob * tariff_pct / 100
    freight = float(brand_row["freight_per_unit_usd"])
    handling = round(0.04 * fob, 2)  # brokerage / port handling
    landed = round(fob + duty + freight + handling, 2)
    return {"fob": fob, "duty": round(duty, 2), "freight": freight,
            "handling": handling, "landed": landed}


def margin_math(landed: float, retail_price: float) -> dict:
    gross_margin_pct = round(100 * (retail_price - landed) / retail_price, 1)
    breakeven_retail = round(landed / 0.55, 2)  # retail needed for 45% margin
    return {"retail_price": retail_price, "gross_margin_pct": gross_margin_pct,
            "breakeven_retail_for_45pct": breakeven_retail}


def forecast_next_quarter_units(sales: pd.DataFrame, category: str) -> int:
    s = sales[sales["category"] == category].tail(6)["units_sold"]
    monthly = s.mean() + (s.iloc[-1] - s.iloc[0]) / 2  # level + simple drift
    return int(monthly * 3)


# ----------------------------------------------------------------- agents

def run_tariff_agent(data: dict, brand_row: pd.Series) -> dict:
    country, category = brand_row["country"], brand_row["category"]
    t = data["tariffs"]
    row = t[(t["country"] == country) & (t["category"] == category)].iloc[0]
    costs = landed_cost_breakdown(brand_row, row["current_tariff_pct"])
    system = ("You are the Tariff Analysis Agent for Ross Stores' sourcing team. "
              "Assess import-duty exposure for a candidate purchase. Respond ONLY with JSON: "
              '{"tariff_risk": "low|medium|high", "duty_share_of_cost_pct": number, '
              '"summary": "2-3 sentences", "watch_items": ["..."]}')
    prompt = f"""Candidate: {brand_row['brand']} ({country}, {category})
Tariff schedule row: base {row['base_tariff_pct']}% -> current {row['current_tariff_pct']}% (trend: {row['trend']}, effective {row['effective_date']})
Landed cost breakdown per unit (USD): {json.dumps(costs, default=float)}
Alternative origins for {category} (country: current tariff %):
{t[t['category'] == category][['country', 'current_tariff_pct']].to_string(index=False)}"""
    out = ask_gemini_json(system, prompt)
    out["current_tariff_pct"] = float(row["current_tariff_pct"])
    out["base_tariff_pct"] = float(row["base_tariff_pct"])
    out["landed_cost"] = costs
    return out


def run_geopolitics_agent(data: dict, brand_row: pd.Series) -> dict:
    country = brand_row["country"]
    agr = data["agreements"]
    agr_row = agr[agr["country"] == country].iloc[0]
    ev = data["events"]
    ev_rows = ev[ev["country"] == country].sort_values("date", ascending=False)
    system = ("You are the Geopolitical Risk Agent for Ross Stores' sourcing team. "
              "Assess country and trade-deal risk for importing from this origin. Respond ONLY with JSON: "
              '{"risk_score": 1-10, "deal_status": "favorable|mixed|unfavorable", '
              '"summary": "2-3 sentences", "key_events": ["..."], "outlook_6_months": "1-2 sentences"}')
    prompt = f"""Origin country: {country}
Trade agreement: {agr_row['agreement']} | status: {agr_row['status']} | tariff relief: {agr_row['tariff_relief']}
Official outlook note: {agr_row['outlook']}
Recent event feed:
{ev_rows[['date', 'event', 'risk_impact', 'direction']].to_string(index=False)}"""
    return ask_gemini_json(system, prompt)


def run_trend_agent(data: dict, brand_row: pd.Series) -> dict:
    category = brand_row["category"]
    tr = data["trends"]
    tr_rows = tr[tr["category"] == category].tail(12)
    forecast = forecast_next_quarter_units(data["sales"], category)
    recent_sales = data["sales"][data["sales"]["category"] == category].tail(6)
    system = ("You are the Market Trend Agent for Ross Stores (off-price retail). "
              "Assess consumer demand momentum for this category. Respond ONLY with JSON: "
              '{"demand_outlook": "strong|moderate|weak", "trend_direction": "rising|flat|declining", '
              '"summary": "2-3 sentences", "seasonal_note": "1 sentence"}')
    prompt = f"""Category: {category}
Last 12 months of market indices:
{tr_rows[['month', 'demand_index', 'social_buzz_score']].to_string(index=False)}
Ross sales, last 6 months:
{recent_sales[['month', 'units_sold']].to_string(index=False)}
Deterministic next-quarter demand forecast: {forecast:,} units (all-brand category total)."""
    out = ask_gemini_json(system, prompt)
    out["next_quarter_forecast_units"] = forecast
    return out


def run_finance_agent(data: dict, brand_row: pd.Series, tariff_out: dict,
                      target_margin_pct: float) -> dict:
    category = brand_row["category"]
    retail = float(data["trends"][data["trends"]["category"] == category]
                   ["avg_retail_price_usd"].iloc[-1])
    landed = tariff_out["landed_cost"]["landed"]
    mm = margin_math(landed, retail)
    viable = mm["gross_margin_pct"] >= target_margin_pct
    partial_viable = mm["gross_margin_pct"] >= target_margin_pct - 8
    system = ("You are the Finance Agent for Ross Stores' merchandising team. "
              "Judge unit economics of this buy. Respond ONLY with JSON: "
              '{"viability": "viable|marginal|unviable", "summary": "2-3 sentences", '
              '"levers": ["cost levers or negotiation angles"]}')
    prompt = f"""Brand: {brand_row['brand']} | Category: {category}
Landed cost/unit: ${landed} (FOB ${tariff_out['landed_cost']['fob']}, duty ${tariff_out['landed_cost']['duty']}, freight ${tariff_out['landed_cost']['freight']}, handling ${tariff_out['landed_cost']['handling']})
Planned retail price: ${retail}
Gross margin: {mm['gross_margin_pct']}% vs target {target_margin_pct}%
Deterministic screen: {"PASSES" if viable else "PASSES PARTIALLY" if partial_viable else "FAILS"} the margin test.
MOQ: {brand_row['moq_units']:,} units | Lead time: {brand_row['lead_time_days']} days | Quality score: {brand_row['quality_score']}/10"""
    out = ask_gemini_json(system, prompt)
    out.update(mm)
    out["landed_cost_per_unit"] = landed
    out["meets_target_margin"] = bool(viable)
    return out


def run_decision_agent(brand_row: pd.Series, requested_qty: int,
                       target_margin_pct: float, tariff_out: dict,
                       geo_out: dict, trend_out: dict, fin_out: dict) -> dict:
    system = ("You are the Chief Procurement Decision Agent for Ross Stores. Four specialist "
              "agents have reported. Decide whether to procure from this brand/country now. "
              "Rules: PARTIAL_YES means buy a reduced quantity (>= MOQ, < requested) to cap tariff/geopolitical "
              "exposure while the situation clarifies. Recommended quantity must be a multiple of 500, >= MOQ "
              "for YES/PARTIAL_YES, and 0 for NO. Respond ONLY with JSON: "
              '{"decision": "YES|PARTIAL_YES|NO", "recommended_qty": number, '
              '"order_timing": "e.g. order now / wait until <event or month>", '
              '"confidence": "high|medium|low", "rationale": "3-5 sentences referencing the agent findings", '
              '"conditions": ["conditions or triggers to revisit"]}')
    prompt = f"""Buy request: {requested_qty:,} units of {brand_row['category']} from {brand_row['brand']} ({brand_row['country']})
MOQ {brand_row['moq_units']:,} | lead time {brand_row['lead_time_days']} days | target margin {target_margin_pct}%

TARIFF AGENT: {json.dumps(tariff_out, default=float)}
GEOPOLITICS AGENT: {json.dumps(geo_out, default=float)}
TREND AGENT: {json.dumps(trend_out, default=float)}
FINANCE AGENT: {json.dumps({k: v for k, v in fin_out.items() if k != 'levers'}, default=float)}"""
    out = ask_gemini_json(system, prompt)
    # guardrails on the LLM's quantity
    qty = int(out.get("recommended_qty", 0) or 0)
    moq = int(brand_row["moq_units"])
    if out.get("decision") == "NO":
        qty = 0
    else:
        qty = max(moq, min(qty, requested_qty))
        qty = int(round(qty / 500) * 500)
    out["recommended_qty"] = qty
    return out


# ------------------------------------------------------------- orchestrator

def run_pipeline(data: dict, brand_name: str, requested_qty: int,
                 target_margin_pct: float, progress_cb=None) -> dict:
    """Run all five agents in sequence. progress_cb(step_name) is optional."""
    brand_row = data["brands"][data["brands"]["brand"] == brand_name].iloc[0]

    def step(name):
        if progress_cb:
            progress_cb(name)

    step("Tariff Agent analyzing duty exposure...")
    tariff_out = run_tariff_agent(data, brand_row)
    step("Geopolitics Agent assessing trade deals & events...")
    geo_out = run_geopolitics_agent(data, brand_row)
    step("Trend Agent reading demand signals...")
    trend_out = run_trend_agent(data, brand_row)
    step("Finance Agent running unit economics...")
    fin_out = run_finance_agent(data, brand_row, tariff_out, target_margin_pct)
    step("Chief Decision Agent synthesizing...")
    decision = run_decision_agent(brand_row, requested_qty, target_margin_pct,
                                  tariff_out, geo_out, trend_out, fin_out)
    return {"brand_row": brand_row, "tariff": tariff_out, "geopolitics": geo_out,
            "trend": trend_out, "finance": fin_out, "decision": decision}


if __name__ == "__main__":
    d = load_data()
    result = run_pipeline(d, "SaigonWear Co", requested_qty=20000,
                          target_margin_pct=45.0, progress_cb=print)
    print(json.dumps({k: v for k, v in result.items() if k != "brand_row"}, indent=2, default=float))
