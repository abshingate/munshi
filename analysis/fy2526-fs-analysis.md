# Exadatum — FY 2025-26 Financial Statement Analysis (handoff brief)

*Prepared 26 July 2026 by a Claude Code session working in `~/Documents/Exadatum/Financials/TDS/`. Written as a complete handoff for another Claude session — self-contained, but see "Companion files" at the end for the live working system.*

---

## 1. Company snapshot

- **EXADATUM SOFTWARE SERVICES PRIVATE LIMITED**, Pune. Incorporated 23-02-2016 (Companies Act 2013). Data analytics/IT services per Note 1, but **zero operating revenue for two consecutive years** — currently functions as an investment-holding vehicle.
- PAN AAECE2023L · TAN PNEE04370C · CIN U72900PN2016PTC158545 · GSTIN 27AAECE2023L1ZS
- Registered address (per ARTH invoice): 10, C-1003, 33 Keshavkunj, Near Old Orbis School, Keshavnagar, Mundhwa, Pune 411036
- **Directors:** Abhijit Suresh Shingate (DIN 07438851, PAN BDPPS9613G, employee EXA00001), Rupali Abhijit Shingate (DIN 07196549, PAN AMYPP3844M, employee EXA00002, HR), Suresh Shingate (DIN 09296794, not on payroll, no shares).
- **Shareholding** (37,504 shares of ₹10, fully paid; 50,000 authorized — the "12,496" sometimes mentioned is unissued authorized capital): Abhijit 22,999 (61%), Monalisa Sandeep Mehta 14,504 (39%), Rupali 1.
- **Auditor:** ARTH & Associates, Chartered Accountants, Pune (FRN 100868W), partner Ankush Mane (M.No. 165902), billing@arth.net.in. Also maintains the company's Tally books ("ARTH Tally"). Signed the FY25-26 financials **22-07-2026**. Accounts NOT yet adopted at AGM (due by 30-09-2026) or filed.
- Only 2 employees = the two salaried directors. No payroll software; TDS compliance taken in-house from FY26-27 (system lives in `~/Documents/Exadatum/Financials/TDS/`).

## 2. Source documents (all on this machine)

- **Audited FS FY25-26 (signed 22-07-2026):** `~/Documents/Exadatum/Financials/FY25-26/Audited Financials FY2025-26 (signed 22-07-2026).pdf` (original in ~/Downloads as "1. Financial Exadatum FY 2025-2026.pdf"). 17 pages: BS, P&L, Notes 1–37.
- **Director Salary Plan FY2026-27 + payslips:** `~/Documents/Exadatum/Financials/Salary Structure Generated on 7th July 2026/`
- **ARTH audit-fee invoice** ARTH251/2026-27 (22-07-2026, ₹1.25L + ₹22.5k GST) and **CS invoice** (Dipti Thite, ₹25k + GST): filed in `~/Documents/Exadatum/Financials/TDS/FY2026-27/invoices/`
- **Units convention:** ALL statement figures are in ₹'000. Verified mathematically: loss 4,415k ÷ 37,504 shares = ₹117.72/share = the stated EPS (117.71).

## 3. Headline figures (₹, converted from ₹'000)

