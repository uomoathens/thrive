# Phase B: who was in the water of Storm Daniel?

Generated automatically by `thrive phase-b`. `sources.json` records what was downloaded and when.

Flood extent: union of every flood polygon in the Copernicus EMS EMSR692 products (28 products, 56 flood layers). This is the largest extent observed from satellites, not the depth of the water.
Population: Eurostat GISCO 1 km grid, column `TOT_P_2021`; the grid file has no age column, so older people are not counted.

| Regional unit | Residents | Flooded area (km²) | Residents in flooded cells | Share of residents | Aged 65+ among those exposed |
| --- | --- | --- | --- | --- | --- |
| Karditsa, Trikala | 228,068 | 877.0 | 33,788 | 14.8% | n/a |
| Larisa | 267,945 | 560.2 | 24,172 | 9.0% | n/a |
| Magnisia, Sporades | 180,170 | 37.8 | 99 | 0.1% | n/a |

Thessaly in total: 58,060 of 676,183 residents (8.6%) lived in the parts of 1 km cells that satellites saw under water, over 1,475 km².

Limits: people are assumed to be spread evenly within each 1 km cell, so a cell that is half under water counts half its residents. Satellites miss water under cloud, in narrow streets and under trees, and the extent mixes several dates. Exposure is not harm: a household in a flooded cell may have been dry on an upper floor, and one outside may have lost everything.
