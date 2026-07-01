#!/usr/bin/env python3
"""Cluster unprocessed reader feedback into pending proposals for editor review.

Uses scripts/feedback_db.mjs for Postgres I/O (postgres npm package already in repo).
Run: POSTGRES_URL=... python3 scripts/process_feedback.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_CLI = ROOT / "scripts" / "feedback_db.mjs"

MIN_LEN = 15
JACCARD_THRESHOLD = 0.55

CATEGORY_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("coverage", re.compile(r"\b(miss(ed|ing)?|cover(age)?|story|stories|topic|event|earnings|ticker)\b", re.I)),
    ("depth", re.compile(r"\b(deep(er|th)?|detail|long(er|er)?|shorter|skim|verbose|summary|brief)\b", re.I)),
    ("format", re.compile(r"\b(format|layout|design|ui|ux|mobile|chart|graph|visual|font|readability|nav)\b", re.I)),
    ("sources", re.compile(r"\b(source|outlet|wsj|bloomberg|economist|nyt|cnbc|ft|atlantic|rss|feed)\b", re.I)),
    ("sections", re.compile(r"\b(section|add a|new column|ondeck|quiz|verdict|narrative|archive)\b", re.I)),
]


def db_cmd(*args: str, stdin: dict | list | None = None) -> object:
    env = None
    proc = subprocess.run(
        ["node", str(DB_CLI), *args],
        input=json.dumps(stdin) if stdin is not None else None,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "feedback_db.mjs failed")
    return json.loads(proc.stdout or "null")


def extract_text(row: dict) -> str | None:
    parts = [row.get("missing") or "", row.get("open") or ""]
    text = " ".join(p.strip() for p in parts if p and str(p).strip()).strip()
    if len(text) < MIN_LEN:
        return None
    if not re.search(r"[a-zA-Z]", text):
        return None
    return text


def normalize(text: str) -> str:
    t = text.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def word_set(text: str) -> set[str]:
    return {w for w in normalize(text).split() if len(w) > 2}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def categorize(text: str) -> str:
    for cat, pat in CATEGORY_RULES:
        if pat.search(text):
            return cat
    return "features"


def title_from_text(text: str) -> str:
    t = text.strip()
    if len(t) <= 72:
        return t[0].upper() + t[1:] if t else t
    cut = t[:72]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut[0].upper() + cut[1:] + "…"


def summary_from_cluster(texts: list[str]) -> str:
    n = len(texts)
    if n == 1:
        return texts[0][:240]
    return f"{n} readers suggested similar changes: " + texts[0][:160] + ("…" if len(texts[0]) > 160 else "")


def cluster_items(items: list[dict]) -> list[dict]:
    clusters: list[dict] = []
    for item in items:
        words = word_set(item["text"])
        placed = False
        for cluster in clusters:
            if jaccard(words, cluster["words"]) >= JACCARD_THRESHOLD:
                cluster["items"].append(item)
                cluster["words"] |= words
                placed = True
                break
        if not placed:
            clusters.append({"words": words, "items": [item]})
    return clusters


def main() -> int:
    rows = db_cmd("unprocessed")
    if not rows:
        print("No unprocessed feedback.")
        return 0

    seen_norm: set[str] = set()
    valid: list[dict] = []
    skipped = 0
    for row in rows:
        text = extract_text(row)
        if not text:
            skipped += 1
            continue
        norm = normalize(text)
        if norm in seen_norm:
            skipped += 1
            continue
        seen_norm.add(norm)
        valid.append({"id": row["id"], "text": text, "category_hint": categorize(text)})

    if not valid:
        print(f"Nothing valid to cluster ({skipped} skipped).")
        ids = [r["id"] for r in rows]
        db_cmd("mark-processed", stdin=ids)
        return 0

    clusters = cluster_items(valid)
    created = 0
    processed_ids: list[int] = []

    for cluster in clusters:
        texts = [i["text"] for i in cluster["items"]]
        ids = [i["id"] for i in cluster["items"]]
        processed_ids.extend(ids)
        cats = [i["category_hint"] for i in cluster["items"]]
        category = max(set(cats), key=cats.count)
        title = title_from_text(texts[0])
        summary = summary_from_cluster(texts)
        pid = db_cmd(
            "insert-proposal",
            stdin={
                "title": title,
                "summary": summary,
                "category": category,
                "status": "pending",
                "source_feedback_ids": ids,
            },
        )
        print(f"  proposal #{pid['id']} [{category}] {title} ({len(ids)} source(s))")
        created += 1

    # Mark invalid/skipped rows processed too so they don't re-queue forever
    all_ids = [r["id"] for r in rows]
    unclustered = [i for i in all_ids if i not in processed_ids]
    processed_ids.extend(unclustered)
    db_cmd("mark-processed", stdin=processed_ids)

    print(f"Created {created} pending proposal(s); marked {len(all_ids)} feedback row(s) processed ({skipped} invalid/skipped).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
