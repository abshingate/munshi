// Bank reconciliation engine.
// Design (see ADR-0016 and ARCHITECTURE.md): statement parsing is code-first
// (CSV) with LLM extraction as fallback for PDFs/images — but every parse is
// validated deterministically (dates, amounts, balance continuity), and
// MATCHING IS PURE CODE. The LLM never decides that two things matched.
"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const DATA_DIR = process.env.TALLY_AI_DATA || "C:\\TallyAI\\data";
const RECON_DIR = path.join(DATA_DIR, "recon");
fs.mkdirSync(RECON_DIR, { recursive: true });

// ---------- CSV parsing (code-first) ----------------------------------------
function csvRows(text) {
  const rows = [];
  let row = [], cell = "", inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') inQ = false;
      else cell += c;
    } else if (c === '"') inQ = true;
    else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n" || c === "\r") {
      if (cell !== "" || row.length) { row.push(cell); rows.push(row); row = []; cell = ""; }
      if (c === "\r" && text[i + 1] === "\n") i++;
    } else cell += c;
  }
  if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

const MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
function parseDate(s) {
  s = String(s || "").trim();
  let m;
  if ((m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/))) return `${m[1]}${m[2].padStart(2, "0")}${m[3].padStart(2, "0")}`;
  if ((m = s.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})/))) return `${m[3]}${m[2].padStart(2, "0")}${m[1].padStart(2, "0")}`;
  if ((m = s.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{2})$/))) return `20${m[3]}${m[2].padStart(2, "0")}${m[1].padStart(2, "0")}`;
  if ((m = s.match(/^(\d{1,2})[ -]([A-Za-z]{3})[a-z]*[ -](\d{4})/))) {
    const mo = MONTHS[m[2].toLowerCase().slice(0, 3)];
    if (mo) return `${m[3]}${String(mo).padStart(2, "0")}${m[1].padStart(2, "0")}`;
  }
  return null;
}
function parseAmount(s) {
  const n = Number(String(s || "").replace(/[₹,\s]/g, "").replace(/^\((.*)\)$/, "-$1"));
  return isNaN(n) ? null : n;
}

// Detect columns from a header row and extract normalized lines.
// Returns null when the CSV doesn't look like a bank statement (LLM fallback).
function parseCsvStatement(text) {
  const rows = csvRows(text);
  let headerIdx = -1, cols = null;
  for (let i = 0; i < Math.min(rows.length, 25); i++) {
    const low = rows[i].map((c) => c.toLowerCase());
    const date = low.findIndex((c) => /date/.test(c));
    if (date === -1) continue;
    const debit = low.findIndex((c) => /(debit|withdraw)/.test(c));
    const credit = low.findIndex((c) => /(credit|deposit)/.test(c));
    const amount = low.findIndex((c) => /^amount|transaction amount/.test(c));
    const desc = low.findIndex((c) => /(narrat|descri|particular|remark|detail)/.test(c));
    const bal = low.findIndex((c) => /balance/.test(c));
    if ((debit !== -1 && credit !== -1) || amount !== -1) {
      headerIdx = i;
      cols = { date, debit, credit, amount, desc, bal };
      break;
    }
  }
  if (headerIdx === -1) return null;

  const lines = [];
  for (const r of rows.slice(headerIdx + 1)) {
    const date = parseDate(r[cols.date]);
    if (!date) continue;
    let amount = null, direction = null;
    if (cols.debit !== -1 && cols.credit !== -1) {
      const d = parseAmount(r[cols.debit]), c = parseAmount(r[cols.credit]);
      if (d) { amount = Math.abs(d); direction = "debit"; }
      else if (c) { amount = Math.abs(c); direction = "credit"; }
    } else if (cols.amount !== -1) {
      const a = parseAmount(r[cols.amount]);
      if (a !== null && a !== 0) { amount = Math.abs(a); direction = a < 0 ? "debit" : "credit"; }
    }
    if (amount === null) continue;
    lines.push({
      date, amount, direction,
      description: cols.desc !== -1 ? String(r[cols.desc] || "").trim() : "",
      balance: cols.bal !== -1 ? parseAmount(r[cols.bal]) : null,
    });
  }
  return lines.length ? lines : null;
}

