# Thriving: when did the flooded land of Thessaly come back?

Generated automatically by `thrive thriving`. `sources.json` records what was read and when.

Measure: greenness (NDVI) from Sentinel-2 (sentinel-2-c1-l2a), per 1 km cell and per ten-day period, compared with the same period of 2019, 2020, 2021 in the same cell. Each group is divided by unflooded cells 3 to 15 km from the flood, so that a dry or wet year does not count as damage or recovery. 100% means as green as normal, relative to those neighbours.
Images: 2,511 of 5,584 scenes used (0 could not be read, 7 failed the reflectance check). Control: 4,822 cells.
Ten-day periods in which a group is not normally green (average greenness below 0.30 in the years before) are skipped, because a bare flooded field then looks the same as a bare normal one. Cells that are not green in a normal year at all (median below 0.15: lakes, towns, bare ground) are left out.

| Period | Year | Scenes | Expected at least |
| --- | --- | --- | --- |
| baseline | 2019 | 1,040 | 600 |
| baseline | 2020 | 1,348 | 600 |
| baseline | 2021 | 1,329 | 600 |
| after | 2023 | 420 | 200 |
| after | 2024 | 1,447 | 600 |

## Greenness season by season

Average over the ten-day periods of each season with a clear view; a season needs at least 5 such periods. In brackets, the 95% interval from 1,000 resamplings of the squares (Poisson bootstrap), with control squares 3 to 15 km from the flood. It shows how much a figure depends on which squares happen to be in a group.

### Observed flood, including flood traces

| Group | Cells | Residents | Autumn 2023 | Spring 2024 | Summer 2024 |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 1,431 | 43,056 | 75% (72% to 78%) | 91% (89% to 93%) | 87% (86% to 88%) |
| Flooded, Karditsa, Trikala | 868 | 29,635 | 89% (88% to 91%) | 102% (101% to 104%) | 90% (89% to 91%) |
| Flooded, Larisa | 528 | 13,340 | 60% (54% to 66%) | 83% (79% to 87%) | 82% (79% to 84%) |
| Flooded, Magnisia, Sporades | 35 | 81 | below zero: mostly still under water | below zero: mostly still under water | n/a |
| Flooded, more older residents | 77 | 12,049 | 97% (93% to 101%) | 98% (95% to 101%) | 92% (90% to 95%) |
| Flooded, fewer older residents | 78 | 29,355 | 97% (90% to 103%) | 99% (93% to 103%) | 91% (89% to 93%) |

### Observed standing water, without flood traces

| Group | Cells | Residents | Autumn 2023 | Spring 2024 | Summer 2024 |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 827 | 20,742 | 54% (50% to 58%) | 81% (77% to 85%) | 85% (83% to 86%) |
| Flooded, Karditsa, Trikala | 459 | 9,572 | 74% (71% to 76%) | 102% (100% to 105%) | 90% (89% to 91%) |
| Flooded, Larisa | 333 | 11,089 | 44% (36% to 52%) | 74% (69% to 80%) | 78% (74% to 82%) |
| Flooded, Magnisia, Sporades | 35 | 81 | below zero: mostly still under water | below zero: mostly still under water | n/a |
| Flooded, more older residents | 28 | 4,441 | 81% (75% to 87%) | 97% (92% to 103%) | 91% (86% to 96%) |
| Flooded, fewer older residents | 29 | 15,563 | 83% (69% to 93%) | 92% (75% to 103%) | 90% (86% to 94%) |

### Copernicus maximum water extent

