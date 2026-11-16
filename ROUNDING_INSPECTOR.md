# Rounding inspector — v0.19.0

Open `ROUNDING_INSPECTOR.html` from the extracted project. Enter a decimal price and a positive decimal tick and select **Compare rounding**, or load an explicitly synthetic example. Results clear when the inputs change. Input is not saved automatically; in the tested flows it stays in the local page, with no network requests.

## What is compared

The exact decision uses the typed decimal strings, nearest tick with ties toward the higher price. The reference-like index uses JavaScript double precision to evaluate `floor(price / tick + 0.5 + 1e-10)`. The tolerance is in tick units. The displayed floating quotient is a short decimal representation, not the exact binary value.

- For price `0.0049999999995` and tick `0.01`, the exact index is 0, while the reference-like step returns 1. The tolerance can affect this decision.
- For price `-0.005` and tick `0.01`, an exact half-tick tie goes to index 0, toward the higher price.

The tool shows the exact aligned price, but **not** the reference's final price: the reference subsequently multiplies by its floating tick and rounds to 10 decimal places. Typed values also cannot reproduce the upstream intermediate calculations in the reference. JavaScript floating arithmetic here is a comparison aid, not a call to Python or Pine. The tool cannot tell which answer is appropriate for an instrument, identify the source of a difference, establish Pine parity, simulate execution, or prove profitability. Check instrument tick rules independently.

## Boundaries and testing

Decimal notation only, up to 12 whole digits, 16 fractional digits in price and 10 in tick. Tick must be positive; absolute price/tick must not exceed 2^40. Inputs over 64 characters are rejected without truncation. These are tool limits, not model limits. Binary conversion and intermediate arithmetic may still be inexact even when the two indexes agree.

Run `node --test tests/*.cjs` and `python -m unittest discover -s tests` from the extracted directory. The Python Decimal and Python floating-step oracle checks require Node; without it they are skipped. Tests use synthetic inputs and do not establish chart behavior, market performance or broker execution. See `TECHNICAL_REVIEW.md` and `VALIDATION.md` for scope and other pending checks.
