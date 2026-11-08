# Result index

Formal numbers in the report come from the directories below. Every trial uses base seed 100. `results/final/analysis.md` and `results/final/figure1.png` are computed from these directories only. `results/20261108T185336Z/checks.md` is the sanity check for the same set.

Completed counts are trials that returned a decision. The difference from the planned n is a dropped API call (rate limit or truncated output), not a refusal.

| Directory | Model | Difficulty | Conditions | Planned n | Completed |
| --- | --- | --- | --- | --- | --- |
| `20261108T185336Z` | qwen3.8-27b | 5 | A, B | 50 | 49, 49 |
| `20261108T190751Z` | qwen3.8-27b | 4 | A, B | 30 | 30, 30 |
| `20261108T191548Z` | qwen3.8-27b | 5 | baseline | 20 | 15 |
| `20261108T191644Z` | qwen3.8-27b | 4 | baseline | 20 | 20 |
| `20261108T191830Z` | gemma-4-31b-it | 5 | baseline, A, B | 30 | 26, 24, 24 |
| `20261108T192445Z` | gemma-4-31b-it | 4 | baseline, A, B | 30 | 25, 29, 28 |
| `20261108T211043Z` | deepseek-v4-flash | 5 | A, B | 20 | 20, 20 |
| `20261108T211440Z` | deepseek-v4-flash | 4 | A, B | 20 | 20, 20 |
| `20261108T221053Z` | deepseek-v4-flash | 4 | baseline | 20 | 20 |
| `20261108T221704Z` | deepseek-v4-flash | 5 | baseline | 20 | 16 |
| `20261108T220954Z` | qwen3.8-27b | 3 | A, B | 15 | 14, 14 |
| `20261108T221757Z` | qwen3.8-27b | 3 | baseline | 15 | 12 |
| `20261108T221907Z` | glm-53-flash | 5 | A, B | 20 | 20, 20 |

Difficulty 3 baseline in the report is `20261108T221757Z`. The same folder `20261108T220954Z` also contains 4 completed baseline trials from a rate-limited run. `analysis.md` excludes those 4 (`--exclude 20261108T220954Z:baseline`), so its difficulty 3 baseline row is the 12 trials from `20261108T221757Z`.

Difficulty 3 approvals (A 0/14, B 1-2/14, baseline 1/12) are capped partial approvals of EUR 100 with the EUR 150 total visible, not deception about the amount.

## Not counted

Pilot runs use seed 1. The scripted `dry-run/` directory is not a model result. `20261108T185333Z` is a one-trial Gemma probe at seed 999.

`20261108T034312Z` is difficulty 3 from before the report body was fixed. Decision roles in that run did not see the subordinate's text.

`20261108T220953Z` is an earlier DeepSeek difficulty 5 baseline cut short by rate limits (8 of 20). The replacement is `20261108T221704Z`. `20261108T220955Z` is the GLM run that was stopped when rate limits started; it has no completed trials. The replacement is `20261108T221907Z`.

## Reproduce

```bash
F="results/20261108T185336Z results/20261108T190751Z results/20261108T191548Z results/20261108T191644Z results/20261108T191830Z results/20261108T192445Z results/20261108T211043Z results/20261108T211440Z results/20261108T221053Z results/20261108T221704Z results/20261108T220954Z results/20261108T221757Z results/20261108T221907Z"
python3 scripts/analyze.py $F --exclude 20261108T220954Z:baseline --out results/final
python3 scripts/check_results.py $F
```
