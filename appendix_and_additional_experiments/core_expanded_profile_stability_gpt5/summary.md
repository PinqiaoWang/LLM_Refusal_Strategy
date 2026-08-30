# Core 200 vs. Expanded 262 profile stability

Models compared: 1

Layer 1 and Layer 2 rates use each dataset's actually judged Non-compliance responses as denominators.

## Layer 2 flattened-matrix comparison

- Spearman rho: 0.9983
- Mean absolute difference: 0.96 pp
- Maximum absolute difference: 2.89 pp (gpt-5 x solidarity)
- Maximum-cell denominators: N=166 (Core), N=212 (Expanded)

## Data-quality exclusions

| Dataset | Judge/API errors | Missing-response skips |
|---|---:|---:|
| Core 200 | 2 | 3 |
| Expanded 262 | 2 | 5 |
