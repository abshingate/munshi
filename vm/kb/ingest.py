#!/usr/bin/env python3
"""
Munshi knowledge base — ingestion pipeline (ADR-0020).

Reads exports you run yourself (Google Takeout mbox, a Drive folder, any
directory of files), extracts text and metadata, and loads them into
PostgreSQL where SQL, full-text and semantic search all work on the same rows.

Idempotent: documents are keyed by SHA-256 of their bytes, so re-running an
import never duplicates. Re-export and re-run whenever you want a refresh.

Usage
-----
    python ingest.py --source gmail-takeout --path ~/Takeout/Mail/business.mbox
    python ingest.py --source filesystem    --path /data/invoices
    python ingest.py --embed                       # generate embeddings
    python ingest.py --stats                       # what's in the index

Nothing here is jurisdiction- or product-specific: `doc_type` and `party` are
free text, and per-source extras go in the JSONB `metadata` column.
"""

import argparse
import email
import email.policy
import hashlib
import mailbox
import os
import re
import sys
from datetime import datetime, date
from pathlib import Path

try:
    import psycopg
except ImportError:
    sys.exit("psycopg not installed. Run: pip install 'psycopg[binary]'")

DB = os.environ.get("MUNSHI_KB_DSN", "postgresql://postgres@localhost/munshi_kb")

# Text extraction is best-effort: a missing optional library degrades that
# format to metadata-only rather than failing the whole import.
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
try:
    import docx
except ImportError:
    docx = None
try:
    import openpyxl
except ImportError:
    openpyxl = None
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_pdf(path):
    if not PdfReader:
        return "", None
    try:
        reader = PdfReader(str(path))
        pages = [p.extract_text() or "" for p in reader.pages]
        return "\n".join(pages), len(reader.pages)
    except Exception:
        return "", None


def extract_docx(path):
    if not docx:
        return "", None
    try:
        d = docx.Document(str(path))
        return "\n".join(p.text for p in d.paragraphs), None
    except Exception:
        return "", None


def extract_xlsx(path):
    if not openpyxl:
        return "", None
    try:
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        out = []
        for ws in wb.worksheets:
            out.append(f"# {ws.title}")
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None]
                if cells:
                    out.append("\t".join(cells))
        return "\n".join(out), None
    except Exception:
        return "", None


def extract_html(raw):
    if not BeautifulSoup:
        return re.sub(r"<[^>]+>", " ", raw)
    return BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)


def clean_text(text):
    """Strip characters PostgreSQL text columns reject.

    PDF extraction routinely emits NUL (0x00) bytes and other control
    characters; Postgres refuses them outright. Found by ingesting real
    scanned challans — worth keeping.
    """
    if not text:
        return text
    text = text.replace("\x00", "")
    return "".join(ch for ch in text if ch >= " " or ch in "\n\r\t")


def extract_text(path):
    """Return (text, page_count) for a file on disk."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text, pages = extract_pdf(path)
    elif suffix in (".docx", ".doc"):
        text, pages = extract_docx(path)
    elif suffix in (".xlsx", ".xls"):
        text, pages = extract_xlsx(path)
    elif suffix in (".txt", ".csv", ".md", ".json", ".xml"):
        try:
            text, pages = path.read_text(errors="replace"), None
        except Exception:
            text, pages = "", None
    elif suffix in (".html", ".htm"):
        try:
            text, pages = extract_html(path.read_text(errors="replace")), None
        except Exception:
            text, pages = "", None
    else:
        text, pages = "", None  # images etc: metadata-only, still findable by filename
    return clean_text(text), pages


# ---------------------------------------------------------------------------
# Heuristics — deliberately simple and overridable
# ---------------------------------------------------------------------------

AMOUNT_RE = re.compile(r"(?:₹|INR|Rs\.?)\s*([\d,]+(?:\.\d{1,2})?)", re.I)


def guess_amount(text):
    """Largest currency-looking figure in the text. A hint for filtering, not
    an accounting figure — never treat this as authoritative."""
    if not text:
        return None
    vals = []
    for m in AMOUNT_RE.finditer(text[:20000]):
        try:
            vals.append(float(m.group(1).replace(",", "")))
        except ValueError:
            pass
    return max(vals) if vals else None


DOC_TYPE_HINTS = [
    ("invoice", r"\b(tax\s+invoice|invoice\s*(no|#))"),
    ("bank-statement", r"\b(statement of account|account statement|detailed statement)\b"),
    ("challan", r"\bchallan\b"),
    ("return", r"\b(return|acknowledg)"),
    ("contract", r"\b(agreement|licence|license|contract)\b"),
]


def guess_doc_type(filename, text):
    blob = f"{filename}\n{(text or '')[:5000]}".lower()
    for label, pattern in DOC_TYPE_HINTS:
        if re.search(pattern, blob, re.I):
            return label
    return None


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def chunk_text(text, size=1500, overlap=200):
    """Split on paragraph boundaries where possible; overlap so a sentence
    spanning a boundary is still retrievable from one chunk."""
    if not text or not text.strip():
        return []
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(text) <= size:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            para = text.rfind("\n\n", start, end)
            if para > start + size // 2:
                end = para
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def connect():
    return psycopg.connect(DB)


def has_embeddings(conn):
    """True when migration 002 has run and pgvector is present.

    The knowledge base is fully usable without it (SQL + full-text search);
    only semantic search needs the column. Every caller must degrade rather
    than fail — see ADR-0020.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='kb_chunk' AND column_name='embedding'"
        )
        return cur.fetchone() is not None


