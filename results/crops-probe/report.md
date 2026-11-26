# Heat, drought and crops in Thessaly: feasibility probe

Generated automatically by `thrive crops-probe`. It checks, before any analysis, whether the open European data needed for a study of heat and drought damage to crops in Thessaly can be downloaded automatically and whether cotton can be separated in the EU crop map. It produces no finding about crops.

## Verdicts

1. European Drought Observatory data download automatically for every needed indicator and every year: **yes** (ready: fapar_anomaly, soil_moisture_anomaly, spei3, tmax, warm_spell).
2. Cotton area in the EU crop map 2022 matches the Eurostat cotton area of Thessaly within ±35%: **yes**.
3. Whether heat stress can be separated from irrigation at field scale needs Sentinel-2 at 10 to 40 m and is the next step; the drought indicators here are about 5 km, coarser than the fields.

## 1. European Drought Observatory files, by year

| indicator | name | directory | listing_error | files | raster_files | formats | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | all_years_present |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| warm_spell | Warm Spell Duration (JRC MARS) | https://drought.emergency.copernicus.eu/data/Drought_Observatories_datasets/EDO_JRC_MARS_Warm_Spell_Duration/ |  | 74 | 72 | .nc, .zip | 2 | 2 | 2 | 2 | 2 | 2 | 2 | True |
| tmax | Daily Maximum Temperature (JRC MARS) | https://drought.emergency.copernicus.eu/data/Drought_Observatories_datasets/EDO_JRC_MARS_Daily_Maximum_Temperature/ |  | 74 | 72 | .nc, .zip | 2 | 2 | 2 | 2 | 2 | 2 | 2 | True |
| heat_cold_wave | Heat and Cold Wave Index | https://drought.emergency.copernicus.eu/data/Drought_Observatories_datasets/EDO_Heat_and_Cold_Wave_Index_HCWI/ |  | 2 | 0 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | False |
| soil_moisture_anomaly | Soil Moisture Index Anomaly | https://drought.emergency.copernicus.eu/data/Drought_Observatories_datasets/EDO_Soil_Moisture_Index_Anomaly/ |  | 67 | 64 | .nc, .zip | 2 | 2 | 2 | 2 | 2 | 2 | 2 | True |
| fapar_anomaly | fAPAR Anomaly (VIIRS) | https://drought.emergency.copernicus.eu/data/Drought_Observatories_datasets/EDO_Fraction_of_Absorbed_Photosynthetically_Active_Radiation_Anomalies_fAPAR_VIIRS/ |  | 34 | 30 | .nc, .zip | 2 | 2 | 2 | 2 | 2 | 2 | 2 | True |
| spei3 | Standardized Precipitation Evapotranspiration Index, 3 months (JRC MARS) | https://drought.emergency.copernicus.eu/data/Drought_Observatories_datasets/EDO_JRC_MARS_Standardized_Precipitation_Evapotranspiration_Index_SPEI3/ |  | 74 | 72 | .nc, .zip | 2 | 2 | 2 | 2 | 2 | 2 | 2 | True |

### Sample read over Thessaly

- **warm_spell**: ver2-1-0/hwd2m_m_edo_20240101_20241231_d.nc; read
  - /tmp/tmpqlytuill/hwd2m_m_edo_20240101_20241231_d.nc: band 203 of 366 (2024-07-21), CRS EPSG:3035, pixel 10000 x 10000, 522 pixels, valid 100%, min 0.0, mean 4.647509578544061, max 14.0
- **tmax**: ver2-1-0/tmaxm_m_edo_20240101_20241231_d.nc; read
  - /tmp/tmpqlytuill/tmaxm_m_edo_20240101_20241231_d.nc: band 203 of 366 (2024-07-21), CRS EPSG:3035, pixel 10000 x 10000, 522 pixels, valid 76%, min 29.299999237060547, mean 36.1313924282412, max 40.0
- **heat_cold_wave**: no sample; failed: no file with a date and an accepted format under the size limit
- **soil_moisture_anomaly**: ver3-0-2/smian_m_eul_20240101_20241221_t.nc; read
  - /tmp/tmpqlytuill/smian_m_eul_20240101_20241221_t.nc: band 21 of 36 (2024-07-21), CRS EPSG:4326, pixel 0.016667 x 0.016667, 14282 pixels, valid 59%, min -2.9898533821105957, mean -0.878532451534361, max 1.6044965982437134
