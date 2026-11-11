# Phase B: who was in the water of Storm Daniel?

Generated automatically by `thrive phase-b`. `sources.json` records what was downloaded and when.

Flood extent: union of the observed-flood polygons in the Copernicus EMS EMSR692 products (28 products, 28 flood layers, each read once). This is the largest extent the satellites saw over all dates, not the depth of the water.
Population: Eurostat census grid 2021, version 2.2 (22 January 2025), column `T`; people aged 65 and over from `Y_GE65`.

| Regional unit | Residents | Flooded area (km²) | Residents in flooded parts of cells | Share of residents | Aged 65+ among all residents | Aged 65+ among those exposed |
| --- | --- | --- | --- | --- | --- | --- |
| Karditsa, Trikala | 228,068 | 877.0 | 33,788 | 14.8% | 28.7% | 30.6% |
| Larisa | 268,444 | 560.2 | 24,184 | 9.0% | 23.3% | 20.3% |
| Magnisia, Sporades | 190,814 | 37.8 | 99 | 0.1% | 23.7% | 29.9% |

Thessaly in total: 58,071 of 687,327 residents (8.4%) lived in the parts of 1 km cells that satellites saw under water, over 1,475 km².

People aged 65 and over were 25.2% of all residents and 26.3% of those exposed, a ratio of 1.04. Above 1, older people were more likely than the average resident to live where the water reached. The age count covers 100.0% of the population; cells without an age figure are left out of these two shares.

## Checks

| Regional unit | Residents on the grid | Census 2021 (ELSTAT) | Difference |
| --- | --- | --- | --- |
| Karditsa, Trikala | 228,068 | 228,386 | -318 (-0.1%) |
| Larisa | 268,444 | 268,963 | -519 (-0.2%) |
| Magnisia, Sporades | 190,814 | 190,906 | -92 (-0.0%) |

Population on the grid near Thessaly that fell in no regional unit (cells at sea or on islets the 1:1 million boundaries leave out): 0 residents in 63 cells.
Copernicus also publishes its own maximum water extent per product. Its union covers 999 km² inside Thessaly, against 1,475 km² for the union of observed floods used here.
Flood classes in the layers used, with the number of polygons: Riverine flood 32,030; Flood trace 16,758; Flooded area 15,272.

## Limits

People are assumed to be spread evenly over the land part of each 1 km cell, so a cell whose land is half under water counts half its residents. Satellites miss water under cloud, in narrow streets and under trees, and the extent mixes several dates. Exposure is not harm: a household in a flooded cell may have stayed dry on an upper floor, and one outside may have lost everything.

Magnesia and the town of Volos: the floods there were mostly flash floods in streets and streams that drained within hours, which satellites passing later rarely see. The low figure for Magnesia therefore says little about how hard it was hit.
