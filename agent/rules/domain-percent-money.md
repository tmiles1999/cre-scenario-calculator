# Domain: percents, money, formulas

## Display percent (cap, loan rate, sweep step)

Always **display percentage**, never a pre-scaled decimal. Use `parse_display_percent_to_decimal`:

| Input | Decimal |
|-------|---------|
| `6.25` | 0.0625 |
| `0.1` | 0.001 (0.1%, not 10%) |
| `6.25%` | 0.0625 |

CLI and wizard use the parser on strings. Streamlit widgets use numeric values → divide by 100 (`gui_app._pct`).

## Down payment (equity fraction)

**Not** the same as loan-rate percents. Accept `25` or `0.25` → 0.25 fraction (`cli._fraction`, wizard `_parse_fraction`).

## Money

Use `parse_money_amount`: `3.2M`, `874k`, `$2,700,000` (commas/spaces ignored).

## Core formulas

- NOI at cap: `price × assumed_cap + percentage_rent_annual`
- Implied price: `operating_income ÷ cap`
- Loan amount: `price × (1 − down_fraction)`
- Cash-on-cash: `(NOI − annual_debt_service) / equity`
- DSCR: `NOI / annual_debt_service` (None when ADS is 0)
- LTV: loan amount / purchase price

## Scenario invariants

- **Cap sweep at fixed price**: LTV constant across rows; NOI moves with cap.
- **Implied price**: same NOI each row; price = NOI ÷ cap.
- **Down sweep**: fixed price and NOI; LTV and CoC move with down %.

`CapRateSweep.cap_rates_low_to_high()` drops non-positive caps (wide sweeps can go ≤ 0).
