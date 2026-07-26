// TallyPrime XML gateway client.
// Tally must be running with "TallyPrime acts as: Both" (F1 > Settings >
// Connectivity), which serves an XML-over-HTTP API on port 9000.
"use strict";

const TALLY_URL = process.env.TALLY_URL || "http://localhost:9000";

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
function unesc(s) {
  return String(s)
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .replace(/&quot;/g, '"').replace(/&apos;/g, "'")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
}

async function post(xml) {
  const res = await fetch(TALLY_URL, {
    method: "POST",
    headers: { "Content-Type": "text/xml" },
    body: xml,
    signal: AbortSignal.timeout(30000),
  });
  return await res.text();
}

// Extract every occurrence of <TAG ...>value</TAG> (non-nested values)
function tagValues(xml, tag) {
  const re = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)</${tag}>`, "gi");
  const out = [];
  let m;
  while ((m = re.exec(xml)) !== null) out.push(unesc(m[1].trim()));
  return out;
}
// Split into blocks by a repeating element, e.g. VOUCHER or LEDGER
function blocks(xml, tag) {
  const re = new RegExp(`<${tag}[\\s>][\\s\\S]*?</${tag}>`, "gi");
  return xml.match(re) || [];
}

function collectionEnvelope(type, fetchList) {
  return `<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>AIList</ID></HEADER><BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES><TDL><TDLMESSAGE><COLLECTION NAME="AIList" ISMODIFY="No"><TYPE>${type}</TYPE><FETCH>${fetchList}</FETCH></COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>`;
}

async function isOnline() {
  try {
    const res = await fetch(TALLY_URL, { method: "GET", signal: AbortSignal.timeout(4000) });
    return res.ok || res.status < 500;
  } catch {
    return false;
  }
}

async function listCompanies() {
  const xml = await post(collectionEnvelope("Company", "NAME,STARTINGFROM,BOOKSFROM"));
  return blocks(xml, "COMPANY").map((b) => ({
    name: (tagValues(b, "NAME")[0] || "").trim(),
  })).filter((c) => c.name);
}

async function listLedgers() {
  const xml = await post(collectionEnvelope("Ledger", "NAME,PARENT,CLOSINGBALANCE"));
  return blocks(xml, "LEDGER").map((b) => ({
    name: tagValues(b, "NAME")[0] || "",
    group: tagValues(b, "PARENT")[0] || "",
    closingBalance: tagValues(b, "CLOSINGBALANCE")[0] || "",
  })).filter((l) => l.name);
}

// dates: YYYYMMDD strings. opts.includeRaw keeps the full voucher XML block
// (needed for the reconciliation bank-date alteration round-trip).
async function dayBook(fromDate, toDate, company, opts = {}) {
  const comp = company ? `<SVCURRENTCOMPANY>${esc(company)}</SVCURRENTCOMPANY>` : "";
  const xml = await post(
    `<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Data</TYPE><ID>Day Book</ID></HEADER><BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><SVFROMDATE>${esc(fromDate)}</SVFROMDATE><SVTODATE>${esc(toDate)}</SVTODATE>${comp}</STATICVARIABLES></DESC></BODY></ENVELOPE>`
  );
  const cap = opts.limit || 200;
  const vouchers = blocks(xml, "VOUCHER").slice(0, cap).map((b) => {
    const remoteM = b.match(/<VOUCHER[^>]*REMOTEID="([^"]*)"/i);
    return {
      date: tagValues(b, "DATE")[0] || "",
      type: tagValues(b, "VOUCHERTYPENAME")[0] || "",
      number: tagValues(b, "VOUCHERNUMBER")[0] || "",
      party: tagValues(b, "PARTYLEDGERNAME")[0] || "",
      narration: tagValues(b, "NARRATION")[0] || "",
      remoteId: remoteM ? remoteM[1] : "",
      ledgerEntries: tagValues(b, "LEDGERNAME").map((name, i) => ({
        ledger: name,
        amount: tagValues(b, "AMOUNT")[i] || "",
      })),
      ...(opts.includeRaw ? { raw: b } : {}),
    };
  });
  return { count: vouchers.length, truncated: blocks(xml, "VOUCHER").length > cap, vouchers };
}

// ADR-0016: the ONLY permitted alteration — set the bank date (reconciliation
// tick) on an existing voucher. Takes the voucher's own full exported XML,
// changes ACTION to Alter, and injects BANKERSDATE into the bank ledger's
// allocations; nothing else in the voucher is modified. Caller MUST verify
// afterwards (re-export and compare financials) — see server /api/recon/apply.
async function setBankDate({ rawVoucherXml, bankLedger, bankersDate, company }) {
  if (!rawVoucherXml || !/^<VOUCHER[\s>]/i.test(rawVoucherXml.trim())) throw new Error("missing voucher XML");
  let v = rawVoucherXml.trim();
  // Force ACTION="Alter" on the opening tag
  v = v.replace(/^<VOUCHER([^>]*?)( ACTION="[^"]*")?([^>]*)>/i, `<VOUCHER$1$3 ACTION="Alter">`);

  // Locate the ALLLEDGERENTRIES.LIST for the bank ledger
  const entryRe = /<ALLLEDGERENTRIES\.LIST>[\s\S]*?<\/ALLLEDGERENTRIES\.LIST>/gi;
  let found = false;
  v = v.replace(entryRe, (block) => {
    const nameM = block.match(/<LEDGERNAME[^>]*>([\s\S]*?)<\/LEDGERNAME>/i);
    if (!nameM || nameM[1].trim().toLowerCase() !== bankLedger.toLowerCase() || found) return block;
    found = true;
    const vchDate = (rawVoucherXml.match(/<DATE[^>]*>(\d{8})<\/DATE>/i) || [])[1] || bankersDate;
    if (/<BANKALLOCATIONS\.LIST>/i.test(block)) {
      if (/<BANKERSDATE[^>]*>/i.test(block)) {
        return block.replace(/<BANKERSDATE[^>]*>[\s\S]*?<\/BANKERSDATE>/i, `<BANKERSDATE>${esc(bankersDate)}</BANKERSDATE>`);
      }
      return block.replace(/<BANKALLOCATIONS\.LIST>/i, `<BANKALLOCATIONS.LIST><BANKERSDATE>${esc(bankersDate)}</BANKERSDATE>`);
    }
    return block.replace(/<\/ALLLEDGERENTRIES\.LIST>/i,
      `<BANKALLOCATIONS.LIST><DATE>${esc(vchDate)}</DATE><BANKERSDATE>${esc(bankersDate)}</BANKERSDATE></BANKALLOCATIONS.LIST></ALLLEDGERENTRIES.LIST>`);
  });
  if (!found) throw new Error(`Bank ledger '${bankLedger}' not found in the voucher`);

  const comp = company ? `<SVCURRENTCOMPANY>${esc(company)}</SVCURRENTCOMPANY>` : "";
  const res = await post(
    `<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME><STATICVARIABLES>${comp}</STATICVARIABLES></REQUESTDESC><REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">${v}</TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>`
  );
  return importResult(res);
}

