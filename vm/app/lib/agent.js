// The AI accountant: persona, Tally tools, knowledge building, and the
// agentic loop (model calls tools until it has an answer).
"use strict";

const fs = require("fs");
const path = require("path");
const tally = require("./tally");

const DATA_DIR = process.env.TALLY_AI_DATA || "C:\\TallyAI\\data";
const KNOWLEDGE_FILE = path.join(DATA_DIR, "knowledge.json");

const PERSONA = `You are "Munshi", an AI accountant built into this Tally Cloud Workstation. You have the judgment of a Chartered Accountant with 20 years of Indian practice: accounting, TallyPrime, GST, TDS, PF/ESI, and small-business compliance.

Your user is NOT an accountant. They may send you a photo of a bill, or say things like "I paid 5000 rent in cash yesterday". Your job is to handle the accounting for them, correctly and safely.

How you work:
- You are connected to the TallyPrime running on this machine through tools. Use them to ground every answer — never invent balances, ledgers, or entries. If Tally is offline, say so and explain how to open it (open Tally; it must be running with 'TallyPrime acts as Both' under F1 > Settings > Connectivity).
- When the user sends a bill/invoice photo: read it carefully (vendor, date, items, taxable value, GST breakup CGST/SGST/IGST, total). Then propose the exact entry you intend to make.
- THE GOLDEN RULE: never create or modify anything in Tally without first showing the user a plain-language summary of the entry (who, what, amount, date, which ledgers) and receiving their clear confirmation ("yes", "ok", "confirm"). One confirmation covers the ledgers you must create for that entry too — list them in the same summary.
- Choose correct voucher types: Purchase for supplier bills, Sales for sales invoices, Payment for money going out, Receipt for money coming in, Contra for bank<->cash, Journal for adjustments.
- Follow Indian conventions: amounts in INR (₹), financial year April-March, GST split into CGST+SGST for intra-state and IGST for inter-state. If the bill's GST treatment is unclear, ask one short question rather than guessing.
- Dates: users speak casually ("yesterday", "26th"). Resolve to real dates; pass dates to tools as YYYYMMDD.
- Ledger discipline: reuse existing ledgers whenever one fits (check the ledger list). Create new ones only when genuinely needed, under the correct Tally group (e.g. Sundry Creditors for a vendor, Indirect Expenses for rent, Duties & Taxes for GST ledgers).
- Keep replies short, warm and jargon-free; explain what you did in one or two sentences a shopkeeper would understand. Use simple bullet points when proposing an entry.
- If the user asks something outside accounting/Tally, help briefly if trivial or say it's outside your desk.
- You cannot file GST/TDS returns on portals — for that, guide the user to the portal shortcuts on the desktop and offer to prepare the figures.`;

const TOOLS = [
  {
    name: "tally_status",
    description: "Check whether TallyPrime's gateway is reachable and list the open companies. Call this first if unsure Tally is running.",
    input_schema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "list_ledgers",
    description: "List all ledgers in the current Tally company with their group and closing balance. Use to find the right ledger or check whether one exists before creating it.",
    input_schema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "get_daybook",
    description: "Get vouchers between two dates (the day book). Use for questions like 'what did I spend last week' or to verify an entry was recorded.",
    input_schema: {
      type: "object",
      properties: {
        from_date: { type: "string", description: "Start date YYYYMMDD" },
        to_date: { type: "string", description: "End date YYYYMMDD" },
      },
      required: ["from_date", "to_date"],
      additionalProperties: false,
    },
  },
  {
    name: "create_ledger",
    description: "Create a new ledger in Tally. ONLY after the user has confirmed the entry that needs it. Group must be a valid Tally group (e.g. 'Sundry Creditors', 'Sundry Debtors', 'Indirect Expenses', 'Duties & Taxes', 'Bank Accounts', 'Cash-in-Hand').",
    input_schema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Ledger name, e.g. 'Sharma Traders'" },
        group: { type: "string", description: "Parent Tally group" },
      },
      required: ["name", "group"],
      additionalProperties: false,
    },
  },
  {
    name: "create_voucher",
    description: "Post a voucher (accounting entry) to Tally. ONLY after the user has explicitly confirmed the summarized entry in this conversation. Debits and credits must balance.",
    input_schema: {
      type: "object",
      properties: {
        voucher_type: { type: "string", enum: ["Journal", "Payment", "Receipt", "Contra", "Sales", "Purchase"] },
        date: { type: "string", description: "Voucher date YYYYMMDD" },
        narration: { type: "string", description: "Short human-readable narration" },
        entries: {
          type: "array",
          items: {
            type: "object",
            properties: {
              ledger: { type: "string" },
              amount: { type: "number", description: "Positive amount in INR" },
              type: { type: "string", enum: ["debit", "credit"] },
            },
            required: ["ledger", "amount", "type"],
            additionalProperties: false,
          },
        },
      },
      required: ["voucher_type", "date", "entries"],
      additionalProperties: false,
    },
  },
  {
    name: "refresh_knowledge",
    description: "Re-read the company and ledger list from Tally into your working knowledge. Use after creating ledgers or if your ledger knowledge seems stale.",
    input_schema: { type: "object", properties: {}, additionalProperties: false },
  },
];

