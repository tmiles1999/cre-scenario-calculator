# cre-calcs

Commercial real estate acquisition helper: cap-rate sensitivity, loan sizing, and year-one metrics (**cash-on-cash**, **DSCR**, **LTV**). NOI is modeled as **purchase price × assumed cap**; debt service is fixed-rate P&I from amortization terms.

## Requirements

- Python **3.10+** (local) or **Docker** (see below)

## Local install and CLI

Create a virtual environment, install the package, then use the `cre-scenarios` entry point or run as a module.

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the CLI. **`--listing-cap`**, **`--rate`** (loan rate), and **`--sweep-step`** are **display percentages only** (always ÷100): `6.25` means **6.25%**, `0.1` means **0.1%** (not a decimal cap). **`--down`** is still equity as a fraction of price (`25` or `0.25` → 25% down). **`--price`** accepts shorthand such as **`3.2M`**, **`874k`**, and **`$2,700,000`** (commas and spaces are ignored).

```bash
cre-scenarios --price 3.2M --listing-cap 6.25 \
  --down 30 --rate 6.75 --amort 25 --balloon 10 \
  --sweep-step 0.25 --sweep-below 4 --sweep-above 4
```

Same numbers in plain form:

```bash
cre-scenarios --price 3200000 --listing-cap 6.25 \
  --down 30 --rate 6.75 --amort 25 --balloon 10 \
  --sweep-step 0.25 --sweep-below 4 --sweep-above 4
```

Equivalent:

```bash
python -m cre_calcs.cli --price 3200000 --listing-cap 6.25 --rate 6.75 ...
```

### Interactive wizard

For guided prompts (sweep type, stated NOI, escalators, cap→price vs down-payment stress):

```bash
cre-wizard
# or
cre-scenarios --interactive
```

- **Cap at fixed price** — same model as the flags above (`NOI = price × cap`).
- **Cap → implied offer price** — fixed year-*N* **stated NOI** with optional **annual or step escalator**; each row shows **implied purchase price = NOI ÷ cap** at a chosen down payment.
- **Down payment sweep** — fixed price and NOI; rows vary **equity / loan** so **LTV** and **cash-on-cash** move with the down payment grid.

In Docker you need a **TTY** and **stdin** so prompts work (`-it`). Examples:

```bash
docker build -t cre-calcs:latest --target runtime .

# Interactive mode (same entrypoint as local: cre-scenarios)
docker run --rm -it cre-calcs:latest --interactive

# Or call the wizard script directly (override entrypoint)
docker run --rm -it --entrypoint cre-wizard cre-calcs:latest
```

With Compose (service `scenarios`):

```bash
docker compose build
docker compose run --rm -it scenarios --interactive
```

If prompts look broken, confirm you used **`-i`** (stdin) and **`-t`** (TTY); plain `docker run --rm` is non-interactive.

### Web GUI (live table + PDF)

Install GUI extras, then run Streamlit from the repo root (with `src` on the path):

```bash
pip install -e ".[gui]"
PYTHONPATH=src streamlit run src/cre_calcs/gui_app.py
```

Three tabs mirror the main scenarios (left to right): **implied price from NOI ÷ cap**, **down-payment sweep**, and **cap at fixed price**. The table updates as you change inputs. Use **Download PDF report** for a styled letter-size PDF (ReportLab).

**Docker:** build the `gui` image and run Streamlit on port **8501**:

```bash
docker compose build gui
docker compose up gui
# browse to http://localhost:8501
```

Or without Compose:

```bash
docker build -t cre-calcs-gui:latest --target gui .
docker run --rm -p 8501:8501 cre-calcs-gui:latest
```

## Local testing

```bash
pip install -e ".[dev]"
pytest
```

PDF export is covered when `reportlab` is installed (included in `.[dev]`).

Verbose output:

```bash
pytest -v
```

## Docker

Requires [Docker Engine](https://docs.docker.com/engine/install/) or Docker Desktop. On **WSL2**, enable Docker Desktop’s WSL integration or install Docker inside the distro so the `docker` CLI is available.

Build and print help (default command):

```bash
docker build -t cre-calcs:latest --target runtime .
docker run --rm cre-calcs:latest
```

Run a scenario (arguments are passed to `cre-scenarios`):

```bash
docker run --rm cre-calcs:latest \
  --price 3200000 --listing-cap 6.25 \
  --down 30 --rate 6.75 --amort 25 --balloon 10
```

### Docker Compose

```bash
docker compose build
docker compose run --rm scenarios --price 3200000 --listing-cap 6.25 \
  --down 30 --rate 6.75 --amort 25 --balloon 10
```

Run the full test suite in a disposable test image:

```bash
docker compose run --rm test
```

This builds the `test` stage (installs `pytest`), copies `tests/`, and runs `pytest -q`.

## Project layout

| Path | Purpose |
|------|---------|
| `src/cre_calcs/` | Library, CLI, wizard, Streamlit GUI (`gui_app.py`), PDF export (`pdf_report.py`) |
| `tests/` | Pytest suite |
| `Dockerfile` | `runtime` (CLI), `test` (pytest), `gui` (Streamlit) stages |
| `docker-compose.yml` | `scenarios`, `test`, and `gui` (port 8501) services |