def create_source(conn, kind, label, location):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO kb_source (kind, label, location) VALUES (%s,%s,%s) RETURNING id",
            (kind, label, location),
        )
        return cur.fetchone()[0]


def insert_document(conn, source_id, doc):
    """Insert one document plus its chunks. Returns True if newly inserted,
    False if the content hash was already present."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM kb_document WHERE content_hash=%s", (doc["content_hash"],))
        if cur.fetchone():
            return False

        cur.execute(
            """INSERT INTO kb_document
               (source_id, content_hash, source_path, filename, doc_type, mime_type,
                doc_date, party, subject, sender, recipients, amount,
                message_id, thread_id, in_reply_to, body_text, page_count, metadata)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING id""",
            (
                source_id, doc["content_hash"], doc["source_path"], doc.get("filename"),
                doc.get("doc_type"), doc.get("mime_type"), doc.get("doc_date"),
                doc.get("party"), doc.get("subject"), doc.get("sender"),
                doc.get("recipients"), doc.get("amount"), doc.get("message_id"),
                doc.get("thread_id"), doc.get("in_reply_to"), doc.get("body_text"),
                doc.get("page_count"), psycopg.types.json.Jsonb(doc.get("metadata", {})),
            ),
        )
        doc_id = cur.fetchone()[0]

        for i, chunk in enumerate(chunk_text(doc.get("body_text") or "")):
            cur.execute(
                "INSERT INTO kb_chunk (document_id, chunk_index, content, token_count) "
                "VALUES (%s,%s,%s,%s)",
                (doc_id, i, chunk, len(chunk) // 4),  # ~4 chars/token, good enough for budgeting
            )
    return True


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def parse_email_date(msg):
    try:
        dt = email.utils.parsedate_to_datetime(msg.get("Date"))
        return dt.date() if dt else None
    except Exception:
        return None


def body_of(msg):
    """Plain text body, falling back to stripped HTML."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                try:
                    return part.get_content()
                except Exception:
                    pass
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                try:
                    return extract_html(part.get_content())
                except Exception:
                    pass
        return ""
    try:
        content = msg.get_content()
        return extract_html(content) if msg.get_content_type() == "text/html" else content
    except Exception:
        return ""


