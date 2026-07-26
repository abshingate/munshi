# Exadatum FY 2025-26 — Complete Bank ↔ Invoice Reconciliation (Handoff Document)

> **Purpose of this document:** Complete handoff of the FY 2025-26 bank-statement ↔ invoice reconciliation for **Exadatum Software Services Private Limited**, prepared so another Claude session can verify these entries **against Tally** without re-deriving anything. Everything below was verified transaction-by-transaction from source PDFs during the reconciliation session of 25-Jul-2026 (continued 26-Jul-2026).
>
> **Prepared by:** Claude session working with Abhijit Shingate (abshingate@exadatum.com).
> **User context:** Two-director company — Abhijit Shingate + Rupali Shingate. No employees other than directors (plus part-time office help). Monthly payslips are NOT maintained (per Abhijit — salary voucher gaps are intentionally IGNORED).

---

## 1. Entities, accounts and source documents

| Entity / Account | Details |
|---|---|
| Company | Exadatum Software Services Pvt Ltd, C1003, 33 Keshavkunj, Keshavnagar, Manjri Road, Mundhwa, Pune 411036. PAN-linked IT refund shows company PAN **AAECE2023L**. TAN for TDS: **PNEE04370C**. EPF establishment: **PUPUN1537009000** |
| **Company bank (primary reconciled account)** | ICICI Current A/c **239005001481**, branch WTC Kharadi (IFSC ICIC0002390). Statement: `~/Documents/Exadatum/Bank/exadatum-bank-statement.pdf` — period 01/04/2025–31/03/2026, **299 transactions**, 16 pages |
| Statement control totals | **Opening balance 5,23,683.55 · Withdrawals 2,14,15,788.98 · Deposits 2,16,84,851.99 · Closing balance 7,92,746.56** (use these to tie out Tally bank ledger) |
| Abhijit personal savings | ICICI **239001515131** (statement `~/Documents/Exadatum/Bank/Abhijit-Statement_MAR2026_497218556.pdf (SECURED).pdf`, FY 25-26, 32 pages). Used to cross-verify all company→Abhijit transfers (INFT refs match 1:1) |
| Abhijit personal credit card | ICICI Visa **4315-XXXX-XXXX-5004**. Consolidated FY25-26 statement: `~/Documents/Exadatum/Bank/Credit Card Statemenmts/FY2025-261784960343700.pdf`. Company expenses charged here were reimbursed via lump-sum transfers (see §5) |
| Office | Office 308, 3rd floor, Crystal Fortune, Keshavnagar (landlord: Crystal Properties — MAHB0000750) |

### Key folders (all under `/Users/admin/Documents/Exadatum/Bank/`)

| Path | Contents |
|---|---|
| `FY-25-26/` | Main records folder (invoices, challans, salary slips, rent receipts). Subfolders: `Amazon/`, `Flipkart/`, `Gmail/` (Google Workspace invoices), `PBC Anthropic/` (Claude invoices+receipts), `Office Rent/`, `FD ICICI/`, `PF PT ESIC Return/`, `Bank Statements/`, `late TDS challans raised by Amedeo (PT Tenant)/`, `ITR_Statement_UPDY3185 2/` (personal ITR bundle — not company) |
| `TDS-FY-25-26/` | All TDS-on-rent challans (TaxPayer counterfoils + `TDS Challan/` receipts). **CIN numbers verified against every bank debit** |
| `Missing Invoices/` | Invoices recovered during this reconciliation (~25 files, all individually verified against exact charge amounts) |
| `Credit Card Statemenmts/` | Card 5004 FY25-26 consolidated statement |
| `CA-payment-invoice-mapping-FY25-26.csv` | **AUTHORITATIVE master mapping** — every company bank debit → invoice file + status (full copy embedded in §3 below) |
| `MISSING-INVOICES-to-collect.md` | Live hunting list with per-card-cycle itemisation (sections A–F) |
| `reconciliation-FY25-26.md` | Narrative reconciliation. **Partially stale** — early sections were superseded as invoices were found; trust the CSV over it |

---

## 2. Headline results

- All **299 statement transactions** were classified. Every debit is mapped in §3.
- **~99.93% of debit value is documented.** Total still missing paperwork ≈ **₹5,400** (see §7) plus one internal MOFSL payment slip.
- All statutory payments fully documented: 12 TDS-on-rent challans (CIN-verified), 5 EPF challans, PTEC, PTRC, property tax, IT.
- All Amazon/Flipkart UPI payments reconcile **to the paisa** (methodology in §8 — critical for line-item entry in Tally).
- All 28 company→Abhijit transfers were verified against his personal statement with **identical INFT/UPI reference numbers** — no discrepancies.
- 4 lump-sum credit-card reimbursements fully itemised against the card statement (§5).

### ⚠ Findings that matter for Tally (read before checking)

1. **Abhijit's Aug-2025 salary (₹98,550) was NEVER PAID.** The voucher exists (`FY-25-26/98550 Abhijit S AUG 2025 Salary_01-09-2025.pdf`) but there is **no debit in the company account and no credit in his personal account** (verified both sides — salary credits jump from 01/08 to 03/10). If Tally has an Aug salary expense/payment entry for Abhijit, it is wrong or unpaid (should be payable or reversed).
2. **April-2025 salaries (₹98,550 ×2 paid 04/05/2025)** have no payslips — intentionally ignored per management. Payments are real (INFT 040145190101 / 040145192371).
3. **Mar-2025 salaries** paid 03/04/2025 were ₹56,883 each (prior-FY salary rate), not 98,550.
4. **Chairs:** Bhagyalaxmi Furniture bill #1234 dated 16/04/25 = ₹28,500 (10 "Sigma Net" chairs + metal rack). Bank paid ₹1,000 (16/04) + ₹24,650 (17/04) = 25,650. Balance **₹2,850 to be treated as DISCOUNT** (decision by Abhijit; no cash was paid).
5. **Painting job:** ONE bill (Shri Pawan Agency, dated 12-7-2025, "Office Painting ₹30,000", file `Missing Invoices/12-07-2025-office-painting-30000.png.pdf`) covers FOUR bank payments: 13/04 ₹3,500 + 30/04 ₹1,500 (cycle-wall cutting) + 06/07 ₹10,000 + 11/07 ₹15,000 = ₹30,000 exact.
6. **Office rent schedule (Crystal Properties)** — net-of-TDS amounts paid by bank: Apr ₹64,900 · May ₹64,900 · Jun ₹38,500 · Jul–Oct ₹49,500/mo · Nov–Mar ₹59,400/mo · PLUS one "difference amount Apr–Oct" payment ₹49,500 on 09/11/2025 (note: the voucher file is named `59500_Difference…` but the voucher inside says **₹49,500** — the filename is wrong). TDS on rent ₹5,500/month paid separately to govt (12 challans).
7. **DJI Drone 04/08/2025:** statement shows SIX debits + THREE credits that day. Three ₹1,01,500 debits were **failed/reversed same-day** (each has a matching RVSL credit). Net real payment = 41,500 + 50,000 + 51,500 = **₹1,43,000** = invoice `143000 DJIDrone 04August2025.pdf`. In Tally there should be ONE net ₹1,43,000 asset purchase (or the 3 legs), NOT ₹4,47,500.
8. **Credit-card reimbursements are approximations**, not paisa-exact: 1,86,000 paid vs 1,85,355.82 itemised (+644); 60,000 vs ~60,224 (−224); 23,233 vs Claude charge 23,778.71 (−545.71); 26,760 vs remaining cycle items ~27,707 (−947); 23,564 vs cycle items 28,308.69 (**under-reimbursed ~₹4,745**); 20,596 vs Claude charge 21,447.43 (−851). Net effect: Abhijit personally absorbed roughly ₹6–7k of company card spend. Tally should book what the company actually paid (the transfer amounts).
9. **Amazon 25-Dec-2025 card charge ₹699** — unclassified (company vs personal). Not in any reimbursement itemisation.
10. **Unreimbursed company-named card charges (never reimbursed, not in books?):** AWS monthly Apr–Nov 2025 on card 5004: 2,583.28 (04-Apr) · 1,165.14 (04-May) · 1,171.52 (04-Jun) · 1,169.11 (03-Jul) · 7,926.30 (03-Aug) · 1,206.98 (03-Sep) · 1,318.15 (04-Oct) · 1,317.11 (03-Nov) ≈ **₹17,858**; plus Google Workspace Apr-25 charge 3,122.28 (03-Apr). These are company-type expenses paid personally with NO reimbursement transfer found. Decide with CA whether to book as director-funded expense / reimburse.
11. **Google Workspace reimbursement 15/11/2025 ₹21,855** vs invoices on file total ₹22,835 (6×3,122 May–Oct + 4,103 Nov) — ₹980 short. Approximation; invoices all on file.
12. **Bhagyalaxmi furniture (Shubham/Ranjit):** invoice 87,430 (12-06) covers advance 25,000 (09/05) + final 62,000 (28/05) — ₹430 gap. Invoice 27,970 (10-10) covers 25,000 (24/09) + 2,970 (16/03). Invoice 6,090 (19-08) vs payment 6,000 (20/08) — ₹90 gap. Minor diffs, accepted.
13. **Carpet:** Classic Carpet invoice ₹9,504 vs paid 2,000+7,500 = 9,500 (₹4 gap, accepted).
14. **PTEC:** challan ₹2,500 vs bank debit ₹2,511.80 (₹11.80 portal fee).
15. **Salary payment dates drift**: Mar-26 salaries paid early on 24/03/2026; Sept-25 salaries paid 03/10; Oct-25 salaries paid 29/10; etc. Match by amount+narration, not month-end.

