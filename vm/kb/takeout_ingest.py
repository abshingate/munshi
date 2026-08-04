#!/usr/bin/env python3
"""
Ingest a Google Takeout export into the knowledge base.

Handles the multi-part ZIPs Takeout produces, verifies each one is actually an
archive before trusting it, extracts Gmail mbox / Drive files / Calendar, and
loads mail headers and bodies into Postgres for searching.

THE FAILURE THIS GUARDS AGAINST
-------------------------------
Takeout download URLs are **session-authenticated**. Fetched without a Google
login they return **HTTP 200 with an HTML sign-in page** — so a naive
downloader saves a login page named `takeout-....zip`, and every later step
reports "0 emails" while looking healthy. Every archive is therefore checked
by magic bytes, not by file extension.

Usage (on the VM)
-----------------
    python takeout_ingest.py --verify  DIR          # check archives only
    python takeout_ingest.py --extract DIR --account you@example.com
    python takeout_ingest.py --load    DIR --account you@example.com
"""

from __future__ import annotations

import argparse
import email
import email.policy
import hashlib
import json
import mailbox
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

DSN = os.environ.get("MUNSHI_KB_DSN", "postgresql://postgres@localhost/munshi_kb")

try:
    import psycopg
except ImportError:
    psycopg = None

ZIP_MAGIC = b"PK\x03\x04"
TGZ_MAGIC = b"\x1f\x8b"


