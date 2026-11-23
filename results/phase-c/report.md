# Phase C, step C.1: replication of the wildfire result of the Hellenic Parliamentary Budget Office

Generated automatically by `thrive phase-c`. `sources.json` records what was downloaded and when.

Source being replicated: Spaliara, M. E. and Tsoukalas, J. (2026). Climate Extremes and Regional Growth in Greece: Evidence from 52 Regions. Research Note No 3, Hellenic Parliamentary Budget Office, November 2026.

## Verdict

The result was replicated: the burnt areas and every coefficient of the gate sector are within tolerance.

## Burnt area of the largest fires (Table C1)

| Region | Year | Burnt ha, THRIVE | Burnt ha, PBO | Share %, THRIVE | Share %, PBO | Within tolerance |
| --- | --- | --- | --- | --- | --- | --- |
| Evros (EL511) | 2023 | 94,578 | 94,578 | 22.3 | 22.3 | yes |
| Evvoia (EL642) | 2021 | 52,668 | 52,668 | 12.6 | 12.6 | yes |
| Kalymnos, Karpathos, Kasos, Kos, Rodos (EL421) | 2023 | 18,687 | 18,687 | 6.9 | 6.9 | yes |

## Growth response to area burnt, 2018 to 2023 (Table C2)

Percentage points of growth in GVA per inhabitant per 1 % of the region's area burnt. Region and year fixed effects, standard errors clustered by region.

| Sector | Measure | Horizon | THRIVE | PBO | Difference | p-value, THRIVE | Within tolerance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | real | year before | -0.57 | -0.57 | -0.00 | 0.15 | yes |
| A | real | fire year | -0.75 | -0.75 | -0.00 | 0.06 | yes |
| A | real | year after | -0.24 | -0.24 | +0.00 | 0.67 | yes |
| A | real | two years after | -0.21 | -0.21 | -0.00 | 0.66 | yes |
| A | real | cumulative | -1.20 | -1.20 | -0.00 | 0.24 | yes |
| B-E | real | year before | +0.02 | +0.02 | -0.00 | 0.94 | yes |
| B-E | real | fire year | -0.11 | -0.11 | +0.00 | 0.44 | yes |
| B-E | real | year after | -0.79 | -0.79 | +0.00 | 0.07 | yes |
| B-E | real | two years after | -0.43 | -0.43 | -0.00 | 0.03 | yes |
| B-E | real | cumulative | -1.33 | -1.33 | +0.00 | 0.03 | yes |
| C | real | year before | -0.13 | -0.13 | -0.00 | 0.05 | yes |
| C | real | fire year | -0.22 | -0.22 | +0.00 | 0.00 | yes |
| C | real | year after | -0.18 | -0.18 | +0.00 | 0.41 | yes |
| C | real | two years after | -0.04 | -0.04 | -0.00 | 0.73 | yes |
| C | real | cumulative | -0.43 | -0.43 | -0.00 | 0.03 | yes |
| G-I | real | year before | +0.07 | +0.07 | +0.00 | 0.54 | yes |
| G-I | real | fire year | -0.21 | -0.21 | +0.00 | 0.05 | yes |
| G-I | real | year after | -0.54 | -0.54 | +0.00 | 0.00 | yes |
| G-I | real | two years after | -0.05 | -0.05 | -0.00 | 0.77 | yes |
| G-I | real | cumulative | -0.80 | -0.80 | +0.00 | 0.00 | yes |
| G-I | nominal | fire year | -0.22 | -0.22 | +0.00 | 0.02 | yes |
| G-I | nominal | year after | -0.41 | -0.41 | -0.00 | 0.01 | yes |
| G-I | nominal | two years after | -0.06 | -0.06 | +0.00 | 0.65 | yes |
| G-I | nominal | cumulative | -0.69 | -0.69 | +0.00 | 0.01 | yes |

## The data

- Regions: 52 NUTS 3 regions of Greece; observations in the gate regression: 312.
- Unit-years with at least 1 % of the area burnt, 2018 to 2023: 27.
- EFFIS fires matched to Greek regions: 1802, years 2016 to 2026.
- Eurostat tables last updated: gva 2026-03-23T23:00:00+0100, population 2026-02-10T11:00:00+0100, volume 2026-03-23T23:00:00+0100.

Tolerances: 0.05 percentage points for each coefficient; 0.3 percentage points for each burnt share; 5% for each burnt area.
