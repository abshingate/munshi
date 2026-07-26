// Draft lifecycle: the AI can only create drafts; posting to Tally happens
// exclusively here, triggered by the user's Confirm tap in the UI.
//   pending -> posting -> posted | failed        (confirm)
//   pending -> rejected                          (reject)
// Guarantees: idempotent posting (a draft posts at most once), ledgers
// verified/created first, voucher verified by day-book read-back after
// posting, source bill images filed under C:\TallyData\Documents\FY..\MM..,
// and every action appended to an audit log.
"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const tally = require("./tally");
const { buildKnowledge } = require("./agent");

const DATA_DIR = process.env.TALLY_AI_DATA || "C:\\TallyAI\\data";
const DRAFTS_FILE = path.join(DATA_DIR, "drafts.json");
const PENDING_DIR = path.join(DATA_DIR, "pending-docs");
const AUDIT_FILE = path.join(DATA_DIR, "audit.log");
const DOCS_ROOT = process.env.TALLY_DOCS || "C:\\TallyData\\Documents";
const BIG_AMOUNT = 100000; // above this, the UI asks for a stronger confirmation

fs.mkdirSync(DATA_DIR, { recursive: true });
fs.mkdirSync(PENDING_DIR, { recursive: true });

let drafts = {};
try { drafts = JSON.parse(fs.readFileSync(DRAFTS_FILE, "utf8")); } catch {}
function save() { fs.writeFileSync(DRAFTS_FILE, JSON.stringify(drafts, null, 2)); }
function audit(event) {
  fs.appendFileSync(AUDIT_FILE, JSON.stringify({ at: new Date().toISOString(), ...event }) + "\n");
}

const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
function docFolderFor(dateYYYYMMDD) {
  const y = Number(dateYYYYMMDD.slice(0, 4));
  const m = Number(dateYYYYMMDD.slice(4, 6));
  const fy = m >= 4 ? `FY${y}-${String(y + 1).slice(2)}` : `FY${y - 1}-${String(y).slice(2)}`;
  return path.join(DOCS_ROOT, fy, `${String(m).padStart(2, "0")}-${MONTHS[m - 1]}`);
}
function sanitize(s) {
  return String(s || "").replace(/[^a-zA-Z0-9 _-]/g, "").trim().replace(/\s+/g, "-").slice(0, 40) || "entry";
}

// images: [{media_type, data(base64)}] from the user message that produced the draft
function createDraft({ voucher, newLedgers, total, images }) {
  const id = crypto.randomBytes(6).toString("hex");
  const docFiles = [];
  for (let i = 0; i < (images || []).length; i++) {
    const f = path.join(PENDING_DIR, `${id}-${i + 1}.jpg`);
    fs.writeFileSync(f, Buffer.from(images[i].data, "base64"));
    docFiles.push(f);
  }
  drafts[id] = {
    id,
    createdAt: new Date().toISOString(),
    status: "pending",
    voucher,
    newLedgers: newLedgers || [],
    total,
    bigAmount: total >= BIG_AMOUNT,
    pendingDocs: docFiles,
  };
  save();
  audit({ event: "draft_created", draft: id, voucher, newLedgers, total });
  return drafts[id];
}

