# Heat, drought and crops in Thessaly: feasibility probe

Generated automatically by `thrive crops-probe`. It checks, before any analysis, whether the open European data needed for a study of heat and drought damage to crops in Thessaly can be downloaded automatically and whether cotton can be separated in the EU crop map. It produces no finding about crops.

## Verdicts

1. European Drought Observatory data download automatically for every needed indicator and every year: **yes** (ready: fapar_anomaly, soil_moisture_anomaly, spei3, tmax, warm_spell).
2. Cotton area in the EU crop map 2022 matches the Eurostat cotton area of Thessaly within ±35%: **no**.
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

- **warm_spell**: ver2-1-0/hwd2m_m_edo_20250101_20251231_d.nc; read
  - /tmp/tmpdid32h7p/hwd2m_m_edo_20250101_20251231_d.nc: CRS EPSG:3035, pixel 10000 x 10000, 522 pixels, valid 100%, min 0.0, mean 0.0, max 0.0
- **tmax**: ver2-1-0/tmaxm_m_edo_20250101_20251231_d.nc; read
  - /tmp/tmpdid32h7p/tmaxm_m_edo_20250101_20251231_d.nc: CRS EPSG:3035, pixel 10000 x 10000, 522 pixels, valid 76%, min 6.400000095367432, mean 12.4506329186355, max 15.5
- **heat_cold_wave**: no sample; failed: no file with a date and an accepted format under the size limit
- **soil_moisture_anomaly**: ver3-0-2/smian_m_eul_20250101_20251221_t.nc; read
  - /tmp/tmpdid32h7p/smian_m_eul_20250101_20251221_t.nc: CRS EPSG:4326, pixel 0.016667 x 0.016667, 14282 pixels, valid 59%, min -3.0712385177612305, mean -0.21013975985230707, max 1.1216092109680176
- **fapar_anomaly**: ver3-1-0/fpanv_m_edo_20250101_20251221_t.nc; read
  - /tmp/tmpdid32h7p/fpanv_m_edo_20250101_20251221_t.nc: CRS EPSG:4326, pixel 0.041667 x 0.041667, 2233 pixels, valid 0%, min None, mean None, max None
- **spei3**: ver1-1-0/sem03_m_edo_20250101_20251221_t.nc; read
  - /tmp/tmpdid32h7p/sem03_m_edo_20250101_20251221_t.nc: CRS EPSG:3035, pixel 10000 x 10000, 522 pixels, valid 76%, min -1.3904458284378052, mean 0.15719139765877324, max 1.880157470703125

## 2. EU crop map 2022 over Thessaly (NUTS EL61)

GeoTIFF files listed: 159; headers read: 159; files over Thessaly: 3.

| class | name | hectares |
|---|---|---|
| 0 | unknown | 133691.8 |
| 100 | Artificial | 199019.3 |
| 211 | Common wheat | 15385.1 |
| 212 | Durum wheat | 243186.2 |
| 213 | Barley | 8234.5 |
| 214 | Rye | 32.8 |
| 215 | Oats | 2699.4 |
| 216 | Maize | 65261.9 |
| 217 | Rice | 12.0 |
| 218 | Triticale | 6853.4 |
| 219 | Other cereals | 55.1 |
| 221 | Potatoes | 82.6 |
| 222 | Sugar beet | 51.3 |
| 223 | Other root crops | 0.8 |
| 230 | Other non-permanent industrial crops | 194129.4 |
| 231 | Sunflower | 10817.9 |
| 232 | Rapeseed and turnip rapeseed | 9332.0 |
| 233 | Soya | 532.6 |
| 240 | Dry pulses | 881.8 |
| 250 | Fodder crops (cereals and leguminous) | 76546.9 |
| 290 | Bare arable land | 9912.0 |
| 300 | Woodland and Shrubland (incl. permanent crops) | 1566625.2 |
| 500 | Grasslands | 236992.5 |
| 600 | Bare land/lichens moss | 4327.0 |
| 700 | Water | 26090.1 |
| 800 | Wetlands | 245.3 |

### Eurostat crop areas, Thessaly

Source: Crop production in EU standard humidity by NUTS 2 region (updated 2026-11-24T23:00:00+0100).

_No rows._

### Crop map against Eurostat

| crop | map_classes | map_hectares | eurostat_label | eurostat_year | eurostat_hectares | map_to_eurostat | within_tolerance |
|---|---|---|---|---|---|---|---|
| Cotton | 230 | 194129.0 |  | 2022 |  |  | False |
| Maize | 216 | 65262.0 |  | 2022 |  |  | False |
| Durum wheat | 212 | 243186.0 |  | 2022 |  |  | False |
| Common wheat | 211 | 15385.0 |  | 2022 |  |  | False |