| Item | FY 2025-26 | FY 2024-25 |
|---|---|---|
| Revenue from operations | **0** | **0** |
| Other income | 6,07,000 | 1,38,74,000 |
| — of which: FD interest | 3,57,000 | 11,92,000 |
| — profit on sale of investments | 1,90,000 | 1,23,62,000 |
| — dividend | 25,000 | — |
| — interest on IT refund | 35,000 | — |
| — rental income | — | 3,20,000 |
| Purchases | 4,99,000 | 7,87,000 |
| Employee benefit expense | 24,05,000 | 23,68,000 |
| Other expenses (Note 23 total) | 14,14,000 | 24,09,000 |
| — rent | 7,79,000 | 1,95,000 |
| — audit fees | 1,25,000 | 1,25,000 |
| — legal & professional | 1,61,000 | 34,000 |
| — commission | 0 | 5,05,000 |
| — balances written off | 0 | 7,07,000 |
| Depreciation | 7,04,000 | 2,46,000 |
| **Profit/(loss) after tax** | **(44,15,000)** | 75,48,000 (after ₹4.94L prior-period exp) |
| Share capital / Reserves | 3,75,000 / 4,47,61,000 | 3,75,000 / 4,91,76,000 |
| Investments (non-current: Motilal Oswal 95L + MF 2.39cr) | 3,34,54,000 | 3,51,21,000 |
| Current investments (MF) | 50,00,000 | 0 |
| Cash & bank (₹7.93L current a/c + ₹14.31L FDs) | 22,24,000 | 90,31,000 |
| Gratuity Fund (asset, Note 11) | 21,50,000 | 21,50,000 |
| Security deposits | 2,93,000 | 2,93,000 |
| Abhijit — salary advance (Note 16) | **2,72,000** | 1,19,000 |
| TDS receivable (Note 17) | 46,000 | 6,24,000 |
| Short-term provisions (audit fee 1.25L + prof fees 25k) | 1,50,000 | 1,50,000 |
| PF payable | 28,000 | 3,000 |

## 4. THE CENTRAL ISSUE — director salary mismatch (unresolved, blocks ITRs & possibly accounts)

**Note 27 (Related Party, AS-18)** — "Salary Payment to Directors & their relatives", FY25-26: **Abhijit ₹17,00,000; Rupali ₹7,00,000** (prior year: ₹12,00,000 each). Note 21 total salaries ₹24,05,000 ≈ 17L+7L — the two notes are mutually consistent, so the ledger itself was built on 17/7 (not a typo).

**Directors' firm position:** both salaries were supposed to be **₹12,60,000 each** (₹1,05,000/month). The FY26-27 salary plan (see §7) was built on that assumption.

**Possible explanations:** (a) actual drawings deviated — Abhijit drew ~₹4.4L extra (the growing salary advance supports this), Rupali ~₹5.6L less; or (b) ARTH misposted drawings/reimbursements into salary. **Resolution test: bank-statement totals of company→personal salary credits, Apr 2025–Mar 2026, per director. NOT YET PROVIDED as of 26-07.** Directors also hold Tally credentials and can inspect the salary ledgers directly.

**Consequences by branch:**
- Books RIGHT (17/7): Abhijit's FY25-26 personal ITR: 17,00,000 − 75,000 std ded = 16,25,000 taxable (new regime) → tax ₹1,25,000 + 4% cess = **₹1,30,000**, plus §234B/C interest ≈ ₹10–14k, payable as self-assessment tax. Company failed to deduct salary TDS on him → cure via Form 26A after he pays (any CA can certify). Rupali at 7L → zero tax (rebate).
- Books WRONG: ARTH must correct & re-sign before AGM adoption (by 30-09) and company ITR (31-10). Both directors then at 12.6L → 11.85L taxable each → **zero tax both** (under ₹12L rebate limit).
- Personal ITRs (due **31-07-2026**) will be filed on bank-record truth regardless; revised returns possible till 31-03-2027. Both MUST use **ITR-2** (company directors + unlisted shareholdings — double ITR-1 disqualification). Share cost for ITR-2 schedule: Abhijit ₹2,29,990 (22,999×₹10), Rupali ₹10. Full walkthrough: `~/Documents/Exadatum/Financials/TDS/ITR-FILING-FY2025-26.md`.

## 5. Director advance — ₹2,72,000 to Abhijit (Note 16)

- Grew from ₹1,19,000 (31-3-25) to ₹2,72,000 (31-3-26). Note text: "salary advance… recoverable in the normal course of employment"; auditors state no other loans to promoters/directors.
- **Companies Act §185 tension:** the FY26-27 salary plan itself pledges "no loans or advances to directors." Exemption argument: advance to a director-employee as part of conditions of service.
- **Income-tax risk — deemed dividend u/s 2(22)(e):** advance to a 61% shareholder from a company with ₹4.47cr accumulated reserves = textbook trigger; taxable in Abhijit's hands, dividend-TDS angle for the company. Defense = ordinary-course-of-employment characterization; needs ARTH's written position.
- **Agreed direction:** clear/adjust it against salary in FY 2026-27 and stop the pattern.

