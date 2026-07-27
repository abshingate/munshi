# Financial-statements generator (`vm/app/lib/fsgen.js`)

Generates complete Schedule III annual financial statements — Balance Sheet,
Statement of Profit & Loss, all notes, the Companies Act depreciation
schedule, EPS and key ratios — directly from a ledger-level Tally trial
balance. No spreadsheet in the loop: the trial balance comes from the Tally
XML gateway, the mapping and company facts live in a JSON config, and the
output is an exact-arithmetic model, a rendered HTML/PDF document, and a
validation report.

## Why

The traditional flow (CA dumps a TB into Excel, tags each ledger, formula-links
the statements, prints to PDF) works — but every manual hop is a place for a
transcription slip, and the workbook's rounding can quietly hide a balance
sheet that doesn't actually balance. This generator keeps all arithmetic in
paise until the final presentation pass, refuses to produce statements while
any validation fails, and reports rounding artefacts explicitly instead of
hiding them.

## Usage

```
node vm/app/lib/fsgen.js --tb tb.json --config company-config.json --out outdir
```

- `tb.json` — `{ "ledgers": [ { "name", "opening", "closing" } ] }` with
  Tally's sign convention (debit positive, credit negative). Use
  `parseTallyLedgerXML()` to build it live from a gateway ledger collection.
- `company-config.json` — see `vm/app/fs-config/example-config.json`.
- Output: `financial-statements.html` (print to PDF via any headless
  browser), `fs-model.json` (every computed value plus the validation
  findings).

Generation is refused (exit 1) while any `error`-level validation stands.

## What the config asks of the user (and how often)

| Input | Frequency | Validated against |
|---|---|---|
| Ledger → statement-line mapping (`mapping`) | New ledgers only — an unmapped ledger is a hard error, so drift is impossible | every TB ledger must resolve |
| Asset blocks (which ledgers form each PPE block + its accumulated-depreciation ledger) | New asset ledgers only | block movement must equal the depreciation expense ledger; net block must tie to the BS |
| Company facts (name, address, incorporation) | Once | — |
| Share capital & shareholders | On change | shares × face value must equal the share-capital ledger; holdings must sum to issued shares |
| Related-party names and per-party amounts | Yearly | must reconcile to the salary ledgers |
| Current/non-current carve-outs (e.g. portion of an investment classified current) | Yearly judgement | cannot exceed the source ledger balance |
| Comparatives (prior year printed figures) | Auto-carried from last year's generated statements | reserves continuity check |
| Boilerplate notes (policies, MSME, contingencies…) | Seeded once, reviewed yearly | — |
| Signing block (auditor, directors, place, date) | Yearly | — |

## Validations

- Trial balance must balance (opening and closing, to the paise)
- Every ledger mapped; every non-zero tag consumed by some statement line
- Balance Sheet must balance in **paise**, not just in printed thousands
- Depreciation schedule ties: gross movement from asset ledgers, charge equals
  the depreciation expense ledger, net block equals the BS line
- Reserves roll-forward: TB opening vs prior signed FS (drift warning), and
  consistency with any P&L-transfer journal already in the books
- P&L recomputed independently from the mapped ledgers and compared
- Related-party remuneration reconciled to the books
- EPS and ratios recomputed
- Rounding footing: any note whose printed lines don't foot to its printed
  total is reported (an honest property of ₹'000 rounding — never hidden)

## Golden testing

Keep last year's signed statements as the expected output and diff a
regeneration against them value-by-value before trusting a new mapping (see
the pattern in this repo's history: the generator was validated by
reproducing an audited FY's statements with 95/96 exact matches — the one
difference being a manual adjustment in the auditor's workbook that the books
did not contain).