| Group | Cells | Residents | Autumn 2023 | Spring 2024 | Summer 2024 |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 841 | 20,770 | 54% (50% to 59%) | 81% (77% to 85%) | 85% (83% to 86%) |
| Flooded, Karditsa, Trikala | 465 | 9,577 | 74% (72% to 76%) | 102% (100% to 104%) | 90% (89% to 91%) |
| Flooded, Larisa | 340 | 11,112 | 44% (36% to 53%) | 74% (68% to 79%) | 78% (74% to 82%) |
| Flooded, Magnisia, Sporades | 36 | 81 | below zero: mostly still under water | below zero: mostly still under water | n/a |
| Flooded, more older residents | 28 | 4,441 | 81% (74% to 88%) | 97% (91% to 103%) | 91% (86% to 96%) |
| Flooded, fewer older residents | 29 | 15,563 | 83% (68% to 93%) | 92% (74% to 103%) | 90% (86% to 94%) |

## What holds under every flood definition and every control area

Each comparison is repeated under all 3 flood definitions and with control squares at 3 distances from the flood: 3 to 15 km (4,822 squares), 5 to 20 km (4,522 squares), 10 to 30 km (3,463 squares). A difference counts as a finding only if, every time, it is at least 3 points and its 95% interval stays on one side of zero. If the interval includes zero every time, no difference is shown. Anything else is not robust.

**Flooded, Larisa against Flooded, Karditsa, Trikala, Spring 2024: Flooded, Larisa lower**

| Control area | Flood definition | Difference | 95% interval |
| --- | --- | --- | --- |
| 3 to 15 km | Observed flood, including flood traces | -19.3 points | -23.5 to -15.1 |
| 3 to 15 km | Observed standing water, without flood traces | -28.2 points | -34.3 to -22.4 |
| 3 to 15 km | Copernicus maximum water extent | -28.2 points | -34.4 to -22.1 |
| 5 to 20 km | Observed flood, including flood traces | -19.1 points | -23.4 to -15.0 |
| 5 to 20 km | Observed standing water, without flood traces | -28.0 points | -34.0 to -22.2 |
| 5 to 20 km | Copernicus maximum water extent | -28.0 points | -34.2 to -21.9 |
| 10 to 30 km | Observed flood, including flood traces | -18.9 points | -23.1 to -14.8 |
| 10 to 30 km | Observed standing water, without flood traces | -27.6 points | -33.6 to -22.0 |
| 10 to 30 km | Copernicus maximum water extent | -27.6 points | -33.8 to -21.7 |

**Flooded, Larisa against Flooded, Karditsa, Trikala, Summer 2024: Flooded, Larisa lower**

| Control area | Flood definition | Difference | 95% interval |
| --- | --- | --- | --- |
| 3 to 15 km | Observed flood, including flood traces | -8.7 points | -11.5 to -6.0 |
| 3 to 15 km | Observed standing water, without flood traces | -12.0 points | -15.8 to -7.8 |
| 3 to 15 km | Copernicus maximum water extent | -12.1 points | -16.0 to -8.3 |
| 5 to 20 km | Observed flood, including flood traces | -8.7 points | -11.4 to -6.0 |
| 5 to 20 km | Observed standing water, without flood traces | -12.0 points | -15.8 to -7.8 |
| 5 to 20 km | Copernicus maximum water extent | -12.1 points | -16.0 to -8.3 |
| 10 to 30 km | Observed flood, including flood traces | -8.7 points | -11.5 to -6.0 |
| 10 to 30 km | Observed standing water, without flood traces | -12.0 points | -15.9 to -7.8 |
| 10 to 30 km | Copernicus maximum water extent | -12.1 points | -16.0 to -8.3 |

**Flooded, more older residents against Flooded, fewer older residents, Spring 2024: no difference shown**