- **fapar_anomaly**: ver3-1-0/fpanv_m_edo_20240101_20241221_t.nc; read
  - /tmp/tmpqlytuill/fpanv_m_edo_20240101_20241221_t.nc: band 21 of 36 (2024-07-21), CRS EPSG:4326, pixel 0.041667 x 0.041667, 2233 pixels, valid 59%, min -6.530825614929199, mean -1.1158155415059872, max 0.8543393015861511
- **spei3**: ver1-1-0/sem03_m_edo_20240101_20241221_t.nc; read
  - /tmp/tmpqlytuill/sem03_m_edo_20240101_20241221_t.nc: band 21 of 36 (2024-07-21), CRS EPSG:3035, pixel 10000 x 10000, 522 pixels, valid 76%, min -4.599279403686523, mean -1.554401262809487, max 1.2134017944335938

## 2. EU crop map 2022 over Thessaly (NUTS EL61)

GeoTIFF files listed: 159; headers read: 159; files over Thessaly: 1.

| class | name | hectares |
|---|---|---|
| 0 | unknown | 66845.9 |
| 100 | Artificial | 99509.6 |
| 211 | Common wheat | 7692.5 |
| 212 | Durum wheat | 121593.1 |
| 213 | Barley | 4117.3 |
| 214 | Rye | 16.4 |
| 215 | Oats | 1349.7 |
| 216 | Maize | 32631.0 |
| 217 | Rice | 6.0 |
| 218 | Triticale | 3426.7 |
| 219 | Other cereals | 27.6 |
| 221 | Potatoes | 41.3 |
| 222 | Sugar beet | 25.6 |
| 223 | Other root crops | 0.4 |
| 230 | Other non-permanent industrial crops | 97064.7 |
| 231 | Sunflower | 5408.9 |
| 232 | Rapeseed and turnip rapeseed | 4666.0 |
| 233 | Soya | 266.3 |
| 240 | Dry pulses | 440.9 |
| 250 | Fodder crops (cereals and leguminous) | 38273.5 |
| 290 | Bare arable land | 4956.0 |
| 300 | Woodland and Shrubland (incl. permanent crops) | 783312.6 |
| 500 | Grasslands | 118496.2 |
| 600 | Bare land/lichens moss | 2163.5 |
| 700 | Water | 13045.1 |
| 800 | Wetlands | 122.6 |

### Eurostat crop areas, Thessaly

Source: Crop production in EU standard humidity by NUTS 2 region (updated 2026-11-24T23:00:00+0100).

