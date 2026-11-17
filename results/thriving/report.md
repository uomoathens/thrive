# Thriving: when did the flooded land of Thessaly come back?

Generated automatically by `thrive thriving`. `sources.json` records what was read and when.

Measure: greenness (NDVI) from Sentinel-2 (sentinel-2-c1-l2a), per 1 km cell and per ten-day period, compared with the same period of 2019, 2020, 2021 in the same cell. Each group is divided by unflooded cells 3 to 15 km from the flood, so that a dry or wet year does not count as damage or recovery. 100% means as green as normal, relative to those neighbours.
Images: 2,511 of 5,584 scenes used (0 could not be read, 7 failed the reflectance check). Control: 4,822 cells.
A 1 km cell counts as flooded when at least 50% of its land lies inside the flood definition. The cells with more and with fewer older residents are split at the median of each regional unit, so that both groups draw on every unit alike.
Ten-day periods in which a group is not normally green (average greenness below 0.30 in the years before) are skipped, because a bare flooded field then looks the same as a bare normal one. Cells that are not green in a normal year at all (median below 0.15: lakes, towns, bare ground) are left out.

| Period | Year | Scenes | Expected at least |
| --- | --- | --- | --- |
| baseline | 2019 | 1,040 | 600 |
| baseline | 2020 | 1,348 | 600 |
| baseline | 2021 | 1,329 | 600 |
| after | 2023 | 420 | 200 |
| after | 2024 | 1,447 | 600 |

## Greenness season by season

Average over the ten-day periods of each season with a clear view; a season needs at least 5 such periods. In brackets, the 95% interval from 1,000 resamplings of the squares (Poisson bootstrap), drawn in blocks of 10 by 10 km so that neighbouring squares are resampled together, with control squares 3 to 15 km from the flood. It shows how much a figure depends on which places happen to be in a group.

### Observed flood, including flood traces

| Group | Cells | Residents | Autumn 2023 | Spring 2024 | Summer 2024 |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 1,431 | 43,056 | 75% (58% to 89%) | 91% (78% to 100%) | 87% (82% to 91%) |
| Flooded, Karditsa, Trikala | 868 | 29,635 | 89% (82% to 96%) | 102% (99% to 106%) | 90% (86% to 94%) |
| Flooded, Larisa | 528 | 13,340 | 60% (30% to 87%) | 83% (64% to 98%) | 82% (72% to 89%) |
| Flooded, Magnisia, Sporades | 35 | 81 | below zero: mostly still under water | below zero: mostly still under water | n/a |
| Flooded, Larisa, outside the Karla basin | 437 | 13,188 | 90% (80% to 99%) | 97% (93% to 101%) | 90% (87% to 93%) |
| Flooded, more older residents | 77 | 11,767 | 98% (92% to 106%) | 98% (94% to 102%) | 92% (89% to 95%) |
| Flooded, fewer older residents | 78 | 29,637 | 96% (87% to 104%) | 98% (91% to 103%) | 91% (88% to 94%) |

### Observed standing water, without flood traces

| Group | Cells | Residents | Autumn 2023 | Spring 2024 | Summer 2024 |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 827 | 20,742 | 54% (30% to 74%) | 81% (60% to 99%) | 85% (77% to 90%) |
| Flooded, Karditsa, Trikala | 459 | 9,572 | 74% (67% to 81%) | 102% (97% to 108%) | 90% (85% to 94%) |
| Flooded, Larisa | 333 | 11,089 | 44% (1% to 82%) | 74% (44% to 98%) | 78% (63% to 90%) |
| Flooded, Magnisia, Sporades | 35 | 81 | below zero: mostly still under water | below zero: mostly still under water | n/a |
| Flooded, Larisa, outside the Karla basin | 247 | 11,013 | 81% (69% to 89%) | 97% (91% to 103%) | 91% (88% to 96%) |
| Flooded, more older residents | 27 | 4,055 | 85% (80% to 95%) | 98% (89% to 105%) | 90% (84% to 98%) |
| Flooded, fewer older residents | 30 | 15,949 | 81% (65% to 93%) | 91% (70% to 100%) | 91% (85% to 96%) |

### Copernicus maximum water extent

