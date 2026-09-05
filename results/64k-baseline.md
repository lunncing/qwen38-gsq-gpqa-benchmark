# GPQA-Diamond 64K One-Shot Baseline

Full run: **198 / 198 questions completed**.

## Frozen results

| Metric | Correct | Accuracy |
|---|---:|---:|
| Official parser | 144 / 198 | 72.73% |
| Normalized extractor | 166 / 198 | 83.84% |
| **Submitted-answer** | **169 / 198** | **85.35%** |
| Strict audited semantic | 170 / 198 | 85.86% |

## Runtime summary

- `finish_reason=length`: 8
- `>=63K completion`: 8
- average completion: 15,260 tokens
- maximum completion: 64,000 tokens
- empty final answers: 7 / 198
- invalid official parses: 33 / 198

## Length-limited questions

`8, 71, 79, 88, 118, 127, 130, 145`

Seven produced no final answer at 64K. `doc118` produced a final answer but still ended with `finish_reason=length`.

## Submitted-answer correction

The normalized result of 166/198 is increased by exactly three independently confirmed extraction false negatives:

- doc101
- doc108
- doc178

This yields **169/198 = 85.35%**.

## Strict audited semantic correction

The strict audited semantic score additionally restores doc17 after independent verification of the released gold discrepancy, producing **170/198 = 85.86%**.

This audited score is not presented as standard benchmark accuracy.

## Freeze policy

These numbers represent the original 64K one-shot checkpoint and should remain unchanged even after adaptive retries are performed.
