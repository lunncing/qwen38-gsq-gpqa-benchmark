#!/usr/bin/env python3

import argparse
import json
import os
import re
import time

TOTAL = 198
BASELINE_SUBMITTED_CORRECT = 169
RETRY_IDS = [8, 71, 79, 88, 118, 127, 130, 145]

# All eight retry-triggering 64K attempts were incorrect under the
# Submitted-answer metric. Seven had no final answer; doc118 submitted A
# against target D. Keeping this explicit makes the unconditional
# replacement rule easy to audit.
BASELINE_RETRY_CORRECT = {
    8: False,
    71: False,
    79: False,
    88: False,
    118: False,
    127: False,
    130: False,
    145: False,
}

DEFAULT_LOG = (
    "/media/nowr/Data/Evals/qwen38-gsq/length-retry-128k/"
    "gpqa-length-retry-128k.jsonl"
)

# Only add an entry here after manually confirming that the model's actual
# submitted answer was unambiguous but the deterministic extractor missed it.
# Example: {123: "C"}
RETRY_SUBMITTED_OVERRIDES = {}


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


def target_letter(v):
    s = str(v or "").strip().upper()
    m = re.search(r"\(([A-D])\)", s)
    if m:
        return m.group(1)
    if s in {"A", "B", "C", "D"}:
        return s
    return None


def extract_answer(text):
    """Deterministic tolerant extraction from the final answer text."""
    s = str(text or "")

    patterns = [
        r"\\boxed\s*\{\s*\\(?:text|mathrm|mathbf|operatorname)\s*\{\s*([A-D])\s*\}\s*\}",
        r"\\boxed\s*\{\s*([A-D])\s*\}",
        r"(?:final\s+answer|correct\s+answer|correct\s+choice|answer)"
        r"\s*(?:is|:)?\s*(?:\*\*)?\s*[\(\[]?([A-D])[\)\]]?(?:\*\*)?",
        r"^\s*(?:\*\*)?\s*([A-D])\s*[\)\].:：-]\s*\S.*$",
        r"^\s*(?:\*\*)?\s*[\(\[]?([A-D])[\)\]]?(?:\*\*)?\s*[.!:]?\s*$",
    ]

    for pat in patterns:
        matches = re.findall(pat, s, flags=re.I | re.M)
        if matches:
            return matches[-1].upper()

    # Parenthesized options are deliberately checked last here. Long reasoning
    # may contain many intermediate (A)/(B)/(C)/(D) references; if no explicit
    # final-answer form exists, the last parenthesized option is only a fallback.
    hits = re.findall(r"\(([A-D])\)", s, flags=re.I)
    return hits[-1].upper() if hits else None


def load_latest_successful(path):
    latest = {}
    attempts = 0
    http_errors = 0

    if not os.path.exists(path):
        return latest, attempts, http_errors

    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                x = json.loads(line)
            except Exception:
                continue

            attempts += 1
            if x.get("status") != 200:
                http_errors += 1
                continue

            try:
                doc_id = int(x.get("doc_id"))
            except Exception:
                continue

            if doc_id not in RETRY_IDS:
                continue

            resp = x.get("response") or {}
            choice = (resp.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            usage = resp.get("usage") or {}

            final = content_to_text(msg.get("content")).strip()
            target = target_letter(x.get("target"))
            pred = RETRY_SUBMITTED_OVERRIDES.get(doc_id) or extract_answer(final)

            latest[doc_id] = {
                "target": target,
                "pred": pred,
                "final": final,
                "finish": choice.get("finish_reason"),
                "tokens": usage.get("completion_tokens"),
            }

    return latest, attempts, http_errors


def score_once(path):
    latest, attempts, http_errors = load_latest_successful(path)

    completed = len(latest)
    pending = len(RETRY_IDS) - completed

    adaptive_correct = BASELINE_SUBMITTED_CORRECT
    rescued = 0
    became_wrong = 0
    still_wrong = 0
    retry_correct_count = 0
    length_again = 0

    rows = []

    for doc_id in RETRY_IDS:
        baseline_ok = BASELINE_RETRY_CORRECT[doc_id]
        r = latest.get(doc_id)

        if r is None:
            rows.append((doc_id, "-", "-", "-", "pending", "-", ""))
            continue

        target = r["target"]
        pred = r["pred"]
        retry_ok = target is not None and pred is not None and pred == target

        adaptive_correct += int(retry_ok) - int(baseline_ok)
        retry_correct_count += int(retry_ok)

        if not baseline_ok and retry_ok:
            rescued += 1
        elif baseline_ok and not retry_ok:
            became_wrong += 1
        elif not baseline_ok and not retry_ok:
            still_wrong += 1

        if r["finish"] == "length":
            length_again += 1

        result = "✓" if retry_ok else "✗"
        preview = r["final"].replace("\n", " ")[:72]
        rows.append(
            (
                doc_id,
                target or "-",
                pred or "-",
                str(r["tokens"] or "-"),
                str(r["finish"] or "-"),
                result,
                preview,
            )
        )

    # Since all pending retry-trigger items were baseline-wrong, the maximum
    # possible final score is the current adaptive score plus all pending items.
    max_possible = adaptive_correct + sum(
        1 for doc_id in RETRY_IDS
        if doc_id not in latest and not BASELINE_RETRY_CORRECT[doc_id]
    )

    print("=" * 96)
    print("GPQA-Diamond Adaptive Submitted-answer — 64K → 128K-on-length")
    print("=" * 96)
    print(f"Retry log              : {path}")
    print(f"64K Submitted baseline : {BASELINE_SUBMITTED_CORRECT}/{TOTAL} = "
          f"{100*BASELINE_SUBMITTED_CORRECT/TOTAL:.2f}%")
    print()
    print(f"Retries completed      : {completed}/{len(RETRY_IDS)}")
    print(f"Retries remaining      : {pending}")
    print(f"Successful retry HTTP  : {completed}")
    print(f"Log records            : {attempts}")
    print(f"HTTP errors            : {http_errors}")
    print(f"128K finish=length     : {length_again}")
    print()
    print(f"Retry correct          : {retry_correct_count}/{completed}" if completed else "Retry correct          : 0/0")
    print(f"Rescued                : {rescued}")
    print(f"Still wrong            : {still_wrong}")
    print(f"Became wrong           : {became_wrong}")
    print()
    print(f"Adaptive Submitted     : {adaptive_correct}/{TOTAL} = "
          f"{100*adaptive_correct/TOTAL:.2f}%")
    print(f"Maximum possible final : {max_possible}/{TOTAL} = "
          f"{100*max_possible/TOTAL:.2f}%")
    print()
    print(f"{'doc':>4} {'tgt':>3} {'128K':>4} {'tokens':>8} {'finish':>8} {'ok':>3}  final")
    print("-" * 96)
    for doc_id, tgt, pred, tokens, finish, result, preview in rows:
        print(
            f"{doc_id:>4} {tgt:>3} {pred:>4} {tokens:>8} "
            f"{finish:>8} {result:>3}  {preview}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--watch", type=float, default=0)
    args = parser.parse_args()

    while True:
        if args.watch:
            print("\033[2J\033[H", end="")
        score_once(args.log)
        if not args.watch:
            break
        print(f"\nRefreshing every {args.watch:g}s — Ctrl+C to exit scorer only.")
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