| Group | Cells | Residents | Autumn 2023 | Spring 2024 | Summer 2024 |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 841 | 20,770 | 54% (31% to 74%) | 81% (61% to 99%) | 85% (77% to 91%) |
| Flooded, Karditsa, Trikala | 465 | 9,577 | 74% (67% to 82%) | 102% (97% to 108%) | 90% (85% to 94%) |
| Flooded, Larisa | 340 | 11,112 | 44% (3% to 82%) | 74% (44% to 97%) | 78% (63% to 90%) |
| Flooded, Magnisia, Sporades | 36 | 81 | below zero: mostly still under water | below zero: mostly still under water | n/a |
| Flooded, Larisa, outside the Karla basin | 250 | 11,036 | 81% (69% to 90%) | 97% (91% to 103%) | 91% (87% to 96%) |
| Flooded, more older residents | 27 | 4,055 | 85% (80% to 95%) | 98% (89% to 105%) | 90% (84% to 98%) |
| Flooded, fewer older residents | 30 | 15,949 | 81% (65% to 93%) | 91% (70% to 100%) | 91% (85% to 96%) |

## What holds under every flood definition and every control area

Each comparison is repeated under all 3 flood definitions and with control squares at 3 distances from the flood: 3 to 15 km (4,822 squares), 5 to 20 km (4,522 squares), 10 to 30 km (3,463 squares). A difference counts as a finding only if, every time, it is at least 3 points and its 95% interval stays on one side of zero. If the interval includes zero every time, no difference is shown. Anything else is not robust.

**Flooded, Larisa against Flooded, Karditsa, Trikala, Spring 2024: Flooded, Larisa lower**

| Control area | Flood definition | Difference | 95% interval |
| --- | --- | --- | --- |
| 3 to 15 km | Observed flood, including flood traces | -19.3 points | -38.9 to -3.7 |
| 3 to 15 km | Observed standing water, without flood traces | -28.1 points | -58.7 to -4.1 |
| 3 to 15 km | Copernicus maximum water extent | -28.2 points | -58.2 to -4.3 |
| 5 to 20 km | Observed flood, including flood traces | -19.1 points | -38.7 to -3.8 |
| 5 to 20 km | Observed standing water, without flood traces | -27.9 points | -58.0 to -4.0 |
| 5 to 20 km | Copernicus maximum water extent | -27.9 points | -57.5 to -4.2 |
| 10 to 30 km | Observed flood, including flood traces | -18.9 points | -37.9 to -3.7 |
| 10 to 30 km | Observed standing water, without flood traces | -27.6 points | -57.0 to -4.2 |
| 10 to 30 km | Copernicus maximum water extent | -27.6 points | -56.4 to -4.2 |

**Flooded, Larisa against Flooded, Karditsa, Trikala, Summer 2024: not robust**

| Control area | Flood definition | Difference | 95% interval |
| --- | --- | --- | --- |
| 3 to 15 km | Observed flood, including flood traces | -8.7 points | -18.4 to -0.0 |
| 3 to 15 km | Observed standing water, without flood traces | -12.2 points | -26.5 to +1.1 |
| 3 to 15 km | Copernicus maximum water extent | -12.2 points | -26.1 to +0.8 |
| 5 to 20 km | Observed flood, including flood traces | -8.7 points | -18.5 to -0.0 |
| 5 to 20 km | Observed standing water, without flood traces | -12.1 points | -26.5 to +1.1 |
| 5 to 20 km | Copernicus maximum water extent | -12.2 points | -26.2 to +0.8 |
| 10 to 30 km | Observed flood, including flood traces | -8.7 points | -18.5 to +0.0 |
| 10 to 30 km | Observed standing water, without flood traces | -12.1 points | -26.6 to +1.1 |
| 10 to 30 km | Copernicus maximum water extent | -12.2 points | -26.3 to +0.8 |

**Flooded, Larisa, outside the Karla basin against Flooded, Karditsa, Trikala, Spring 2024: no difference shown**

| Control area | Flood definition | Difference | 95% interval |
| --- | --- | --- | --- |
| 3 to 15 km | Observed flood, including flood traces | -4.8 points | -10.4 to +0.7 |
| 3 to 15 km | Observed standing water, without flood traces | -5.4 points | -14.4 to +2.2 |
| 3 to 15 km | Copernicus maximum water extent | -5.4 points | -14.2 to +2.0 |
| 5 to 20 km | Observed flood, including flood traces | -4.8 points | -10.3 to +0.7 |
| 5 to 20 km | Observed standing water, without flood traces | -5.3 points | -14.2 to +2.3 |
| 5 to 20 km | Copernicus maximum water extent | -5.3 points | -14.0 to +2.1 |
| 10 to 30 km | Observed flood, including flood traces | -4.7 points | -10.2 to +0.7 |
| 10 to 30 km | Observed standing water, without flood traces | -5.2 points | -13.9 to +2.3 |
| 10 to 30 km | Copernicus maximum water extent | -5.2 points | -13.8 to +2.2 |