async function executeTool(name, input, config) {
  const company = config.company || undefined;
  switch (name) {
    case "tally_status": {
      const online = await tally.isOnline();
      if (!online) return { online: false, hint: "Tally is not reachable on port 9000. It must be open, with 'TallyPrime acts as: Both' set under F1 > Settings > Connectivity." };
      const companies = await tally.listCompanies();
      return { online: true, companies };
    }
    case "list_ledgers":
      return { ledgers: await tally.listLedgers() };
    case "get_daybook":
      return await tally.dayBook(input.from_date, input.to_date, company);
    case "create_ledger":
      return await tally.createLedger({ name: input.name, group: input.group, company });
    case "create_voucher":
      return await tally.createVoucher({
        voucherType: input.voucher_type,
        date: input.date,
        narration: input.narration,
        entries: input.entries,
        company,
      });
    case "refresh_knowledge":
      return await buildKnowledge();
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

// --- Knowledge: a cached snapshot of the company + ledgers, injected into
// --- the system prompt so the model knows the books without tool calls -----
async function buildKnowledge() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  const online = await tally.isOnline();
  if (!online) {
    const k = { at: new Date().toISOString(), online: false, text: "Tally was OFFLINE at last check — no company data loaded. Use tally_status to re-check." };
    fs.writeFileSync(KNOWLEDGE_FILE, JSON.stringify(k));
    return { refreshed: false, reason: "tally offline" };
  }
  const companies = await tally.listCompanies();
  const ledgers = await tally.listLedgers();
  let text = `Companies open in Tally: ${companies.map((c) => c.name).join(", ") || "(none)"}\n`;
  text += `Ledgers (${ledgers.length}) — name | group | closing balance:\n`;
  for (const l of ledgers.slice(0, 400)) {
    text += `${l.name} | ${l.group} | ${l.closingBalance}\n`;
  }
  if (ledgers.length > 400) text += `...and ${ledgers.length - 400} more (use list_ledgers for the full list)\n`;
  if (text.length > 20000) text = text.slice(0, 20000) + "\n...(truncated — use list_ledgers)";
  const k = { at: new Date().toISOString(), online: true, text };
  fs.writeFileSync(KNOWLEDGE_FILE, JSON.stringify(k));
  return { refreshed: true, companies: companies.length, ledgers: ledgers.length };
}

function loadKnowledge() {
  try {
    return JSON.parse(fs.readFileSync(KNOWLEDGE_FILE, "utf8"));
  } catch {
    return null;
  }
}

function buildSystem() {
  const k = loadKnowledge();
  const system = [
    { type: "text", text: PERSONA, cache_control: { type: "ephemeral" } },
  ];
  if (k) {
    system.push({
      type: "text",
      text: `CURRENT BOOKS SNAPSHOT (as of ${k.at}):\n${k.text}`,
      cache_control: { type: "ephemeral" },
    });
  }
  // Volatile content stays last, after the cache breakpoints
  const now = new Date();
  const ist = new Date(now.getTime() + (330 + now.getTimezoneOffset()) * 60000);
  system.push({ type: "text", text: `Today's date (IST): ${ist.toISOString().slice(0, 10)}` });
  return system;
}

// --- The agentic loop -------------------------------------------------------
// messages: full conversation (persisted by the server). Returns
// { reply, steps } and appends the assistant/tool turns to messages.
async function runAgent({ provider, config, messages, onStep }) {
  const steps = [];
  const MAX_TURNS = 12;

  for (let turn = 0; turn < MAX_TURNS; turn++) {
    const response = await provider.chat({
      system: buildSystem(),
      messages,
      tools: TOOLS,
    });

    if (response.stopReason === "refusal") {
      messages.push({ role: "assistant", content: [{ type: "text", text: "I can't help with that request." }] });
      return { reply: "I can't help with that request.", steps };
    }

    messages.push({ role: "assistant", content: response.content });

    if (response.stopReason !== "tool_use") {
      const reply = response.content
        .filter((b) => b.type === "text")
        .map((b) => b.text)
        .join("\n");
      return { reply, steps };
    }

    // Execute every tool call in this assistant turn; return all results
    // together in a single user message.
    const toolUses = response.content.filter((b) => b.type === "tool_use");
    const results = [];
    for (const tu of toolUses) {
      steps.push(tu.name);
      if (onStep) onStep(tu.name);
      try {
        const result = await executeTool(tu.name, tu.input || {}, config);
        results.push({
          type: "tool_result",
          tool_use_id: tu.id,
          content: JSON.stringify(result).slice(0, 40000),
        });
      } catch (err) {
        results.push({
          type: "tool_result",
          tool_use_id: tu.id,
          content: `Error: ${err.message}`,
          is_error: true,
        });
      }
    }
    messages.push({ role: "user", content: results });
  }

  const fallbackText = "I did a lot of work on that but hit my step limit — tell me to continue if you'd like me to keep going.";
  messages.push({ role: "assistant", content: [{ type: "text", text: fallbackText }] });
  return { reply: fallbackText, steps };
}

module.exports = { runAgent, buildKnowledge, loadKnowledge, TOOLS };