## 6. Other findings — status register

| # | Finding | Status |
|---|---|---|
| A | **Rent ₹7.79L FY25-26 / ₹1.95L FY24-25** — RECONCILED: landlord M/S Crystal Properties (partnership firm, PAN AAGFC0073K, Range Hills Rd Pune; partners Shashank Yadav / Nitin Soni). License 06-12-2024→31-03-2026 (ENDED; deposit ₹1.1L refunded in FY26-27). ₹55,000/mo + 18% GST; Dec-2024 rent-free fit-out. Books record rent GST-inclusive: 55k×12×1.18=₹7,78,800≈"779"; 55k×3×1.18=₹1,94,700≈"195". TDS: FY24-25 not required (₹1.65L < then-threshold ₹2.4L/yr); FY25-26 required ₹5,500/mo = ₹66,000/yr (10% on base excl GST) — directors say deducted & deposited (they paid challans themselves; ARTH filed returns). | Pending only TRACES evidence (challans/26Q/Form 16A). **No rent → no 194I obligation in FY26-27.** |
| B | **Prior-year TDS process** — directors deposited all challans themselves; ARTH filed the quarterly returns. FY24-25 commission ₹5.05L TDS: directors say done. | Verify via e-Pay Tax Payment History + TRACES Statement Status/Defaults (all logins available). |
| C | **Audit fee TDS timing** — fee provisioned ₹1.25L at 31-03-2026 (Note 8) → strictly 194J TDS was due at provision (deposit 30-04-2026). Instead deducted ₹12,500 at invoice (25-07-2026), planned for FY26-27 Q2 reporting. ~₹625 interest exposure; ARTH asked to advise treatment in writing. | Minor; awaiting ARTH advice. |
| D | **Gratuity** — ₹21.5L fund asset (LIC group gratuity, arranged by directors directly, fully funded before 2020, frozen in books since) with NO AS-15 liability booked. Not a cash issue: obligation accrues for the two director-employees (~10 yrs service; post-revision basic ≈₹1.67L/mo → accrued ≈₹9.5–10L each, trending to ₹20L/head cap, payable tax-free u/s 10(10)). DECISION: recognize liability + true up fund value in **FY26-27 books** (entries only, no fresh funding) unless FY25-26 accounts reopen for the salary issue — then include in re-signing. Directors to obtain LIC master policy + current fund statement. Note: gratuity provision is NOT tax-deductible (40A(7)) → zero ITR impact either way. | Decision made; LIC docs pending. |
| E | **Purchases ₹4.99L (FY25-26) with nil revenue & nil inventory** — unexplained; sits inside the carried-forward loss; wanted: one-line explanation from directors for the file (no book change needed). | OPEN question to directors. |
| F | **Rental income ₹3.2L FY24-25** — RESOLVED: company owned a property during FY24-25, earned rent, sold it that year (sale inside the ₹1.24cr profit on sale of investments; tenant TDS explains part of ₹6.24L TDS receivable; Investment Property nil at both dates). | Closed. |
| G | Prior-period expenses ₹4.94L (FY24-25) — left unexplained by choice; closed year, harmless. | Waived. |
| H | Drafting errors — several note pages headed "March 31, 2025" over 2026 data; Note 3.3 shareholding columns both labeled 2025; EPS note ₹'000 header over per-share values. | Fix only if accounts reopen. |
| I | Structural — zero revenue 2 yrs; FY26-27 commits ≈₹1.09cr salaries+TDS = deliberate reserves drawdown. Board resolution must state THAT rationale (plan's placeholder "revenue growth" is disproved by the accounts). Liquidity: ₹72L liquid vs ₹1.09cr annual commitment → planned investment liquidations; ring-fence 7th-of-month TDS money. GST: ITC being expensed (₹51k "GST P&L") with no outward supplies — conscious review advised. | Advisory, standing. |

## 7. FY 2026-27 payroll/TDS context (the forward-looking frame these accounts feed)

- Salary plan (7-Jul-2026, "Director Salary Plan FY2026_27_Revised.pdf"): both directors revised ₹12.6L→**₹50,00,000 gross each** from 01-04-2026; Apr–Jun paid at old rate ₹1,05,000/mo (**needs bank verification** — same doubt as the FY25-26 mismatch); July off-cycle arrears ₹9,35,001 each (TDS ₹2,75,000 each); thereafter ₹91,700/mo TDS each; March true-up ₹91,200 (must be recomputed with CA for other income + surcharge marginal relief — both directors have MF SIPs; Abhijit has Zerodha ZYK185). Annual TDS ≈ ₹10,99,800 each (cess included).
- **Immediate deadline: 07-08-2026 deposit** — salary TDS ₹7,33,400 combined (arrears ₹5,50,000 + July ₹1,83,400, one 92B/Section 392 challan, major head 0021) + ₹12,500 (194J, ARTH invoice; register shows net payable to ARTH ₹1,35,000). Board resolution must be minuted before arrears disbursement.
- Q1 FY26-27 had nil TDS (no return needed; TRACES non-filing declaration advised). New Income Tax Act 2025 in force: salary TDS = §392 (old 192), other TDS = §393, returns Form 138/140/144 (old 24Q/26Q/27Q), late fee §427.
- Other FY25-26-ITR-relevant deadlines: personal ITRs 31-07-2026 (ITR-2, see §4); company ITR-6 **31-10-2026 — on-time filing REQUIRED to carry forward the ₹44.15L loss**; AGM adoption by 30-09-2026.

## 8. ARTH dependency map (what can/cannot be routed around)

- **Hard dependency (only ARTH):** revising/re-signing the FY25-26 accounts if the salary entries are wrong; auditor positions inside those accounts (gratuity, §185 note). Replacing a statutory auditor mid-term is deliberately hard — treat as locked-in for FY25-26.
- **Soft:** salary ledger explanation (directors hold Tally credentials and can self-inspect); company ITR filing (any CA); Form 26A certificate (any CA).
- **None:** all TDS history (self-service via TRACES deductor login + e-filing TAN login), personal ITRs, all FY26-27 TDS operations, Form 16A/16 generation.
- A final email to ARTH (v5) covering items 1–8 is drafted in the issues file (appendix) — status: not yet confirmed sent. 7-day response clock on the salary item.

## 9. Open questions awaiting the directors (as of 26-07-2026)

1. **Bank salary totals Apr 2025–Mar 2026 per director** ← decides §4; personal ITR deadline 31-07.
2. What was actually bank-paid Apr–Jun 2026 (validates the arrears math before the 07-08 challan).
3. One-line explanation of the ₹4.99L purchases (finding E).
4. LIC master policy + current fund statement (finding D).
5. TRACES/Payment-History screenshots (findings A/B closure).
6. DSC status; CA contact confirmation; FY26-27 return-filing route (suggestion on file: ARTH files Q2 from our data, in-house from Q3).

## 10. Companion files (the live system — do not duplicate, extend)

All in `~/Documents/Exadatum/Financials/TDS/`:
- `CLAUDE.md` — operating instructions (commands: "Process this invoice", "Monthly TDS run", "Quarterly TDS return"); auto-loaded by sessions in that folder
- `FY25-26-FINANCIALS-ISSUES.md` — the issue register this analysis summarizes, incl. the v5 ARTH email
- `company-profile.md` — all identifiers, directors, shareholders, findings list
- `GUIDE.md`, `SOP-PER-INVOICE.md`, `COMPLIANCE-CALENDAR.md`, `PORTAL-PROCEDURE-TDS-PAYMENT.md`, `ITR-FILING-FY2025-26.md`
- `FY2026-27/tds-register.csv` (2 entries: ARTH ₹12,500 TDS; Dipti Thite ₹0 below-threshold) · `FY2026-27/salary-tds-schedule.csv` · `vendors.csv` (ARTH, Dipti Thite, Crystal Properties)
- `credentials.md` — ⚠ SENSITIVE: all portal logins (e-filing TAN, TRACES deductor, GST, PF, PT, Tally) + directors' personal identifiers. Reference it; never copy its contents elsewhere or publish.
- Google Calendar reminders exist for all statutory deadlines (monthly 5th, quarterly returns, ITRs, March special date).
