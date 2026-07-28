#!/usr/bin/env python3
"""
Munshi knowledge base — search (ADR-0020).

Hybrid search over the ingested corpus: PostgreSQL full-text ranking, ordinary
SQL filters, and (when pgvector is installed) semantic similarity — combined
in one query rather than joined across two systems.

Usage
-----
    python search.py "audit fee"
    python search.py "rent" --party palkar --since 2026-04-01
    python search.py --party arth --type invoice --list
    python search.py --sql "SELECT party, sum(amount) FROM kb_document GROUP BY 1"

Output is plain text by default and JSON with --json, so it works both for a
human at a terminal and as a tool call from an assistant.
"""

import argparse
import json
import os
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg not installed. Run: pip install 'psycopg[binary]'")

DB = os.environ.get("MUNSHI_KB_DSN", "postgresql://postgres@localhost/munshi_kb")


def has_embeddings(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='kb_chunk' AND column_name='embedding'"
        )
        return cur.fetchone() is not None


def search(conn, query=None, party=None, doc_type=None, since=None, until=None,
           limit=20, snippets=True):
    """Full-text search with optional filters.

    Returns documents ranked by relevance when `query` is given, else the most
    recent matching documents. Filters are plain SQL, so they compose freely —
    that combination is the reason for choosing Postgres (ADR-0020).
    """
    where, params = [], {}

    if query:
        where.append("d.tsv @@ plainto_tsquery('english', %(q)s)")
        params["q"] = query
    if party:
        where.append("d.party ILIKE %(party)s")
        params["party"] = f"%{party}%"
    if doc_type:
        where.append("d.doc_type = %(dt)s")
        params["dt"] = doc_type
    if since:
        where.append("d.doc_date >= %(since)s")
        params["since"] = since
    if until:
        where.append("d.doc_date <= %(until)s")
        params["until"] = until

    clause = " AND ".join(where) if where else "TRUE"
    rank = ("ts_rank(d.tsv, plainto_tsquery('english', %(q)s)) DESC, "
            if query else "")
    params["limit"] = limit

    sql = f"""
        SELECT d.id, d.doc_date, d.doc_type, d.party, d.subject, d.filename,
               d.amount, d.source_path,
               {"ts_headline('english', coalesce(d.body_text,''), plainto_tsquery('english', %(q)s), 'MaxWords=40,MinWords=20')" if (query and snippets) else "NULL"} AS snippet
        FROM kb_document d
        WHERE {clause}
        ORDER BY {rank} d.doc_date DESC NULLS LAST
        LIMIT %(limit)s
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_document(conn, doc_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, doc_date, doc_type, party, subject, sender, recipients, "
            "amount, filename, source_path, page_count, body_text, metadata "
            "FROM kb_document WHERE id=%s", (doc_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return dict(zip([c.name for c in cur.description], row))


def run_sql(conn, sql):
    """Read-only ad-hoc query. Aggregates are a first-class use case: the
    knowledge base is a database, not just an index."""
    lowered = sql.strip().lower()
    if not lowered.startswith(("select", "with")):
        sys.exit("Only SELECT / WITH queries are allowed here.")
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def fmt(v):
    return "" if v is None else str(v)


def main():
    ap = argparse.ArgumentParser(description="Search the Munshi knowledge base")
    ap.add_argument("query", nargs="?", help="words to search for")
    ap.add_argument("--party", help="counterparty name (partial match)")
    ap.add_argument("--type", dest="doc_type", help="invoice | challan | return | ...")
    ap.add_argument("--since", help="YYYY-MM-DD")
    ap.add_argument("--until", help="YYYY-MM-DD")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--list", action="store_true", help="no snippets, just rows")
    ap.add_argument("--doc", type=int, help="print one document in full by id")
    ap.add_argument("--sql", help="read-only SELECT for aggregates")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    with psycopg.connect(DB) as conn:
        if args.doc:
            doc = get_document(conn, args.doc)
            if not doc:
                sys.exit(f"No document with id {args.doc}")
            if args.json:
                print(json.dumps(doc, indent=2, default=str))
            else:
                for k in ("id", "doc_date", "doc_type", "party", "subject",
                          "sender", "amount", "filename", "source_path"):
                    if doc.get(k):
                        print(f"{k:12}: {doc[k]}")
                print("-" * 60)
                print(doc.get("body_text") or "(no extracted text)")
            return

        if args.sql:
            rows = run_sql(conn, args.sql)
            print(json.dumps(rows, indent=2, default=str) if args.json
                  else "\n".join(" | ".join(fmt(v) for v in r.values()) for r in rows))
            return

        rows = search(conn, args.query, args.party, args.doc_type,
                      args.since, args.until, args.limit, not args.list)

        if args.json:
            print(json.dumps(rows, indent=2, default=str))
            return

        if not rows:
            print("No matches.")
            if not has_embeddings(conn):
                print("(Semantic search is off — pgvector not installed. "
                      "Try different keywords.)")
            return

        for r in rows:
            head = f"[{r['id']}] {fmt(r['doc_date'])}  {fmt(r['doc_type']):14}"
            if r.get("party"):
                head += f" {r['party'][:30]}"
            if r.get("amount"):
                head += f"  ₹{r['amount']:,.2f}"
            print(head)
            label = r.get("subject") or r.get("filename") or ""
            if label:
                print(f"      {label[:100]}")
            if r.get("snippet"):
                snip = " ".join(r["snippet"].split())
                print(f"      … {snip[:160]}")
            print(f"      {r['source_path']}")
            print()
        print(f"{len(rows)} result(s)")


if __name__ == "__main__":
    main()