**Flooded, Larisa, outside the Karla basin against Flooded, Karditsa, Trikala, Summer 2024: no difference shown**

| Control area | Flood definition | Difference | 95% interval |
| --- | --- | --- | --- |
| 3 to 15 km | Observed flood, including flood traces | -0.6 points | -4.7 to +4.7 |
| 3 to 15 km | Observed standing water, without flood traces | +1.0 points | -4.0 to +8.2 |
| 3 to 15 km | Copernicus maximum water extent | +0.8 points | -4.2 to +7.9 |
| 5 to 20 km | Observed flood, including flood traces | -0.6 points | -4.7 to +4.7 |
| 5 to 20 km | Observed standing water, without flood traces | +1.0 points | -4.0 to +8.2 |
| 5 to 20 km | Copernicus maximum water extent | +0.8 points | -4.2 to +7.9 |
| 10 to 30 km | Observed flood, including flood traces | -0.5 points | -4.8 to +4.7 |
| 10 to 30 km | Observed standing water, without flood traces | +1.0 points | -4.0 to +8.2 |
| 10 to 30 km | Copernicus maximum water extent | +0.8 points | -4.2 to +8.0 |

**Flooded, more older residents against Flooded, fewer older residents, Spring 2024: no difference shown**

| Control area | Flood definition | Difference | 95% interval |
| --- | --- | --- | --- |
| 3 to 15 km | Observed flood, including flood traces | -0.1 points | -5.8 to +8.0 |
| 3 to 15 km | Observed standing water, without flood traces | +7.8 points | -4.6 to +27.6 |
| 3 to 15 km | Copernicus maximum water extent | +7.8 points | -4.6 to +27.6 |
| 5 to 20 km | Observed flood, including flood traces | -0.1 points | -5.8 to +8.0 |
| 5 to 20 km | Observed standing water, without flood traces | +7.7 points | -4.6 to +27.3 |
| 5 to 20 km | Copernicus maximum water extent | +7.7 points | -4.6 to +27.3 |
| 10 to 30 km | Observed flood, including flood traces | -0.1 points | -5.7 to +7.8 |
| 10 to 30 km | Observed standing water, without flood traces | +7.5 points | -4.5 to +26.7 |
| 10 to 30 km | Copernicus maximum water extent | +7.5 points | -4.5 to +26.7 |

**Flooded, more older residents against Flooded, fewer older residents, Summer 2024: no difference shown**

| Control area | Flood definition | Difference | 95% interval |
| --- | --- | --- | --- |
| 3 to 15 km | Observed flood, including flood traces | +0.9 points | -3.0 to +4.7 |
| 3 to 15 km | Observed standing water, without flood traces | -0.5 points | -7.4 to +9.2 |
| 3 to 15 km | Copernicus maximum water extent | -0.5 points | -7.4 to +9.2 |
| 5 to 20 km | Observed flood, including flood traces | +0.9 points | -3.0 to +4.7 |
| 5 to 20 km | Observed standing water, without flood traces | -0.5 points | -7.4 to +9.1 |
| 5 to 20 km | Copernicus maximum water extent | -0.5 points | -7.4 to +9.1 |
| 10 to 30 km | Observed flood, including flood traces | +0.9 points | -3.0 to +4.7 |
| 10 to 30 km | Observed standing water, without flood traces | -0.5 points | -7.5 to +9.2 |
| 10 to 30 km | Copernicus maximum water extent | -0.5 points | -7.5 to +9.2 |

## When did each group come back (counted from 2024-03-01)

A group counts as recovered at a threshold α on the first of 3 ten-day periods in a row in which its greenness, relative to the control, is at least α of normal. Gaps of up to 3 periods are interpolated. The count starts with the first growing season after the flood, for the reason given under Limits.

### Observed flood, including flood traces

