# ADR-0022: Extracting Tally into the knowledge base

- **Status:** accepted
- **Date:** 2026-07-29
- **Supersedes:** none
- **Related:** ADR-0020 (knowledge base on Postgres + pgvector)

## Context

Munshi needs to answer questions about a company's actual books — "what did we
pay this vendor", "when did we last deduct TDS on rent", "what happened in
FY2019-20". Tally holds that data, but only exposes it through an XML gateway
on `localhost:9000` while the application is open.

The first attempt at this produced a **badly wrong answer** that was written
into a client-facing verification document: it concluded that ~97% of the
company's bank transactions were unrecorded in its books, and framed this as
evidence of systemic bookkeeping failure. The real figure was that the books
contain 10,135 vouchers, every one balanced.

That near-miss shapes this decision.

## Decision

### 1. Query with Collections scoped by period, never with report IDs

Tally answers from its **currently loaded period**. Report IDs such as
`Day Book` and `Ledger Vouchers` accept `SVFROMDATE`/`SVTODATE` and then
**ignore them**, returning the same cached response for every range.

Evidence: eleven consecutive financial years each returned byte-identical
output of exactly 850,261 characters.

The working form adds company and current-date scoping:

```xml
<STATICVARIABLES>
  <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
  <SVCURRENTCOMPANY>…exact company name…</SVCURRENTCOMPANY>
  <SVFROMDATE TYPE="Date">20190401</SVFROMDATE>
  <SVTODATE TYPE="Date">20200331</SVTODATE>
  <SVCURRENTDATE TYPE="Date">20200331</SVCURRENTDATE>
</STATICVARIABLES>
```

With `SVCURRENTCOMPANY` + `SVCURRENTDATE`, FY2019-20 returned **3,106**
vouchers. Without them: **zero**.

Results are additionally filtered by voucher date in Python, so the extractor
never depends on the gateway having honoured the request.

### 2. Double-entry balance is the acceptance test

Every voucher must satisfy `sum(debits) == sum(credits)`. This is checked at
extract time and re-checkable at any time via `tally_ask.py overview`.

This is what distinguishes "the parser returned rows" from "the parser is
correct". A regex that returns plausible-looking data can still be silently
dropping entries; a voucher whose sides disagree cannot be.

**An imbalance is treated as a parser bug until proven otherwise.** When 22
vouchers failed, the cause was our own `abs()` call destroying the sign of
*negative contra lines* (forex revaluation on an EEFC account), not bad data.
Reporting those as data-quality problems would have been a second false
accusation.

### 3. Attribute-tolerant parsing, entity unescaping, word-boundary matching

Three concrete traps, each of which produced silent wrongness:

- Tally decorates tags with attributes (`<DATE TYPE="Date">`). A regex
  requiring `<DATE>` matches nothing and drops **every** voucher.
- The response header contains `<VOUCHER>0</VOUCHER>` as a counter. A
  `<VOUCHER` prefix match counts it as a voucher.
- Ledger names arrive XML-escaped (`ARTH &amp; Associates`), so a search for
  the real name fails to match its own ledger.
- Vendor lookup uses **word boundaries**. Substring `ARTH` also matches
  Krit**arth**, **P**arth and Sidd**harth** — merging four vendors' money into
  one total.

## Consequences

**Good.** Munshi can answer questions about a decade of books from the
company's own records, with every figure traceable to a voucher. The balance
invariant means the extraction is provably faithful rather than merely
plausible.

**Constraint.** Extraction requires Tally running with the company open. This
is a manual precondition; the extractor fails clearly rather than returning
partial data.

**Unresolved.** The books are the company's *assertions*. Reconciling them
against bank statements — the independent evidence — is separate work.

## The rule this establishes

> **Absence of evidence from a tool is first a claim about the tool.**

Before reporting that records are missing, incomplete, or wrong, positively
verify the retrieval path by fetching something known to exist. A query
returning nothing is not a finding until the query is proven to work.

This applies with particular force when the conclusion is an accusation about
someone's records — a client's, an accountant's, or a vendor's. The cost of
publishing a false accusation is far higher than the cost of one more check.

Recorded as lessons L010–L014 in `vm/rules/lessons.json`.
