# Phase C: wildfires, regional growth and Tourism, after the Hellenic Parliamentary Budget Office

Generated automatically by `thrive phase-c`. `sources.json` records what was downloaded and when.

Source being replicated: Spaliara, M. E. and Tsoukalas, J. (2026). Climate Extremes and Regional Growth in Greece: Evidence from 52 Regions. Research Note No 3, Hellenic Parliamentary Budget Office, November 2026.

## Verdict on the replication

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

## Tourism nights after a fire (beyond the Note)

The Note ends in 2023, when regional accounts end. Eurostat counts nights spent at tourist accommodation by NUTS 3 region up to 2025, so the same event study is run on the annual growth of nights, 2022 to 2025. Percentage points of growth in nights per 1 % of the region's area burnt; region and year fixed effects; standard errors clustered by region. This is an extension of the Note, not part of the replication.

| Nights by | Year before | Fire year | Year after | Two years after | Cumulative | Observations |
| --- | --- | --- | --- | --- | --- | --- |
| all guests | -0.56 (p 0.39) | -0.17 (p 0.67) | -0.41 (p 0.58) | +0.03 (p 0.94) | -0.54 (p 0.72) | 208 |
| guests from abroad | -0.45 (p 0.62) | -0.80 (p 0.24) | -1.07 (p 0.26) | -0.71 (p 0.27) | -2.59 (p 0.21) | 208 |

The same cumulative effect, fire year to two years after, under each check fixed in advance:

| Check | Nights by | Cumulative | Observations |
| --- | --- | --- | --- |
| 2022 to 2025, all regions | all guests | -0.54 (p 0.72) | 208 |
| 2022 to 2025, all regions | guests from abroad | -2.59 (p 0.21) | 208 |
| 2023 to 2025, without the rebound of 2022 from the pandemic | all guests | -1.20 (p 0.37) | 156 |
| 2023 to 2025, without the rebound of 2022 from the pandemic | guests from abroad | -2.16 (p 0.26) | 156 |
| 2022 to 2025, without Evros | all guests | -1.94 (p 0.13) | 204 |
| 2022 to 2025, without Evros | guests from abroad | -3.48 (p 0.12) | 204 |
| 2022 to 2025, without the region of Rhodes | all guests | -0.68 (p 0.65) | 204 |
| 2022 to 2025, without the region of Rhodes | guests from abroad | -3.02 (p 0.14) | 204 |

Following THRIVE's own rule, a direction is reported as a finding only when every check agrees and is significant at the 5 % level:

- all guests: **not robust**
- guests from abroad: **not robust**

Nights in the regions with the largest recent fires (all guests):

| Region | Fires burning 1 % or more | 2021 | 2022 | 2023 | 2024 | 2025 |
| --- | --- | --- | --- | --- | --- | --- |
| Kalymnos, Karpathos, Kasos, Kos, Rodos (EL421) | 2023 (6.9 %) | 14,171,238 (+102.5 %) | 24,182,894 (+70.6 %) | 25,158,840 (+4.0 %) | 28,745,136 (+14.3 %) | 29,164,349 (+1.5 %) |
| Evros (EL511) | 2022 (1.1 %), 2023 (22.3 %) | 296,377 (-9.0 %) | 461,903 (+55.8 %) | 552,585 (+19.6 %) | 590,011 (+6.8 %) | 615,172 (+4.3 %) |
| Evvoia (EL642) | 2016 (1.1 %), 2019 (1.0 %), 2021 (12.6 %) | 960,340 (+23.2 %) | 1,555,193 (+61.9 %) | 1,748,518 (+12.4 %) | 1,721,401 (-1.6 %) | 1,957,544 (+13.7 %) |

## The data

- Regions: 52 NUTS 3 regions of Greece; observations in the gate regression: 312.
- Unit-years with at least 1 % of the area burnt, 2018 to 2023: 27.
- EFFIS fires matched to Greek regions: 1802, years 2016 to 2026.
- Eurostat tables last updated: gva 2026-03-23T23:00:00+0100, population 2026-02-10T11:00:00+0100, volume 2026-03-23T23:00:00+0100.

Tolerances: 0.05 percentage points for each coefficient; 0.3 percentage points for each burnt share; 5% for each burnt area.
