# Methodology

## Benchmark

- Benchmark: GPQA-Diamond
- Total questions: 198
- Evaluation mode: generative multiple choice
- Choice processing follows the same `process_docs` path used by lm-eval, with `random.seed(0)`.

## Primary score: Submitted-answer

The primary local metric is **Submitted-answer accuracy**.

It begins with the deterministic normalized extractor result and corrects only cases where the model's actual final answer is unambiguously recoverable but the automatic extractor assigned the wrong option.

Confirmed extraction corrections:

- doc101: B
- doc108: A
- doc178: C

No benchmark-gold changes are included in Submitted-answer.

## Other reported metrics

### Official parser

Strict parser behavior based primarily on parenthesized answer forms such as `(A)`.

### Normalized extractor

A deterministic tolerant extractor that also accepts common forms such as boxed answers, `Answer: C`, and bare option letters.

### Strict audited semantic

Starts from Submitted-answer and additionally restores independently verified benchmark-gold defects when the model genuinely solved the item.

Current strict add-back:

- doc17

This score is reported separately from standard benchmark scoring.

## 64K one-shot protocol

All 198 questions receive a single attempt with `max_tokens=64000`.

Observed generation-limit cases:

`8, 71, 79, 88, 118, 127, 130, 145`

## Adaptive retry protocol

The adaptive experiment uses a predeclared trigger:

`finish_reason == "length"`

Only those eight cases receive a retry.

The retry:

- restarts from the original prompt;
- uses the same model;
- keeps the original choice order;
- keeps `seed=1234`;
- keeps `temperature=1.0`;
- keeps `top_p=0.95`;
- keeps `top_k=20`;
- keeps `min_p=0.0`;
- keeps `presence_penalty=0.0`;
- keeps `repeat_penalty=1.0`;
- keeps `enable_thinking=true`;
- keeps `reasoning_effort=xhigh`;
- increases the output budget to `max_tokens=128000`.

The 128K result unconditionally replaces the corresponding 64K result in the adaptive metric, even if the replacement is worse.

There is no correctness-dependent retry and no third attempt after 128K.

Therefore the adaptive score is **not** pass@2 or best-of-two.

## Logging architecture

Requests are sent through a local HTTP logging proxy:

```text
client → 127.0.0.1:1235 → 127.0.0.1:1234 llama-server
```

The proxy records the complete request and response as JSONL before returning the response to the client.

## Reporting policy

The repository keeps the following separate:

1. 64K one-shot result.
2. Submitted-answer correction.
3. Strict audited semantic correction.
4. Adaptive 64K→128K result.

These are not interchangeable metrics and should not be presented as if they used the same evaluation protocol.