def ingest_mbox(conn, source_id, mbox_path, attach_dir):
    """Ingest an mbox: one row per message, plus one row per attachment.

    Attachments are written to disk (documents stay the source of truth,
    ADR-0012) and indexed with a link back to their parent message.
    """
    attach_dir = Path(attach_dir)
    attach_dir.mkdir(parents=True, exist_ok=True)
    box = mailbox.mbox(str(mbox_path), factory=lambda f: email.message_from_binary_file(f, policy=email.policy.default))

    added = skipped = attachments = 0
    for key in box.keys():
        try:
            msg = box[key]
        except Exception:
            continue

        subject = str(msg.get("Subject") or "")
        sender = str(msg.get("From") or "")
        to = [t.strip() for t in str(msg.get("To") or "").split(",") if t.strip()]
        body = clean_text(body_of(msg) or "")
        msg_id = str(msg.get("Message-ID") or "")
        raw = (msg_id + subject + sender + body[:5000]).encode("utf-8", "replace")

        doc = {
            "content_hash": sha256_bytes(raw),
            "source_path": f"{mbox_path}#{msg_id}",
            "filename": None,
            "doc_type": "email",
            "mime_type": "message/rfc822",
            "doc_date": parse_email_date(msg),
            "party": sender.split("<")[0].strip().strip('"') or None,
            "subject": subject,
            "sender": sender,
            "recipients": to,
            "amount": guess_amount(body),
            "message_id": msg_id,
            "thread_id": str(msg.get("References") or msg.get("In-Reply-To") or msg_id).split()[0] if (msg.get("References") or msg.get("In-Reply-To") or msg_id) else None,
            "in_reply_to": str(msg.get("In-Reply-To") or "") or None,
            "body_text": body,
            "metadata": {"labels": str(msg.get("X-Gmail-Labels") or "")},
        }
        if insert_document(conn, source_id, doc):
            added += 1
        else:
            skipped += 1

        # Attachments: save to disk, index with the parent's context.
        if msg.is_multipart():
            for part in msg.walk():
                filename = part.get_filename()
                if not filename or "attachment" not in str(part.get("Content-Disposition")):
                    continue
                try:
                    payload = part.get_payload(decode=True)
                except Exception:
                    continue
                if not payload:
                    continue
                safe = re.sub(r"[^\w\-. ]", "_", filename)[:120]
                digest = sha256_bytes(payload)
                out = attach_dir / f"{digest[:12]}_{safe}"
                if not out.exists():
                    out.write_bytes(payload)
                text, pages = extract_text(out)
                adoc = {
                    "content_hash": digest,
                    "source_path": str(out),
                    "filename": filename,
                    "doc_type": guess_doc_type(filename, text) or "attachment",
                    "mime_type": part.get_content_type(),
                    "doc_date": parse_email_date(msg),
                    "party": sender.split("<")[0].strip().strip('"') or None,
                    "subject": subject,
                    "sender": sender,
                    "recipients": to,
                    "amount": guess_amount(text),
                    "message_id": msg_id,
                    "thread_id": doc["thread_id"],
                    "body_text": text,
                    "page_count": pages,
                    "metadata": {"from_email": True, "parent_subject": subject},
                }
                if insert_document(conn, source_id, adoc):
                    attachments += 1

        if (added + skipped) % 200 == 0:
            conn.commit()
            print(f"  ... {added} new, {skipped} existing, {attachments} attachments", flush=True)

    conn.commit()
    return added, skipped, attachments


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".terraform"}


def ingest_filesystem(conn, source_id, root):
    root = Path(root)
    added = skipped = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        if any(p in SKIP_DIRS for p in path.parts):
            continue
        try:
            data = path.read_bytes()
        except Exception:
            continue
        text, pages = extract_text(path)
        stat = path.stat()
        doc = {
            "content_hash": sha256_bytes(data),
            "source_path": str(path),
            "filename": path.name,
            "doc_type": guess_doc_type(path.name, text),
            "mime_type": None,
            "doc_date": date.fromtimestamp(stat.st_mtime),
            "amount": guess_amount(text),
            "body_text": text,
            "page_count": pages,
            "metadata": {"size_bytes": stat.st_size, "relative_to": str(root)},
        }
        if insert_document(conn, source_id, doc):
            added += 1
        else:
            skipped += 1
        if (added + skipped) % 100 == 0:
            conn.commit()
            print(f"  ... {added} new, {skipped} existing", flush=True)
    conn.commit()
    return added, skipped, 0


# ---------------------------------------------------------------------------
# Embeddings — optional; provider-agnostic by design (ADR-0010 seam)
# ---------------------------------------------------------------------------

