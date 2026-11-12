# Phase B: who was in the water of Storm Daniel?

Generated automatically by `thrive phase-b`. `sources.json` records what was downloaded and when.

Flood extent: the Copernicus EMS EMSR692 products (28 products, 28 flood layers, each read once), merged over every date the satellites passed. The main table uses the first definition below; the others follow it.
Population: Eurostat census grid 2021, version 2.2 (22 January 2025), column `T`; people aged 65 and over from `Y_GE65`.

## Main result: Observed flood, including flood traces

| Regional unit | Residents | Flooded area (km²) | Residents in flooded parts of cells | Share of residents | Aged 65+ among all residents | Aged 65+ among those exposed | Ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Karditsa, Trikala | 228,068 | 877.0 | 33,788 | 14.8% | 28.7% | 30.6% | 1.07 |
| Larisa | 268,444 | 560.2 | 24,184 | 9.0% | 23.3% | 20.3% | 0.87 |
| Magnisia, Sporades | 190,814 | 37.8 | 99 | 0.1% | 23.7% | 29.9% | too few exposed |

Thessaly in total: 58,071 of 687,327 residents (8.4%) lived in the parts of 1 km cells inside this extent, over 1,475 km².

The ratio compares the share of people aged 65 and over among those exposed with their share among all residents. Above 1, older people were more likely than the average resident to live where the water reached. A regional unit with fewer than 1,000 people exposed gets no ratio. The age count covers 100.0% of the population.

## The same question under each flood definition

| Flood definition | Flooded area in Thessaly (km²) | Residents exposed | Share of residents | Ratio, Thessaly | Ratio, Karditsa, Trikala | Ratio, Larisa | Ratio, Magnisia, Sporades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Observed flood, including flood traces | 1,475 | 58,071 | 8.4% | 1.04 (0.97 to 1.14) | 1.07 (0.99 to 1.14) | 0.87 (0.78 to 0.98) | too few exposed |
| Observed standing water, without flood traces | 913 | 33,919 | 4.9% | 0.95 (0.87 to 1.07) | 1.19 (1.10 to 1.27) | 0.79 (0.71 to 0.88) | too few exposed |
| Copernicus maximum water extent | 999 | 35,824 | 5.2% | 0.95 (0.86 to 1.06) | 1.18 (1.09 to 1.25) | 0.79 (0.71 to 0.87) | too few exposed |

In brackets, the 95% interval from 1,000 resamplings of the 1 km squares (Poisson bootstrap). It shows how much a ratio depends on which squares the water happened to reach. A direction counts only if the interval stays on one side of 1 under every flood definition.

Direction for Thessaly as a whole, across all definitions: **not robust**. Direction inside the regional units, across all definitions and every unit with enough people exposed: **not robust**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.

Direction in each regional unit, across all definitions: Karditsa, Trikala: **not robust**; Larisa: **older people less exposed**; Magnisia, Sporades: **no data**.

## Checks

| Regional unit | Residents on the grid | Census 2021 (ELSTAT) | Difference |
| --- | --- | --- | --- |
| Karditsa, Trikala | 228,068 | 228,386 | -318 (-0.1%) |
| Larisa | 268,444 | 268,963 | -519 (-0.2%) |
| Magnisia, Sporades | 190,814 | 190,906 | -92 (-0.0%) |

Population on the grid near Thessaly that fell in no regional unit (cells at sea or on islets the 1:1 million boundaries leave out): 0 residents in 63 cells.
Area of each flood class inside Thessaly, before merging (classes overlap between dates): Flood trace 1,236 km²; Flooded area 913 km².

## Limits

People are assumed to be spread evenly over the land part of each 1 km cell, so a cell whose land is half under water counts half its residents. Satellites miss water under cloud, in narrow streets and under trees, and the extent mixes several dates. A flood trace marks ground where the water had already gone when the image was taken. Statistical offices may adjust small counts on the grid to protect confidentiality, and the grid flags each such figure, so single cells are approximate even where the totals match the census. Exposure is not harm: a household in a flooded cell may have stayed dry on an upper floor, and one outside may have lost everything.

Magnesia and the town of Volos: the floods there were mostly flash floods in streets and streams that drained within hours, which satellites passing later rarely see. The low figure for Magnesia therefore says little about how hard it was hit.