async function createLedger({ name, group, company }) {
  const comp = company ? `<SVCURRENTCOMPANY>${esc(company)}</SVCURRENTCOMPANY>` : "";
  const res = await post(
    `<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>All Masters</REPORTNAME><STATICVARIABLES>${comp}</STATICVARIABLES></REQUESTDESC><REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF"><LEDGER NAME="${esc(name)}" ACTION="Create"><NAME>${esc(name)}</NAME><PARENT>${esc(group)}</PARENT></LEDGER></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>`
  );
  return importResult(res);
}

// entries: [{ledger, amount (positive number), type: "debit"|"credit"}]
// date: YYYYMMDD; voucherType: Journal|Payment|Receipt|Contra|Sales|Purchase
async function createVoucher({ voucherType, date, narration, entries, company }) {
  const dr = entries.filter((e) => e.type === "debit").reduce((s, e) => s + e.amount, 0);
  const cr = entries.filter((e) => e.type === "credit").reduce((s, e) => s + e.amount, 0);
  if (Math.abs(dr - cr) > 0.01) {
    throw new Error(`Voucher does not balance: debits ${dr} vs credits ${cr}`);
  }
  const lines = entries.map((e) => {
    // Tally convention: debit => ISDEEMEDPOSITIVE Yes with negative amount
    const amt = e.type === "debit" ? -Math.abs(e.amount) : Math.abs(e.amount);
    const pos = e.type === "debit" ? "Yes" : "No";
    return `<ALLLEDGERENTRIES.LIST><LEDGERNAME>${esc(e.ledger)}</LEDGERNAME><ISDEEMEDPOSITIVE>${pos}</ISDEEMEDPOSITIVE><AMOUNT>${amt.toFixed(2)}</AMOUNT></ALLLEDGERENTRIES.LIST>`;
  }).join("");
  const comp = company ? `<SVCURRENTCOMPANY>${esc(company)}</SVCURRENTCOMPANY>` : "";
  const res = await post(
    `<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME><STATICVARIABLES>${comp}</STATICVARIABLES></REQUESTDESC><REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER VCHTYPE="${esc(voucherType)}" ACTION="Create"><DATE>${esc(date)}</DATE><VOUCHERTYPENAME>${esc(voucherType)}</VOUCHERTYPENAME><NARRATION>${esc(narration || "")}</NARRATION>${lines}</VOUCHER></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>`
  );
  return importResult(res);
}

function importResult(xml) {
  const created = Number(tagValues(xml, "CREATED")[0] || 0);
  const altered = Number(tagValues(xml, "ALTERED")[0] || 0);
  const errors = Number(tagValues(xml, "ERRORS")[0] || 0);
  const lineError = tagValues(xml, "LINEERROR").join("; ");
  return { created, altered, errors, lineError: lineError || undefined, ok: errors === 0 && (created > 0 || altered > 0) };
}

module.exports = { isOnline, listCompanies, listLedgers, dayBook, createLedger, createVoucher, setBankDate };
