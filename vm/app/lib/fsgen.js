// fsgen.js — Schedule III financial-statements generator.
//
// Takes a ledger-level trial balance (from the Tally gateway or a JSON fixture)
// plus a company config, and produces the complete annual financial statements:
// Balance Sheet, Statement of Profit & Loss, all notes, the Companies Act
// depreciation schedule, EPS, key ratios — as an exact-arithmetic model, a
// rendered HTML document, and a validation report.
//
// Sign convention for the TB input: debit balances positive, credit negative
// (Tally's native convention). All model arithmetic is in rupees to the paise;
// rounding to ₹'000 happens only at presentation, and the rounder reports any
// note whose printed lines no longer foot to its printed total.
//
// The model never invents a number: every value is either summed from mapped
// ledgers, computed from other lines, or supplied in the config (comparatives,
// shareholding, related-party amounts) — and validations cross-check the
// supplied ones against the books wherever the books can know better.

'use strict';

const EPS = 0.01; // paise tolerance for exact-arithmetic checks

// ---------------------------------------------------------------- utilities

function sum(arr) { return arr.reduce((a, b) => a + b, 0); }
function r0(x) { return Math.round(x); }
function rK(x) { return Math.round(x / 1000); } // rupees -> printed ₹'000

function fmtK(x) {
  // present a ₹'000 figure the way the statements do: rounded, thousands
  // separators (Indian grouping), dash for zero, parentheses not used (the
  // statements show negatives with a leading minus in P&L context).
  if (x === null || x === undefined) return '';
  if (x === 0) return '-';
  return inGroup(x);
}

function inGroup(n) {
  const neg = n < 0; let s = String(Math.abs(n));
  let last3 = s.slice(-3), rest = s.slice(0, -3);
  if (rest) last3 = ',' + last3;
  rest = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
  return (neg ? '(' : '') + rest + last3 + (neg ? ')' : '');
}

// one-decimal ₹'000 figure with Indian grouping (used where the statements
// show paise-bearing thousands, e.g. related-party amounts): 1192.2 → 1,192.2
function fmtK1(x) {
  if (x === 0) return '-';
  const neg = x < 0, a = Math.abs(x);
  const whole = Math.floor(a), dec = Math.round((a - whole) * 10);
  const w = dec === 10 ? whole + 1 : whole, d = dec === 10 ? 0 : dec;
  return (neg ? '(' : '') + inGroup(w) + '.' + d + (neg ? ')' : '');
}

// ---------------------------------------------------------------- TB input

// Parse the XML produced by a Tally gateway ledger collection with
// Name / OpeningBalance / ClosingBalance native methods.
function parseTallyLedgerXML(xml) {
  const ledgers = [];
  const blocks = xml.split(/<LEDGER[ >]/).slice(1);
  for (const b of blocks) {
    const name = (b.match(/NAME="([^"]*)"/) || b.match(/<NAME[^>]*>([^<]*)<\/NAME>/) || [])[1];
    const op = parseTallyAmount((b.match(/<OPENINGBALANCE[^>]*>([^<]*)</) || [])[1]);
    const cl = parseTallyAmount((b.match(/<CLOSINGBALANCE[^>]*>([^<]*)</) || [])[1]);
    if (name !== undefined) ledgers.push({ name: name.trim(), opening: op, closing: cl });
  }
  return { ledgers };
}

function parseTallyAmount(s) {
  if (!s) return 0;
  s = String(s).trim();
  // Tally exports credits as positive with trailing " Cr" in some formats,
  // or plain signed decimals. Handle both; our convention: Dr +, Cr −.
  const m = s.match(/^(-?[\d.]+)\s*(Dr|Cr)?$/i);
  if (!m) return 0;
  let v = parseFloat(m[1]);
  if (/cr/i.test(m[2] || '')) v = -Math.abs(v);
  return v;
}

// ---------------------------------------------------------------- model