| Control area | Flood definition | Difference | 95% interval |
| --- | --- | --- | --- |
| 3 to 15 km | Observed flood, including flood traces | -0.9 points | -6.0 to +6.0 |
| 3 to 15 km | Observed standing water, without flood traces | +5.2 points | -7.3 to +22.6 |
| 3 to 15 km | Copernicus maximum water extent | +5.2 points | -7.7 to +24.3 |
| 5 to 20 km | Observed flood, including flood traces | -0.9 points | -5.9 to +5.9 |
| 5 to 20 km | Observed standing water, without flood traces | +5.2 points | -7.2 to +22.5 |
| 5 to 20 km | Copernicus maximum water extent | +5.2 points | -7.5 to +24.0 |
| 10 to 30 km | Observed flood, including flood traces | -0.9 points | -5.8 to +5.8 |
| 10 to 30 km | Observed standing water, without flood traces | +5.2 points | -6.9 to +22.1 |
| 10 to 30 km | Copernicus maximum water extent | +5.2 points | -7.3 to +23.6 |

**Flooded, more older residents against Flooded, fewer older residents, Summer 2024: no difference shown**

| Control area | Flood definition | Difference | 95% interval |
| --- | --- | --- | --- |
| 3 to 15 km | Observed flood, including flood traces | +1.1 points | -1.9 to +4.3 |
| 3 to 15 km | Observed standing water, without flood traces | +0.8 points | -5.1 to +7.1 |
| 3 to 15 km | Copernicus maximum water extent | +0.8 points | -5.4 to +7.4 |
| 5 to 20 km | Observed flood, including flood traces | +1.1 points | -1.9 to +4.3 |
| 5 to 20 km | Observed standing water, without flood traces | +0.8 points | -5.1 to +7.1 |
| 5 to 20 km | Copernicus maximum water extent | +0.8 points | -5.4 to +7.4 |
| 10 to 30 km | Observed flood, including flood traces | +1.1 points | -1.9 to +4.3 |
| 10 to 30 km | Observed standing water, without flood traces | +0.8 points | -5.2 to +7.1 |
| 10 to 30 km | Copernicus maximum water extent | +0.8 points | -5.4 to +7.4 |

## When did each group come back (counted from 2024-03-01)

A group counts as recovered at a threshold α on the first of 3 ten-day periods in a row in which its greenness, relative to the control, is at least α of normal. Gaps of up to 3 periods are interpolated. The count starts with the first growing season after the flood, for the reason given under Limits.

### Observed flood, including flood traces

| Group | Lowest point | Recovered at 80% | Recovered at 85% | Recovered at 90% | Recovered at 95% |
| --- | --- | --- | --- | --- | --- |
| All flooded cells | 43% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-09-11 (day 370) |
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
| Flooded, Karditsa, Trikala | 30% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) |
| Flooded, Larisa | 2% (2023-09-11) | 2024-04-11 (day 217) | 2024-04-11 (day 217) | 2024-09-21 (day 380) | 2024-10-11 (day 400) |
| Flooded, Magnisia, Sporades | below zero (2023-11-11) | not within the period | not within the period | not within the period | not within the period |
| Flooded, more older residents | 44% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) |
| Flooded, fewer older residents | 46% (2023-09-11) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-03-01 (day 176) | 2024-09-01 (day 360) |

Order of recovery the same under every threshold: **no**.
Days by which the cells with more older residents recovered later (positive) or earlier (negative) than those with fewer: α 80%: +0; α 85%: +0; α 90%: +0; α 95%: -184.

Recovery days, across every flood definition and threshold: **not robust**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.

## Limits

In the first weeks after the flood the flooded fields often look greener than normal. The storm struck a few weeks before the cotton harvest, and in a normal year the harvested fields of the plain are bare by October; fields left unharvested and wet kept some green cover. Greenness alone cannot tell crop from weeds, so greenness right after the flood does not mean the land was working again. That is why the recovery count starts with the next growing season.

Greenness measures fields and gardens coming back, not households: a farm can be green again while its owners are still waiting for help, and a village can be rebuilt on land that stays bare. Clouds remove many autumn and winter images, crops rotate between years, and farmers may have left fields fallow on purpose. Greenness below zero means the ground is mostly water. The cells with more older residents are compared with those with fewer within the flooded area only, and both include the fields around each village.