---

## 3. MASTER MAPPING — every company bank debit → invoice (AUTHORITATIVE)

Status legend: **MATCHED** = invoice verified · **PARTIAL** = partially documented · **MISSING** = no invoice · **IGNORED** = per management decision · **INTERNAL** = FD/investment transfer, not an expense.

All file paths relative to `/Users/admin/Documents/Exadatum/Bank/`. This is a verbatim copy of `CA-payment-invoice-mapping-FY25-26.csv` (state as of 26-Jul-2026):

```csv
Payment Date,Amount INR,Bank Narration / Payee,Invoice / Supporting Document (path relative to Bank folder),Status,Notes
03/04/2025,56883.00,Salary Mar-25 Abhijit,FY-25-26/56883_abhijit_mar_sal_03-04-2025.pdf,MATCHED,
03/04/2025,56883.00,Salary Mar-25 Rupali,FY-25-26/56883_rupali_mar_sal_03-04-2025.pdf,MATCHED,
07/04/2025,5000000.00,MOSL PMS2 50L investment,FY-25-26/MOSL PMS2 50L-SummaryUX307-04-2025.pdf,INTERNAL,Investment - payment summary on file
08/04/2025,2896.00,Amazon UPI,"FY-25-26/Amazon/2299 08April2025 invoice.pdf + Missing Invoices/amazon-8-apr-2025-597-invoice.pdf",MATCHED,2299+597=2896 exact; two orders clubbed
08/04/2025,8000.00,Vinayak Gadi sofa,FY-25-26/8000 Vinayak Sofa 08-04-2025.pdf,MATCHED,Payment slip: Sofa payment Vinayak Gadi-SummaryUX308-04-2025.pdf
13/04/2025,3500.00,Office painting advance (9096252962@ybl),Missing Invoices/12-07-2025-office-painting-30000.png.pdf,MATCHED,"Shri Pawan Agency bill 12-7-2025 Rs30000 = 3500+1500+10000+15000 (all four painting-job payments)"
14/04/2025,26694.00,Amazon UPI,"FY-25-26/Amazon/23499 14April2025 invoice refund.pdf + 1599 14April2025 invoice.pdf + 798 14April2025 invoice.pdf + 798 14April2025 invoice 2.pdf",MATCHED,23499+1599+798+798=26694 exact; 23499 refunded 21/04
15/04/2025,64900.00,Office rent April (Crystal),FY-25-26/Office Rent/64900_April_2025_OfficeRent.pdf,MATCHED,
16/04/2025,1000.00,Office chairs advance,FY-25-26/28500 Bhagyalaxmi 16-4-2025.pdf,MATCHED,Bill 1234: 10 Sigma chairs Rs28500; Rs1000 advance; Rs2850 discount
16/04/2025,5222.00,Amazon UPI,FY-25-26/Amazon/5222 16April2025 invoice.pdf,MATCHED,Refunded 21/04
17/04/2025,938.00,Amazon UPI,FY-25-26/Amazon/938 17April2025 invoice 2.pdf,MATCHED,
17/04/2025,24650.00,Office chairs part-payment (9623784845@okbi = Bhagyalaxmi Furniture phone),FY-25-26/28500 Bhagyalaxmi 16-4-2025.pdf,MATCHED,"Bill Rs28500; paid 1000 advance + 24650 = 25650 by bank; balance Rs2850 treated as discount"
21/04/2025,17071.03,Symphony air cooler,FY-25-26/17071 21April2025 SymphonyAirCooler Invoice_#104595-1.pdf,MATCHED,
21/04/2025,7999.00,Amazon UPI,FY-25-26/Amazon/7999 21April2025 invoice.pdf,MATCHED,
24/04/2025,1488.00,AMC MOFSL,FY-25-26/AMC MOSL for 2024-25 and 2025-26_24-04-2025.pdf,MATCHED,
27/04/2025,16998.00,Amazon UPI,FY-25-26/Amazon/16998 27Apr2025 invoice.pdf,MATCHED,Duplicate copy '16998 27April2025' can be deleted
28/04/2025,18998.00,Amazon UPI,"FY-25-26/Amazon/10999 28Apr2025 invoice.pdf + 7999 28Apr2025 invoice.pdf",MATCHED,10999+7999=18998; the 7999 refunded same day
30/04/2025,6500.00,Pegboards / MDF laser cutting,FY-25-26/6500 MDF Laser Cutting 30-4-2025.pdf,MATCHED,
30/04/2025,1500.00,Cycle wall cutting (part of painting job),Missing Invoices/12-07-2025-office-painting-30000.png.pdf,MATCHED,Covered by Pawan Agency Rs30000 bill
01/05/2025,5872.00,MDF peg boards,FY-25-26/5872 Bhagyalaxmi .jpeg,MATCHED,
04/05/2025,98550.00,Salary Apr-25 Abhijit,NONE,IGNORED,Per management: payslips not maintained monthly
04/05/2025,98550.00,Salary Apr-25 Rupali,NONE,IGNORED,Per management: payslips not maintained monthly
05/05/2025,770.91,Kraftix stickers,FY-25-26/771 _Kraftix Digital_2025-26_K_3526.pdf,MATCHED,
06/05/2025,64900.00,Office rent May (Crystal),FY-25-26/Office Rent/64900_May_2025_OfficeRent.pdf,MATCHED,
08/05/2025,6440.00,Glass shelf (Kawade),FY-25-26/6440 Kawade 26-03-2025.jpeg,MATCHED,Invoice dated 26-03 paid 08-05
08/05/2025,3525.00,Amazon UPI,FY-25-26/Amazon/3525 08May2025 invoice.pdf,MATCHED,Refunded 18/05
09/05/2025,2952.00,EPF Apr-25 (challan 3152505013170),FY-25-26/2952-EPF-Apr-25-_3152505013170_09052025.pdf,MATCHED,
09/05/2025,25000.00,Furniture advance (Bhagyalaxmi/Shubham),FY-25-26/87430 Bhagyalaxmi 12-06-2025.pdf,MATCHED,Invoice 87430 covers advance 25000 + final 62000 (Rs430 diff)
21/05/2025,36999.00,Amazon UPI,FY-25-26/Amazon/36999 21May2025 invoice.pdf,MATCHED,
21/05/2025,659.00,Amazon UPI,FY-25-26/Amazon/659 21May2025 invoice.pdf,MATCHED,
24/05/2025,345.00,Amazon UPI,FY-25-26/Amazon/345 24May2025 invoice.pdf,MATCHED,
26/05/2025,1849.00,Amazon UPI,FY-25-26/Amazon/1849 26May2025 invoice.pdf,MATCHED,
28/05/2025,62000.00,Office furniture final (Bhagyalaxmi/Shubham),FY-25-26/87430 Bhagyalaxmi 12-06-2025.pdf,MATCHED,See 09/05 row
01/06/2025,98550.00,Salary May-25 Abhijit,FY-25-26/98550_Abhijit S May 2025 Salary_01-06-2025.pdf,MATCHED,
01/06/2025,98550.00,Salary May-25 Rupali,FY-25-26/98550_Rupali S May 2025 Salary_01-06-2025.pdf,MATCHED,
01/06/2025,1788.00,ARTH Associates (APR certificate),FY-25-26/1788_ArthAssociates_01-06-2025.pdf,MATCHED,
01/06/2025,11800.00,ARTH Associates (TDS filing),FY-25-26/11800_ArthAssociates_01-06-2025.pdf,MATCHED,
07/06/2025,2511.80,PTEC FY25-26,FY-25-26/Exadatum-PTEC-Transaction-april-2025-to-mar-2026.pdf,MATCHED,Challan Rs2500 + portal fee Rs11.80
07/06/2025,2452.00,EPF Mar-25 wage month (TRRN 3152504006613),FY-25-26/2452-EPF-Mar2025_3152504006613_07062025.pdf,MATCHED,Payment Confirmation Receipt; A/c-1 1568 + A/c-10 834 + A/c-21 50
07/06/2025,2952.00,EPF May-25 (challan 3152506009486),FY-25-26/2952-EPF-May2025_3152506009486_07062025.pdf,MATCHED,
10/06/2025,38500.00,Office rent June (Crystal),FY-25-26/Office Rent/38500_June_2025_OfficeRent.pdf,MATCHED,
12/06/2025,14030.00,WOL3D filaments,FY-25-26/14030_Wol3D_invoice-6800_12Jun_2025.pdf,MATCHED,
14/06/2025,6000.00,RS Group PTEC return filing,FY-25-26/6000_TheRSGroup_PTEC_ReturnFiling_14-06-2025.pdf,MATCHED,
14/06/2025,5748.00,TDS on rent Apr-25 (CIN 25061400116702),TDS-FY-25-26/5748_APR RENT TDS PNEE04370C_...TaxPayer.pdf + TDS Challan/5748_OfficeRentTDS_Apr2025_ChallanReceipt.pdf,MATCHED,CIN verified vs bank
14/06/2025,5665.00,TDS on rent May-25 (CIN 25061400119489),TDS-FY-25-26/5665_MAY RENT TDS_...TaxPayer.pdf + ChallanReceipt,MATCHED,CIN verified
14/06/2025,5583.00,TDS on rent Jun-25 (CIN 25061400121967),TDS-FY-25-26/5583_JUNE RENT TDS_...TaxPayer.pdf + ChallanReceipt,MATCHED,CIN verified
14/06/2025,960.00,Paint for cycle wall,NONE,MISSING,
14/06/2025,12260.00,Plywood + Fevicol (Bhagyalaxmi),"FY-25-26/11260 Bhagyalaxmi 14-06-2025.pdf + 1000 Bhagyalaxmi 14-06-2025.pdf",MATCHED,11260+1000=12260 exact
14/06/2025,950.00,Water Jan-May (Akshara Enterprises; 19 bottles x Rs50),FY-25-26/400 Water Charges 31-5-2025.pdf (bill 197 Apr+May Rs400),PARTIAL,"Jan-Mar memo Rs550 missing; vendor 9545517101. Bills 250 (Rs300 June) and 353 (Rs100 July) on file were paid by CASH separately"
14/06/2025,40000.00,TDS refund to Amedeo Aragona (PT tenant),FY-25-26/late TDS challans raised by Amedeo (PT Tenant)/ (challans + workings xlsx),MATCHED,
17/06/2025,470.00,Office paint primer,FY-25-26/470 PavanElectricals 17-6-2025.pdf,MATCHED,
18/06/2025,1000.00,RS Group (late fee),FY-25-26/Rs. 1000 Late Fee Challan.pdf,MATCHED,Challan dated 18-06-2025
19/06/2025,1450.00,Cycle wall primer,FY-25-26/1450 PavanElectricals .pdf,MATCHED,
25/06/2025,5546.59,OnlyScrews,FY-25-26/OnlyScrews - Order #ONLSCR10007 confirmed.pdf,MATCHED,
25/06/2025,3894.00,Global Automate (angle brackets),FY-25-26/3894 Global Automate Solutions 25-6-2025.pdf,MATCHED,
25/06/2025,280.00,Porter for Global Automate order,NONE,MISSING,
25/06/2025,8410.10,Amazon UPI,FY-25-26/Amazon/8410 25June2025 invoice.pdf,MATCHED,
29/06/2025,2000.00,Office carpet advance,FY-25-26/9504 Classic Carpet.pdf,MATCHED,Invoice 9504 covers 2000+7500 (Rs4 diff)
30/06/2025,7500.00,Office carpet final,FY-25-26/9504 Classic Carpet.pdf,MATCHED,
01/07/2025,1995.00,Amazon UPI,FY-25-26/Amazon/1995 01July2025 invoice.pdf,MATCHED,Refunded 12/07
02/07/2025,28000.00,WOL3D filaments,FY-25-26/28000 WOL 3D 3-7-2025.pdf,MATCHED,Duplicate copy (1) can be deleted
02/07/2025,10691.00,Amazon UPI,"FY-25-26/Amazon/5090 02July2025 invoice.pdf + 5600 02July2025 invoice.pdf",MATCHED,5090.40+5600.60=10691 exact
03/07/2025,98550.00,Salary Jun-25 Abhijit,FY-25-26/98550_Abhijit S June 2025 Salary_03-07-2025.pdf,MATCHED,
03/07/2025,98550.00,Salary Jun-25 Rupali,FY-25-26/98550_Rupali S June 2025 Salary_03-07-2025.pdf,MATCHED,
06/07/2025,640.00,Paint external,FY-25-26/640 PavanElectricals .pdf,MATCHED,
06/07/2025,10000.00,Office ceiling paint (9096252962@ybl),Missing Invoices/12-07-2025-office-painting-30000.png.pdf,MATCHED,Covered by Pawan Agency Rs30000 bill
07/07/2025,5500.00,TDS on rent (CIN 25070700542310),TDS-FY-25-26/PNEE04370C_25070700542310ICIC_DTAX_07072025_TaxPayer.pdf + TDS Challan/5500_OfficeRentTDS_July2025_ChallanReceipt.pdf,MATCHED,CIN verified
09/07/2025,49500.00,Office rent July (Crystal),FY-25-26/49500_July_2025_OfficeRent_09-07-2025.pdf,MATCHED,
11/07/2025,15000.00,Paint final (9096252962@ybl),Missing Invoices/12-07-2025-office-painting-30000.png.pdf,MATCHED,Covered by Pawan Agency Rs30000 bill
12/07/2025,5475.00,Amazon UPI,FY-25-26/Amazon/5475 12July2025 invoice.pdf,MATCHED,
18/07/2025,5712.00,Glass shelf (Kawade),FY-25-26/5712 Kawade 16-07-2025.jpeg,MATCHED,
18/07/2025,8129.98,Amazon UPI,"FY-25-26/Amazon/2460 18July2025 invoice.pdf + 5670 18July2025 invoice.pdf",MATCHED,2461.42+5668.56=8129.98 exact
22/07/2025,6961.00,Amazon UPI,"FY-25-26/Amazon/1959 22July2025 invoice.pdf + 5001 22July2025 invoice.pdf",MATCHED,1959.40+5001.60=6961 exact
30/07/2025,4469.00,Flipkart (order OD435069837472873100),FY-25-26/Flipkart/4465_Flipkart_OD435069837472873100.pdf,MATCHED,4211+254 delivery+4 platform fee=4469 exact; refunded 04/08
01/08/2025,2952.00,EPF Jul-25 (challan 3152508000968),FY-25-26/2952-EPF-July2025_3152508000968_01082025.pdf,MATCHED,
01/08/2025,2952.00,EPF Jun-25 (challan 3152507001565),FY-25-26/2952-EPF-June2025_3152507001565_01082025.pdf,MATCHED,
01/08/2025,98550.00,Salary Jul-25 Abhijit,FY-25-26/98550 Abhijit S July 2025 Salary_01-08-2025.pdf,MATCHED,
01/08/2025,98550.00,Salary Jul-25 Rupali,FY-25-26/98550 Rupali S July 2025 Salary_01-08-2025.pdf,MATCHED,
01/08/2025,5500.00,TDS on rent (CIN 25080100240275),TDS-FY-25-26/5500_OfficeRentTDS_Aug2025_01082025_TaxPayer.pdf + ChallanReceipt,MATCHED,CIN verified
01/08/2025,49500.00,Office rent Aug (Crystal),FY-25-26/49500_Aug_2025_OfficeRent_01-08-2025.pdf,MATCHED,
04/08/2025,143000.00,DJI Drone (net of 3 reversed attempts of 101500),FY-25-26/143000 DJIDrone 04August2025.pdf,MATCHED,41500+50000+51500=143000
05/08/2025,4204.00,Amazon UPI,FY-25-26/Amazon/4204 05Aug2025 invoice.pdf,MATCHED,
20/08/2025,6000.00,Plywood top (Bhagyalaxmi/Shubham),FY-25-26/6090 Bhagyalaxmi 19-08-2025.pdf,MATCHED,Rs90 difference - review
21/08/2025,76460.00,Property tax balance E2903,FY-25-26/76460_PT_E2903_Property_Tax_Balance_21-08-2025.pdf,MATCHED,Receipt: E2903 PT Property Tax Receipt Sept 2025
31/08/2025,1403.00,Amazon UPI,FY-25-26/Amazon/1403 31Aug2025 invoice.pdf,MATCHED,
01/09/2025,2262.00,Logo paint,NONE,MISSING,
01/09/2025,98550.00,Salary Aug-25 Rupali,FY-25-26/98550 Rupali S Aug 2025 Salary_01-09-2025.pdf,MATCHED,NOTE: Abhijit Aug-25 salary voucher exists but was NEVER PAID (no bank debit; no personal credit)
01/09/2025,5500.00,TDS on rent (CIN 25090100306790),TDS-FY-25-26/5500_SEPTRentTDS_01092025_TaxPayer.pdf + ChallanReceipt,MATCHED,CIN verified
01/09/2025,49500.00,Office rent Sept (Crystal),FY-25-26/49500_Sept_2025_OfficeRent_01-09-2025.pdf,MATCHED,
07/09/2025,6732.00,Amazon UPI,"FY-25-26/Amazon/373 + 455 + 5903 07Sep2025 invoices",MATCHED,373.30+455.35+5903.35=6732 exact
08/09/2025,839.21,Amazon UPI,FY-25-26/Amazon/839.21 08Sep2025 invoice.pdf,MATCHED,
09/09/2025,1912.00,Flipkart (order OD435425514983728100),FY-25-26/Flipkart/941_Flipkart_OD435425514983728100.pdf (bundle: products 338+139+941 + delivery 368 + fees 12 = 1798),PARTIAL,~Rs114 item invoice missing; the 3 files are identical bundles - keep one; check Rs456 refund 18/09
16/09/2025,11745.00,Amazon UPI,"FY-25-26/Amazon/ 11 files dated 16Sep2025 + Downloads/16-09-2025/16-dec-invoice-10.pdf (899.40) + 16-dec-invoice-11.pdf (433.15)",MATCHED,Union = 11745.00 exact; move the 2 new files into Amazon folder
19/09/2025,1550.00,Robu (Macfos),FY-25-26/1550_ROBU.IN order# (3022198).png,MATCHED,
20/09/2025,691.02,Amazon UPI,"FY-25-26/Amazon/197 20Sep2025 invoice.pdf + 489 20Sep2025 invoice.pdf",MATCHED,198.45+492.57=691.02 exact
24/09/2025,25000.00,Office cabinets (Bhagyalaxmi/Shubham),FY-25-26/27970 Bhagyalaxmi 10-10-2025.pdf,MATCHED,Invoice 27970 = 25000 (24/09) + 2970 (16/03)
28/09/2025,18879.00,Udyami import-export (paytm-44808797),Missing Invoices/udyami-6886650-Tax.pdf (invoice GME/25-26/4460),MATCHED,"Train The Eximprenuers Nov-2025; 15999.15 + GST = 18879.00 exact"
30/09/2025,5753.99,Amazon UPI,"FY-25-26/Amazon/ 4 files dated 30Sep2025 + Downloads/30-09-2025/30-dec-2025-invoice-1..4.pdf",MATCHED,Union = 5753.99 exact; move the 4 new files into Amazon folder
01/10/2025,1695.71,Amazon UPI,FY-25-26/Amazon/1695.71 01Oct2025 invoice.pdf,MATCHED,
03/10/2025,98550.00,Salary Sep-25 Abhijit,FY-25-26/98550_Abhijit S Sept 2025 Salary_03-10-2025.pdf,MATCHED,
03/10/2025,98550.00,Salary Sep-25 Rupali,FY-25-26/98550_Rupali S Sept 2025 Salary_03-10-2025.pdf,MATCHED,
04/10/2025,11203.06,Amazon UPI,"FY-25-26/Amazon/2909 04Oct2025 invoice.pdf + 2909.03 04Oct2025 invoice.pdf + 5380 04Oct2025 invoice.pdf",MATCHED,2909.03+2909.03 (two shipments same order)+5380+5 shipping = 11203.06 exact
05/10/2025,24835.00,Voltera reimbursement,FY-25-26/24835_Voltera_Invoice-VOLT-11256.pdf,MATCHED,
05/10/2025,5849.00,Parallels reimbursement,FY-25-26/5849_Parallels_AKD-736121562097.pdf,MATCHED,Card charge 20-Sep 5849.35
07/10/2025,5500.00,TDS on rent (CIN 25100700848739),TDS-FY-25-26/5500_OCTRentTDS_07102025_TaxPayer.pdf + ChallanReceipt,MATCHED,CIN verified
10/10/2025,49500.00,Office rent Oct (Crystal),FY-25-26/49500_Oct_2025_OfficeRent_10-10-2025.pdf,MATCHED,
12/10/2025,2611.23,Amazon UPI,"FY-25-26/Amazon/1936.48 12Oct2025 invoice.pdf + 669.75 12Oct2025 invoice.pdf",MATCHED,1940.18+671.05=2611.23 exact
13/10/2025,147500.00,ARTH statutory audit FY24-25,FY-25-26/147500 ARTH 371 Exadatum Statutory audit for FY 2024-25.pdf,MATCHED,
14/10/2025,20596.00,Anthropic Claude reimbursement,FY-25-26/PBC Anthropic/Receipt-2624-2633-2403.pdf (S$300 10-Oct = Rs21447.43 on card),MATCHED,Approximate reimbursement of card charge
14/10/2025,35190.00,CrystalTech aluminium advance,FY-25-26/35190_CrystalTech_Advance_14-10-2025.pdf,MATCHED,Proforma on file: Quotation_Proforma_551 (08-Oct-2025)
18/10/2025,1214.00,Amazon UPI,FY-25-26/Amazon/1214 18Oct2025 invoice.pdf,MATCHED,
29/10/2025,40000.00,CrystalTech aluminium final,FY-25-26/40000_CrystalTech_Final_29-10-2025.pdf,MATCHED,
29/10/2025,98550.00,Salary Oct-25 Abhijit,FY-25-26/98550_Abhijit S Oct 2025 Salary_29-10-2025.pdf,MATCHED,
29/10/2025,98550.00,Salary Oct-25 Rupali,FY-25-26/98550_Rupali S Oct 2025 Salary_29-10-2025.pdf,MATCHED,
04/11/2025,10000.00,Office help salary Jul-Oct (via Rupali),FY-25-26/OfficeHelp Salary July2025_Oct2025_04-11-2025.pdf,MATCHED,
04/11/2025,5500.00,TDS on rent (CIN 25110400311942),TDS-FY-25-26/5500_NOVRentTDS_04112025_TaxPayer.pdf + ChallanReceipt,MATCHED,CIN verified
05/11/2025,10620.00,Udyami training,FY-25-26/10620_Udyami_7150449-Tax.pdf,MATCHED,
05/11/2025,28997.35,Agoda,FY-25-26/28997_Agoda_Receipt.pdf,MATCHED,Partial refund 14498.76 credited 27/01
09/11/2025,49500.00,Office rent difference Apr-Oct (Crystal),"FY-25-26/59500_Difference_Amt_OfficeRent_JuntoOct2025_09-11-2025.pdf + Office Rent/Diffrence_APR2025 _TO_OCT2025.pdf",MATCHED,Voucher inside is Rs49500 (filename misleading)
09/11/2025,59400.00,Office rent Nov (Crystal),FY-25-26/59400_Nov_2025_OfficeRent_09-11-2025.pdf,MATCHED,
15/11/2025,21855.00,Google Workspace reimbursement May-Nov,"FY-25-26/Gmail/3122_May..Oct2025 (6 files) + 4103_Nov2025",PARTIAL,Invoices total 22835 vs paid 21855 (Rs980 diff) - review
15/11/2025,2901.00,N8N reimbursement,FY-25-26/2901_N8N Receipt.html,MATCHED,
15/11/2025,2715.00,Claude reimbursement,FY-25-26/PBC Anthropic/Receipt-2891-4032-3386.pdf (S$39.69 02-Nov = Rs2778.99 on card),MATCHED,Approximate
15/11/2025,7999.00,Coursera reimbursement,FY-25-26/7999_Coursera-Receipt_Order #431049140.pdf,MATCHED,Card charge 06-Nov 7999
23/11/2025,1100.00,Udyami Oyo dinner,NONE,MISSING,
02/12/2025,5500.00,TDS on rent (CIN 25120200229102),TDS-FY-25-26/5500_DECRentTDS_02122025_TaxPayer.pdf + ChallanReceipt,MATCHED,CIN verified
11/12/2025,59400.00,Office rent Dec (Crystal),FY-25-26/59400_Dec_2025_OfficeRent_11-12-2025.jpeg,MATCHED,
11/12/2025,150.00,Water Oct-25 (Akshara; 3 bottles x Rs50),NONE,MISSING,Ask Akshara (9545517101) for duplicate Oct memo
28/12/2025,186000.00,Credit card reimbursement (card 4315-XX-5004 cycle 13Nov-12Dec),"Credit Card Statemenmts/FY2025-261784960343700.pdf; invoices: Udyami PMP 128616 = FY-25-26/Udyami_7288187-Tax.pdf; Workspace 4103.57 = Gmail/4103_Nov2025; Claude 21453.01 = PBC Anthropic receipt 03-Dec; Envato 16012.21 = Missing Invoices/26-11-2025-envato-invoice-16012.pdf; Udemy 6000 = Missing Invoices/04-12-2025-udemy-invoice-6000.pdf; N8N 2998.52 = Missing Invoices/26-11-2025-N8N-invoice.pdf; AWS 2909.32 = Missing Invoices/01-12-2025-aws-2909.pdf; OpenAI 2176.00 = Invoice-HU3SOMCQ-0001.pdf ($23.60); OpenAI 1087.19 = Invoice-THQMME5Q-0001.pdf ($11.80 Rupali acct)",MATCHED,"All 9 card charges documented. Card items total 185355.82 vs 186000 (+644 rounding)"
28/12/2025,15886.00,TipTop hotel reimbursement,FY-25-26/15886 TipTop 28 Dec 2025.pdf,MATCHED,Card charge 18-Dec 15886.50
29/12/2025,98550.00,Salary Dec-25 Abhijit,FY-25-26/98550_Abhijit S Dec 2025 Salary_29-12-2025.pdf,MATCHED,
29/12/2025,98550.00,Salary Dec-25 Rupali,FY-25-26/98550_Rupali S Dec 2025 Salary_29-12-2025.pdf,MATCHED,
29/12/2025,2000000.00,Transfer to FD 239010020578,FD advices in FY-25-26/FD ICICI/,INTERNAL,
05/01/2026,5500.00,TDS on rent (CIN 26010500077219),TDS-FY-25-26/5500_JANRentTDS_05012026_TaxPayer.pdf + ChallanReceipt,MATCHED,CIN verified
05/01/2026,59400.00,Office rent Jan (Crystal),FY-25-26/59400_Jan_2026_OfficeRent_05-01-2026.pdf,MATCHED,
14/01/2026,29500.00,Dipti Thete retainership,FY-25-26/29500_Dipti Thete Retainership Fees FY202526_14-01-2026.pdf,MATCHED,Also 29500_EXADATUM_Dipti_Fees.pdf
14/01/2026,400.00,ROC fee AOC-4 (via Dipti),FY-25-26/400_Fee for AOC-4_14-01-2026.pdf,MATCHED,Reimb voucher: 900_EXADATUM_ROC_Dipti_Reembursement_Voucher.pdf
14/01/2026,400.00,ROC fee MGT-7A (via Dipti),FY-25-26/400_Fee for MGT-7A_14-01-2026.pdf,MATCHED,
14/01/2026,100.00,MacFOS data search (via Dipti),FY-25-26/100_MacFOS DataSearch_14-01-2026.pdf,MATCHED,
23/01/2026,60000.00,AI services reimbursement (card cycle 13Dec-12Jan),"Credit Card Statemenmts/FY2025-261784960343700.pdf; invoices: Claude 23468.40 = PBC Anthropic receipt 07-Jan; Workspace Dec 4460.40 = 31-12-2025-google-4460.pdf (inv 5450442578); AWS Dec 2859.17 = 01-01-2025-aws-2859.pdf; LinkedIn 24959.88 = Missing Invoices/01-08-2026-linkedin-24960.pdf; Cursor 1849.05 = Invoice-B74489BC-0003.pdf ($20); Runway 1636.40 = Invoice-B6HLEXJN-0001.pdf ($17.70); Runway 886.29 = Invoice-AK9D4RU4-0001.pdf ($9.44 DCC); Luma 462.26 = Invoice-VDNAMY8L-0001.pdf ($5)",PARTIAL,"MISSING invoices: AWS micro-charges ~858.82+52.29+52.96. Cycle company items ~60224 vs 60000"
30/01/2026,98550.00,Salary Jan-26 Abhijit,FY-25-26/98550_Abhijit S Jan 2026 Salary_30-01-2026.pdf,MATCHED,
30/01/2026,98550.00,Salary Jan-26 Rupali,FY-25-26/98550_Rupali S Jan 2026 Salary_30-01-2026.pdf,MATCHED,
05/02/2026,5500.00,TDS on rent (CIN 26020500329660),TDS-FY-25-26/5500_FEBRentTDS_05022026_TaxPayer.pdf + ChallanReceipt,MATCHED,CIN verified
05/02/2026,59400.00,Office rent Feb (Crystal),FY-25-26/59400_Feb_2026_OfficeRent_05-02-2026.pdf,MATCHED,
09/02/2026,4800000.00,Transfer to FD 239010020993,Closed 06/03 with interest back to account,INTERNAL,
19/02/2026,23233.00,Claude reimbursement (card),Credit Card Statemenmts/FY2025-261784960343700.pdf; Claude 23778.71 (07-Feb) = PBC Anthropic receipt 07-Feb S$324.77,MATCHED,Approximate (Rs545.71 under card charge)
01/03/2026,98550.00,Salary Feb-26 Abhijit,FY-25-26/98550_Abhijit S Feb 2026 Salary_01-03-2026.pdf,MATCHED,
01/03/2026,98550.00,Salary Feb-26 Rupali,FY-25-26/98550_Rupali S Feb 2026 Salary_01-03-2026.pdf,MATCHED,
05/03/2026,26760.00,CloudFlare + others reimbursement (card cycle 13Jan-12Feb),"Credit Card Statemenmts/FY2025-261784960343700.pdf; invoices: CloudFlare 15362.45 = FY-25-26/CloudFlare.pdf; Claude 23778.71 covered by 19/02 reimb; Workspace Jan 4460.40 = 31-01-2026-google-4460.pdf.pdf (inv 5473695035); AWS Jan 3359.80 = Missing Invoices/01-02-2025-aws-3359.pdf; Cursor refund -1327.28 = Refund-3177-7909.pdf (-$15.05); Cursor Pro Plus 5582.08 = Invoice-B74489BC-0004.pdf ($60)",PARTIAL,"MISSING invoices: AWS 269.52. Cycle company items ~51486; 26760+23233 covers ~49993"
06/03/2026,5500.00,TDS on rent Mar (CIN 26030600003183),"TDS-FY-25-26/5500_MARRentTDS_06032026_TaxPayer.pdf + ChallanReceipt + FY-25-26/5500_TDSonRent_09-03-2026.pdf",MATCHED,CIN verified
06/03/2026,59400.00,Office rent Mar (Crystal),FY-25-26/59400_Mar_2026_OfficeRent_06-03-2026.pdf,MATCHED,
07/03/2026,1500000.00,MOFSL investment 1st tranche,FY-25-26/MOFSL 15 lakhs 07-03-2026.pdf,INTERNAL,
07/03/2026,3658.00,Global (wheels),FY-25-26/3658_Global_07-03-2026.pdf,MATCHED,
09/03/2026,1500000.00,MOFSL investment 2nd tranche,NONE,MISSING,Payment slip not on file (1st and 3rd are)
10/03/2026,2000.00,Ceiling fans advance,FY-25-26/27200_Fan_10-03-2026.pdf,MATCHED,Invoice 27200 = 2000+25200
12/03/2026,1500000.00,MOFSL investment 3rd tranche,FY-25-26/MOFSL 15 lakhs investment 3rd 12-03-2026.pdf,INTERNAL,
13/03/2026,25200.00,Ceiling fans final,FY-25-26/27200_Fan_10-03-2026.pdf,MATCHED,
13/03/2026,200.00,Porter,FY-25-26/200 Porter_invoice_CRN1528756086.pdf,MATCHED,
15/03/2026,9554.00,Voltera custom duty (FedEx),"FY-25-26/Voltera Custom Duty 5 March 2026.pdf (FedEx invoice BOM-C-283537) + 9554_Voltera _CustomeDuty_15-03-2026.pdf",MATCHED,
15/03/2026,7500.00,Office cleaning petty cash,FY-25-26/7500 Office Cleaning Petty Cash_15-03-2026.pdf,MATCHED,
16/03/2026,4500.00,Foam printing (1st),FY-25-26/9000_FoamSheetPrinting_.pdf,MATCHED,Invoice 9000 = 4500+4500
16/03/2026,2596.00,Global (slot gantry),FY-25-26/2596_Global_04-24-2026.pdf,MATCHED,
16/03/2026,9490.00,Bhagyalaxmi,FY-25-26/9490_Bhagyalakshmi_Sale_2025-26 165_16-03-2026.pdf,MATCHED,
16/03/2026,2970.00,Bhagyalaxmi balance of invoice 27970,FY-25-26/27970 Bhagyalaxmi 10-10-2025.pdf,MATCHED,
16/03/2026,264.00,Porter global,FY-25-26/264 porter global invoice 16-03-2026.pdf,MATCHED,
16/03/2026,4500.00,Foam sheet market (2nd),FY-25-26/9000_FoamSheetPrinting_.pdf,MATCHED,
24/03/2026,23564.00,Credit card reimbursement (card cycle 13Feb-12Mar),"Credit Card Statemenmts/FY2025-261784960343700.pdf; invoices: Claude 24118.01 = PBC Anthropic receipt 04-Mar; Anthropic 1643.76 = receipt 13-Feb; ElevenLabs 548.37 = Invoice-GQEK3KII-0001.pdf ($5.90)",PARTIAL,"MISSING invoices: Canva 511.75; Microsoft 1486.80. Cycle items 28308.69 vs 23564 reimbursed (underpaid ~4745)"
24/03/2026,98550.00,Salary Mar-26 Abhijit,FY-25-26/98550_Abhijit S Mar 2026 Salary_24-03-2026.pdf,MATCHED,
24/03/2026,98550.00,Salary Mar-26 Rupali,FY-25-26/98550_Rupali S Mar 2026 Salary_24-03-2026.pdf,MATCHED,
24/03/2026,4460.00,Google Workspace Mar,FY-25-26/4460_Gmail-March-Invoice-5529512535.pdf,MATCHED,Card charge 03-Mar 4460.40
24/03/2026,3778.00,AWS Mar,FY-25-26/3778_aws-march-invoice.pdf,MATCHED,Card charge 04-Mar 3778.73
24/03/2026,2503.00,AWS,FY-25-26/2503_aws-abshingate-exadatum-com-invoice.pdf,MATCHED,Card charge 03-Mar 2503.67
```