// ---------- deterministic validation -----------------------------------------
// If balances are present, every row must satisfy prev ± amount = balance
// (tried in both sign orientations) — catches LLM extraction errors cold.
function validateLines(lines) {
  const warnings = [];
  if (!Array.isArray(lines) || lines.length === 0) return { ok: false, warnings: ["No transactions found"] };
  for (const l of lines) {
    if (!/^\d{8}$/.test(l.date || "")) warnings.push(`Bad date: ${JSON.stringify(l.date)}`);
    if (!(l.amount > 0)) warnings.push(`Bad amount on ${l.date}: ${l.amount}`);
    if (l.direction !== "debit" && l.direction !== "credit") warnings.push(`Bad direction on ${l.date}`);
  }
  const withBal = lines.filter((l) => typeof l.balance === "number");
  let balanceChecked = false;
  if (withBal.length >= Math.max(3, lines.length * 0.8)) {
    let okCount = 0;
    for (let i = 1; i < withBal.length; i++) {
      const prev = withBal[i - 1], cur = withBal[i];
      const delta = cur.direction === "credit" ? cur.amount : -cur.amount;
      if (Math.abs(prev.balance + delta - cur.balance) < 0.05) okCount++;
    }
    balanceChecked = true;
    const ratio = okCount / (withBal.length - 1);
    if (ratio < 0.9) warnings.push(`Balance continuity check failed for ${(100 - ratio * 100).toFixed(0)}% of rows — extraction may be wrong; review carefully.`);
  }
  return { ok: warnings.length === 0, warnings, balanceChecked, count: lines.length };
}

// ---------- LLM extraction (PDF / image / unrecognized CSV) ------------------
const EXTRACT_SYS = `You extract bank statement transactions. Output ONLY a JSON object, no prose, of the shape:
{"lines":[{"date":"YYYYMMDD","description":"...","amount":123.45,"direction":"debit","balance":6789.01}]}
Rules: amount is always positive; direction is "debit" when money LEFT the account (withdrawal) and "credit" when money CAME IN (deposit); balance is the running balance after the transaction, or null if the statement has none; include every transaction row, skip headers/totals.`;

async function llmExtract(provider, file) {
  const blocks = [];
  if (file.text) blocks.push({ type: "text", text: `Statement content:\n${file.text.slice(0, 150000)}` });
  else if (file.media_type === "application/pdf") blocks.push({ type: "document", source: { type: "base64", media_type: "application/pdf", data: file.data } });
  else blocks.push({ type: "image", source: { type: "base64", media_type: file.media_type, data: file.data } });
  blocks.push({ type: "text", text: "Extract all transactions as specified." });
  const r = await provider.chat({
    system: [{ type: "text", text: EXTRACT_SYS }],
    messages: [{ role: "user", content: blocks }],
    tools: [],
    maxTokens: 32000,
  });
  const text = r.content.filter((b) => b.type === "text").map((b) => b.text).join("");
  const start = text.indexOf("{"), end = text.lastIndexOf("}");
  if (start === -1 || end === -1) throw new Error("Could not read the statement — is it a bank statement?");
  return JSON.parse(text.slice(start, end + 1)).lines || [];
}

// ---------- matching (pure code) ---------------------------------------------
// Statement "credit" (money in) matches a voucher where the bank ledger is
// DEBITED (Tally exports debits as negative amounts).
function dayDiff(a, b) {
  const d = (x) => new Date(`${x.slice(0, 4)}-${x.slice(4, 6)}-${x.slice(6, 8)}`);
  return Math.abs((d(a) - d(b)) / 86400000);
}
function refsOf(s) {
  return (String(s || "").match(/\d{4,}/g) || []).filter((r) => r.length >= 4);
}