function buildModel(tb, config) {
  const V = []; // validation findings: {level: 'error'|'warn'|'info', code, message}
  const push = (level, code, message) => V.push({ level, code, message });

  const ledgers = tb.ledgers.map(l => ({ ...l, name: l.name.trim() }));

  // V1 — TB integrity
  const opSum = sum(ledgers.map(l => l.opening));
  const clSum = sum(ledgers.map(l => l.closing));
  if (Math.abs(opSum) > EPS) push('error', 'TB_OPENING_UNBALANCED', `TB opening balances sum to ${opSum.toFixed(2)}, expected 0`);
  if (Math.abs(clSum) > EPS) push('error', 'TB_CLOSING_UNBALANCED', `TB closing balances sum to ${clSum.toFixed(2)}, expected 0`);

  // V2 — every ledger must be mapped
  const mapping = config.mapping;
  const byTag = {};      // tag -> {closing, opening, ledgers[]}
  for (const l of ledgers) {
    const tag = mapping[l.name];
    if (tag === undefined) {
      push('error', 'UNMAPPED_LEDGER', `Ledger "${l.name}" (closing ${l.closing.toFixed(2)}) has no mapping tag — classify it before generating`);
      continue;
    }
    const t = (byTag[tag] = byTag[tag] || { closing: 0, opening: 0, ledgers: [] });
    t.closing += l.closing; t.opening += l.opening; t.ledgers.push(l.name);
  }
  const ledgerByName = Object.fromEntries(ledgers.map(l => [l.name, l]));

  // tag accessor: sign=+1 sums debits as positive (assets/expenses);
  // sign=-1 flips (liabilities/income presented positive)
  const usedTags = new Set();
  function tag(tagName, sign = 1) {
    usedTags.add(tagName);
    const t = byTag[tagName];
    return t ? sign * t.closing : 0;
  }

  // -------- depreciation schedule (Companies Act) from asset blocks
  const dep = { blocks: [], totals: { grossOpen: 0, additions: 0, deductions: 0, grossClose: 0, accOpen: 0, forYear: 0, accClose: 0, netClose: 0, netOpen: 0 } };
  for (const b of config.assetBlocks) {
    const ls = b.ledgers.map(n => {
      const l = ledgerByName[n];
      if (!l) push('error', 'ASSET_LEDGER_MISSING', `Asset block "${b.label}": ledger "${n}" not found in TB`);
      return l || { opening: 0, closing: 0 };
    });
    const acc = ledgerByName[b.accDepLedger] || { opening: 0, closing: 0 };
    if (!ledgerByName[b.accDepLedger]) push('error', 'ACCDEP_LEDGER_MISSING', `Asset block "${b.label}": accumulated-depreciation ledger "${b.accDepLedger}" not found`);
    const grossOpen = sum(ls.map(l => l.opening));
    const grossClose = sum(ls.map(l => l.closing));
    const additions = sum(ls.map(l => Math.max(0, l.closing - l.opening)));
    const deductions = sum(ls.map(l => Math.max(0, l.opening - l.closing)));
    const accOpen = -acc.opening, accClose = -acc.closing; // acc-dep ledgers carry credit balances
    const forYear = accClose - accOpen;
    const blk = { label: b.label, grossOpen, additions, deductions, grossClose, accOpen, forYear, accClose, netClose: grossClose - accClose, netOpen: grossOpen - accOpen };
    dep.blocks.push(blk);
    for (const k of Object.keys(dep.totals)) dep.totals[k] += blk[k];
  }
  // V6a — depreciation expense ledger must equal schedule movement
  const depExpense = tag(config.depreciationExpenseTag, 1);
  if (Math.abs(depExpense - dep.totals.forYear) > EPS)
    push('error', 'DEP_MISMATCH', `Depreciation expense ledger ${depExpense.toFixed(2)} ≠ accumulated-depreciation movement ${dep.totals.forYear.toFixed(2)}`);

  // -------- notes: line values from tags per the config note structure.
  // Two passes: first compute every line from its tags/fixed/carveout sources,
  // then apply cross-line deductions (a carve-out may live in a later note)
  // and only then foot the totals.
  const noteValues = {}; // key -> rupees value (presentation-positive)
  for (const note of config.notes) {
    for (const line of note.lines) {
      let v = 0;
      if (line.tags) v = sum(line.tags.map(t => tag(t, line.sign ?? 1)));
      if (line.fixed !== undefined) v = line.fixed;
      if (line.carveout) {
        // e.g. current portion of an investment held in a single ledger/tag
        v = line.carveout.amount;
        const src = tag(line.carveout.fromTag, 1);
        if (v - src > EPS) push('error', 'CARVEOUT_EXCEEDS', `Note ${note.no} "${line.label}": carve-out ${v} exceeds source balance ${src}`);
      }
      noteValues[line.key] = v;
    }
  }
  for (const note of config.notes) {
    let total = 0;
    for (const line of note.lines) {
      if (line.deduct) noteValues[line.key] -= sum(line.deduct.map(k => {
        if (noteValues[k] === undefined) push('error', 'DEDUCT_UNKNOWN_KEY', `Note ${note.no} "${line.label}": deduct key "${k}" not found`);
        return noteValues[k] ?? 0;
      }));
      total += noteValues[line.key];
    }
    noteValues[`note${note.no}Total`] = total;
  }

  // -------- P&L (rupees, exact)
  const pnl = {};
  pnl.revenue = noteValues.revenueOps ?? 0;
  pnl.otherIncome = noteValues.note19Total;
  pnl.totalRevenue = pnl.revenue + pnl.otherIncome;
  pnl.purchases = noteValues.note20Total;
  pnl.employee = noteValues.note21Total;
  pnl.finance = noteValues.note22Total;
  pnl.depreciation = dep.totals.forYear;
  pnl.otherExpenses = noteValues.note23Total;
  pnl.totalExpenses = pnl.purchases + pnl.employee + pnl.finance + pnl.depreciation + pnl.otherExpenses;
  pnl.pbt = pnl.totalRevenue - pnl.totalExpenses;
  pnl.tax = 0;
  pnl.pat = pnl.pbt - pnl.tax;
  pnl.priorPeriod = noteValues.note24Total ?? 0;
  pnl.patAfterPP = pnl.pat - pnl.priorPeriod;

  // V8 — PAT must equal the net of all P&L-mapped ledgers
  const plTags = new Set();
  for (const n of config.notes) if (n.pl) for (const li of n.lines) (li.tags || []).forEach(t => plTags.add(t));
  const plNet = -sum(ledgers.filter(l => plTags.has(mapping[l.name])).map(l => l.closing)) - dep.totals.forYear;
  if (Math.abs(plNet - pnl.patAfterPP) > EPS)
    push('error', 'PL_RECOMPUTE_MISMATCH', `P&L recompute ${plNet.toFixed(2)} ≠ statement PAT ${pnl.patAfterPP.toFixed(2)}`);

  // -------- reserves roll-forward
  const resLedger = ledgerByName[config.reservesLedger];
  const openingReservesTB = resLedger ? -resLedger.opening : 0;
  const res = { opening: openingReservesTB, movement: pnl.patAfterPP, closing: openingReservesTB + pnl.patAfterPP };
  // V7 — continuity against prior-year signed FS
  if (config.priorFS && config.priorFS.closingReserves !== undefined) {
    const drift = openingReservesTB - config.priorFS.closingReserves;
    if (Math.abs(drift) > EPS)
      push('warn', 'RESERVES_OPENING_DRIFT', `TB opening reserves ${openingReservesTB.toFixed(2)} differ from prior signed FS ${config.priorFS.closingReserves.toFixed(2)} by ${drift.toFixed(2)}`);
  }
  // If the books already carry a P&L-transfer journal, reserves ledger closing
  // will differ from opening; cross-check it against our computed closing.
  if (resLedger && Math.abs(resLedger.opening - resLedger.closing) > EPS) {
    const bookClosing = -resLedger.closing;
    if (Math.abs(bookClosing - res.closing) > EPS)
      push('error', 'RESERVES_TRANSFER_MISMATCH', `Books carry a P&L transfer making reserves ${bookClosing.toFixed(2)}, but computed closing is ${res.closing.toFixed(2)}`);
  }

  // -------- share capital
  const sc = config.shareCapital;
  const scLedger = tag(config.shareCapitalTag, -1);
  const scStated = sc.issuedShares * sc.faceValue;
  if (Math.abs(scLedger - scStated) > EPS)
    push('error', 'SHARE_CAPITAL_MISMATCH', `Share-capital ledger ${scLedger.toFixed(2)} ≠ issued ${sc.issuedShares} × ₹${sc.faceValue}`);
  const shSum = sum(sc.shareholders.map(s => s.shares));
  if (shSum !== sc.issuedShares)
    push('error', 'SHAREHOLDING_MISMATCH', `Shareholders' shares total ${shSum} ≠ issued ${sc.issuedShares}`);

  // -------- balance sheet (rupees, exact)
  const bs = {};
  bs.shareCapital = scStated;
  bs.reserves = res.closing;
  bs.shareholdersFunds = bs.shareCapital + bs.reserves;
  bs.nonCurrentLiab = 0;
  bs.tradePayables = noteValues.note6Total;
  bs.otherCurrentLiab = noteValues.note7Total;
  bs.shortTermProvisions = noteValues.note8Total;
  bs.currentLiab = (noteValues.shortTermBorrowings ?? 0) + bs.tradePayables + bs.otherCurrentLiab + bs.shortTermProvisions;
  bs.totalEquityLiab = bs.shareholdersFunds + bs.nonCurrentLiab + bs.currentLiab;
  bs.ppe = dep.totals.netClose;
  bs.nonCurrentInvestments = noteValues.note9Total;
  bs.longTermLoansAdv = noteValues.note11Total;
  bs.otherNonCurrentAssets = noteValues.note12Total;
  bs.nonCurrentAssets = bs.ppe + bs.nonCurrentInvestments + (noteValues.note10Total ?? 0) + bs.longTermLoansAdv + bs.otherNonCurrentAssets;
  bs.currentInvestments = noteValues.note13Total;
  bs.tradeReceivables = noteValues.note14Total;
  bs.cashAndBank = noteValues.note15Total;
  bs.shortTermLoansAdv = noteValues.note16Total;
  bs.otherCurrentAssets = noteValues.note17Total;
  bs.currentAssets = bs.currentInvestments + bs.tradeReceivables + bs.cashAndBank + bs.shortTermLoansAdv + bs.otherCurrentAssets;
  bs.totalAssets = bs.nonCurrentAssets + bs.currentAssets;

  // V4 — the balance sheet must balance to the paise
  if (Math.abs(bs.totalAssets - bs.totalEquityLiab) > EPS)
    push('error', 'BS_UNBALANCED', `Assets ${bs.totalAssets.toFixed(2)} ≠ Equity+Liabilities ${bs.totalEquityLiab.toFixed(2)} (diff ${(bs.totalAssets - bs.totalEquityLiab).toFixed(2)})`);

  // V6b — PPE net equals BS line (by construction, but assert the block math)
  if (Math.abs(dep.totals.grossClose - dep.totals.accClose - bs.ppe) > EPS)
    push('error', 'DEP_NET_MISMATCH', 'Depreciation schedule net block does not tie to BS PPE');

  // -------- related parties
  const rpt = { transactions: [], totals: { cur: 0, prev: 0, recv: 0, pay: 0 } };
  for (const t of config.relatedParties.transactions) {
    const recv = t.receivableTag ? tag(t.receivableTag, 1) : 0;
    rpt.transactions.push({ ...t, receivable: recv });
    rpt.totals.cur += t.amount; rpt.totals.prev += t.prevAmount ?? 0; rpt.totals.recv += recv;
  }
  // V9 — RPT remuneration must reconcile with the salary ledger
  if (config.relatedParties.validateAgainstTag) {
    const bookSalary = tag(config.relatedParties.validateAgainstTag, 1);
    const diff = bookSalary - rpt.totals.cur - (config.relatedParties.nonRelatedPortion ?? 0);
    if (Math.abs(diff) > EPS)
      push('error', 'RPT_SALARY_MISMATCH', `Related-party remuneration ${rpt.totals.cur.toFixed(2)} + non-related ${(config.relatedParties.nonRelatedPortion ?? 0).toFixed(2)} ≠ salary ledger ${bookSalary.toFixed(2)}`);
  }

  // -------- EPS
  const eps = { pat: pnl.patAfterPP, shares: sc.issuedShares, basic: pnl.patAfterPP / sc.issuedShares };

  // -------- ratios (current year; comparatives from config)
  const ratios = {
    current: bs.currentLiab ? bs.currentAssets / bs.currentLiab : null,
    roe: bs.shareholdersFunds ? (pnl.patAfterPP / bs.shareholdersFunds) * 100 : null,
    roce: bs.shareholdersFunds ? (pnl.pbt / bs.shareholdersFunds) * 100 : null,
  };

  // V3 — every mapped tag must be consumed by the note structure (or listed as known)
  const structural = new Set([config.shareCapitalTag, config.reservesLedgerTag, config.depreciationExpenseTag, 'Fixed Assets']);
  for (const t of Object.keys(byTag)) {
    if (!usedTags.has(t) && !structural.has(t) && Math.abs(byTag[t].closing) > EPS)
      push('error', 'UNUSED_TAG', `Tag "${t}" (balance ${byTag[t].closing.toFixed(2)}) is not consumed by any statement line`);
  }

  return { config, ledgers, byTag, noteValues, dep, pnl, bs, res, rpt, eps, ratios, validations: V };
}

