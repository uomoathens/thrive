# Thriving: when did the flooded land of Thessaly come back?

Generated automatically by `thrive thriving`. `sources.json` records what was read and when.

Measure: greenness (NDVI) from Sentinel-2 (sentinel-2-c1-l2a), per 1 km cell and per ten-day period, compared with the same period of 2019, 2020, 2021 in the same cell. Each group is divided by unflooded cells 3 to 15 km from the flood, so that a dry or wet year does not count as damage or recovery. 100% means as green as normal, relative to those neighbours.
Images: 2,448 of 4,900 scenes used (0 could not be read, 7 failed the reflectance check). Control: 4,822 cells.
Ten-day periods in which a group is not normally green (average greenness below 0.30 in the years before) are skipped, because a bare flooded field then looks the same as a bare normal one. Cells that are not green in a normal year at all (median below 0.15: lakes, towns, bare ground) are left out.

| Period | Year | Scenes | Expected at least |
| --- | --- | --- | --- |
| baseline | 2019 | 911 | 600 |
| baseline | 2020 | 1,187 | 600 |
| baseline | 2021 | 1,168 | 600 |
| after | 2023 | 368 | 200 |
| after | 2024 | 1,266 | 600 |

## Greenness season by season

Average over the ten-day periods of each season with a clear view; a season needs at least 5 such periods.

### Observed flood, including flood traces

| Group | Cells | Residents | Autumn 2023 | Spring 2024 | Summer 2024 |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 1,431 | 43,056 | 75% | 91% | 87% |
| Flooded, Karditsa, Trikala | 868 | 29,635 | 89% | 102% | 90% |
| Flooded, Larisa | 528 | 13,340 | 60% | 83% | 82% |
| Flooded, Magnisia, Sporades | 35 | 81 | below zero: mostly still under water | below zero: mostly still under water | n/a |
| Flooded, more older residents | 77 | 12,049 | 97% | 98% | 92% |
| Flooded, fewer older residents | 78 | 29,355 | 97% | 99% | 91% |

### Observed standing water, without flood traces

| Group | Cells | Residents | Autumn 2023 | Spring 2024 | Summer 2024 |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 827 | 20,742 | 54% | 81% | 85% |
| Flooded, Karditsa, Trikala | 459 | 9,572 | 74% | 102% | 90% |
| Flooded, Larisa | 333 | 11,089 | 44% | 74% | 78% |
| Flooded, Magnisia, Sporades | 35 | 81 | below zero: mostly still under water | below zero: mostly still under water | n/a |
| Flooded, more older residents | 28 | 4,441 | 81% | 97% | 91% |
| Flooded, fewer older residents | 29 | 15,563 | 83% | 92% | 90% |

### Copernicus maximum water extent

| Group | Cells | Residents | Autumn 2023 | Spring 2024 | Summer 2024 |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 841 | 20,770 | 54% | 81% | 85% |
| Flooded, Karditsa, Trikala | 465 | 9,577 | 74% | 102% | 90% |
| Flooded, Larisa | 340 | 11,112 | 44% | 74% | 78% |
| Flooded, Magnisia, Sporades | 36 | 81 | below zero: mostly still under water | below zero: mostly still under water | n/a |
| Flooded, more older residents | 28 | 4,441 | 81% | 97% | 91% |
| Flooded, fewer older residents | 29 | 15,563 | 83% | 92% | 90% |

## What holds under every flood definition

A difference counts only if it has the same sign under all 3 flood definitions and is at least 3 points each time; if it is smaller than that every time, there is no clear difference.

| Comparison | Season | Differences | Verdict |
| --- | --- | --- | --- |
| Flooded, Larisa against Flooded, Karditsa, Trikala | Spring 2024 | -19.3 points, -28.1 points, -28.2 points | **Flooded, Larisa lower** |
| Flooded, Larisa against Flooded, Karditsa, Trikala | Summer 2024 | -8.7 points, -12.0 points, -12.1 points | **Flooded, Larisa lower** |
| Flooded, more older residents against Flooded, fewer older residents | Spring 2024 | -0.9 points, +5.3 points, +5.3 points | **not robust** |
| Flooded, more older residents against Flooded, fewer older residents | Summer 2024 | +1.0 points, +0.8 points, +0.8 points | **no clear difference** |

## When did each group come back (counted from 2024-03-01)

A group counts as recovered at a threshold α on the first of 3 ten-day periods in a row in which its greenness, relative to the control, is at least α of normal. Gaps of up to 3 periods are interpolated. The count starts with the first growing season after the flood, for the reason given under Limits.

### Observed flood, including flood traces

| Group | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 43% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-05-01 (day 237) | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 51% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) |
| Flooded, Larisa | 31% (2023-09-11) | 2024-03-01 (day 176) | 2024-05-01 (day 237) | 2024-09-11 (day 370) | 2024-09-21 (day 380) |
| Flooded, Magnisia, Sporades | below zero (2023-11-11) | not within the period | not within the period | not within the period | not within the period |
| Flooded, more older residents | 68% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) |
| Flooded, fewer older residents | 67% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) |

Order of recovery the same under every threshold: **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: α 80%: +0; α 85%: +0; α 90%: +0; α 95%: +0.

### Observed standing water, without flood traces

| Group | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 16% (2023-09-11) | 2024-05-01 (day 237) | 2024-05-01 (day 237) | 2024-08-21 (day 349) | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 30% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) |
| Flooded, Larisa | 1% (2023-09-11) | 2024-04-11 (day 217) | 2024-04-11 (day 217) | 2024-09-21 (day 380) | 2024-10-11 (day 400) |
| Flooded, Magnisia, Sporades | below zero (2023-11-11) | not within the period | not within the period | not within the period | not within the period |
| Flooded, more older residents | 44% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) |
| Flooded, fewer older residents | 46% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-09-01 (day 360) |

Order of recovery the same under every threshold: **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: α 80%: +0; α 85%: +0; α 90%: +0; α 95%: -184.

### Copernicus maximum water extent

| Group | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 16% (2023-09-11) | 2024-05-01 (day 237) | 2024-05-01 (day 237) | 2024-08-21 (day 349) | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 31% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) |
| Flooded, Larisa | 2% (2023-09-11) | 2024-04-11 (day 217) | 2024-04-11 (day 217) | 2024-09-21 (day 380) | 2024-10-11 (day 400) |
| Flooded, Magnisia, Sporades | below zero (2023-11-11) | not within the period | not within the period | not within the period | not within the period |
| Flooded, more older residents | 44% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) |
| Flooded, fewer older residents | 46% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-09-01 (day 360) |

Order of recovery the same under every threshold: **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: α 80%: +0; α 85%: +0; α 90%: +0; α 95%: -184.

Recovery days, across every flood definition and threshold: **not robust**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.

## Limits

In the first weeks after the flood the flooded fields often look greener than normal. In a normal year the cotton of the plain is defoliated and picked in September and October; after Daniel many fields were left unharvested and wet, and weeds grew on them. A satellite sees green either way, so greenness right after the flood does not mean the land was working again. That is why the recovery count starts with the next growing season.

Greenness measures fields and gardens coming back, not households: a farm can be green again while its owners are still waiting for help, and a village can be rebuilt on land that stays bare. Clouds remove many autumn and winter images, crops rotate between years, and farmers may have left fields fallow on purpose. Greenness below zero means the ground is mostly water. The cells with more older residents are compared with those with fewer within the flooded area only, and both include the fields around each village.
