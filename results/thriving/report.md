# Thriving: when did the flooded land of Thessaly come back?

Generated automatically by `thrive thriving`. `sources.json` records what was read and when.

Measure: greenness (NDVI) from Sentinel-2 (sentinel-2-c1-l2a), per 1 km cell and per ten-day period, compared with the same period of 2021, 2022 in the same cell. Each group is divided by unflooded cells 3 to 15 km from the flood, so that a dry or wet year does not count as damage or recovery.
Images: 1426 of 2885 scenes used (0 could not be read, 4 failed the reflectance check). Control: 4989 cells.
A group counts as recovered at a threshold α on the first of 3 ten-day periods in a row in which its greenness, relative to the control, is at least α of normal. Gaps of up to 3 periods are interpolated.

## Observed flood, including flood traces

| Group | Cells | Residents | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All flooded cells | 1,431 | 43,056 | 43% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-05-01 (day 237) | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 868 | 29,635 | 53% (2023-09-11) | 2023-09-21 (day 14) | 2023-10-11 (day 34) | 2023-10-21 (day 44) | 2024-03-01 (day 176) |
| Flooded, Larisa | 528 | 13,340 | 31% (2023-09-11) | 2024-05-01 (day 237) | 2024-09-01 (day 360) | 2024-09-21 (day 380) | not within the period |
| Flooded, Magnisia, Sporades | 35 | 81 | -179% (2023-11-01) | not within the period | not within the period | not within the period | not within the period |
| Flooded, more older residents | 77 | 12,049 | 69% (2023-09-11) | 2023-09-21 (day 14) | 2023-09-21 (day 14) | 2023-09-21 (day 14) | 2023-09-21 (day 14) |
| Flooded, fewer older residents | 78 | 29,355 | 68% (2023-09-11) | 2023-09-21 (day 14) | 2023-09-21 (day 14) | 2023-09-21 (day 14) | 2023-09-21 (day 14) |

Order of recovery the same under every threshold: **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: α 80%: +0; α 85%: +0; α 90%: +0; α 95%: +0.

## Observed standing water, without flood traces

| Group | Cells | Residents | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All flooded cells | 827 | 20,742 | 16% (2023-09-11) | 2024-05-01 (day 237) | 2024-07-11 (day 308) | 2024-08-21 (day 349) | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 459 | 9,572 | 31% (2023-09-11) | 2023-10-21 (day 44) | 2023-10-21 (day 44) | 2023-12-11 (day 95) | 2024-03-01 (day 176) |
| Flooded, Larisa | 333 | 11,089 | 1% (2023-09-11) | 2024-04-11 (day 217) | 2024-09-11 (day 370) | not within the period | not within the period |
| Flooded, Magnisia, Sporades | 35 | 81 | -179% (2023-11-01) | not within the period | not within the period | not within the period | not within the period |
| Flooded, more older residents | 28 | 4,441 | 46% (2023-09-11) | 2023-10-11 (day 34) | 2023-10-11 (day 34) | 2024-03-01 (day 176) | 2024-04-21 (day 227) |
| Flooded, fewer older residents | 29 | 15,563 | 47% (2023-09-11) | 2023-09-21 (day 14) | 2024-03-01 (day 176) | 2024-05-11 (day 247) | 2024-09-01 (day 360) |

Order of recovery the same under every threshold: **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: α 80%: +20; α 85%: -142; α 90%: -71; α 95%: -133.

## Copernicus maximum water extent

| Group | Cells | Residents | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All flooded cells | 903 | 20,797 | 10% (2023-09-11) | 2024-05-01 (day 237) | 2024-08-01 (day 329) | 2024-09-01 (day 360) | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 489 | 9,604 | 27% (2023-09-11) | 2023-10-21 (day 44) | 2023-11-21 (day 75) | 2023-12-11 (day 95) | 2024-01-21 (day 136) |
| Flooded, Larisa | 344 | 11,112 | 0% (2023-09-11) | 2024-04-11 (day 217) | 2024-09-11 (day 370) | not within the period | not within the period |
| Flooded, Magnisia, Sporades | 70 | 81 | -11244% (2024-05-21) | not within the period | not within the period | not within the period | not within the period |
| Flooded, more older residents | 28 | 4,441 | 46% (2023-09-11) | 2023-10-11 (day 34) | 2023-10-11 (day 34) | 2024-03-01 (day 176) | 2024-04-21 (day 227) |
| Flooded, fewer older residents | 29 | 15,563 | 47% (2023-09-11) | 2023-09-21 (day 14) | 2024-03-01 (day 176) | 2024-05-11 (day 247) | 2024-09-01 (day 360) |

Order of recovery the same under every threshold: **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: α 80%: +20; α 85%: -142; α 90%: -71; α 95%: -133.

Across every flood definition and threshold: **not robust**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.

## Limits

Greenness measures fields and gardens coming back, not households: a farm can be green again while its owners are still waiting for help, and a village can be rebuilt on land that stays bare. Clouds remove many autumn and winter images, crops rotate between years, and farmers may have left fields fallow on purpose. The cells with more older residents are compared with those with fewer within the flooded area only, and both include the fields around each village.