Note on the CSV: the 6 recovered Amazon invoices referenced as `Downloads/16-09-2025/…` and `Downloads/30-09-2025/…` may since have been moved into `FY-25-26/Amazon/` or `Missing Invoices/` — if a path 404s, search by amount in those folders (also as `Missing Invoices/amazon-16-dec-2025-899-invoice.pdf` and `amazon-16-dec-2025-433-invoice.pdf` for the 16-Sep pair).

---

## 4. CREDIT side of the company statement (income/receipts — needed for Tally income & investment ledgers)

No invoices are needed for credits; classify them as below. Complete inventory by category:

### 4.1 FD interest credits (monthly, ICICI FDs linked to this account)
- FD **XXX6059**: 8,080.00 (02/04) · 8,946.00 (02/05) · 3,327.00 (02/06, TDS 5,619 deducted this month) · 8,051.00 (02/07) · 8,051.00 (02/08) · 8,052.00 (02/09) · 8,052.00 (02/10) · 6,995.00 (02/11) · 6,995.00 (02/12) · 6,995.00 (02/01) · 6,995.00 (02/02) · 6,995.00 (02/03) — later months net of TDS ~777/mo
- FD **XXX7071**: 16,329.00 (03/04) · 18,016.00 (03/05) · 16,214.00 (03/06) · 16,214.00 (03/07) · 16,215.00 (03/08) · 16,214.00 (03/09) · 16,214.00 (03/10) · 16,215.00 (03/11) · 16,214.00 (03/12) · 16,214.00 (03/01) · 16,214.00 (03/02) — net of TDS ~1,801–1,802/mo
- FD **XXX7488**: 10,961.00 + 5,928.00 (28/04, two FDs 7488/7489) · 11,105.00 (28/05) · 9,995.00 (28/06) · 9,995.00 (28/07) · 9,994.00 (28/08) · 9,994.00 (28/09) · 9,994.00 (28/10) · 9,994.00 (28/11) · 9,995.00 (28/12) — net of TDS ~1,110–1,111 from Jun
- FD **XXX0578**: 4,204.00 (29/01, TDS 467)
- FD **XXX0993**: 6,657.00 (06/03, TDS 740)
- **TDS deducted by bank on FD interest** (for 26AS/Tally TDS receivable): visible in narrations — 5,619 (Jun on 6059), 1,802×8 (7071), 1,110/1,111×7 (7488), 895/894 (6059 Jul–Oct), 777×5 (6059 Nov–Mar), 467 (0578), 740 (0993)

