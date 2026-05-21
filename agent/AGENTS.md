# cre-calcs — agent guide

Commercial real estate acquisition helper: cap-rate sensitivity, loan sizing, and year-one metrics (cash-on-cash, DSCR, LTV).

## Architecture

```
model.py, income.py     → immutable inputs (Listing, LoanTerms, sweeps, StatedNoi)
metrics.py, mortgage.py → ratios and amortizing debt service
scenarios.py            → build_* → list[ScenarioRow]
table.py, pdf_report.py → formatting and PDF export
cli.py, wizard.py       → argparse / questionary entry points
gui_app.py, gui_shared  → Streamlit UI (keys in gui_shared for tests)
```

Edit domain logic in `scenarios` / `metrics` / `model`; keep CLI and GUI as thin adapters.

## Three scenario modes

| Mode | Builder | What varies per row |
|------|---------|---------------------|
| Cap at fixed price | `build_cap_rate_scenarios` | Assumed cap → NOI = price × cap |
| Implied price | `build_cap_implied_price_scenarios` | Cap → price = NOI ÷ cap |
| Down payment sweep | `build_down_payment_scenarios` | Down % → LTV, CoC |

Balloon term is informational for exit display; year-one CoC/DSCR use level-pay P&I only.

## Commands

```bash
pip install -e ".[dev]"
pytest -q

cre-scenarios --price 3.2M --listing-cap 6.25 --down 30 --rate 6.75 --amort 25 --balloon 10
cre-wizard   # or cre-scenarios --interactive

pip install -e ".[gui]"
PYTHONPATH=src streamlit run src/cre_calcs/gui_app.py

docker compose run --rm test
```

User-facing install and Docker details: see [README.md](README.md).

## Where to edit

| Task | Primary files |
|------|----------------|
| New metric or ratio | `metrics.py`, `tests/test_metrics.py` |
| Loan / amortization math | `mortgage.py`, `tests/test_mortgage.py` |
| New scenario grid | `scenarios.py`, matching `tests/test_*.py` |
| CLI flags | `cli.py`, `tests/test_cli.py` |
| Interactive prompts | `wizard.py` |
| Streamlit UI / widget keys | `gui_app.py`, `gui_shared.py`, `tests/test_gui_shared.py` |
| Percent / money parsing | `percent_parse.py`, `money_parse.py` |

## Conventions

- Frozen `@dataclass(slots=True)` with validation in `__post_init__`.
- Tests use `math.isclose`; mirror module layout under `tests/`.
- Public exports live in `__init__.py` `__all__`.
- Parsing rules (display percent vs down fraction vs money): see `agent/rules/domain-percent-money.md`.

## Agent config (all tools)

Shared instructions live under `agent/`. After editing, run:

```bash
python3 agent/sync.py
```

See `agent/README.md` and skill `sync-agent-config`.