function matchLines(lines, vouchers, bankLedger) {
  const bank = [];
  vouchers.forEach((v, i) => {
    const be = (v.ledgerEntries || []).find((e) => e.ledger.toLowerCase() === bankLedger.toLowerCase());
    if (!be) return;
    const amt = parseAmount(be.amount);
    if (amt === null || amt === 0) return;
    bank.push({
      id: `v${i}`, voucher: v, amount: Math.abs(amt),
      moneyIn: amt < 0, // Tally: bank ledger debited (negative export) = deposit
      refs: refsOf(`${v.narration} ${v.number} ${v.party}`),
    });
  });
  const stmt = lines.map((l, i) => ({ id: `s${i}`, line: l, amount: l.amount, moneyIn: l.direction === "credit", refs: refsOf(l.description) }));

  const usedS = new Set(), usedV = new Set(), matched = [];
  const tryPass = (maxDays, needRef) => {
    for (const s of stmt) {
      if (usedS.has(s.id)) continue;
      const cands = bank.filter((b) =>
        !usedV.has(b.id) && b.moneyIn === s.moneyIn &&
        Math.abs(b.amount - s.amount) < 0.01 &&
        dayDiff(b.voucher.date, s.line.date) <= maxDays &&
        (!needRef || s.refs.some((r) => b.refs.includes(r)))
      );
      if (cands.length === 1) {
        usedS.add(s.id); usedV.add(cands[0].id);
        matched.push({
          stmt: s.line, voucher: cands[0].voucher,
          reason: needRef ? "amount + reference number" : `amount + date within ${maxDays} day(s)`,
          confidence: needRef || maxDays <= 3 ? "high" : "medium",
        });
      }
    }
  };
  tryPass(0, true);   // same day + matching reference
  tryPass(15, true);  // reference match, looser date
  tryPass(3, false);  // amount unique within 3 days
  tryPass(15, false); // amount unique within the period

  // Symmetric groups: when the leftovers on both sides form equal-sized sets
  // of identical (date, amount, direction) items — e.g. two ₹400 fees paid the
  // same day — any pairing is equally defensible, so pair them off rather than
  // leaving both sides "unmatched" for a human to shrug at. Refs are still
  // preferred: within a group, ref-sharing pairs are consumed first.
  const groupKey = (date, amount, moneyIn) => `${date}|${amount.toFixed(2)}|${moneyIn}`;
  const leftS = stmt.filter((s) => !usedS.has(s.id));
  const leftV = bank.filter((b) => !usedV.has(b.id));
  const groups = new Map();
  for (const s of leftS) {
    const k = groupKey(s.line.date, s.amount, s.moneyIn);
    (groups.get(k) || groups.set(k, { s: [], v: [] }).get(k)).s.push(s);
  }
  for (const b of leftV) {
    const k = groupKey(b.voucher.date, b.amount, b.moneyIn);
    const g = groups.get(k);
    if (g) g.v.push(b);
  }
  for (const g of groups.values()) {
    if (g.s.length < 2 || g.s.length !== g.v.length) continue;
    const vLeft = [...g.v];
    for (const s of g.s) {
      const iRef = vLeft.findIndex((b) => s.refs.some((r) => b.refs.includes(r)));
      const b = vLeft.splice(iRef >= 0 ? iRef : 0, 1)[0];
      usedS.add(s.id); usedV.add(b.id);
      matched.push({
        stmt: s.line, voucher: b.voucher,
        reason: "identical amount/date group (paired off)",
        confidence: "medium",
      });
    }
  }

  return {
    matched,
    bankOnly: stmt.filter((s) => !usedS.has(s.id)).map((s) => s.line),
    bookOnly: bank.filter((b) => !usedV.has(b.id)).map((b) => ({ ...b.voucher, bankAmount: b.amount, moneyIn: b.moneyIn })),
  };
}

// ---------- session persistence ----------------------------------------------
function newSession(data) {
  const id = crypto.randomBytes(5).toString("hex");
  const s = { id, createdAt: new Date().toISOString(), status: "parsed", ...data };
  fs.writeFileSync(path.join(RECON_DIR, `${id}.json`), JSON.stringify(s));
  return s;
}
function getSession(id) {
  try { return JSON.parse(fs.readFileSync(path.join(RECON_DIR, `${String(id).replace(/[^a-f0-9]/g, "")}.json`), "utf8")); }
  catch { return null; }
}
function saveSession(s) {
  fs.writeFileSync(path.join(RECON_DIR, `${s.id}.json`), JSON.stringify(s));
}

module.exports = { parseCsvStatement, validateLines, llmExtract, matchLines, newSession, getSession, saveSession, parseAmount };