### 4.2 FD principal closures (credits)
- 21/05/2025 — 9,92,825.00 — FD 239010017489 closure
- 08/10/2025 — 10,83,788.00 — FD 239013032735 closure
- 28/12/2025 — 20,00,000.00 — FD 239010017488 closure
- 29/01/2026 — 20,00,000.00 — FD 239010020578 closure (created 29/12/2025)
- 03/02/2026 — 30,00,000.00 — FD 239010017071 closure
- 06/03/2026 — 48,00,000.00 — FD 239010020993 closure (created 09/02/2026)

### 4.3 ICCL / Indian Clearing Corporation NEFT credits (investment payouts, ~75k roughly monthly)
50,05,262.09 (02/04, RTGS — large redemption) · 75,183.46 (02/07) · 75,067.45 (03/07) · 75,654.96 (01/08) · 75,013.30 (04/08) · 75,337.70 (01/09) · 75,034.04 (02/09) · 74,975.08 + 75,000.57 (01/10) · 75,070.53 + 75,001.15 (03/11) · 75,057.67 + 74,945.52 (03/12) · 75,166.54 + 75,010.18 (01/01) · 74,892.06 + 75,048.48 (02/02) · 75,018.49 + 75,612.06 (02/03)

### 4.4 Dividends / small ACH credits
ANGEL 871.20 (02/04) + 1,989.00 (16/06) · Bajaj Finance 248 (26/05) + 910 (25/07) · Archean CMS 769.50 (03/06) · PEL 1,108 + Polycab 976 (01/07) · Trent 531 + Emdura 502.75 (07/07) · PSL 418 (29/07) · AdityaBirla 104 (01/08) · Airtel 558 + AU Small 243 (11/08) · APAR 2,432 (13/08) · Premier Energies 50.62 (14/08) + 101.25 (20/09) · MHIL 167.40 (18/08) · BSE 1,366 + Hitachi 102 (22/08) · Interglobe 369 (01/09) · Prestige 271.40 + Kalyan 1,449 (22/09) · BEL 554.04 (23/09) + 1,075.81 (10/03) · Garden Reach 211.68 (24/09) · MCX 1,944 (25/09) · Global Health 116 (08/10) · GujaratFluoro 172 (10/10) · Bharat Dynamics 103.40 (21/10) + 546.50 (25/02) · PG Electroplast 64.25 (27/10) · Waaree 225 (06/11) · TD Power 322 (17/11) · Coforge 817 (18/11) + 817 (18/02) · CG Power 383.40 (13/02)

