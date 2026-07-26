// Document metadata index — makes filed documents searchable by everything
// the system knew at filing time (voucher type, amount, ledgers, narration,
// date, entry code), not just the filename. Local JSON index; no external
// search service. Filenames of unindexed files (older filings, Drive inbox)
// are searchable via backfill/scan.
"use strict";

const fs = require("fs");
const path = require("path");

const DATA_DIR = process.env.TALLY_AI_DATA || "C:\\TallyAI\\data";
const INDEX_FILE = path.join(DATA_DIR, "doc-index.json");
const DOCS_ROOT = process.env.TALLY_DOCS || "C:\\TallyData\\Documents";
const DRIVE_ROOT = "C:\\TallyData\\Drive";

let index = {};
try { index = JSON.parse(fs.readFileSync(INDEX_FILE, "utf8")); } catch {}
function save() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(INDEX_FILE, JSON.stringify(index));
}

function addEntry(relPath, meta) {
  index[relPath] = { ...meta, indexedAt: new Date().toISOString() };
  save();
}

function walk(root, base = "") {
  const out = [];
  let entries = [];
  try { entries = fs.readdirSync(path.join(root, base), { withFileTypes: true }); } catch { return out; }
  for (const e of entries) {
    if (e.name.startsWith(".") || e.name.startsWith("_")) continue;
    const rel = base ? `${base}/${e.name}` : e.name;
    if (e.isDirectory()) out.push(...walk(root, rel));
    else out.push(rel);
  }
  return out;
}

// Index minimal metadata (parsed from our filename convention) for filed
// documents that predate the index or arrived out-of-band.
function backfill() {
  let changed = false;
  for (const rel of walk(DOCS_ROOT)) {
    if (index[rel]) continue;
    const name = path.basename(rel);
    const m = name.match(/^(\d{4}-\d{2}-\d{2})_(.+?)_M-([a-f0-9]+)/i);
    index[rel] = {
      date: m ? m[1].replace(/-/g, "") : "",
      label: m ? m[2].replace(/-/g, " ") : name,
      marker: m ? `M-${m[3]}` : "",
      backfilled: true,
    };
    changed = true;
  }
  if (changed) save();
}

// Search filed documents (metadata) + Drive inbox (filenames).
// All query tokens must match somewhere; results newest-first.
function search(query, limit = 30) {
  backfill();
  const tokens = String(query || "").toLowerCase().split(/\s+/).filter(Boolean);
  if (tokens.length === 0) return [];
  const results = [];

  for (const [rel, m] of Object.entries(index)) {
    const full = path.join(DOCS_ROOT, rel);
    if (!fs.existsSync(full)) continue;
    const hay = [
      rel, m.label, m.narration, m.voucher_type, m.marker,
      (m.ledgers || []).join(" "), String(m.total || ""), m.date,
    ].join(" ").toLowerCase();
    if (tokens.every((t) => hay.includes(t))) {
      const st = fs.statSync(full);
      results.push({
        root: "documents", path: rel, name: path.basename(rel),
        size: st.size, mtime: st.mtimeMs,
        meta: { date: m.date, total: m.total, voucher_type: m.voucher_type, narration: m.narration || m.label, marker: m.marker },
      });
    }
  }

  for (const rel of walk(DRIVE_ROOT)) {
    const hay = rel.toLowerCase();
    if (tokens.every((t) => hay.includes(t))) {
      const full = path.join(DRIVE_ROOT, rel);
      const st = fs.statSync(full);
      results.push({ root: "drive", path: rel, name: path.basename(rel), size: st.size, mtime: st.mtimeMs, meta: {} });
    }
  }

  results.sort((a, b) => (b.meta.date || "").localeCompare(a.meta.date || "") || b.mtime - a.mtime);
  return results.slice(0, limit);
}

module.exports = { addEntry, search, DOCS_ROOT };
