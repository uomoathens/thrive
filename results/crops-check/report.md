# Heat and summer crops in Thessaly: placebo and unseen Summers

Generated automatically by `thrive crops-check` from the panel of the latest `thrive crops-heat` run. The checks and the rule were fixed on 2026-11-26, before they were computed; see `config/crops-check-plan.md`.

Verdict: **not robust**. Reason: not every main estimate is below zero with its interval below zero; the placebo shows an effect of heat that has not happened yet; hot days do not improve the prediction of every unseen Summer.

## Main estimates (common effect of each year)

| threshold_C | hot_days_in | n | b | lo | hi | pct | pct_lo | pct_hi |
|---|---|---|---|---|---|---|---|---|
| 35 | this ten-day period | 60299 | -0.0006325 | -0.002111 | 0.0008462 | -0.06323 | -0.2109 | 0.08465 |
| 35 | this and the previous ten-day period | 60299 | -0.001683 | -0.003087 | -0.0002783 | -0.1681 | -0.3082 | -0.02783 |
| 37 | this ten-day period | 60299 | -0.005742 | -0.007121 | -0.004363 | -0.5725 | -0.7095 | -0.4353 |
| 37 | this and the previous ten-day period | 60299 | -0.006231 | -0.007543 | -0.004919 | -0.6212 | -0.7515 | -0.4907 |
| 40 | this ten-day period | 60299 | -0.009694 | -0.01281 | -0.006579 | -0.9647 | -1.273 | -0.6558 |
| 40 | this and the previous ten-day period | 60299 | -0.01149 | -0.01427 | -0.008706 | -1.142 | -1.416 | -0.8668 |

## Placebo: hot days of the next ten-day period

| threshold_C | hot_days_in | n | b_next | lo_next | hi_next |
|---|---|---|---|---|---|
| 35 | this ten-day period | 60299 | 0.006416 | 0.005071 | 0.007761 |
| 35 | this and the previous ten-day period | 60299 | 0.006212 | 0.004678 | 0.007746 |
| 37 | this ten-day period | 60299 | 0.005593 | 0.004266 | 0.00692 |
| 37 | this and the previous ten-day period | 60299 | 0.004388 | 0.002879 | 0.005896 |
| 40 | this ten-day period | 60299 | 0.006113 | 0.002888 | 0.009338 |
| 40 | this and the previous ten-day period | 60299 | 0.003403 | -0.0004318 | 0.007237 |

## Unseen Summers: fitted on 2019 to 2022

| threshold_C | test_year | rows | rmse_without | rmse_with | improves |
|---|---|---|---|---|---|
| 35 | 2023 | 8769 | 0.1951 | 0.1941 | True |
| 35 | 2024 | 2159 | 0.2212 | 0.2199 | True |
| 35 | 2025 | 12447 | 0.3605 | 0.3614 | False |
| 37 | 2023 | 8769 | 0.1951 | 0.1942 | True |
| 37 | 2024 | 2159 | 0.2212 | 0.2222 | False |
| 37 | 2025 | 12447 | 0.3605 | 0.3597 | True |
| 40 | 2023 | 8769 | 0.1951 | 0.194 | True |
| 40 | 2024 | 2159 | 0.2212 | 0.2226 | False |
| 40 | 2025 | 12447 | 0.3605 | 0.3602 | True |

Prediction error is the root mean square error of log greenness after removing the normal of each square and ten-day period and the common level of the test Summer, which both models get alike.