### 4.5 Refunds & reversals (should net against corresponding expenses)
- Amazon refunds: 3,199 (02/04) · 1,399 (04/04) · 23,499 + 5,102 (21/04) · 7,999 (28/04) · 10,999 (05/05) · 3,525 (18/05) · 1,995 (12/07) · 4,998 (02/08)
- Flipkart refunds: 4,465 (04/08 — reverses the 30/07 order) · 456 (18/09 — likely return on order OD435425514983728100)
- DJI drone reversals: 1,01,500 ×3 (04/08, RVSL, cancel the 3 failed debits)
- Agoda partial refund: 14,498.76 (27/01, against 28,997.35 paid 05/11)
- PayPal micro-credits: 1.19 + 1.01 (08/09, ref BDPPS9613GP)
- API/test credits: ₹1 ×3 (29/12 ×2, 04/02, 12/02) + ₹1 debit "Test /MOFSL" (06/03)
- **Income-tax refund: 6,64,670.00 (16/02/2026)** — "ITDTAX REFUND 2025-26 AAECE2023L" via SBIN
- Amedeo-related: ₹40,000 DEBIT on 14/06 was a TDS refund TO the tenant Amedeo Aragona (his challans ₹6,955 + ₹81,788 of 29-Apr-2025 are in the Amedeo folder with workings xlsx)

