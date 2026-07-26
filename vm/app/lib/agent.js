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
- When the user sends a bill/invoice photo: read it carefully (vendor, date, items, taxable value, GST breakup CGST/SGST/IGST, total). Then draft the exact entry.
- THE GOLDEN RULE (enforced by the app, not just by you): you CANNOT write to Tally directly. The only way to record anything is the propose_entry tool, which creates a DRAFT. The app shows the user a card with the full entry and a Confirm button — posting happens only when the user taps Confirm. Include any new ledgers the entry needs in the same draft. After proposing, briefly tell the user what's in the card and to tap Confirm to record it (or Reject to discard). Never claim an entry has been recorded — the app tells the user that after posting and verification.
- If the bill photo came with the same message, the app files it automatically under C:\TallyData\Documents (organized by financial year and month) when the draft is confirmed, and links it in the voucher narration — you can mention this.
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
    name: "propose_entry",
    description: "Create a DRAFT accounting entry for the user to confirm. This is the ONLY way to record anything in Tally — the app shows the draft as a card and posts it only when the user taps Confirm. Include any ledgers that must be created for this entry in new_ledgers (with correct Tally groups, e.g. 'Sundry Creditors', 'Indirect Expenses', 'Duties & Taxes'). Debits and credits must balance.",
    input_schema: {
      type: "object",
      properties: {
        voucher_type: { type: "string", enum: ["Journal", "Payment", "Receipt", "Contra", "Sales", "Purchase"] },
        date: { type: "string", description: "Voucher date YYYYMMDD" },
        narration: { type: "string", description: "Short human-readable narration, e.g. 'Shop rent for July paid in cash'" },
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
        new_ledgers: {
          type: "array",
          description: "Ledgers that don't exist yet and must be created before posting",
          items: {
            type: "object",
            properties: {
              name: { type: "string" },
              group: { type: "string", description: "Parent Tally group" },
            },
            required: ["name", "group"],
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

function validateDraft(input) {
  const dr = (input.entries || []).filter((e) => e.type === "debit").reduce((s, e) => s + e.amount, 0);
  const cr = (input.entries || []).filter((e) => e.type === "credit").reduce((s, e) => s + e.amount, 0);
  if (!input.entries || input.entries.length < 2) throw new Error("An entry needs at least one debit and one credit line.");
  if (Math.abs(dr - cr) > 0.01) throw new Error(`Draft does not balance: debits ${dr} vs credits ${cr}.`);
  if (!/^\d{8}$/.test(input.date || "")) throw new Error("Date must be YYYYMMDD.");
  const d = new Date(`${input.date.slice(0, 4)}-${input.date.slice(4, 6)}-${input.date.slice(6, 8)}`);
  const max = new Date(Date.now() + 7 * 86400000);
  if (isNaN(d.getTime()) || d < new Date("2000-01-01") || d > max) {
    throw new Error("Date is invalid or too far in the future.");
  }
  return { total: dr };
}

async function executeTool(name, input, config, context) {
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
    case "propose_entry": {
      const { total } = validateDraft(input);
      const draft = context.createDraft({
        voucher: {
          voucher_type: input.voucher_type,
          date: input.date,
          narration: input.narration || "",
          entries: input.entries,
        },
        newLedgers: input.new_ledgers || [],
        total,
      });
      return {
        draft_id: draft.id,
        status: "awaiting_user_confirmation",
        note: "The draft card is now visible to the user. Posting happens only when they tap Confirm — do not claim the entry is recorded.",
      };
    }
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
async function runAgent({ provider, config, messages, context = {}, onStep }) {
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
        const result = await executeTool(tu.name, tu.input || {}, config, context);
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