| freq | crops | strucpro | geo | time | label | thousand_ha |
|---|---|---|---|---|---|---|
| A | C0000 | AR_THS_HA | EL61 | 2019 | Cereals for the production of grain (including seed) | 157.88 |
| A | C0000 | AR_THS_HA | EL61 | 2020 | Cereals for the production of grain (including seed) | 157.3 |
| A | C0000 | AR_THS_HA | EL61 | 2021 | Cereals for the production of grain (including seed) | 160.1 |
| A | C0000 | AR_THS_HA | EL61 | 2022 | Cereals for the production of grain (including seed) | 161.92 |
| A | C0000 | AR_THS_HA | EL61 | 2023 | Cereals for the production of grain (including seed) | 175.33 |
| A | C0000 | AR_THS_HA | EL61 | 2024 | Cereals for the production of grain (including seed) | 151.03 |
| A | C1110 | AR_THS_HA | EL61 | 2019 | Common wheat and spelt | 10.1 |
| A | C1110 | AR_THS_HA | EL61 | 2020 | Common wheat and spelt | 9.71 |
| A | C1110 | AR_THS_HA | EL61 | 2021 | Common wheat and spelt | 10.01 |
| A | C1110 | AR_THS_HA | EL61 | 2022 | Common wheat and spelt | 9.07 |
| A | C1110 | AR_THS_HA | EL61 | 2023 | Common wheat and spelt | 11.12 |
| A | C1110 | AR_THS_HA | EL61 | 2024 | Common wheat and spelt | 8.99 |
| A | C1111 | AR_THS_HA | EL61 | 2019 | Common winter wheat and spelt | 10.1 |
| A | C1111 | AR_THS_HA | EL61 | 2020 | Common winter wheat and spelt | 9.71 |
| A | C1111 | AR_THS_HA | EL61 | 2021 | Common winter wheat and spelt | 10.01 |
| A | C1111 | AR_THS_HA | EL61 | 2022 | Common winter wheat and spelt | 9.07 |
| A | C1111 | AR_THS_HA | EL61 | 2023 | Common winter wheat and spelt | 11.12 |
| A | C1111 | AR_THS_HA | EL61 | 2024 | Common winter wheat and spelt | 8.99 |
| A | C1112 | AR_THS_HA | EL61 | 2019 | Common spring wheat and spelt | 0.0 |
| A | C1112 | AR_THS_HA | EL61 | 2020 | Common spring wheat and spelt | 0.0 |
| A | C1112 | AR_THS_HA | EL61 | 2021 | Common spring wheat and spelt | 0.0 |
| A | C1112 | AR_THS_HA | EL61 | 2022 | Common spring wheat and spelt | 0.0 |
| A | C1112 | AR_THS_HA | EL61 | 2023 | Common spring wheat and spelt | 0.0 |
| A | C1112 | AR_THS_HA | EL61 | 2024 | Common spring wheat and spelt | 0.0 |
| A | C1120 | AR_THS_HA | EL61 | 2019 | Durum wheat | 76.22 |
| A | C1120 | AR_THS_HA | EL61 | 2020 | Durum wheat | 76.19 |
| A | C1120 | AR_THS_HA | EL61 | 2021 | Durum wheat | 89.57 |
| A | C1120 | AR_THS_HA | EL61 | 2022 | Durum wheat | 86.43 |
| A | C1120 | AR_THS_HA | EL61 | 2023 | Durum wheat | 92.41 |
| A | C1120 | AR_THS_HA | EL61 | 2024 | Durum wheat | 84.16 |
| A | C1200 | AR_THS_HA | EL61 | 2019 | Rye and winter cereal mixtures (maslin) | 0.42 |
| A | C1200 | AR_THS_HA | EL61 | 2020 | Rye and winter cereal mixtures (maslin) | 0.43 |
| A | C1200 | AR_THS_HA | EL61 | 2021 | Rye and winter cereal mixtures (maslin) | 0.44 |
| A | C1200 | AR_THS_HA | EL61 | 2022 | Rye and winter cereal mixtures (maslin) | 0.31 |
| A | C1200 | AR_THS_HA | EL61 | 2023 | Rye and winter cereal mixtures (maslin) | 0.27 |
| A | C1200 | AR_THS_HA | EL61 | 2024 | Rye and winter cereal mixtures (maslin) | 0.33 |
| A | C1220 | AR_THS_HA | EL61 | 2020 | Winter cereal mixtures (maslin) | 0.0 |
| A | C1220 | AR_THS_HA | EL61 | 2021 | Winter cereal mixtures (maslin) | 0.0 |
| A | C1220 | AR_THS_HA | EL61 | 2022 | Winter cereal mixtures (maslin) | 0.0 |
| A | C1220 | AR_THS_HA | EL61 | 2023 | Winter cereal mixtures (maslin) | 0.0 |
| A | C1220 | AR_THS_HA | EL61 | 2024 | Winter cereal mixtures (maslin) | 0.0 |
| A | C1300 | AR_THS_HA | EL61 | 2019 | Barley | 39.98 |
| A | C1300 | AR_THS_HA | EL61 | 2020 | Barley | 39.76 |
| A | C1300 | AR_THS_HA | EL61 | 2021 | Barley | 28.59 |
| A | C1300 | AR_THS_HA | EL61 | 2022 | Barley | 32.48 |
| A | C1300 | AR_THS_HA | EL61 | 2023 | Barley | 37.22 |
| A | C1300 | AR_THS_HA | EL61 | 2024 | Barley | 27.63 |
| A | C1310 | AR_THS_HA | EL61 | 2019 | Winter barley | 39.98 |
| A | C1310 | AR_THS_HA | EL61 | 2020 | Winter barley | 39.76 |
| A | C1310 | AR_THS_HA | EL61 | 2021 | Winter barley | 28.59 |
| A | C1310 | AR_THS_HA | EL61 | 2022 | Winter barley | 32.48 |
| A | C1310 | AR_THS_HA | EL61 | 2023 | Winter barley | 37.22 |
| A | C1310 | AR_THS_HA | EL61 | 2024 | Winter barley | 27.63 |
| A | C1320 | AR_THS_HA | EL61 | 2019 | Spring barley | 0.0 |
| A | C1320 | AR_THS_HA | EL61 | 2020 | Spring barley | 0.0 |
| A | C1320 | AR_THS_HA | EL61 | 2021 | Spring barley | 0.0 |
| A | C1320 | AR_THS_HA | EL61 | 2022 | Spring barley | 0.0 |
| A | C1320 | AR_THS_HA | EL61 | 2023 | Spring barley | 0.0 |
| A | C1320 | AR_THS_HA | EL61 | 2024 | Spring barley | 0.0 |
| A | C1410 | AR_THS_HA | EL61 | 2019 | Oats | 7.99 |
| A | C1410 | AR_THS_HA | EL61 | 2020 | Oats | 6.72 |
| A | C1410 | AR_THS_HA | EL61 | 2021 | Oats | 6.75 |
| A | C1410 | AR_THS_HA | EL61 | 2022 | Oats | 7.14 |
| A | C1410 | AR_THS_HA | EL61 | 2023 | Oats | 7.36 |
| A | C1410 | AR_THS_HA | EL61 | 2024 | Oats | 7.77 |
| A | C1500 | AR_THS_HA | EL61 | 2019 | Grain maize and corn-cob-mix | 22.37 |
| A | C1500 | AR_THS_HA | EL61 | 2020 | Grain maize and corn-cob-mix | 23.7 |
| A | C1500 | AR_THS_HA | EL61 | 2021 | Grain maize and corn-cob-mix | 23.91 |
| A | C1500 | AR_THS_HA | EL61 | 2022 | Grain maize and corn-cob-mix | 25.7 |
| A | C1500 | AR_THS_HA | EL61 | 2023 | Grain maize and corn-cob-mix | 26.14 |
| A | C1500 | AR_THS_HA | EL61 | 2024 | Grain maize and corn-cob-mix | 21.39 |
| A | C1600 | AR_THS_HA | EL61 | 2019 | Triticale | 0.61 |
| A | C1600 | AR_THS_HA | EL61 | 2020 | Triticale | 0.6 |
| A | C1600 | AR_THS_HA | EL61 | 2021 | Triticale | 0.59 |
| A | C1600 | AR_THS_HA | EL61 | 2022 | Triticale | 0.5 |
| A | C1600 | AR_THS_HA | EL61 | 2023 | Triticale | 0.62 |
| A | C1600 | AR_THS_HA | EL61 | 2024 | Triticale | 0.57 |
| A | C1700 | AR_THS_HA | EL61 | 2019 | Sorghum | 0.18 |
| A | C1700 | AR_THS_HA | EL61 | 2020 | Sorghum | 0.17 |
| A | C1700 | AR_THS_HA | EL61 | 2021 | Sorghum | 0.2 |
| A | C1700 | AR_THS_HA | EL61 | 2022 | Sorghum | 0.22 |
| A | C1700 | AR_THS_HA | EL61 | 2023 | Sorghum | 0.15 |
| A | C1700 | AR_THS_HA | EL61 | 2024 | Sorghum | 0.14 |
| A | C2000 | AR_THS_HA | EL61 | 2019 | Rice | 0.0 |
| A | C2000 | AR_THS_HA | EL61 | 2020 | Rice | 0.0 |
| A | C2000 | AR_THS_HA | EL61 | 2021 | Rice | 0.0 |
| A | C2000 | AR_THS_HA | EL61 | 2022 | Rice | 0.01 |
| A | C2000 | AR_THS_HA | EL61 | 2023 | Rice | 0.01 |
| A | C2000 | AR_THS_HA | EL61 | 2024 | Rice | 0.0 |
| A | G0000 | AR_THS_HA | EL61 | 2019 | Plants harvested green from arable land | 50.18 |
| A | G0000 | AR_THS_HA | EL61 | 2020 | Plants harvested green from arable land | 39.38 |
| A | G0000 | AR_THS_HA | EL61 | 2021 | Plants harvested green from arable land | 20.73 |
| A | G0000 | AR_THS_HA | EL61 | 2022 | Plants harvested green from arable land | 22.61 |
| A | G0000 | AR_THS_HA | EL61 | 2023 | Plants harvested green from arable land | 18.22 |
| A | G0000 | AR_THS_HA | EL61 | 2024 | Plants harvested green from arable land | 26.58 |
| A | G1000 | AR_THS_HA | EL61 | 2019 | Temporary grasses and grazings | 7.27 |
| A | G1000 | AR_THS_HA | EL61 | 2020 | Temporary grasses and grazings | 7.51 |
| A | G1000 | AR_THS_HA | EL61 | 2021 | Temporary grasses and grazings | 8.76 |
| A | G1000 | AR_THS_HA | EL61 | 2022 | Temporary grasses and grazings | 8.82 |
| A | G1000 | AR_THS_HA | EL61 | 2023 | Temporary grasses and grazings | 8.38 |
| A | G1000 | AR_THS_HA | EL61 | 2024 | Temporary grasses and grazings | 7.85 |
| A | G2000 | AR_THS_HA | EL61 | 2019 | Leguminous plants harvested green | 5.72 |
| A | G2000 | AR_THS_HA | EL61 | 2020 | Leguminous plants harvested green | 0.04 |
| A | G2000 | AR_THS_HA | EL61 | 2021 | Leguminous plants harvested green | 2.48 |
| A | G2000 | AR_THS_HA | EL61 | 2022 | Leguminous plants harvested green | 4.05 |
| A | G2000 | AR_THS_HA | EL61 | 2023 | Leguminous plants harvested green | 0.11 |
| A | G2000 | AR_THS_HA | EL61 | 2024 | Leguminous plants harvested green | 0.11 |
| A | G2900 | AR_THS_HA | EL61 | 2019 | Other leguminous plants harvested green n.e.c. (clover etc.) | 0.0 |
| A | G2900 | AR_THS_HA | EL61 | 2020 | Other leguminous plants harvested green n.e.c. (clover etc.) | 0.0 |
| A | G2900 | AR_THS_HA | EL61 | 2021 | Other leguminous plants harvested green n.e.c. (clover etc.) | 0.0 |
| A | G2900 | AR_THS_HA | EL61 | 2022 | Other leguminous plants harvested green n.e.c. (clover etc.) | 0.0 |
| A | G2900 | AR_THS_HA | EL61 | 2023 | Other leguminous plants harvested green n.e.c. (clover etc.) | 0.0 |
| A | G2900 | AR_THS_HA | EL61 | 2024 | Other leguminous plants harvested green n.e.c. (clover etc.) | 0.0 |
| A | G3000 | AR_THS_HA | EL61 | 2019 | Green maize | 29.58 |
| A | G3000 | AR_THS_HA | EL61 | 2020 | Green maize | 29.11 |
| A | G3000 | AR_THS_HA | EL61 | 2021 | Green maize | 6.71 |
| A | G3000 | AR_THS_HA | EL61 | 2022 | Green maize | 6.95 |
| A | G3000 | AR_THS_HA | EL61 | 2023 | Green maize | 6.95 |
| A | G3000 | AR_THS_HA | EL61 | 2024 | Green maize | 17.11 |
| A | G9100 | AR_THS_HA | EL61 | 2019 | Other cereals harvested green (excluding green maize) | 7.61 |
| A | G9100 | AR_THS_HA | EL61 | 2020 | Other cereals harvested green (excluding green maize) | 2.72 |
| A | G9100 | AR_THS_HA | EL61 | 2021 | Other cereals harvested green (excluding green maize) | 2.78 |
| A | G9100 | AR_THS_HA | EL61 | 2022 | Other cereals harvested green (excluding green maize) | 2.79 |
| A | G9100 | AR_THS_HA | EL61 | 2023 | Other cereals harvested green (excluding green maize) | 2.79 |
| A | G9100 | AR_THS_HA | EL61 | 2024 | Other cereals harvested green (excluding green maize) | 1.51 |
| A | I0000 | AR_THS_HA | EL61 | 2019 | Industrial crops | 97.28 |
| A | I0000 | AR_THS_HA | EL61 | 2020 | Industrial crops | 98.94 |
| A | I0000 | AR_THS_HA | EL61 | 2021 | Industrial crops | 96.71 |
| A | I0000 | AR_THS_HA | EL61 | 2022 | Industrial crops | 99.93 |
| A | I0000 | AR_THS_HA | EL61 | 2023 | Industrial crops | 86.45 |
| A | I0000 | AR_THS_HA | EL61 | 2024 | Industrial crops | 85.5 |
| A | I1110 | AR_THS_HA | EL61 | 2019 | Rape and turnip rape seeds | 0.13 |
| A | I1110 | AR_THS_HA | EL61 | 2020 | Rape and turnip rape seeds | 0.11 |
| A | I1110 | AR_THS_HA | EL61 | 2021 | Rape and turnip rape seeds | 1.23 |
| A | I1110 | AR_THS_HA | EL61 | 2022 | Rape and turnip rape seeds | 5.98 |
| A | I1110 | AR_THS_HA | EL61 | 2023 | Rape and turnip rape seeds | 4.31 |
| A | I1110 | AR_THS_HA | EL61 | 2024 | Rape and turnip rape seeds | 2.81 |
| A | I1111 | AR_THS_HA | EL61 | 2019 | Winter rape and turnip rape seeds | 0.13 |
| A | I1111 | AR_THS_HA | EL61 | 2020 | Winter rape and turnip rape seeds | 0.11 |
| A | I1111 | AR_THS_HA | EL61 | 2021 | Winter rape and turnip rape seeds | 1.23 |
| A | I1111 | AR_THS_HA | EL61 | 2022 | Winter rape and turnip rape seeds | 5.98 |
| A | I1111 | AR_THS_HA | EL61 | 2023 | Winter rape and turnip rape seeds | 4.31 |
| A | I1111 | AR_THS_HA | EL61 | 2024 | Winter rape and turnip rape seeds | 2.81 |
| A | I1112 | AR_THS_HA | EL61 | 2019 | Spring rape and turnip rape seeds | 0.0 |
| A | I1112 | AR_THS_HA | EL61 | 2020 | Spring rape and turnip rape seeds | 0.0 |
| A | I1112 | AR_THS_HA | EL61 | 2021 | Spring rape and turnip rape seeds | 0.0 |
| A | I1112 | AR_THS_HA | EL61 | 2022 | Spring rape and turnip rape seeds | 0.0 |
| A | I1112 | AR_THS_HA | EL61 | 2023 | Spring rape and turnip rape seeds | 0.0 |
| A | I1112 | AR_THS_HA | EL61 | 2024 | Spring rape and turnip rape seeds | 0.0 |
| A | I1120 | AR_THS_HA | EL61 | 2019 | Sunflower seed | 0.85 |
| A | I1120 | AR_THS_HA | EL61 | 2020 | Sunflower seed | 0.9 |
| A | I1120 | AR_THS_HA | EL61 | 2021 | Sunflower seed | 0.82 |
| A | I1120 | AR_THS_HA | EL61 | 2022 | Sunflower seed | 1.41 |
| A | I1120 | AR_THS_HA | EL61 | 2023 | Sunflower seed | 0.68 |
| A | I1120 | AR_THS_HA | EL61 | 2024 | Sunflower seed | 7.68 |
| A | I1130 | AR_THS_HA | EL61 | 2019 | Soya | 0.02 |
| A | I1130 | AR_THS_HA | EL61 | 2020 | Soya | 0.01 |
| A | I1130 | AR_THS_HA | EL61 | 2021 | Soya | 0.0 |
| A | I1130 | AR_THS_HA | EL61 | 2022 | Soya | 0.0 |
| A | I1130 | AR_THS_HA | EL61 | 2023 | Soya | 0.05 |
| A | I1130 | AR_THS_HA | EL61 | 2024 | Soya | 0.01 |
| A | I1140 | AR_THS_HA | EL61 | 2019 | Linseed (oil flax) | 0.01 |
| A | I1140 | AR_THS_HA | EL61 | 2020 | Linseed (oil flax) | 0.01 |
| A | I1140 | AR_THS_HA | EL61 | 2021 | Linseed (oil flax) | 0.01 |
| A | I1140 | AR_THS_HA | EL61 | 2022 | Linseed (oil flax) | 0.01 |
| A | I1140 | AR_THS_HA | EL61 | 2023 | Linseed (oil flax) | 0.03 |
| A | I1140 | AR_THS_HA | EL61 | 2024 | Linseed (oil flax) | 0.04 |
| A | I2100 | AR_THS_HA | EL61 | 2019 | Fibre flax | 0.0 |
| A | I2100 | AR_THS_HA | EL61 | 2020 | Fibre flax | 0.0 |
| A | I2100 | AR_THS_HA | EL61 | 2021 | Fibre flax | 0.0 |
| A | I2100 | AR_THS_HA | EL61 | 2022 | Fibre flax | 0.0 |
| A | I2100 | AR_THS_HA | EL61 | 2023 | Fibre flax | 0.0 |
| A | I2100 | AR_THS_HA | EL61 | 2024 | Fibre flax | 0.0 |
| A | I2300 | AR_THS_HA | EL61 | 2019 | Cotton fibre | 90.27 |
| A | I2300 | AR_THS_HA | EL61 | 2020 | Cotton fibre | 90.15 |
| A | I2300 | AR_THS_HA | EL61 | 2021 | Cotton fibre | 84.18 |
| A | I2300 | AR_THS_HA | EL61 | 2022 | Cotton fibre | 81.83 |
| A | I2300 | AR_THS_HA | EL61 | 2023 | Cotton fibre | 73.44 |
| A | I2300 | AR_THS_HA | EL61 | 2024 | Cotton fibre | 67.75 |
| A | I2900 | AR_THS_HA | EL61 | 2019 | Other fibre crops n.e.c. | 0.0 |
| A | I2900 | AR_THS_HA | EL61 | 2020 | Other fibre crops n.e.c. | 0.0 |
| A | I2900 | AR_THS_HA | EL61 | 2021 | Other fibre crops n.e.c. | 0.0 |
| A | I2900 | AR_THS_HA | EL61 | 2022 | Other fibre crops n.e.c. | 0.0 |
| A | I2900 | AR_THS_HA | EL61 | 2023 | Other fibre crops n.e.c. | 0.0 |
| A | I2900 | AR_THS_HA | EL61 | 2024 | Other fibre crops n.e.c. | 0.0 |
| A | I3000 | AR_THS_HA | EL61 | 2019 | Tobacco | 1.74 |
| A | I3000 | AR_THS_HA | EL61 | 2020 | Tobacco | 1.53 |
| A | I3000 | AR_THS_HA | EL61 | 2021 | Tobacco | 1.56 |
| A | I3000 | AR_THS_HA | EL61 | 2022 | Tobacco | 0.98 |
| A | I3000 | AR_THS_HA | EL61 | 2023 | Tobacco | 1.06 |
| A | I3000 | AR_THS_HA | EL61 | 2024 | Tobacco | 1.33 |
| A | I5000 | AR_THS_HA | EL61 | 2019 | Aromatic, medicinal and culinary plants | 1.97 |
| A | I5000 | AR_THS_HA | EL61 | 2020 | Aromatic, medicinal and culinary plants | 2.54 |
| A | I5000 | AR_THS_HA | EL61 | 2021 | Aromatic, medicinal and culinary plants | 2.79 |
| A | I5000 | AR_THS_HA | EL61 | 2022 | Aromatic, medicinal and culinary plants | 3.1 |
| A | I5000 | AR_THS_HA | EL61 | 2023 | Aromatic, medicinal and culinary plants | 3.11 |
| A | I5000 | AR_THS_HA | EL61 | 2024 | Aromatic, medicinal and culinary plants | 3.52 |
| A | I6000 | AR_THS_HA | EL61 | 2019 | Energy crops n.e.c. | 2.04 |
| A | I6000 | AR_THS_HA | EL61 | 2020 | Energy crops n.e.c. | 3.6 |
| A | I6000 | AR_THS_HA | EL61 | 2021 | Energy crops n.e.c. | 6.03 |
| A | I6000 | AR_THS_HA | EL61 | 2022 | Energy crops n.e.c. | 6.55 |
| A | I6000 | AR_THS_HA | EL61 | 2023 | Energy crops n.e.c. | 3.73 |
| A | I6000 | AR_THS_HA | EL61 | 2024 | Energy crops n.e.c. | 2.34 |
| A | P0000 | AR_THS_HA | EL61 | 2019 | Dry pulses and protein crops for the production of grain (including seed and mixtures of cereals and pulses) | 22.87 |
| A | P0000 | AR_THS_HA | EL61 | 2020 | Dry pulses and protein crops for the production of grain (including seed and mixtures of cereals and pulses) | 24.6 |
| A | P0000 | AR_THS_HA | EL61 | 2021 | Dry pulses and protein crops for the production of grain (including seed and mixtures of cereals and pulses) | 24.0 |
| A | P0000 | AR_THS_HA | EL61 | 2022 | Dry pulses and protein crops for the production of grain (including seed and mixtures of cereals and pulses) | 23.4 |
| A | P0000 | AR_THS_HA | EL61 | 2023 | Dry pulses and protein crops for the production of grain (including seed and mixtures of cereals and pulses) | 22.46 |
| A | P0000 | AR_THS_HA | EL61 | 2024 | Dry pulses and protein crops for the production of grain (including seed and mixtures of cereals and pulses) | 27.75 |
| A | P1100 | AR_THS_HA | EL61 | 2019 | Field peas | 2.81 |
| A | P1100 | AR_THS_HA | EL61 | 2020 | Field peas | 3.02 |
| A | P1100 | AR_THS_HA | EL61 | 2021 | Field peas | 4.34 |
| A | P1100 | AR_THS_HA | EL61 | 2022 | Field peas | 4.57 |
| A | P1100 | AR_THS_HA | EL61 | 2023 | Field peas | 4.74 |
| A | P1100 | AR_THS_HA | EL61 | 2024 | Field peas | 5.41 |
| A | P1200 | AR_THS_HA | EL61 | 2019 | Broad and field beans | 0.42 |
| A | P1200 | AR_THS_HA | EL61 | 2020 | Broad and field beans | 0.54 |
| A | P1200 | AR_THS_HA | EL61 | 2021 | Broad and field beans | 0.38 |
| A | P1200 | AR_THS_HA | EL61 | 2022 | Broad and field beans | 0.44 |
| A | P1200 | AR_THS_HA | EL61 | 2023 | Broad and field beans | 0.55 |
| A | P1200 | AR_THS_HA | EL61 | 2024 | Broad and field beans | 1.04 |
| A | P1300 | AR_THS_HA | EL61 | 2019 | Sweet lupins | 0.09 |
| A | P1300 | AR_THS_HA | EL61 | 2020 | Sweet lupins | 0.11 |
| A | P1300 | AR_THS_HA | EL61 | 2021 | Sweet lupins | 0.07 |
| A | P1300 | AR_THS_HA | EL61 | 2022 | Sweet lupins | 0.08 |
| A | P1300 | AR_THS_HA | EL61 | 2023 | Sweet lupins | 0.1 |
| A | P1300 | AR_THS_HA | EL61 | 2024 | Sweet lupins | 0.09 |
| A | R1000 | AR_THS_HA | EL61 | 2019 | Potatoes (including seed potatoes) | 0.24 |
| A | R1000 | AR_THS_HA | EL61 | 2020 | Potatoes (including seed potatoes) | 0.4 |
| A | R1000 | AR_THS_HA | EL61 | 2021 | Potatoes (including seed potatoes) | 0.29 |
| A | R1000 | AR_THS_HA | EL61 | 2022 | Potatoes (including seed potatoes) | 0.23 |
| A | R1000 | AR_THS_HA | EL61 | 2023 | Potatoes (including seed potatoes) | 0.16 |
| A | R1000 | AR_THS_HA | EL61 | 2024 | Potatoes (including seed potatoes) | 0.19 |
| A | R2000 | AR_THS_HA | EL61 | 2019 | Sugar beet (excluding seed) | 0.45 |
| A | R2000 | AR_THS_HA | EL61 | 2020 | Sugar beet (excluding seed) | 0.53 |
| A | R2000 | AR_THS_HA | EL61 | 2021 | Sugar beet (excluding seed) | 0.28 |
| A | R2000 | AR_THS_HA | EL61 | 2022 | Sugar beet (excluding seed) | 0.06 |
| A | R2000 | AR_THS_HA | EL61 | 2023 | Sugar beet (excluding seed) | 0.01 |
| A | R2000 | AR_THS_HA | EL61 | 2024 | Sugar beet (excluding seed) | 0.03 |

### Crop map against Eurostat

| crop | map_classes | map_hectares | eurostat_label | eurostat_year | eurostat_hectares | map_to_eurostat | within_tolerance |
|---|---|---|---|---|---|---|---|
| Cotton | 230 | 97065.0 | Cotton fibre | 2022 | 81830.0 | 1.19 | True |
| Maize, grain and green | 216 | 32631.0 | Grain maize and corn-cob-mix, Green maize, Other cereals harvested green (excluding green maize) | 2022 | 35440.0 | 0.92 | True |
| Wheat, durum and common | 211, 212 | 129286.0 | Common wheat and spelt, Durum wheat | 2022 | 95500.0 | 1.35 | False |