---

## 5. Credit-card 4315-XX-5004 — company-expense itemisation per reimbursement

The company reimbursed Abhijit's personal card via lump transfers. **Every transfer + card-bill payment was traced in his personal statement** (a/c 239001515131): reimbursement lands → `CC BillPay-5004` goes out same day.

| Reimbursement (company bank) | Card cycle | Card bill paid (personal acct) |
|---|---|---|
| 14/10/2025 ₹20,596 (AnthropicClaude) | 13-Sep→12-Oct | 22,765.58 on 14/10 |
| 28/12/2025 ₹1,86,000 (CreditCard) + ₹15,886 (TipTop) | 13-Nov→12-Dec | 2,03,777.24 on 28/12 |
| 23/01/2026 ₹60,000 (AIServices) | 13-Dec→12-Jan | 65,858.44 on 23/01 |
| 19/02/2026 ₹23,233 (Claude) + 05/03/2026 ₹26,760 (ClousFareAndThi) | 13-Jan→12-Feb | 58,590.49 on 01/03 |
| 24/03/2026 ₹23,564 | 13-Feb→12-Mar | 42,266.00 on 24/03 |

### 5.1 ₹1,86,000 (28/12) — COMPLETE, all 9 charges invoiced
| Card date | Vendor | ₹ | FX | Invoice |
|---|---|---|---|---|
| 24-Nov | Udyami PMP (charged as **MYSCOOT TECH Gurgaon**) | 1,28,616.00 | — | `FY-25-26/Udyami_7288187-Tax.pdf` (PMP invoice, Nov 24) |
| 26-Nov | Envato Elements annual (#19576388) | 16,012.21 | $175.23 | `Missing Invoices/26-11-2025-envato-invoice-16012.pdf` |
| 04-Dec | Udemy (IN2025-3151971) | 6,000.00 | — | `Missing Invoices/04-12-2025-udemy-invoice-6000.pdf` |
| 03-Dec | Google Workspace (Nov usage) | 4,103.57 | — | `FY-25-26/Gmail/4103_Nov2025_5426438002.pdf` |
| 26-Nov | N8N Cloud Starter | 2,998.52 | €28.32 | `Missing Invoices/26-11-2025-N8N-invoice.pdf` |
| 04-Dec | AWS Nov-25 (acct 335208753055, billed to Exadatum) | 2,909.32 | $32.56 | `Missing Invoices/01-12-2025-aws-2909.pdf` |
| 04-Dec | Claude.ai Max 20x | 21,453.01 | S$300.00 | `FY-25-26/PBC Anthropic/Receipt-2604-0253-1528.pdf` |
| 11-Dec | OpenAI (HU3SOMCQ-0001) | 2,176.00 | $23.60 | `Missing Invoices/11-12-2025-openai-Invoice-2176.pdf` |
| 03-Dec | OpenAI (THQMME5Q-0001, **Rupali's account**) | 1,087.19 | $11.80 | `Missing Invoices/03-12-2025-openai-Invoice-1087.pdf` |
| | **Total** | **1,85,355.82** | | vs 1,86,000 (+644.18 rounding) |

### 5.2 ₹60,000 "AIServices" (23/01) — cycle 13-Dec→12-Jan (~60,224 of company items)
Documented: Claude S$324.77 = 23,468.40 (07-Jan, `PBC Anthropic/Receipt-2131-6567-0707.pdf`) · LinkedIn Premium Business 24,959.88 (08-Jan, `Missing Invoices/01-08-2026-linkedin-24960.pdf`) · Cursor Pro $20 = 1,849.05 (12-Jan, `Invoice-B74489BC-0003.pdf`) · Runway Standard $17.70 = 1,636.40 (11-Jan, `Invoice-B6HLEXJN-0001.pdf` + receipt 2121-4385) · Runway credits $9.44 DCC = 886.29 (11-Jan, `Invoice-AK9D4RU4-0001.pdf` + receipt 2130-2097) · Luma $5 = 462.26 (11-Jan, `Invoice-VDNAMY8L-0001.pdf` + receipt 2913-2420) · Workspace Dec 4,460.40 (03-Jan, `Missing Invoices/31-12-2025-google-4460.pdf`, inv 5450442578) · AWS Dec 2,859.17 (04-Jan, `Missing Invoices/01-01-2025-aws-2859.pdf`).
**STILL MISSING:** AWS second-account small charges: 22-Dec micro-charges ×22 (44.49–49.12 each, net ~858.82) + 52.29 (24-Dec) + 52.96 (03-Jan). Also unclassified: Amazon ₹699 (25-Dec). TipTop 15,886.50 (18-Dec) also falls in this cycle but was reimbursed separately.

### 5.3 ₹23,233 (19/02) + ₹26,760 (05/03) — cycle 13-Jan→12-Feb (~51,486 of company items)
Documented: Claude S$324.77 = 23,778.71 (07-Feb, receipt on file; ↔ the 23,233 transfer) · CloudFlare $165.20 = 15,362.45 (07-Feb, `FY-25-26/CloudFlare.pdf` — 2-yr registration of **aaiga.ai** domain) · Cursor Pro Plus $60 = 5,582.08 (19-Jan, `Invoice-B74489BC-0004.pdf`) · Cursor refund −$15.05 = −1,327.28 (19-Jan, `Refund-3177-7909.pdf`) · Workspace Jan 4,460.40 (03-Feb, `31-01-2026-google-4460.pdf.pdf`, inv 5473695035) · AWS Jan 3,359.80 (03-Feb, `01-02-2025-aws-3359.pdf`).
**STILL MISSING:** AWS 269.52 (03-Feb, second account).

### 5.4 ₹23,564 (24/03) — cycle 13-Feb→12-Mar (28,308.69 of company items → under-reimbursed ~₹4,745)
Documented: Claude S$324.77 = 24,118.01 (05-Mar, receipt 04-Mar) · Anthropic extra usage $17.70 = 1,643.76 (13-Feb, receipt) · ElevenLabs $5.90 = 548.37 (18-Feb, `Invoice-GQEK3KII-0001.pdf`). The cycle's AWS 2,503.67 + 3,778.73 and Workspace 4,460.40 were reimbursed by three separate same-day exact transfers (2,503 / 3,778 / 4,460 on 24/03).
**STILL MISSING:** Microsoft India 1,486.80 (06-Mar) · Canva 500 + 11.75 DCC/GST (01-Mar).

### 5.5 Other card facts
- Voltera import: card charge 26-Sep $279.96 = 25,860.91 (incl. forex markup); company reimbursed ₹24,835 = invoice VOLT-11256 on 05/10.
- Parallels: card 20-Sep 5,849.35 (+DCC 58.49+10.52 GST); reimbursed ₹5,849 on 05/10.
- Coursera: card 06-Nov 7,999; reimbursed via UPI 15/11.
- Amazon retail on card 24-May 11,745.99 = the two orphan invoices `Amazon/10547 24May2025` + `1199 24May2025` (order 171-2637886-1641132 etc.) — card purchase, part of card bills, NOT a company-bank payment.
- Card also carries a personal EMI amortisation (~3,466–3,655/mo Apr–Aug, "<20/24>…<24/24>") and personal spends (Zomato, YouTube, Netflix-type) — NOT company.
- Canva 29-Mar 500 (+fees) falls in the NEXT cycle (13-Mar→12-Apr) — not reimbursed in FY25-26.

---

## 6. Personal-statement cross-verification (a/c 239001515131)

All 28 company→Abhijit transfers matched with identical refs. Sample refs for spot-checks (format: INFT ref / amount / date): 039817150881 / 56,883 / 03-04 · 040145190101 / 98,550 / 04-05 · 040444418051 / 98,550 / 01-06 · 040789781981 / 98,550 / 03-07 · 041109721241 / 98,550 / 01-08 · 041807947241 / 98,550 / 03-10 · 041832779461 / 24,835 Voltera · 041832788741 / 5,849 Parallels · 041953512071 / 20,596 AnthropicClaude · 042113646951 / 98,550 / 29-10 · 042482778451 / 98,550 / 01-12 · 042797551241 / 1,86,000 CreditCard · 042797564801 / 15,886 TipTop · 042801455021 / 98,550 / 29-12 · 043103977521 / 60,000 AIServices · 043172855671 / 98,550 / 30-01 · 043419940151 / 23,233 Claude · 043526168981 / 98,550 / 01-03 · 043572947401 / 26,760 ClousFareAndThi · 043802902121 / 23,564 · 043802930411 / 98,550 / 24-03 · 043802943121 / 4,460 Gmail · 043802998581 / 3,778 AWS · 043803289031 / 2,503 AWS. UPI reimbursements 15/11: Gmail 21,855 (ref 108577973656) · N8N 2,901 (108577995643) · Claude 2,715 (108577999687) · Coursera 7,999 (108578003936).

---

## 7. STILL MISSING (as of handoff) — total ≈ ₹5,400 + one internal slip

| Item | Amount (₹) | Detail / how to close |
|---|---|---|
| Microsoft India | 1,486.80 | Card 06-Mar-26. account.microsoft.com → Order history |
| AWS second account | 1,233.59 | 22-Dec micro ×22 (~858.82) + 52.29 + 52.96 + 269.52 — likely a second AWS org (check gmail/elxim.root/Rupali logins), Dec-25 & Jan-26 invoices |
| Udyami Oyo dinner | 1,100.00 | 23/11, gpay-1125950598 — likely petty/staff-welfare without invoice |
| Water memos (Akshara, 9545517101) | 550 + 150 | Jan–Mar-25 memo (11 bottles) + Oct-25 memo (3 bottles) — duplicates from vendor |
| Canva | 511.75 | Card 01-Mar-26 (500 + DCC/GST). canva.com → Billing → Invoices |
| Porter (Global Automate order) | 280.00 | 25/06 — petty transport, likely no invoice |
| Paint for cycle wall (paytmqr679rt9) | 960.00 | 14/06 — paint-material vendor, no bill (NOT part of the Pawan ₹30,000 bill) |
| Flipkart item invoice | ~114 | Order OD435425514983728100 (09-09) — one shipment's product invoice absent from bundle; check ₹456 refund 18/09 as possible return |
| Amazon 25-Dec card charge | 699.00 | Classify company vs personal |
| MOFSL 2nd tranche slip | (15,00,000 internal) | 09/03 payment slip — download from MOFSL; 1st (07/03) & 3rd (12/03) slips on file |

Also open decisions: Abhijit Aug-25 salary (pay or cancel voucher) · the ~₹18k of unreimbursed AWS Apr–Nov card charges (§2.10) · under-reimbursement ~₹4,745 on the 24/03 cycle.

---

## 8. Methodology & gotchas (IMPORTANT when re-verifying against Tally)

1. **Amazon clubbing:** one UPI debit = several orders. Match a bank debit to the **sum of invoice totals**, same-date (order date = payment date; invoices generate at shipping, same day or a few days later). Never match cross-month (Amazon UPI charges at order time).
2. **Use in-PDF totals, not filenames.** Filenames are rounded (e.g. file "197" = ₹198.45 inside; "5670" = ₹5,668.56). Each Amazon PDF contains a product invoice + an MKT-xxx shipping-fee invoice — sum all blocks. Exact examples that reconcile to ₹0.00: 08/04 = 2,299+597 · 14/04 = 23,499+1,599+798+798 · 28/04 = 10,999+7,999 · 02/07 = 5,090.40+5,600.60 · 18/07 = 2,461.42+5,668.56 · 22/07 = 1,959.40+5,001.60 · 07/09 = 373.30+455.35+5,903.35 · 16/09 = 11 invoices+899.40+433.15 = 11,745.00 · 20/09 = 198.45+492.57 · 30/09 = 2,801.04+435.90+252.07+327.30+1,937.68 = 5,753.99 · 04/10 = 2,909.03+2,909.03+5,380+5 (the two "2909" files are two shipments of ONE order 405-2581393-6845949) · 12/10 = 1,940.18+671.05.
3. **Flipkart:** one payment = one order incl. delivery ("GT Charges") + platform fees, all inside one multi-invoice bundle PDF. 30/07: 4,211+254+4 = 4,469. 09/09: bundle totals 1,798 vs paid 1,912 (~114 gap).
4. **Foreign-currency card charges:** match invoices on the **FX amount** (S$/$/€) printed in the card statement, never the INR (which includes bank markup). One exception: Runway credits $9.44 was merchant-DCC-converted to ₹886.29 (no FX shown on statement).
5. **Misleading filenames encountered (do not trust names):** `59500_Difference…` = voucher ₹49,500 · `Voltera Custom Duty 5 March 2026.pdf` = FedEx invoice 17-Nov-25 ₹9,554 · `5500_AUGRentTDS_07072025` = July challan (deleted as dup) · `01-01-2025-aws-2859.pdf` = 01-Jan-**2026** statement · `2596_Global_04-24-2026` = paid 16-03-2026 · `16-dec-invoice-*.pdf` / `30-dec-2025-invoice-*.pdf` = September invoices.
6. **TDS-on-rent challans:** verify by **CIN**, not filename. All 12 CINs listed in §3 rows.
7. **Duplicates were purged on 25-Jul-2026** (15 byte-identical files moved to macOS Trash), incl. `(1)` copies, fake "refund" re-downloads (`5222_Amazon_Refund…`, `7999 28Apr refund` were re-downloads of purchase invoices, NOT credit notes), and 2 of the 3 identical Flipkart bundles. A former duplicate folder `Bank/FY25-26` (≡ `TDS-FY-25-26`) was removed by the user.
8. **Invoices WITHOUT bank payments** (reverse gaps — don't expect these in the company bank ledger): Bhagyalaxmi 88,020 (21-04) & 15,812 (03-03, prior FY) · Kawade 3,375 / 2,250 / 2,438 (Jul–Aug) · MDF 16,500 (18-02, prior FY) · Amazon 10,547 + 1,199 (24-May, paid on card 5004) · Amazon 385 / 1,052 / 249 / 2,454 / 2,199 / 669.75 (04-Oct order 405-3043396) · Flipkart 1,291 (order OD435071810022586100, full value 1,519 — card/other) · Dipti invoice #266 ₹35,400 (23-03-2026, paid 18-04-2026 = FY 2026-27) · SureshS ₹36,000 TDS challan (CIN 26042500062390, 26-04-2025 — paid from some other account, in `TDS-FY-25-26/TDS Challan/`) · `BDPPS9613G_25090500321718ICIC_DTAX_05092025` challan (personal PAN, matches no company debit) · prior-FY salary slips 56,783 ×2 (02-03-2025).
9. **Cash-paid receipts on file** (petty cash, no bank debit): Akshara water 300 (Jun) + 100 (Jul). Office cleaning ₹7,500 (15/03) IS bank-paid.
10. **`reconciliation-FY25-26.md` is partially stale** (checkbox sections reflect 25-Jul mid-state). The CSV (§3) + `MISSING-INVOICES-to-collect.md` are current.

---

## 9. Quick Tally tie-out checklist suggested for the next session

1. Bank ledger (ICICI 1481) closing balance = **₹7,92,746.56**; totals per §1.
2. Salaries: 56,883×2 (Apr, for Mar-25) + 98,550×2 × 11 months (May-25…Mar-26 payment dates, **Aug-25 Abhijit absent**). Verify Tally's salary payable vs the never-paid Aug voucher.
3. Rent expense: gross ₹55,000/mo Apr–Oct (net 49,500 + TDS 5,500) rising to ₹66,000... — actually verify against vouchers: Apr/May paid 64,900, Jun 38,500, diff-voucher 49,500, Jul–Oct 49,500, Nov–Mar 59,400, + 12 TDS challans ₹5,500 (and 5,748/5,665/5,583 incl. interest for Apr–Jun paid late on 14/06). Landlord: Crystal Properties.
4. Fixed assets: DJI drone ₹1,43,000 (net!), Symphony cooler 17,071.03, furniture (Bhagyalaxmi 28,500 chairs w/ 2,850 discount + 87,430 + 27,970 + 12,260 + 6,090/6,000 + sofa 8,000 + carpet 9,504/9,500 + fans 27,200), aluminium partitions (CrystalTech 75,190 invoice = 35,190+40,000).
5. Investments: MOSL PMS 50L (07/04) + MOFSL 45L (3×15L Mar-26) + FD movements per §4.2 + TRF to FD 20L (29/12) & 48L (09/02).
6. Director reimbursements per §5 — book as expense heads (software subscriptions, training, etc.), not as director loans, with the noted approximation differences.
7. IT refund ₹6,64,670 (16/02) and FD-interest TDS per §4.1 → TDS receivable reconciliation.
8. GST input: most SaaS invoices carry 18% IGST under reverse-charge-style billing (OpenAI/Cloudflare/ElevenLabs bill IGST directly); domestic GST invoices: Udyami (CGST+SGST), Udemy (IGST 915.25), FedEx duty invoice, WOL3D, Robu, etc.