| Group | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 43% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 51% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 |
| Flooded, Larisa | 31% (2023-09-11) | already at this level on 2024-03-01 | 2024-05-01 (day 237) | 2024-09-11 (day 370) | 2024-09-21 (day 380) |
| Flooded, Magnisia, Sporades | below zero (2023-11-11) | not within the period | not within the period | not within the period | not within the period |
| Flooded, Larisa, outside the Karla basin | 63% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 |
| Flooded, more older residents | 68% (2024-12-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 |
| Flooded, fewer older residents | 66% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 |

Order of recovery the same under every threshold and every run length (2, 3, 5 ten-day periods in a row): **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer, 2 periods in a row: α 80%: +0; α 85%: +0; α 90%: +0; α 95%: +0.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer, 3 periods in a row: α 80%: +0; α 85%: +0; α 90%: +0; α 95%: +0.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer, 5 periods in a row: α 80%: +0; α 85%: +0; α 90%: +0; α 95%: +0.

### Observed standing water, without flood traces

| Group | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 16% (2023-09-11) | 2024-05-01 (day 237) | 2024-05-01 (day 237) | 2024-08-21 (day 349) | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 30% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 |
| Flooded, Larisa | 1% (2023-09-11) | 2024-04-11 (day 217) | 2024-04-11 (day 217) | 2024-09-21 (day 380) | 2024-10-11 (day 400) |
| Flooded, Magnisia, Sporades | below zero (2023-11-11) | not within the period | not within the period | not within the period | not within the period |
| Flooded, Larisa, outside the Karla basin | 52% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 |
| Flooded, more older residents | 44% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 |
| Flooded, fewer older residents | 46% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | 2024-05-01 (day 237) | 2024-09-01 (day 360) |

Order of recovery the same under every threshold and every run length (2, 3, 5 ten-day periods in a row): **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer, 2 periods in a row: α 80%: +0; α 85%: +0; α 90%: +0; α 95%: -71.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer, 3 periods in a row: α 80%: +0; α 85%: +0; α 90%: -61; α 95%: -184.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer, 5 periods in a row: α 80%: +0; α 85%: -61; α 90%: -20; α 95%: +10.

### Copernicus maximum water extent

| Group | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 16% (2023-09-11) | 2024-05-01 (day 237) | 2024-05-01 (day 237) | 2024-08-21 (day 349) | 2024-09-11 (day 370) |
| Flooded, Karditsa, Trikala | 31% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 |
| Flooded, Larisa | 2% (2023-09-11) | 2024-04-11 (day 217) | 2024-04-11 (day 217) | 2024-09-21 (day 380) | 2024-10-11 (day 400) |
| Flooded, Magnisia, Sporades | below zero (2023-11-11) | not within the period | not within the period | not within the period | not within the period |
| Flooded, Larisa, outside the Karla basin | 53% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 |
| Flooded, more older residents | 44% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 | already at this level on 2024-03-01 |
| Flooded, fewer older residents | 46% (2023-09-11) | already at this level on 2024-03-01 | already at this level on 2024-03-01 | 2024-05-01 (day 237) | 2024-09-01 (day 360) |

Order of recovery the same under every threshold and every run length (2, 3, 5 ten-day periods in a row): **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer, 2 periods in a row: α 80%: +0; α 85%: +0; α 90%: +0; α 95%: -71.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer, 3 periods in a row: α 80%: +0; α 85%: +0; α 90%: -61; α 95%: -184.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer, 5 periods in a row: α 80%: +0; α 85%: -61; α 90%: -20; α 95%: +10.

Recovery days, across every flood definition and threshold: **not robust**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.

## Limits

Autumn greenness after the flood is hard to read. The storm struck a few weeks before the cotton harvest, and in a normal year the harvested fields of the plain are bare by October, so a field that was never harvested, or that later grew weeds or another crop, can look as green as normal or greener while yielding nothing. Greenness alone cannot tell crop from weeds, so greenness right after the flood does not mean the land was working again. That is why the recovery count starts with the next growing season.

Storm Elias brought a second flood on 27 and 28 September 2023, so autumn 2023 reflects both storms. In Larisa the basin of the former Lake Karla filled with water and stayed flooded well into 2024; land under water there measures a new lake, not slow recovery, which is why Larisa is also compared without that basin.

Greenness measures fields and gardens coming back, not households: a farm can be green again while its owners are still waiting for help, and a village can be rebuilt on land that stays bare. Clouds remove many autumn and winter images, crops rotate between years, and farmers may have left fields fallow on purpose. Greenness below zero means the ground is mostly water. The cells with more older residents are compared with those with fewer within the flooded area only, and both include the fields around each village.
