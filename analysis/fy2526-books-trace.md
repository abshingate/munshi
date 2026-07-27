# Exadatum FY25-26 — Voucher-Level Books Trace (companion to fy2526-fs-analysis.md)

*26-Jul-2026, from the live Tally company (Edit Log edition) on the cloud
workstation, via the XML gateway. Extends — does not duplicate — the FS
analysis brief and `~/Documents/Exadatum/Financials/TDS/FY25-26-FINANCIALS-ISSUES.md`.
Voucher numbers cited throughout are verifiable in Tally's Day Book.*

## A. THE SALARY LEDGERS ANSWER §4 — books show ~₹11.92L each, SYMMETRIC

**Monthly payroll journal (Jnl #123–134, one per month, Apr-25 → Mar-26, 12 of 12 present):**

```
Dr Salary Expeness            1,98,700   (combined, both directors)
Dr Employers Contribution PF      1,202
Dr PF Admin/EDLI                    550
   Cr PF Paid                             2,952
   Cr PT Paid                               400
   Cr SALARY PAYABLE                    1,97,100
```

12 × 1,98,700 = **₹23,84,400** = the Salary Expeness ledger total exactly.
(FS Note 21's 24,05,000 ≈ this + employer PF ~14.4k + misc — the P&L TOTAL is fine.)

**Monthly payments (bank ledger ABH-239005001481): ₹98,550 to EACH director,
every month** — narration suffix identifies the beneficiary
(`…/ABHIJITSHINGATE` vs `…/RUPALIS`). Payment batches: 03-Apr (Mar-25
arrears ₹56,883 each), 04-May, 01-Jun, 03-Jul, 01-Aug, [Sep: see below],
03-Oct, 29-Oct, 01-Dec, 29-Dec, 30-Jan, 01-Mar, 24-Mar. My earlier
"Nov/Feb missing" observation was an artifact of batch dates at month
edges — **all 12 months are present**; correction noted.

**Implied gross per director: ₹99,350/month → ₹11,92,200/year — EQUAL for
both.** Not 17L/7L. Close to (though not exactly) the directors' remembered
₹12.6L (12.6L would be ₹1,05,000/mo vs booked ₹99,350/mo — the ~₹5,650/mo
gap needs one look at the salary structure, but the SYMMETRY is beyond doubt).

**Predicted bank-statement salary credits (the brief's §4 resolution test),
from the books' bank ledger:**
- Abhijit: 56,883 + 98,550 × 11 (Sep skipped — see B) = **₹11,40,933**
- Rupali: 56,883 + 98,550 × 12 = **₹12,39,483**

### ✅ RESOLUTION TEST CONFIRMED (26-Jul-2026, from the bank work in `~/Documents/Exadatum/Bank/`)

`reconciliation-FY25-26.md` (statement `exadatum-bank-statement.pdf`, ICICI
239005001481, 299 txns, reconciled 25-Jul-2026) independently records:

- §4: *"All 28 company→Abhijit transfers appear in the personal statement
  with identical INFT/UPI reference numbers — every salary (56,883 Mar-25;
  98,550 × 11 months)"* → **Abhijit ₹11,40,933, exactly as predicted.**
- §5: *"Salaries: May 2025 – Mar 2026, Abhijit & Rupali, ₹98,550 each/month
  — all vouchers on file"* + §1: April salaries paid 04/05 (₹98,550 ×2)
  → **Rupali 12 × 98,550 + 56,883 = ₹12,39,483, exactly as predicted.**
- §3: Abhijit's personal-statement salary credits *"jump from 01/08 to
  03/10"* → the missing Sep credit is precisely the Jnl #138 Aug set-off
  month.

**Three-way agreement: Tally ledgers ↔ company bank statement ↔ Abhijit's
personal statement (reference-number matched).** The ledgers are true.
**Note 27's 17/7 split is a disclosure/allocation error by ARTH**, not a
ledger fact. The P&L needs no change; the related-party note (and any
salary-TDS/ITR arithmetic built on 17/7) does. Consequences in §C are now
operative, not conditional.

**One correction the other way (books → bank file):** the reconciliation's
§3 flags *"Abhijit Aug 2025 salary ₹98,550 was never paid … Fix in books:
either pay it or cancel the voucher."* The books already handled it —
**Jnl #138 (01-Sep-25) set the Aug salary off against Abhijit's personal
ledger** (he owed the company; the set-off later feeds the year-end ADV SAL
sweep, Jnl #151). No bank debit is *expected*; nothing to fix. Addendum
appended to the reconciliation file.

## B. THE ADVANCE — mechanics fully traced (feeds §5)

Three vouchers tell the whole story:
- **Jnl #140 (03-Apr-25)**: opening interplay between Abhijit's personal
  ledger and SALARY PAYABLE (₹1,13,766 — the Mar-25 arrears cycle).
- **Jnl #138 (01-Sep-25)**: *"Aug month salary adjusted in abhijit sir a/c"* —
  Abhijit's Aug salary (₹98,350) was NOT bank-paid; it was set off against
  his personal ledger (he owed the company).
- **Jnl #151 (31-Mar-26)**: *"Debit balance of Abhijit sir transferred to
  advance sal"* — the year-end sweep that CREATED the ₹2,71,955.32
  "ABHIJIT SHINGATE - ADV SAL" balance. The "salary advance" is not a
  granted advance; it's the reclassified net of Abhijit's personal drawings
  through the year (after the Aug set-off).

Implication for §5: the "recoverable in the normal course of employment"
label is a year-end characterization of drawings. The Sep set-off shows the
clearing mechanism already in use — the agreed FY26-27 clear-against-salary
direction has precedent in the books. The §2(22)(e) analysis should use this
drawings-swept-to-advance fact pattern, not a "company granted an advance"
one.

## B2. FINDING E ANSWERED — the ₹4.99L "purchases" are prototyping hardware

Traced every voucher touching the Purchases ledger (group Purchase
Accounts; closing ₹4,99,428.24 — matches FS Note to the rupee). Composition,
largest first: DJI drone ₹1,43,000 (Dhaani Enterprises, Jnl 04-Aug),
Crystal Technology aluminium ₹75,190, Amazon equipment ₹37,658 (21-May),
WOL 3D printer filaments ₹28,000, Voltera (via Abhijit reimb.) ₹25,336,
Udyami "Train The Eximprenuers" ₹18,879, plus smaller electronics/materials
(Robu, Global Automate, foam, fans etc.). **These are R&D/prototyping and
office fit-out purchases during the zero-revenue build year — not trading
stock.** The Bank-folder reconciliation shows almost all are invoice-backed
(drone invoice ties ₹1,43,000 exact; Amazon UPI payments reconcile to the
paisa). Finding E is explained; residual question for ARTH is only
classification (P&L purchases vs fixed assets for the drone/aluminium —
capitalization judgement), not existence.

## C. Consequences now that the bank statements confirm A

1. **Both directors' FY25-26 gross salary ≈ ₹11.92L** → new regime, ₹75k
   std deduction → taxable ≈ ₹11.17L each → **within the ₹12L rebate zone →
   zero tax BOTH** (vs ₹1.3L+ Abhijit would pay under the 17/7 note). The
   ITR-2s (due 31-07) should be prepared on ledger+bank truth.
2. **ARTH question sharpens from "which is right?" to "Note 27 shows 17/7 —
   the ledgers you keep show 11.92/11.92 (Jnl #123–134, equal monthly
   payments). Please correct the related-party disclosure or show the
   workings behind 17/7."** Note the accounts are signed but NOT adopted
   (AGM by 30-09) — the correction window is open.
3. The FY26-27 arrears/TDS math (brief §7) built on 12.6L should be
   re-checked against the booked 11.92L before the 07-08 challan.

## C2. Correction plan handed to the CA

The full fix plan (FS revision before AGM, advance extinguishment options,
FY26-27 entries, §185/2(22)(e) confirmations, deadlines) is written up for
ARTH at **`~/Documents/Exadatum/Financials/CA-correction-plan-FY25-26.md`**.
Core stance: FY25-26 vouchers are NOT to be altered (books tie to bank
exactly; Edit Log company); the advance is cleared in FY26-27 — preferably
by immediate bank repayment (Option A), else salary set-off (Option B, Jnl
#138 precedent) — and Note 27 is corrected in reissued FS before adoption.

## D. Verification status of the books overall (context for this trace)

- Trial balance consistent (ledger sum = current-year loss ₹44,14,610.36,
  matching the FS loss "4,415" exactly — a strong books↔FS tie-out).
- 450 vouchers FY25-26; monthly counts 20–56, no gaps; year-end closed
  31-03-2026 by ARTH; FY26-27 empty (clean handover).
- Ledger hygiene items for eventual cleanup (NOT before ITR season):
  misspelled "Salary Expeness"; three Abhijit advance-type ledgers; several
  zero-balance director-loan ledgers.

## F. TALLY TIE-OUT vs `analysis/bank-invoice-analysis.md` §9 (run 26-Jul-2026, live books)

The third session's handoff embeds the statement control totals and a
suggested tie-out checklist. Executed against the live Tally ledgers:

| Check | Statement / handoff | Tally ledger | Verdict |
|---|---|---|---|
| Bank closing 31-03-26 (ICICI 1481) | **7,92,746.56** | `ABH-239005001481` Dr **7,92,746.56** | ✅ EXACT, to the paisa |
| Rent expense (gross) | net paid 7,12,800 + TDS 66,000 = **7,78,800** | `Rental Expenses` **7,78,800** | ✅ EXACT |
| Salary expense | 12 × 1,98,700 | `Salary Expeness` **23,84,400** | ✅ EXACT (see §A) |
| SALARY PAYABLE closing | should be nil if Aug set-off is real | **0** (absent from non-zero list) | ✅ — confirms Jnl #138; the "never-paid Aug voucher" needs NO fix |
| Director advance | 2,71,955.32 | `ABHIJIT SHINGATE - ADV SAL` **2,71,955.32** | ✅ |
| IT refund interest | refund 6,64,670 rec'd 16-02 | `Interest on Income Tax Refund` income **34,650**; `TDS Receivable` **45,544.40** | ✅ plausible; verify 45,544 vs 26AS (FD-interest TDS per handoff §4.1 sums to a similar order) |
| Investments | MOSL PMS 50L + MOFSL 45L | `Motilal Oswal Investment` **1,45,00,000** (likely incl. ~50L opening), `MUTUAL FUND INVESTMENT` **2,39,53,688.56** (source of the ~₹75k×2/mo ICCL credits) | ✅ consistent; exact roll-forward = ARTH workings |
| FDs at year-end | all big FDs closed in-year | `Fixed Deposit` **14,30,950** + accrued int 10,218 | ✅ plausible (small FDs 6059/7488 still paying interest through Mar) |
| FD interest income | §4.1 credits + TDS gross-up | `Interest on FD` **3,56,660** | ✅ plausible |
| Dividends | §4.4 small ACH credits | `Dividend / Interest on Investment` **25,515.10** | ✅ plausible |

**Bottom line: the books tie to the actual bank statement exactly on every
hard number checked.** Combined with the other session's 299/299 transaction
classification (~99.93% of debit value invoice-backed), FY25-26 is in far
better shape than the FS-note errors suggested — the defects are in ARTH's
disclosures (Note 27) and small paperwork gaps (~₹5,400), not in the books.

Items the handoff leaves as management decisions (unchanged, for Abhijit +
CA): (a) ~₹17,858 of AWS Apr–Nov + ₹3,122 Workspace Apr charged to the
personal card, never reimbursed and probably not in books — reimburse/book
as director-funded or ignore; (b) the ₹4,745 under-reimbursement on the
24/03 cycle; (c) Amazon ₹699 of 25-Dec company-vs-personal. Note for
FY26-27: the CloudFlare ₹15,362 was a 2-year registration of **aaiga.ai**.

## E. Still wanted (updated 26-Jul after absorbing `~/Documents/Exadatum/Bank/`)

1. ~~Bank statements Apr-25→Mar-26~~ — **DONE**: statements found in the Bank
   folder, already reconciled line-by-line by the other session
   (`reconciliation-FY25-26.md`); salary predictions confirmed (§A above).
   Remaining bank-side opens live in that file + `MISSING-INVOICES-to-collect.md`:
   a handful of invoices still to collect (AWS micro-charges, Microsoft,
   Canva, water/paint petty receipts), the ₹23,564 under-reimbursement
   (~₹4,745 short — tell ARTH), MOFSL 2nd-tranche slip, SureshS TDS ₹36,000
   paid from an unknown account.
2. The salary structure behind ₹99,350 vs remembered ₹1,05,000 gross.
3. Everything else in the brief's §9 stands.

## G. FY23-24 FS absorbed (26-Jul, from ~/Downloads/2. Exadatum Financials 2023-24.pdf)

- **No director advance existed at 31-03-2024** (Note 19 nil; none at 31-03-2023
  either) → the ₹1,19,000 opening advance **arose entirely within FY24-25**. The
  evidence hunt for it is one year wide, not open-ended.
- Salary history: FY23-24 ₹5,00,000 each (Note 26, Abhijit + Rupali); FY24-25
  ₹12,00,000 each booked (per FY25-26 FS comparative; employee benefit 2,368);
  FY25-26 ₹11,92,200 each booked. FY24-25 was paid irregularly in arrears
  (e.g. "july sal" transfers of ₹56,783 paid 02-03-2025) — the ₹1.19L advance
  most likely = payments to Abhijit exceeding the payable balance at points in
  time (salary-timing excess), possibly plus unsubmitted reimbursements. ARTH's
  FY24-25 ledger roll-forward will show which.
- **Company owns the flat (investment property ₹3.83 Cr, Note 13/2.13; furniture
  improvement ₹10,69,971 in FY23-24)** — confirms Amedeo was the COMPANY's
  tenant. Rental income: FY22-23 ₹8.22L, FY23-24 ₹18.58L (≈160k/mo ✓), FY24-25
  only ₹3.20L → consistent with Amedeo moving out ~May-2024 to the Mann/Sonal
  flat that appears in his TDS workings; the "₹9.68L Apr–Sep-24 rent" in those
  workings evidently spans both landlords. Softens (but keep asking) the
  rental-income question to ARTH.