// ------------------------------------------------------- presentation pass

// Round everything to ₹'000 and check that each note's printed lines still
// foot to the printed total; report divergences as info findings (they are a
// property of rounding, not of the books — but readers notice them).
function presentModel(m) {
  const P = { notes: {}, footingNotes: [] };
  for (const note of m.config.notes) {
    const lines = note.lines.map(li => ({ label: li.label, k: rK(m.noteValues[li.key]) , key: li.key }));
    const total = rK(m.noteValues[`note${note.no}Total`]);
    const foot = sum(lines.map(l => l.k));
    if (foot !== total) P.footingNotes.push(`Note ${note.no} (${note.title}): printed lines foot to ${foot} but printed total is ${total} (₹'000 rounding artefact)`);
    P.notes[note.no] = { lines, total };
  }
  P.bs = Object.fromEntries(Object.entries(m.bs).map(([k, v]) => [k, rK(v)]));
  P.pnl = Object.fromEntries(Object.entries(m.pnl).map(([k, v]) => [k, rK(v)]));
  P.dep = {
    blocks: m.dep.blocks.map(b => Object.fromEntries(Object.entries(b).map(([k, v]) => [k, typeof v === 'number' ? rK(v) : v]))),
    totals: Object.fromEntries(Object.entries(m.dep.totals).map(([k, v]) => [k, rK(v)])),
  };
  P.res = { opening: rK(m.res.opening), movement: rK(m.res.movement), closing: rK(m.res.closing) };
  P.eps = { basic: Math.round(m.eps.basic * 100) / 100 };
  P.ratios = Object.fromEntries(Object.entries(m.ratios).map(([k, v]) => [k, v === null ? null : Math.round(v * 100) / 100]));
  P.rpt = {
    transactions: m.rpt.transactions.map(t => ({ ...t, amountK: rK(t.amount), prevK: rK(t.prevAmount ?? 0), receivableK: rK(t.receivable) })),
    totals: { cur: rK(m.rpt.totals.cur), prev: rK(m.rpt.totals.prev), recv: rK(m.rpt.totals.recv) },
  };
  return P;
}