function get(id) { return drafts[id] || null; }
function listPending() {
  return Object.values(drafts).filter((d) => d.status === "pending")
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

function reject(id) {
  const d = drafts[id];
  if (!d) throw Object.assign(new Error("Draft not found"), { code: 404 });
  if (d.status !== "pending") throw Object.assign(new Error(`Draft is already ${d.status}`), { code: 409 });
  d.status = "rejected";
  for (const f of d.pendingDocs || []) { try { fs.unlinkSync(f); } catch {} }
  d.pendingDocs = [];
  save();
  audit({ event: "draft_rejected", draft: id });
  return d;
}

async function confirm(id, config) {
  const d = drafts[id];
  if (!d) throw Object.assign(new Error("Draft not found"), { code: 404 });
  // Idempotency: only a pending draft can post, and it flips to "posting"
  // synchronously before any I/O — a double-tap or retry gets a 409.
  if (d.status !== "pending") throw Object.assign(new Error(`Draft is already ${d.status}`), { code: 409 });
  d.status = "posting";
  save();

  const company = config.company || undefined;
  try {
    if (!(await tally.isOnline())) throw new Error("Tally is not reachable — open Tally on the computer and try again.");

    // 1. Ledgers: create the declared new ones, then verify every entry ledger exists
    const existing = new Set((await tally.listLedgers()).map((l) => l.name.toLowerCase()));
    for (const nl of d.newLedgers) {
      if (existing.has(nl.name.toLowerCase())) continue;
      const r = await tally.createLedger({ name: nl.name, group: nl.group, company });
      if (!r.ok) throw new Error(`Could not create ledger '${nl.name}': ${r.lineError || "Tally rejected it"}`);
      existing.add(nl.name.toLowerCase());
      audit({ event: "ledger_created", draft: id, ledger: nl });
    }
    const missing = d.voucher.entries.filter((e) => !existing.has(e.ledger.toLowerCase()));
    if (missing.length) throw new Error(`These ledgers don't exist in Tally: ${missing.map((e) => e.ledger).join(", ")}`);

    // 2. File the bill documents and build the narration marker
    const marker = `[M-${id}]`;
    const docPaths = [];
    if ((d.pendingDocs || []).length) {
      const folder = docFolderFor(d.voucher.date);
      fs.mkdirSync(folder, { recursive: true });
      const dateStr = `${d.voucher.date.slice(0, 4)}-${d.voucher.date.slice(4, 6)}-${d.voucher.date.slice(6, 8)}`;
      const label = sanitize(d.voucher.narration || d.voucher.entries[0].ledger);
      d.pendingDocs.forEach((src, i) => {
        const dst = path.join(folder, `${dateStr}_${label}_M-${id}${d.pendingDocs.length > 1 ? `_${i + 1}` : ""}.jpg`);
        fs.copyFileSync(src, dst);
        docPaths.push(dst);
      });
    }
    const docNote = docPaths.length ? ` [Doc: ${path.relative(DOCS_ROOT, docPaths[0])}]` : "";
    const narration = `${d.voucher.narration || ""} ${marker}${docNote}`.trim();

    // 3. Post the voucher — but first check it isn't already in Tally from a
    // previous attempt that failed only on the response (double-post guard)
    const pre = await tally.dayBook(d.voucher.date, d.voucher.date, company);
    const alreadyPosted = pre.vouchers.some((v) => (v.narration || "").includes(marker));
    const result = alreadyPosted ? { ok: true } : await tally.createVoucher({
      voucherType: d.voucher.voucher_type,
      date: d.voucher.date,
      narration,
      entries: d.voucher.entries,
      company,
    });
    if (!result.ok) throw new Error(`Tally rejected the voucher: ${result.lineError || "unknown error"}`);

    // 4. Verify after write: the voucher must be readable back from the day book
    let verified = false;
    for (let attempt = 0; attempt < 3 && !verified; attempt++) {
      const day = await tally.dayBook(d.voucher.date, d.voucher.date, company);
      verified = day.vouchers.some((v) => (v.narration || "").includes(marker));
      if (!verified) await new Promise((r) => setTimeout(r, 1500));
    }

    // Rich metadata into the document index — this is what makes filed
    // documents searchable by amount, ledger, narration, party, etc.
    const docindex = require("./docindex");
    for (const p of docPaths) {
      docindex.addEntry(path.relative(DOCS_ROOT, p).split(path.sep).join("/"), {
        date: d.voucher.date,
        label: d.voucher.narration || d.voucher.entries[0].ledger,
        narration: d.voucher.narration,
        voucher_type: d.voucher.voucher_type,
        ledgers: d.voucher.entries.map((e) => e.ledger),
        total: d.total,
        marker,
      });
    }

    for (const f of d.pendingDocs || []) { try { fs.unlinkSync(f); } catch {} }
    d.pendingDocs = [];
    d.status = "posted";
    d.postedAt = new Date().toISOString();
    d.verified = verified;
    d.marker = marker;
    d.docPaths = docPaths;
    save();
    audit({ event: "voucher_posted", draft: id, marker, verified, docPaths, voucher: d.voucher });

    // 5. Books changed — refresh the AI's knowledge snapshot
    buildKnowledge().catch(() => {});

    return d;
  } catch (err) {
    d.status = "pending"; // allow the user to retry after fixing the cause
    save();
    audit({ event: "post_failed", draft: id, error: err.message });
    throw err;
  }
}

module.exports = { createDraft, get, listPending, confirm, reject, BIG_AMOUNT };
