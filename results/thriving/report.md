# Thriving: when did the flooded land of Thessaly come back?

Generated automatically by `thrive thriving`. `sources.json` records what was read and when.

Measure: greenness (NDVI) from Sentinel-2 (sentinel-2-c1-l2a), per 1 km cell and per ten-day period, compared with the same period of 2019, 2020, 2021 in the same cell. Each group is divided by unflooded cells 3 to 15 km from the flood, so that a dry or wet year does not count as damage or recovery.
Images: 2448 of 4900 scenes used (0 could not be read, 7 failed the reflectance check). Control: 4822 cells.
A group counts as recovered at a threshold α on the first of 3 ten-day periods in a row in which its greenness, relative to the control, is at least α of normal. Gaps of up to 3 periods are interpolated.
Only ten-day periods in which the land is normally green count: the average greenness of the group in the years before must be at least 0.30. In autumn and winter the fields of the plain are bare even in a normal year, so a bare flooded field looks normal then and would count as recovered too early. Cells that are not green in a normal year at all (median below 0.15: lakes, towns, bare ground) are left out.

| Period | Year | Scenes | Expected at least |
| --- | --- | --- | --- |
| baseline | 2019 | 911 | 600 |
| baseline | 2020 | 1,187 | 600 |
| baseline | 2021 | 1,168 | 600 |
| after | 2023 | 368 | 200 |
| after | 2024 | 1,266 | 600 |

## Observed flood, including flood traces

| Group | Cells | Residents | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All flooded cells | 1,431 | 43,056 | 43% (2023-09-11) | 2023-10-11 (day 34) | 2024-01-21 (day 136) | 2024-03-01 (day 176) | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 868 | 29,635 | 51% (2023-09-11) | 2023-09-21 (day 14) | 2023-10-11 (day 34) | 2023-10-11 (day 34) | 2023-10-21 (day 44) |
| Flooded, Larisa | 528 | 13,340 | 31% (2023-09-11) | 2024-03-01 (day 176) | 2024-05-01 (day 237) | 2024-09-11 (day 370) | 2024-09-21 (day 380) |
| Flooded, Magnisia, Sporades | 35 | 81 | -123% (2023-11-11) | not within the period | not within the period | not within the period | not within the period |
| Flooded, more older residents | 77 | 12,049 | 68% (2023-09-11) | 2023-09-21 (day 14) | 2023-09-21 (day 14) | 2023-09-21 (day 14) | 2023-09-21 (day 14) |
| Flooded, fewer older residents | 78 | 29,355 | 67% (2023-09-11) | 2023-09-21 (day 14) | 2023-09-21 (day 14) | 2023-09-21 (day 14) | 2023-09-21 (day 14) |

Order of recovery the same under every threshold: **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: α 80%: +0; α 85%: +0; α 90%: +0; α 95%: +0.

## Observed standing water, without flood traces

| Group | Cells | Residents | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All flooded cells | 827 | 20,742 | 16% (2023-09-11) | 2024-05-01 (day 237) | 2024-05-01 (day 237) | 2024-08-21 (day 349) | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 459 | 9,572 | 30% (2023-09-11) | 2023-10-21 (day 44) | 2023-10-21 (day 44) | 2023-10-21 (day 44) | 2023-10-21 (day 44) |
| Flooded, Larisa | 333 | 11,089 | 1% (2023-09-11) | 2024-04-11 (day 217) | 2024-04-11 (day 217) | 2024-09-21 (day 380) | 2024-10-11 (day 400) |
| Flooded, Magnisia, Sporades | 35 | 81 | -123% (2023-11-11) | not within the period | not within the period | not within the period | not within the period |
| Flooded, more older residents | 28 | 4,441 | 44% (2023-09-11) | 2023-10-01 (day 24) | 2023-10-11 (day 34) | 2023-10-21 (day 44) | 2024-01-21 (day 136) |
| Flooded, fewer older residents | 29 | 15,563 | 46% (2023-09-11) | 2023-09-21 (day 14) | 2023-10-11 (day 34) | 2023-10-21 (day 44) | 2024-09-01 (day 360) |

Order of recovery the same under every threshold: **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: α 80%: +10; α 85%: +0; α 90%: +0; α 95%: -224.

## Copernicus maximum water extent

| Group | Cells | Residents | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All flooded cells | 841 | 20,770 | 16% (2023-09-11) | 2024-05-01 (day 237) | 2024-05-01 (day 237) | 2024-08-21 (day 349) | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 465 | 9,577 | 31% (2023-09-11) | 2023-10-21 (day 44) | 2023-10-21 (day 44) | 2023-10-21 (day 44) | 2023-10-21 (day 44) |
| Flooded, Larisa | 340 | 11,112 | 2% (2023-09-11) | 2024-04-11 (day 217) | 2024-04-11 (day 217) | 2024-09-21 (day 380) | 2024-10-11 (day 400) |
| Flooded, Magnisia, Sporades | 36 | 81 | -119% (2023-11-11) | not within the period | not within the period | not within the period | not within the period |
| Flooded, more older residents | 28 | 4,441 | 44% (2023-09-11) | 2023-10-01 (day 24) | 2023-10-11 (day 34) | 2023-10-21 (day 44) | 2024-01-21 (day 136) |
| Flooded, fewer older residents | 29 | 15,563 | 46% (2023-09-11) | 2023-09-21 (day 14) | 2023-10-11 (day 34) | 2023-10-21 (day 44) | 2024-09-01 (day 360) |

Order of recovery the same under every threshold: **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: α 80%: +10; α 85%: +0; α 90%: +0; α 95%: -224.

Across every flood definition and threshold: **not robust**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.

## Limits

Greenness measures fields and gardens coming back, not households: a farm can be green again while its owners are still waiting for help, and a village can be rebuilt on land that stays bare. Clouds remove many autumn and winter images, crops rotate between years, and farmers may have left fields fallow on purpose. The cells with more older residents are compared with those with fewer within the flooded area only, and both include the fields around each village.