// ---------------------------------------------------------------- HTML

function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }

function renderHTML(m, P) {
  const c = m.config, co = c.company, st = c.statement, sg = c.signing;
  const comp = c.comparatives; // printed ₹'000 values from the prior signed FS
  const h = [];
  const th2 = `<th class="r">${esc(st.asAt)}<br>Amount (₹' 000)</th><th class="r">${esc(st.prevAsAt)}<br>Amount (₹' 000)</th>`;
  const row = (label, note, cur, prev, cls = '') =>
    `<tr class="${cls}"><td>${label}</td><td class="c">${note ?? ''}</td><td class="r">${fmtK(cur)}</td><td class="r">${prev === undefined ? '' : fmtK(prev)}</td></tr>`;

  h.push(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${esc(co.name)} — Financial Statements ${esc(st.fyLabel)}</title><style>
  @page { size: A4; margin: 15mm 16mm; }
  body { font-family: "Times New Roman", Georgia, serif; font-size: 10pt; color:#111; margin:0; }
  h1 { font-size: 11pt; margin: 0; } h2 { font-size: 10.5pt; margin: 0 0 2mm; }
  .hdr { font-weight: bold; margin-bottom: 3mm; }
  table { border-collapse: collapse; width: 100%; margin: 2mm 0 4mm; }
  th, td { border: .5pt solid #444; padding: 1mm 2mm; vertical-align: top; }
  th { background: #f0f0f0; } td.r, th.r { text-align: right; white-space: nowrap; } td.c { text-align: center; }
  tr.tot td { font-weight: bold; border-top: 1pt solid #000; }
  tr.sec td { font-weight: bold; border: none; padding-top: 2mm; }
  .page { page-break-after: always; } .note-title { font-weight: bold; margin: 3mm 0 1mm; }
  .fine { font-size: 8.5pt; } .sig { margin-top: 10mm; width: 100%; } .sig td { border: none; }
  </style></head><body>`);

  // ---- Balance Sheet
  h.push(`<div class="page"><div class="hdr">${esc(co.name)}<br>Balance Sheet as at ${esc(st.asAt)}</div>
  <table><tr><th>Particulars</th><th class="c">Note</th>${th2}</tr>
  <tr class="sec"><td colspan="4">Equity and liabilities</td></tr>
  <tr class="sec"><td colspan="4">Shareholders' funds</td></tr>
  ${row('&nbsp;&nbsp;Share capital', 3, P.bs.shareCapital, comp.bs.shareCapital)}
  ${row('&nbsp;&nbsp;Reserves and surplus', 4, P.bs.reserves, comp.bs.reserves)}
  ${row('', '', P.bs.shareholdersFunds, comp.bs.shareholdersFunds, 'tot')}
  ${row('Non current liabilities (deferred tax, borrowings, provisions)', 5, 0, 0)}
  ${row('Trade payables', 6, P.bs.tradePayables, comp.bs.tradePayables ?? 0)}
  ${row('Other current liabilities', 7, P.bs.otherCurrentLiab, comp.bs.otherCurrentLiab)}
  ${row('Short-term provisions', 8, P.bs.shortTermProvisions, comp.bs.shortTermProvisions)}
  ${row('', '', P.bs.currentLiab, comp.bs.currentLiab, 'tot')}
  ${row('<b>Total</b>', '', P.bs.totalEquityLiab, comp.bs.total, 'tot')}
  <tr class="sec"><td colspan="4">Assets — Non-current</td></tr>
  ${row('&nbsp;&nbsp;Property, plant and equipment', 26, P.bs.ppe, comp.bs.ppe)}
  ${row('&nbsp;&nbsp;Investments', 9, P.bs.nonCurrentInvestments, comp.bs.nonCurrentInvestments)}
  ${row('&nbsp;&nbsp;Long-term loans & advances', 11, P.bs.longTermLoansAdv, comp.bs.longTermLoansAdv)}
  ${row('&nbsp;&nbsp;Other non-current assets', 12, P.bs.otherNonCurrentAssets, comp.bs.otherNonCurrentAssets)}
  ${row('', '', P.bs.nonCurrentAssets, comp.bs.nonCurrentAssets, 'tot')}
  <tr class="sec"><td colspan="4">Current assets</td></tr>
  ${row('&nbsp;&nbsp;Current investments', 13, P.bs.currentInvestments, comp.bs.currentInvestments ?? 0)}
  ${row('&nbsp;&nbsp;Trade receivables', 14, P.bs.tradeReceivables, comp.bs.tradeReceivables ?? 0)}
  ${row('&nbsp;&nbsp;Cash and bank balance', 15, P.bs.cashAndBank, comp.bs.cashAndBank)}
  ${row('&nbsp;&nbsp;Short-term loans & advances', 16, P.bs.shortTermLoansAdv, comp.bs.shortTermLoansAdv)}
  ${row('&nbsp;&nbsp;Other current assets', 17, P.bs.otherCurrentAssets, comp.bs.otherCurrentAssets)}
  ${row('', '', P.bs.currentAssets, comp.bs.currentAssets, 'tot')}
  ${row('<b>Total</b>', '', P.bs.totalAssets, comp.bs.total, 'tot')}
  </table>${signBlock(sg, co)}</div>`);

  // ---- P&L
  h.push(`<div class="page"><div class="hdr">${esc(co.name)}<br>Statement of Profit and Loss for the year ended ${esc(st.asAt)}</div>
  <table><tr><th>Particulars</th><th class="c">Note</th>${th2}</tr>
  ${row('Revenue from operations', 18, P.pnl.revenue, comp.pnl.revenue)}
  ${row('Other income', 19, P.pnl.otherIncome, comp.pnl.otherIncome)}
  ${row('<b>Total Revenue</b>', '', P.pnl.totalRevenue, comp.pnl.totalRevenue, 'tot')}
  ${row('Purchase', 20, P.pnl.purchases, comp.pnl.purchases)}
  ${row('Employee benefit expense', 21, P.pnl.employee, comp.pnl.employee)}
  ${row('Finance costs', 22, P.pnl.finance, comp.pnl.finance)}
  ${row('Depreciation and amortization expense', 26, P.pnl.depreciation, comp.pnl.depreciation)}
  ${row('Other expenses', 23, P.pnl.otherExpenses, comp.pnl.otherExpenses)}
  ${row('<b>Total expenses</b>', '', P.pnl.totalExpenses, comp.pnl.totalExpenses, 'tot')}
  ${row('<b>(Loss)/Profit before tax</b>', '', P.pnl.pbt, comp.pnl.pbt, 'tot')}
  ${row('Tax expense', '', 0, 0)}
  ${row('<b>(Loss)/Profit after tax for the year</b>', '', P.pnl.pat, comp.pnl.pat, 'tot')}
  ${row('Prior period expenses', 24, P.pnl.priorPeriod, comp.pnl.priorPeriod)}
  ${row('<b>(Loss)/Profit after prior period expenses</b>', '', P.pnl.patAfterPP, comp.pnl.patAfterPP, 'tot')}
  ${row('(Loss)/Profit per equity share — basic & diluted (₹)', 28, null, undefined)}
  <tr><td></td><td></td><td class="r"><b>${P.eps.basic.toFixed(2)}</b></td><td class="r"><b>${(comp.eps ?? 0).toFixed(2)}</b></td></tr>
  </table>${signBlock(sg, co)}</div>`);

  // ---- boilerplate notes 1–2
  h.push(`<div class="page"><div class="hdr">${esc(co.name)}<br>Notes forming part of Financial Statements as on ${esc(st.asAt)}</div>`);
  for (const b of c.boilerplate.front) h.push(`<div class="note-title">${esc(b.title)}</div><div class="fine">${b.html}</div>`);
  h.push(`</div>`);

  // ---- numeric notes
  h.push(`<div class="page"><div class="hdr">${esc(co.name)}<br>Notes forming part of Financial Statements as on ${esc(st.asAt)}</div>`);
  // Note 3 — share capital
  const sc = c.shareCapital;
  h.push(`<div class="note-title">Note 3 — Share Capital</div>
  <table><tr><th></th><th class="r">No. of shares</th><th class="r">Amount (₹' 000)</th></tr>
  <tr><td>Authorised — Equity shares of ₹${sc.faceValue} each</td><td class="r">${inGroup(sc.authorizedShares)}</td><td class="r">${fmtK(rK(sc.authorizedShares * sc.faceValue))}</td></tr>
  <tr><td>Issued, subscribed and fully paid up</td><td class="r">${inGroup(sc.issuedShares)}</td><td class="r">${fmtK(rK(sc.issuedShares * sc.faceValue))}</td></tr></table>
  <table><tr><th>Shareholder (>5% and others listed)</th><th class="r">Shares</th><th class="r">%</th></tr>
  ${sc.shareholders.map(s => `<tr><td>${esc(s.name)}</td><td class="r">${inGroup(s.shares)}</td><td class="r">${(s.shares / sc.issuedShares * 100).toFixed(0)}%</td></tr>`).join('')}
  <tr class="tot"><td>Total</td><td class="r">${inGroup(sc.issuedShares)}</td><td class="r">100%</td></tr></table>`);
  // Note 4 — reserves
  h.push(`<div class="note-title">Note 4 — Reserves & Surplus</div>
  <table><tr><th></th>${th2}</tr>
  ${row('Balance as per prior year financial statements', '', P.res.opening, comp.reserves.opening)}
  ${row('(Loss)/Profit for the year', '', P.res.movement, comp.reserves.movement)}
  ${row('Net surplus/(deficit) in the statement of profit and loss', '', P.res.closing, comp.reserves.closing, 'tot')}</table>`);
  // Notes from structure
  for (const note of c.notes) {
    if (note.hidden) continue;
    const pn = P.notes[note.no];
    h.push(`<div class="note-title">Note ${note.no} — ${esc(note.title)}</div><table><tr><th></th>${th2}</tr>
    ${note.lines.map((li, i) => row(esc(li.label), '', pn.lines[i].k, comp.notes?.[li.key])).join('')}
    ${row(note.totalLabel || 'Total', '', pn.total, comp.notes?.[`note${note.no}Total`], 'tot')}</table>`);
  }
  h.push(`</div>`);

  // ---- Note 26 dep schedule
  h.push(`<div class="page"><div class="hdr">${esc(co.name)} — Note 26: Property, plant and equipment (₹' 000)</div>
  <table><tr><th>Description</th><th class="r">Gross as at ${esc(st.prevAsAt)}</th><th class="r">Additions</th><th class="r">Deductions</th><th class="r">Gross as at ${esc(st.asAt)}</th>
  <th class="r">Acc. dep. opening</th><th class="r">For the year</th><th class="r">Acc. dep. closing</th><th class="r">Net ${esc(st.asAt)}</th><th class="r">Net ${esc(st.prevAsAt)}</th></tr>
  ${P.dep.blocks.map(b => `<tr><td>${esc(b.label)}</td><td class="r">${fmtK(b.grossOpen)}</td><td class="r">${fmtK(b.additions)}</td><td class="r">${fmtK(b.deductions)}</td><td class="r">${fmtK(b.grossClose)}</td><td class="r">${fmtK(b.accOpen)}</td><td class="r">${fmtK(b.forYear)}</td><td class="r">${fmtK(b.accClose)}</td><td class="r">${fmtK(b.netClose)}</td><td class="r">${fmtK(b.netOpen)}</td></tr>`).join('')}
  <tr class="tot"><td>Total</td><td class="r">${fmtK(P.dep.totals.grossOpen)}</td><td class="r">${fmtK(P.dep.totals.additions)}</td><td class="r">${fmtK(P.dep.totals.deductions)}</td><td class="r">${fmtK(P.dep.totals.grossClose)}</td><td class="r">${fmtK(P.dep.totals.accOpen)}</td><td class="r">${fmtK(P.dep.totals.forYear)}</td><td class="r">${fmtK(P.dep.totals.accClose)}</td><td class="r">${fmtK(P.dep.totals.netClose)}</td><td class="r">${fmtK(P.dep.totals.netOpen)}</td></tr></table></div>`);

  // ---- Note 27–28: related party, EPS; 33 ratios; closing boilerplate
  h.push(`<div class="page"><div class="hdr">${esc(co.name)} — Notes (continued)</div>
  <div class="note-title">Note 27 — Related Party Transactions (AS-18)</div>
  <div class="fine">Key Management Personnel: ${c.relatedParties.kmp.map(esc).join('; ')}.<br>
  Relatives of KMP: ${c.relatedParties.relatives.map(esc).join('; ')}.</div>
  <table><tr><th>Particulars</th><th class="r">During ${esc(st.fyLabel)} (₹' 000)</th><th class="r">During prior year (₹' 000)</th><th class="r">Receivable as on ${esc(st.asAt)} (₹' 000)</th></tr>
  ${P.rpt.transactions.map(t => `<tr><td>${esc(t.label)}</td><td class="r">${fmtK1(t.amount / 1000)}</td><td class="r">${fmtK(t.prevK)}</td><td class="r">${fmtK1(t.receivable / 1000)}</td></tr>`).join('')}
  <tr class="tot"><td>Total</td><td class="r">${fmtK1(m.rpt.totals.cur / 1000)}</td><td class="r">${fmtK(P.rpt.totals.prev)}</td><td class="r">${fmtK1(m.rpt.totals.recv / 1000)}</td></tr></table>
  <div class="fine">${c.relatedParties.noteHtml || ''}</div>
  <div class="note-title">Note 28 — Earnings per share (AS-20)</div>
  <table><tr><th></th><th class="r">${esc(st.fyLabel)}</th><th class="r">Prior year</th></tr>
  ${row('Net (loss)/profit after tax (₹\' 000)', '', P.pnl.patAfterPP, comp.pnl.patAfterPP)}
  <tr><td>Weighted average number of equity shares</td><td></td><td class="r">${inGroup(sc.issuedShares)}</td><td class="r">${inGroup(sc.issuedShares)}</td></tr>
  <tr class="tot"><td>Basic (loss)/profit per share (₹)</td><td></td><td class="r">${P.eps.basic.toFixed(2)}</td><td class="r">${(comp.eps ?? 0).toFixed(2)}</td></tr></table>
  <div class="note-title">Note 33 — Key Ratios</div>
  <table><tr><th>Ratio</th><th class="r">${esc(st.asAt)}</th><th class="r">${esc(st.prevAsAt)}</th></tr>
  <tr><td>Current ratio</td><td class="r">${P.ratios.current ?? 'N.A.'}</td><td class="r">${comp.ratios?.current ?? 'N.A.'}</td></tr>
  <tr><td>Return on equity (%)</td><td class="r">${P.ratios.roe ?? 'N.A.'}</td><td class="r">${comp.ratios?.roe ?? 'N.A.'}</td></tr>
  <tr><td>Return on capital employed (%)</td><td class="r">${P.ratios.roce ?? 'N.A.'}</td><td class="r">${comp.ratios?.roce ?? 'N.A.'}</td></tr></table>`);
  for (const b of c.boilerplate.back) h.push(`<div class="note-title">${esc(b.title)}</div><div class="fine">${b.html}</div>`);
  h.push(signBlock(sg, co));
  h.push(`</div></body></html>`);
  return h.join('\n');
}

function signBlock(sg, co) {
  return `<table class="sig"><tr>
  <td><b>For ${esc(sg.auditor.firm)}</b><br>Chartered Accountants<br>Firm Registration Number: ${esc(sg.auditor.frn)}<br><br><br>${esc(sg.auditor.partner)}<br>Partner<br>Membership No.: ${esc(sg.auditor.membershipNo)}<br><br>Place: ${esc(sg.place)}<br>Date: ${esc(sg.date)}</td>
  <td>For and on behalf of the Board of Directors of<br><b>${esc(co.name)}</b><br><br><br>${sg.directors.map(d => `${esc(d.name)}<br>Director — DIN: ${esc(d.din)}`).join('<br><br>')}<br><br>Place: ${esc(sg.place)}<br>Date: ${esc(sg.date)}</td></tr></table>`;
}

// ---------------------------------------------------------------- CLI

function generate(tb, config) {
  const model = buildModel(tb, config);
  const errors = model.validations.filter(v => v.level === 'error');
  const presented = presentModel(model);
  const html = errors.length ? null : renderHTML(model, presented);
  return { model, presented, html };
}

if (require.main === module) {
  const fs = require('fs'), path = require('path');
  const args = Object.fromEntries(process.argv.slice(2).map((a, i, arr) => a.startsWith('--') ? [a.slice(2), arr[i + 1]] : []).filter(x => x.length));
  if (!args.tb || !args.config) {
    console.error('usage: node fsgen.js --tb tb.json --config config.json [--out dir]');
    process.exit(2);
  }
  const tb = JSON.parse(fs.readFileSync(args.tb, 'utf8'));
  const config = JSON.parse(fs.readFileSync(args.config, 'utf8'));
  const { model, presented, html } = generate(tb, config);
  const out = args.out || '.';
  fs.mkdirSync(out, { recursive: true });
  fs.writeFileSync(path.join(out, 'fs-model.json'), JSON.stringify({ presented, validations: model.validations }, null, 1));
  if (html) fs.writeFileSync(path.join(out, 'financial-statements.html'), html);
  for (const v of model.validations) console.log(`[${v.level.toUpperCase()}] ${v.code}: ${v.message}`);
  for (const f of presented.footingNotes) console.log(`[ROUNDING] ${f}`);
  const errs = model.validations.filter(v => v.level === 'error').length;
  console.log(errs ? `\n${errs} error(s) — statements NOT generated` : `\nOK — statements generated in ${out}`);
  process.exit(errs ? 1 : 0);
}

module.exports = { parseTallyLedgerXML, buildModel, presentModel, renderHTML, generate };