def embed_pending(conn, batch=64):
    """Embed chunks that have no vector yet.

    Provider is chosen by env var so no vendor is hard-coded:
      MUNSHI_EMBED_PROVIDER = openai (default) | none
      MUNSHI_EMBED_MODEL    = text-embedding-3-small
      OPENAI_API_KEY        = ...
    """
    if not has_embeddings(conn):
        print("Semantic search is not enabled on this database.\n"
              "  pgvector is not installed, so kb_chunk has no embedding column.\n"
              "  Install pgvector, then apply migrations/002_pgvector_embeddings.sql\n"
              "  and re-run this command. SQL and full-text search work meanwhile.")
        return 0

    provider = os.environ.get("MUNSHI_EMBED_PROVIDER", "openai").lower()
    if provider == "none":
        print("Embedding disabled (MUNSHI_EMBED_PROVIDER=none). "
              "SQL and full-text search still work.")
        return 0
    model = os.environ.get("MUNSHI_EMBED_MODEL", "text-embedding-3-small")

    if provider == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            sys.exit("pip install openai  (or set MUNSHI_EMBED_PROVIDER=none)")
        if not os.environ.get("OPENAI_API_KEY"):
            sys.exit("OPENAI_API_KEY not set (or set MUNSHI_EMBED_PROVIDER=none)")
        client = OpenAI()

        def embed(texts):
            resp = client.embeddings.create(model=model, input=texts)
            return [d.embedding for d in resp.data]
    else:
        sys.exit(f"Unknown MUNSHI_EMBED_PROVIDER: {provider}")

    total = 0
    while True:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, content FROM kb_chunk WHERE embedding IS NULL LIMIT %s", (batch,)
            )
            rows = cur.fetchall()
            if not rows:
                break
            vectors = embed([r[1][:8000] for r in rows])
            for (cid, _), vec in zip(rows, vectors):
                cur.execute(
                    "UPDATE kb_chunk SET embedding=%s, embedding_model=%s WHERE id=%s",
                    (str(vec), model, cid),
                )
        conn.commit()
        total += len(rows)
        print(f"  embedded {total}", flush=True)
    return total


def show_stats(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM kb_document")
        docs = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM kb_chunk")
        chunks = cur.fetchone()[0]
        print(f"Documents : {docs}")
        if has_embeddings(conn):
            cur.execute("SELECT count(*) FROM kb_chunk WHERE embedding IS NOT NULL")
            print(f"Chunks    : {chunks}  ({cur.fetchone()[0]} embedded)")
        else:
            print(f"Chunks    : {chunks}")
            print("Semantic search: unavailable (pgvector not installed — "
                  "run migration 002 to enable). SQL and full-text search work.")
        cur.execute(
            "SELECT coalesce(doc_type,'(none)'), count(*) FROM kb_document "
            "GROUP BY 1 ORDER BY 2 DESC LIMIT 15"
        )
        print("\nBy type:")
        for t, n in cur.fetchall():
            print(f"  {t:20} {n}")
        cur.execute("SELECT min(doc_date), max(doc_date) FROM kb_document WHERE doc_date IS NOT NULL")
        lo, hi = cur.fetchone()
        if lo:
            print(f"\nDate range: {lo} → {hi}")


def main():
    ap = argparse.ArgumentParser(description="Munshi knowledge base ingestion")
    ap.add_argument("--source", choices=["gmail-takeout", "drive-takeout", "filesystem", "tally"])
    ap.add_argument("--path")
    ap.add_argument("--label", help="note recorded against this import run")
    ap.add_argument("--attachments", default=r"C:\TallyData\KnowledgeBase\attachments")
    ap.add_argument("--embed", action="store_true", help="embed chunks lacking vectors")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    with connect() as conn:
        if args.stats:
            show_stats(conn)
            return
        if args.embed:
            n = embed_pending(conn)
            print(f"Embedded {n} chunks.")
            return
        if not args.source or not args.path:
            ap.error("--source and --path are required (or use --stats / --embed)")

        src = Path(args.path)
        if not src.exists():
            sys.exit(f"Not found: {src}")

        source_id = create_source(conn, args.source, args.label or src.name, str(src))
        print(f"Ingesting {args.source} from {src} ...")

        if args.source == "gmail-takeout":
            added, skipped, att = ingest_mbox(conn, source_id, src, args.attachments)
        else:
            added, skipped, att = ingest_filesystem(conn, source_id, src)

        with conn.cursor() as cur:
            cur.execute("UPDATE kb_source SET document_count=%s WHERE id=%s", (added, source_id))
        conn.commit()

        print(f"\nDone. {added} new, {skipped} already present"
              + (f", {att} attachments" if att else ""))
        print("Next: python ingest.py --embed     (optional, enables semantic search)")


if __name__ == "__main__":
    main()
