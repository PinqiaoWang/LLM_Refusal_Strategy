# May-August robustness analysis

Models compared: 13

Query overlap: 138 shared, 62 May-only, 124 August-only.

## May 200 versus August 262

- Layer 2 Pearson r: 0.9884
- Layer 2 Spearman rho: 0.9773
- Layer 2 mean absolute difference: 3.37 pp
- Layer 2 maximum absolute difference: 15.01 pp (grok-4.20 x alternative_offer)

## Shared 138 repeated generation

- Layer 2 Pearson r: 0.9886
- Layer 2 Spearman rho: 0.9752
- Layer 2 mean absolute difference: 3.04 pp
- Mean Layer 0 exact agreement across models: 0.8980
- Mean binary NC agreement across models: 0.9186

Rates exclude judge/API errors and missing-response skips. Layer 1 and Layer 2 rates are conditional on Non-compliance within each run. Response-level Layer 1 and Layer 2 agreement is restricted to pairs judged Non-compliance in both runs.
