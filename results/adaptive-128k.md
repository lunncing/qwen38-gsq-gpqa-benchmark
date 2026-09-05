# Adaptive 64K → 128K Retry Results

This page tracks the separately reported adaptive generation-budget experiment.

## Trigger

A retry is performed if and only if the original 64K attempt ended with:

`finish_reason == "length"`

The predefined retry set is:

`8, 71, 79, 88, 118, 127, 130, 145`

## Replacement rule

The 128K retry outcome unconditionally replaces the corresponding 64K outcome in the adaptive score.

No result is selected based on correctness.

## Current status

| doc | target | 64K final | 128K answer | 128K tokens | finish | status |
|---:|:---:|:---:|:---:|---:|:---:|---|
| 8 | D | none | D | 61,221 | stop | rescued |
| 71 | D | none | — | — | — | pending |
| 79 | B | none | — | — | — | pending |
| 88 | B | none | — | — | — | pending |
| 118 | D | answer present | — | — | — | pending |
| 127 | C | none | — | — | — | pending |
| 130 | B | none | — | — | — | pending |
| 145 | A | none | — | — | — | pending |

## Provisional adaptive Submitted-answer score

64K Submitted-answer baseline:

**169 / 198 = 85.35%**

After the successful doc8 rescue:

**170 / 198 = 85.86%**

This is provisional until all eight predefined retry cases are complete.

## Important protocol note

This adaptive result must not be labeled one-shot pass@1. It uses a grade-independent runtime trigger and a larger generation budget only for first-pass `length` cases.
