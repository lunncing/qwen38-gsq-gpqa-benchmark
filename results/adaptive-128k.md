# Adaptive 64K → 128K Retry Results

This page records the completed adaptive generation-budget experiment.

## Trigger

A retry is performed if and only if the original 64K attempt ended with:

`finish_reason == "length"`

The predefined retry set is:

`8, 71, 79, 88, 118, 127, 130, 145`

## Replacement rule

The 128K retry outcome unconditionally replaces the corresponding 64K outcome in the adaptive score.

No result is selected based on correctness. Each retry starts again from the original prompt, and no third retry is performed if the 128K attempt also ends in `length`.

## Final retry results

| doc | target | 128K answer | completion tokens | finish | result | note |
|---:|:---:|:---:|---:|:---:|:---:|---|
| 8 | D | D | 72,622 | stop | ✓ | rescued |
| 71 | D | A | 78,037 | stop | ✗ | natural stop, wrong |
| 79 | B | — | 128,000 | length | ✗ | no submitted final answer |
| 88 | B | D | 89,399 | stop | ✗ | recovered from proxy after runner transport reset |
| 118 | D | D | 29,219 | stop | ✓ | rescued |
| 127 | C | — | 128,000 | length | ✗ | no submitted final answer |
| 130 | B | A | 49,563 | stop | ✗ | natural stop, wrong |
| 145 | A | C | 84,577 | stop | ✗ | natural stop, wrong |

All eight predefined retries are semantically complete.

- Correct / rescued: **2 / 8**
- Still wrong: **6 / 8**
- Reached the 128K generation limit again: **2 / 8** (`doc79`, `doc127`)
- Natural `stop` but incorrect: **4 / 8** (`doc71`, `doc88`, `doc130`, `doc145`)
- Total retry completion tokens: **659,417**
- Mean retry completion tokens: **82,427.1**

### doc88 transport note

`doc88` completed normally at the model/proxy layer with:

- target `B`
- submitted answer `D`
- `finish_reason=stop`
- `completion_tokens=89399`

The retry runner had been paused while the already-issued request continued. The logging proxy persisted the complete response, but the runner later recorded a `ChunkedEncodingError / Connection reset by peer` rather than a normal `status=200` record. The recovered proxy response is therefore used for the semantic adaptive result while the original runner error remains unchanged for auditability.

## Final adaptive scores

Frozen 64K Submitted-answer baseline:

**169 / 198 = 85.35%**

The 128K retries rescue exactly two previously incorrect length-triggered cases (`doc8` and `doc118`):

**171 / 198 = 86.36%**

Thus adaptive generation budgeting changes the primary Submitted-answer result by:

**+2 questions = +1.01 percentage points**

The Strict audited semantic baseline is **170 / 198 = 85.86%**. Adding the same two rescued retry cases gives:

**172 / 198 = 86.87%**

These adaptive results are now final under the predefined protocol.

## Benchmark-audit note: doc79

`doc79` is still incorrect under Submitted-answer because the 128K retry produced no final answer. Separately, audit of the benchmark item found that the revised prompt removed critical information from the original author version: the `RC` flag and an additional `GAA → 165` example. Under the original intended rule, reverse complement → codon translation → peptide molecular weight gives target `B = 315`; under the revised two-example prompt, the hidden algorithm is underdetermined.

This benchmark-quality classification does **not** add credit to Submitted-answer, Strict audited semantic, or broad-defensible scoring because the model submitted no final answer. It is relevant only to benchmark-quality / clean-denominator analyses.

## Important protocol note

This adaptive result must not be labeled one-shot pass@1. It uses a grade-independent runtime trigger and a larger generation budget only for first-pass `length` cases.

The 128K result is used unconditionally even if it is worse than the corresponding 64K result.