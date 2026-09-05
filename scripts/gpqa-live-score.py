#!/usr/bin/env python3

import os
import re
import json
import time
import argparse
from numbers import Integral

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

from datasets import load_dataset
try:
    from datasets.utils.logging import disable_progress_bar
    disable_progress_bar()
except Exception:
    pass

from lm_eval.tasks.gpqa.generative.utils import process_docs


LOG = "/media/nowr/Data/Evals/qwen38-gsq/live/gpqa-diamond-full-xhigh-64k-noquestion.jsonl"
CACHE = "/media/nowr/Data/AI-Cache/huggingface/datasets"
TOTAL = 198


def norm_text(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def target_letter(v):
    if isinstance(v, Integral):
        i = int(v)
        if 0 <= i <= 3:
            return "ABCD"[i]

    s = str(v).strip().upper()

    m = re.search(r"\(([A-D])\)", s)
    if m:
        return m.group(1)

    if s in ("A", "B", "C", "D"):
        return s

    try:
        i = int(s)
        if 0 <= i <= 3:
            return "ABCD"[i]
    except Exception:
        pass

    return None


def content_to_text(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        out = []
        for x in content:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict):
                t = x.get("text")
                if isinstance(t, str):
                    out.append(t)
        return "\n".join(out)

    return str(content or "")


def request_text(req):
    out = []
    for m in req.get("messages", []):
        out.append(content_to_text(m.get("content")))
    return "\n".join(out)


def official_extract(text):
    # Mirrors the important part of GPQA flexible extraction:
    # parenthesized multiple-choice answer such as (A), (B), ...
    hits = re.findall(r"\(([A-D])\)", text or "", flags=re.I)
    return hits[-1].upper() if hits else None


def normalized_extract(text):
    # Diagnostic extraction: more tolerant than the benchmark parser.
    s = str(text or "")

    # First accept the ordinary "(A)" / "(B)" / ... form.
    p = official_extract(s)
    if p:
        return p

    patterns = [
        # LaTeX boxed answers:
        # \boxed{C}
        # \boxed{\text{C}}
        # \boxed{\mathrm{C}}
        # \boxed{\mathbf{C}}
        r"^\s*(?:\*\*)?\s*([A-D])\s*[\)\].:：-]\s*\S.*$",
        r"\\boxed\s*\{\s*\\(?:text|mathrm|mathbf|operatorname)\s*\{\s*([A-D])\s*\}\s*\}",
        r"\\boxed\s*\{\s*([A-D])\s*\}",

        # Natural-language final answer forms
        r"(?:final\s+answer|correct\s+answer|correct\s+choice|answer)"
        r"\s*(?:is|:)?\s*(?:\*\*)?\s*[\(\[]?([A-D])[\)\]]?(?:\*\*)?",

        # A bare option
        r"^\s*(?:\*\*)?\s*[\(\[]?([A-D])[\)\]]?(?:\*\*)?\s*[.!:]?\s*$",
    ]

    for pat in patterns:
        matches = re.findall(pat, s, flags=re.I | re.M)
        if matches:
            return matches[-1].upper()

    return None


print("Loading GPQA-Diamond from local cache...")

raw = load_dataset(
    "Idavidrein/gpqa",
    "gpqa_diamond",
    split="train",
    cache_dir=CACHE,
)

import random
random.seed(0)
processed = process_docs(raw)
docs = list(processed)

doc_index = []
for i, d in enumerate(docs):
    q = norm_text(d.get("Question"))
    tgt = target_letter(d.get("answer"))
    doc_index.append((i, q, tgt))

print(f"Loaded {len(doc_index)} processed GPQA-Diamond questions.")


def find_doc(req):
    p = norm_text(request_text(req))

    matches = []
    for doc_id, q, tgt in doc_index:
        if q and q in p:
            matches.append((len(q), doc_id, tgt))

    if not matches:
        return None, None

    # Longest match wins, avoids accidental short substring collisions.
    _, doc_id, tgt = max(matches)
    return doc_id, tgt


def score_once():
    if not os.path.exists(LOG):
        print("Live log not created yet:")
        print(LOG)
        return

    attempts = 0
    http_errors = 0
    unmatched = 0

    # doc_id -> latest successful response
    results = {}

    with open(LOG, encoding="utf-8") as f:
        for line in f:
            try:
                x = json.loads(line)
            except Exception:
                continue

            attempts += 1

            status = x.get("status")
            if status != 200:
                http_errors += 1
                continue

            doc_id, target = find_doc(x.get("request", {}))

            if doc_id is None:
                unmatched += 1
                continue

            resp = x.get("response", {})
            choices = resp.get("choices") or [{}]
            c = choices[0]
            msg = c.get("message") or {}
            usage = resp.get("usage") or {}

            final = content_to_text(msg.get("content")).strip()
            reasoning = content_to_text(msg.get("reasoning_content"))

            pred_official = official_extract(final)
            pred_norm = normalized_extract(final)

            results[doc_id] = {
                "seq": x.get("seq"),
                "target": target,
                "official": pred_official,
                "normalized": pred_norm,
                "final": final,
                "reasoning_chars": len(reasoning),
                "final_chars": len(final),
                "tokens": usage.get("completion_tokens"),
                "finish": c.get("finish_reason"),
            }

    completed = len(results)
    empty = sum(not r["final"] for r in results.values())
    invalid_official = sum(r["official"] is None for r in results.values())

    official_correct = sum(
        r["official"] is not None
        and r["target"] is not None
        and r["official"] == r["target"]
        for r in results.values()
    )

    normalized_correct = sum(
        r["normalized"] is not None
        and r["target"] is not None
        and r["normalized"] == r["target"]
        for r in results.values()
    )

    length_stops = sum(
        r["finish"] == "length"
        for r in results.values()
    )

    near_64k = sum(
        isinstance(r["tokens"], (int, float))
        and r["tokens"] >= 63000
        for r in results.values()
    )

    toks = [
        int(r["tokens"])
        for r in results.values()
        if isinstance(r["tokens"], (int, float))
    ]

    print("=" * 76)
    print("GPQA-Diamond LIVE")
    print("=" * 76)
    print(f"Completed unique      : {completed}/{TOTAL}")
    print(f"Pending               : {TOTAL-completed}")
    print(f"API attempts          : {attempts}")
    print(f"HTTP errors/retries   : {http_errors}")
    print(f"Unmatched responses   : {unmatched}")
    print()
    print(f"Empty final           : {empty}/{completed}" if completed else "Empty final           : 0")
    print(f"Invalid official parse: {invalid_official}/{completed}" if completed else "Invalid official parse: 0")
    print()

    if completed:
        print(
            f"Official live score   : {official_correct}/{completed} "
            f"= {100*official_correct/completed:.2f}%"
        )
        print(
            f"Normalized live score : {normalized_correct}/{completed} "
            f"= {100*normalized_correct/completed:.2f}%"
        )

    print()
    print(f"finish_reason=length  : {length_stops}")
    print(f">=63K completion      : {near_64k}")

    if toks:
        print(f"Average completion    : {sum(toks)/len(toks):.0f} tokens")
        print(f"Max completion        : {max(toks)} tokens")

    print()
    print("Latest completed questions")
    print("-" * 100)
    print(
        f"{'doc':>4} {'tgt':>3} {'pred':>4} {'norm':>4} "
        f"{'off':>3} {'diag':>4} {'tokens':>7} {'finish':>7}  final"
    )
    print("-" * 100)

    ordered = sorted(
        results.items(),
        key=lambda z: (z[1]["seq"] if z[1]["seq"] is not None else -1)
    )[-12:]

    for doc_id, r in ordered:
        off_ok = (
            "✓" if r["official"] is not None
            and r["official"] == r["target"] else "✗"
        )
        norm_ok = (
            "✓" if r["normalized"] is not None
            and r["normalized"] == r["target"] else "✗"
        )

        final_preview = r["final"].replace("\n", " ")[:55]
        if not final_preview:
            final_preview = "<EMPTY>"

        print(
            f"{doc_id:>4} "
            f"{str(r['target'] or '-'):>3} "
            f"{str(r['official'] or '-'):>4} "
            f"{str(r['normalized'] or '-'):>4} "
            f"{off_ok:>3} "
            f"{norm_ok:>4} "
            f"{str(r['tokens'] or '-'):>7} "
            f"{str(r['finish'] or '-'):>7}  "
            f"{final_preview}"
        )


parser = argparse.ArgumentParser()
parser.add_argument("--watch", type=float, default=0)
args = parser.parse_args()

while True:
    if args.watch:
        print("\033[2J\033[H", end="")

    score_once()

    if not args.watch:
        break

    print(f"\nRefreshing every {args.watch:g}s — Ctrl+C to exit scorer only.")
    time.sleep(args.watch)
