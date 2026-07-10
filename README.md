# Ross Stores — Agentic Procurement Advisor

An agentic AI prototype that answers, for any candidate buy:
**"Should Ross procure this product from this brand/country — and if only
partially, how many units and when?"** — based on tariffs, geopolitical trade
deals, and consumer demand trends.

Five cooperating agents (Tariff, Geopolitics, Trend, Finance, Chief Decision)
run on Google Gemini with deterministic finance guardrails, orchestrated in
plain Python, served through a Streamlit dashboard.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then paste your Gemini API key into .env
python data_gen.py            # regenerate the synthetic datasets (optional; committed)
streamlit run app.py
```

Open http://localhost:8501, pick a category/brand in the sidebar, set the
requested quantity and target margin, and click **Run agentic analysis**.

## Project layout

| Path | What it is |
|---|---|
| `data_gen.py` | Seeded synthetic-data generator (6 datasets in `data/`) |
| `agents.py` | The agentic core: 5 agents + orchestrator (`run_pipeline`) |
| `app.py` | Streamlit dashboard |
| `docs/problem_statement.md` | Problem statement & justification |
| `make_ppt.py` | Generates the submission PPT (`Ross_Agentic_Procurement.pptx`) |

## Demo scenarios worth showing

- **Apparel · MeiTex Garments (China)** — 46.5% tariff usually forces **NO** or
  a heavily reduced buy; compare with **SaigonWear Co (Vietnam)**.
- **Footwear · DaNang Soles (Vietnam)** — rising demand + pending tariff relief
  often yields **PARTIAL_YES** with "revisit after the October ratification vote".
- **Home Goods · Casa Loma Living (Mexico)** — USMCA duty-free, short lead time:
  a clean **YES**.