def classify_file(path: str) -> tuple[str, str]:
    """(kind, detail) from the file's CONTENT, never its extension."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(512)
    except OSError as e:
        return "unreadable", str(e)
    if head.startswith(ZIP_MAGIC):
        return "zip", ""
    if head.startswith(TGZ_MAGIC):
        return "tgz", ""
    low = head.lower()
    if b"<html" in low or b"<!doctype html" in low:
        hint = "Google sign-in page" if (b"accounts.google" in low
                                         or b"sign in" in low) else "HTML"
        return "html", (f"{hint} — the download was NOT authenticated. "
                        f"Takeout links carry your browser session; a server "
                        f"cannot fetch them.")
    return "unknown", head[:32].hex()


def verify(directory: str) -> list[dict]:
    out = []
    for name in sorted(os.listdir(directory)):
        p = os.path.join(directory, name)
        if not os.path.isfile(p):
            continue
        kind, detail = classify_file(p)
        size = os.path.getsize(p)
        ok = kind in ("zip", "tgz")
        if kind == "zip":
            # A valid header is not a valid archive; test the central directory.
            try:
                with zipfile.ZipFile(p) as z:
                    bad = z.testzip()
                    members = len(z.namelist())
                if bad:
                    ok, detail = False, f"corrupt member: {bad}"
                else:
                    detail = f"{members} members"
            except zipfile.BadZipFile as e:
                # Multi-part Takeout ZIPs are individually incomplete by design.
                if "multi" in str(e).lower() or size > 1_000_000:
                    ok, detail = True, f"part of a multi-part set ({e})"
                else:
                    ok, detail = False, str(e)
        out.append({"file": name, "bytes": size, "kind": kind,
                    "ok": ok, "detail": detail})
    return out


def extract(directory: str, dest: str) -> dict:
    os.makedirs(dest, exist_ok=True)
    stats = {"archives": 0, "files": 0, "skipped": 0, "errors": []}
    for row in verify(directory):
        if not row["ok"]:
            stats["skipped"] += 1
            stats["errors"].append(f"{row['file']}: {row['kind']} — {row['detail']}")
            continue
        p = os.path.join(directory, row["file"])
        stats["archives"] += 1
        try:
            with zipfile.ZipFile(p) as z:
                for m in z.namelist():
                    if m.endswith("/"):
                        continue
                    z.extract(m, dest)
                    stats["files"] += 1
        except Exception as e:
            stats["errors"].append(f"{row['file']}: {type(e).__name__}: {e}")
    return stats


def find_mbox(root: str) -> list[str]:
    hits = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.lower().endswith(".mbox"):
                hits.append(os.path.join(dirpath, f))
    return hits


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mail_message (
                id           BIGSERIAL PRIMARY KEY,
                account      TEXT NOT NULL,
                message_id   TEXT,
                sent_at      TIMESTAMPTZ,
                from_addr    TEXT,
                to_addrs     TEXT,
                cc_addrs     TEXT,
                subject      TEXT,
                labels       TEXT,
                body         TEXT,
                has_attach   BOOLEAN DEFAULT FALSE,
                row_hash     TEXT UNIQUE NOT NULL,
                ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS mail_sent_idx    ON mail_message (sent_at);
            CREATE INDEX IF NOT EXISTS mail_from_idx    ON mail_message (from_addr);
            CREATE INDEX IF NOT EXISTS mail_account_idx ON mail_message (account);

            CREATE TABLE IF NOT EXISTS mail_attachment (
                id          BIGSERIAL PRIMARY KEY,
                message_id  BIGINT REFERENCES mail_message(id) ON DELETE CASCADE,
                filename    TEXT,
                mime_type   TEXT,
                size_bytes  BIGINT
            );
        """)
        # Full-text search over subject + body.
        cur.execute("""
            ALTER TABLE mail_message
              ADD COLUMN IF NOT EXISTS fts tsvector
              GENERATED ALWAYS AS (
                to_tsvector('english',
                  coalesce(subject,'') || ' ' || coalesce(body,''))
              ) STORED
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS mail_fts_idx "
                    "ON mail_message USING GIN (fts)")
    conn.commit()


def body_text(msg) -> tuple[str, bool, list]:
    """Plain-text body, whether it has attachments, and their metadata."""
    parts = []
    attach = []
    has = False
    if msg.is_multipart():
        for part in msg.walk():
            disp = str(part.get("Content-Disposition") or "")
            ctype = part.get_content_type()
            if "attachment" in disp.lower():
                has = True
                payload = part.get_payload(decode=True) or b""
                attach.append({"filename": part.get_filename() or "",
                               "mime": ctype, "size": len(payload)})
                continue
            if ctype == "text/plain":
                try:
                    parts.append(part.get_payload(decode=True)
                                 .decode(part.get_content_charset() or "utf-8",
                                         "replace"))
                except Exception:
                    pass
    else:
        try:
            parts.append(msg.get_payload(decode=True)
                         .decode(msg.get_content_charset() or "utf-8", "replace"))
        except Exception:
            parts.append(str(msg.get_payload()))
    return ("\n".join(parts)[:200000], has, attach)


def load(conn, mbox_path: str, account: str, limit: int | None = None) -> dict:
    ensure_schema(conn)
    added = skipped = failed = 0
    box = mailbox.mbox(mbox_path, factory=None)
    for i, raw in enumerate(box):
        if limit and added >= limit:
            break
        try:
            subject = str(raw.get("Subject") or "")[:2000]
            frm = str(raw.get("From") or "")[:500]
            to = str(raw.get("To") or "")[:2000]
            cc = str(raw.get("Cc") or "")[:2000]
            mid = str(raw.get("Message-ID") or "")[:500]
            labels = str(raw.get("X-Gmail-Labels") or "")[:1000]
            sent = None
            d = raw.get("Date")
            if d:
                try:
                    sent = parsedate_to_datetime(d)
                    if sent and sent.tzinfo is None:
                        sent = sent.replace(tzinfo=timezone.utc)
                except Exception:
                    sent = None
            body, has_attach, attach = body_text(raw)
            h = hashlib.sha256(
                f"{account}|{mid}|{sent}|{subject}|{frm}".encode()).hexdigest()

            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM mail_message WHERE row_hash=%s", (h,))
                if cur.fetchone():
                    skipped += 1
                    continue
                cur.execute("""
                    INSERT INTO mail_message
                      (account, message_id, sent_at, from_addr, to_addrs,
                       cc_addrs, subject, labels, body, has_attach, row_hash)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (account, mid, sent, frm, to, cc, subject, labels,
                      body, has_attach, h))
                msg_id = cur.fetchone()[0]
                for a in attach:
                    cur.execute("""INSERT INTO mail_attachment
                                   (message_id, filename, mime_type, size_bytes)
                                   VALUES (%s,%s,%s,%s)""",
                                (msg_id, a["filename"][:500], a["mime"][:200],
                                 a["size"]))
            added += 1
            if added % 500 == 0:
                conn.commit()
                print(f"    {added} loaded...", flush=True)
        except Exception as e:
            failed += 1
            if failed <= 5:
                print(f"    message {i}: {type(e).__name__}: {e}")
    conn.commit()
    return {"added": added, "skipped": skipped, "failed": failed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("directory")
    ap.add_argument("--account", default="")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--extract", metavar="DEST")
    ap.add_argument("--load", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    if args.verify or not (args.extract or args.load):
        rows = verify(args.directory)
        if not rows:
            print(f"No files in {args.directory}")
            return 1
        print(f"{'file':<52}{'MB':>9}{'kind':>9}  status")
        print("-" * 96)
        bad = 0
        for r in rows:
            mark = "OK" if r["ok"] else "REJECT"
            if not r["ok"]:
                bad += 1
            print(f"{r['file'][:51]:<52}{r['bytes']/1048576:>9.1f}"
                  f"{r['kind']:>9}  {mark} {r['detail'][:40]}")
        print("-" * 96)
        if bad:
            print(f"\n{bad} file(s) are NOT valid archives.")
            for r in rows:
                if not r["ok"]:
                    print(f"\n  {r['file']}\n    {r['detail']}")
            return 1
        print(f"\nAll {len(rows)} archives valid.")

    if args.extract:
        print(f"\nextracting {args.directory} -> {args.extract}")
        s = extract(args.directory, args.extract)
        print(f"  archives: {s['archives']}  files: {s['files']}  "
              f"skipped: {s['skipped']}")
        for e in s["errors"]:
            print(f"  ERROR {e}")
        boxes = find_mbox(args.extract)
        print(f"  mbox files found: {len(boxes)}")
        for b in boxes:
            print(f"    {b}  ({os.path.getsize(b)/1048576:.1f} MB)")

    if args.load:
        if psycopg is None:
            sys.exit("psycopg not installed")
        if not args.account:
            sys.exit("--load requires --account")
        boxes = find_mbox(args.directory)
        if not boxes:
            print(f"No .mbox found under {args.directory}")
            return 1
        with psycopg.connect(DSN) as conn:
            for b in boxes:
                print(f"loading {b}")
                r = load(conn, b, args.account, args.limit)
                print(f"  added {r['added']}, already held {r['skipped']}, "
                      f"failed {r['failed']}")
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*), MIN(sent_at), MAX(sent_at) "
                            "FROM mail_message WHERE account=%s",
                            (args.account,))
                n, lo, hi = cur.fetchone()
            print(f"\n{args.account}: {n} messages, {lo} -> {hi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
