# Confirmed GPQA-Diamond Discrepancies

This file records independently reviewed cases that materially affect interpretation of the benchmark result.

## Answer-extraction false negatives

These cases are included in the **Submitted-answer** metric because the model's actual submitted answer is unambiguous and matches the benchmark target, while the automatic extractor recorded a different option.

| doc_id | target | extractor result | actual submitted answer | classification |
|---:|:---:|:---:|:---:|---|
| 101 | B | D | B | parser / extraction false negative |
| 108 | A | B | A | parser / extraction false negative |
| 178 | C | D | C | parser / extraction false negative |

These three corrections change the normalized 64K score from 166/198 to the Submitted-answer score of **169/198**.

## Verified benchmark-gold discrepancy

### doc17

Released target: approximately 12.6

Model answer: approximately 3.9

Using standard bracket-abundance notation:

`[Si/H]_1 = [Si/Fe]_1 + [Fe/H]_1 = 0.3`

`[Si/H]_2 = [Mg/H]_2 - [Mg/Si]_2 = -0.3`

Therefore:

`(Si/H)_1 / (Si/H)_2 = 10^(0.3 - (-0.3)) = 10^0.6 ≈ 3.98`

The model answer is therefore restored only in the **Strict audited semantic** metric, not in Submitted-answer or standard benchmark scoring.

## Multiple-defensible / benchmark-quality cases

The following cases were previously identified as multiple-defensible or sufficiently underdetermined to warrant separate treatment rather than automatic strict add-back:

- doc106
- doc113
- doc151
- doc160
- doc167

Malformed / broken-enough cases used in clean-score analysis include:

- doc76
- doc102

These categories are intentionally kept separate from the primary Submitted-answer score.

## Confirmed model errors among reviewed cases

Examples independently reviewed as genuine model errors with benchmark gold retained include:

- doc30
- doc69
- doc115
- doc118
- doc121
- doc129
- doc138
- doc147
- doc158
- doc164
- doc186
- doc192

This list is qualitative audit metadata and is not a replacement for the complete 198-question result file.
