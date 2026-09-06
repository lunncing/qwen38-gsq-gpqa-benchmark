# Qwen3.8-27B GSQ-RCO IQ3_S — GPQA-Diamond Evaluation

Independent local evaluation of **Qwen3.8-27B GSQ-RCO IQ3_S** on the full **GPQA-Diamond** benchmark (198 questions).

This repository separates four notions of accuracy so that model errors are not conflated with answer-extraction failures or benchmark defects:

1. **Official parser** — strict benchmark-style parsing.
2. **Normalized extractor** — deterministic tolerant extraction for common answer formats.
3. **Submitted-answer** — normalized score plus only independently confirmed answer-extraction false negatives.
4. **Strict audited semantic** — Submitted-answer plus independently verified benchmark-gold defects where the model genuinely solved the item.

The **Submitted-answer score is the primary local model-quality metric** in this repository.

## 64K one-shot baseline

| Metric | Correct | Accuracy |
|---|---:|---:|
| Official parser | 144 / 198 | 72.73% |
| Normalized extractor | 166 / 198 | 83.84% |
| **Submitted-answer** | **169 / 198** | **85.35%** |
| Strict audited semantic | 170 / 198 | 85.86% |

Confirmed answer-extraction false negatives included in Submitted-answer:

- `doc101`: target B, actual submitted B
- `doc108`: target A, actual submitted A
- `doc178`: target C, actual submitted C

The strict audited semantic score additionally restores `doc17`, where an independent derivation supports the model answer rather than the released benchmark target.

## 64K generation-limit cases

Eight questions ended with `finish_reason=length` at 64,000 completion tokens:

`8, 71, 79, 88, 118, 127, 130, 145`

Seven of the eight had no final answer at the 64K cap. `doc118` had an answer present but still ended with `finish_reason=length`.

## Adaptive 64K → 128K evaluation

A separate adaptive experiment retries **all and only** questions whose first attempt ended with `finish_reason=length`.

The retry rule is grade-independent and was fixed before the retry outcomes were known:

- start again from the original prompt;
- keep the same model and request settings;
- keep `seed=1234`;
- keep `temperature=1.0`, `top_p=0.95`, `top_k=20`, `min_p=0.0`;
- keep `presence_penalty=0.0`, `repeat_penalty=1.0`;
- keep `enable_thinking=true`, `reasoning_effort=xhigh`;
- change the output budget from `max_tokens=64000` to `max_tokens=128000`;
- the 128K outcome unconditionally replaces the 64K outcome in the adaptive score;
- no third retry is performed if 128K also ends in `length`.

This is an **adaptive generation-budget evaluation**, not pass@2, best-of-two, or self-consistency.

### Final adaptive results

| doc | target | 128K answer | tokens | finish | result |
|---:|:---:|:---:|---:|:---:|:---:|
| 8 | D | D | 72,622 | stop | ✓ rescued |
| 71 | D | A | 78,037 | stop | ✗ |
| 79 | B | — | 128,000 | length | ✗ |
| 88 | B | D | 89,399 | stop | ✗ recovered from proxy |
| 118 | D | D | 29,219 | stop | ✓ rescued |
| 127 | C | — | 128,000 | length | ✗ |
| 130 | B | A | 49,563 | stop | ✗ |
| 145 | A | C | 84,577 | stop | ✗ |

All **8/8** predefined retries are complete. Exactly two cases were rescued: `doc8` and `doc118`.

Final adaptive Submitted-answer score:

**171 / 198 = 86.36%**

Final adaptive Strict audited semantic score:

**172 / 198 = 86.87%**

Relative to the frozen 64K Submitted-answer baseline, adaptive 128K retry adds:

**+2 questions = +1.01 percentage points**

Two retries (`doc79`, `doc127`) reached the 128K completion limit again without a final answer. Four more (`doc71`, `doc88`, `doc130`, `doc145`) stopped naturally but remained incorrect.

`doc88` is a transport/logging edge case: its complete `stop`, 89,399-token response was persisted by the logging proxy before the paused runner later encountered `Connection reset by peer`. The recovered proxy result is target B → submitted D, so it is semantically complete and incorrect; the original runner error is retained rather than rewritten.

`doc79` is separately classified in benchmark audit as **BROKEN / MISSING_CRITICAL_CONTEXT** because the revised benchmark prompt removed the original `RC` clue and an additional example. That classification does not grant Submitted-answer credit because the model produced no final answer.

See [`results/adaptive-128k.md`](results/adaptive-128k.md) for the full retry record.

## Runtime / logging architecture

```text
retry client
        ↓
127.0.0.1:1235  openai-log-proxy.py
        ↓
127.0.0.1:1234  llama-qwen.service / llama-server
```

The 128K logging proxy writes separately to:

```text
/media/nowr/Data/Evals/qwen38-gsq/length-retry-128k/gpqa-length-retry-128k-proxy.jsonl
```

The retry runner stores doc-indexed results in:

```text
/media/nowr/Data/Evals/qwen38-gsq/length-retry-128k/gpqa-length-retry-128k.jsonl
```

This separation keeps the original 64K baseline metrics frozen.

## Repository layout

- [`methodology.md`](methodology.md) — scoring definitions and retry protocol
- [`results/64k-baseline.md`](results/64k-baseline.md) — frozen one-shot 64K results
- [`results/adaptive-128k.md`](results/adaptive-128k.md) — completed adaptive retry results
- [`audit/confirmed-discrepancies.md`](audit/confirmed-discrepancies.md) — confirmed parser/gold/benchmark-quality discrepancies
- [`scripts/gpqa-live-score.py`](scripts/gpqa-live-score.py) — original 64K live scorer
- [`scripts/gpqa-adaptive-score.py`](scripts/gpqa-adaptive-score.py) — adaptive 64K→128K scorer, including the audited doc88 proxy recovery
- [`scripts/openai-log-proxy.py`](scripts/openai-log-proxy.py) — local request/response logging proxy

## Reporting rule

The **64K one-shot result and the adaptive 64K→128K result are different inference protocols and are reported separately**. The adaptive result must not be presented as a one-shot pass@1 score.