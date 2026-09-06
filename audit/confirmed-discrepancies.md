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

## Broken / missing-critical-context benchmark item

### doc79

Released/revised target: **B = 315**

128K retry: **no final answer**, `finish_reason=length`, `completion_tokens=128000`

Independent audit of the source metadata found that the author's earlier version explicitly supplied an `RC` flag and an additional `GAA → 165` example. Those clues were removed during revision while the target remained unchanged.

The intended rule is:

1. take the DNA reverse complement;
2. translate the resulting codons;
3. calculate the peptide molecular weight using free-amino-acid masses minus water for peptide-bond formation.

Examples under that intended rule:

- `AGG` → reverse complement `CCT` → Pro → approximately 115
- deleted check example `GAA` → reverse complement `TTC` → Phe → approximately 165
- `TGCTGA` → reverse complement `TCAGCA` → Ser-Ala → approximately 176
- `ACAGTGACC` → reverse complement `GGTC ACTGT` → `GGT | CAC | TGT` → Gly-His-Cys → approximately 315

Thus **315 is correct under the author's intended hidden rule**, but the revised prompt as presented is underdetermined because only two input/output pairs remain and the critical `RC` clue was removed.

Classification:

- runtime: `GENERATION_BUDGET_EXHAUSTED`
- benchmark audit: `BROKEN / MISSING_CRITICAL_CONTEXT`
- model semantic credit: **none**, because no final answer was submitted

This classification does not alter Submitted-answer, Strict audited semantic, or broad-defensible credit. It is relevant to clean-denominator / benchmark-quality analyses.

## Confirmed 128K model error: doc88

Target: **B = triplet of triplets**

Recovered 128K answer: **D = triplet**

Runtime:

- `finish_reason=stop`
- `completion_tokens=89399`
- complete response persisted by the logging proxy
- runner later recorded a transport error after being paused: `ChunkedEncodingError / Connection reset by peer`

The response is therefore semantically complete despite the runner-side `status=-1` record.

The model correctly recognized a ring-contracted bicyclo[3.3.1]nonane motif, but assigned the wrong regioisomer for product 1:

- model assignment: `2-methylene-3-oxobicyclo[3.3.1]nonane`
- independently supported assignment: `7-methylenebicyclo[3.3.1]nonan-3-one`

That structural error propagated to the NMR analysis. The model's incorrect product 3 left the most deshielded C-H coupled to only one adjacent CH2 group, producing `triplet`. In the intended product, that proton is coupled through the rigid bicyclo[3.3.1]nonane framework to two distinct two-proton vicinal sets with different coupling constants, giving `triplet of triplets`.

Classification:

`MODEL_WRONG_GOLD_RIGHT — regiostructure identification failure`

This is not a parser error, benchmark-gold error, generation-budget failure, or multiple-defensible case.

## Multiple-defensible / benchmark-quality cases

The following cases were previously identified as multiple-defensible or sufficiently underdetermined to warrant separate treatment rather than automatic strict add-back:

- doc106
- doc113
- doc151
- doc160
- doc167

Malformed / broken-enough cases used in clean-score analysis include:

- doc76
- doc79
- doc102

These categories are intentionally kept separate from the primary Submitted-answer score.

## Confirmed model errors among reviewed cases

Examples independently reviewed as genuine model errors with benchmark gold retained include:

- doc30
- doc69
- doc71
- doc88
- doc115
- doc121
- doc129
- doc138
- doc147
- doc158
- doc164
- doc186
- doc192

`doc118` was incorrect in the frozen 64K baseline but was rescued by its predefined 128K retry, so it is not listed here as a final adaptive model error.

This list is qualitative audit metadata and is not a replacement for the complete 198-question result file.