# Heat and summer crops in Thessaly

Generated automatically by `thrive crops-heat`. `sources.json` records what was read and when.

Question: in the 1 km squares of Thessaly where cotton and maize grow, is the crop less green in the ten-day periods with more hot days, once soil moisture and the normal season of each square are accounted for?

Squares: 1039 squares with at least 50 ha of cotton and maize in the EU crop map 2022 (55,184 ha of cotton class and 11,942 ha of maize). Summers: 2019, 2020, 2021, 2022, 2023, 2024, 2025, ten-day periods June to September. Sentinel-2 scenes used: 722 of 1,319.

Sentinel-2 collection by summer: 2019 sentinel-2-c1-l2a, 2020 sentinel-2-c1-l2a, 2021 sentinel-2-c1-l2a, 2022 sentinel-2-l2a, 2023 sentinel-2-c1-l2a, 2024 sentinel-2-c1-l2a, 2025 sentinel-2-c1-l2a. The reprocessed collection 1 of Earth Search has no scenes for 2022, so that summer is read from the original Level-2A collection of the same ESA product; a common effect of each year absorbs any difference in level between the two.

Heat: daily maximum temperature of the European Drought Observatory (JRC MARS, 10 km), counted as days at or above a threshold in each ten-day period. Soil moisture: soil moisture index anomaly of the European Drought Observatory (about 2 km). Greenness: median Sentinel-2 NDVI of each square in each ten-day period.

Model: log greenness on hot days and soil moisture, with a separate normal for each square and ten-day period of the year, and either a common effect of each year or a common effect of each ten-day period of each year. Standard errors are clustered on 10 km blocks. Squares flooded by Storm Daniel are left out from September 2023 to the end of 2024.

## Verdict

Across all 12 specifications: **not robust**. A direction is reported as a finding only if every specification agrees and every 95% interval stays on one side of zero.

## Every specification

| threshold_C | hot_days_in | common_effect | n | cells | clusters | b | se | lo | hi | pct | pct_lo | pct_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 35 | this ten-day period | each year | 60299 | 1039 | 46 | -0.0006325 | 0.0007544 | -0.002111 | 0.0008462 | -0.06323 | -0.2109 | 0.08465 |
| 35 | this ten-day period | each ten-day period of each year | 60299 | 1039 | 46 | 0.003604 | 0.004168 | -0.004564 | 0.01177 | 0.3611 | -0.4554 | 1.184 |
| 35 | this and the previous ten-day period | each year | 60299 | 1039 | 46 | -0.001683 | 0.0007165 | -0.003087 | -0.0002783 | -0.1681 | -0.3082 | -0.02783 |
| 35 | this and the previous ten-day period | each ten-day period of each year | 60299 | 1039 | 46 | 0.004135 | 0.00428 | -0.004253 | 0.01252 | 0.4144 | -0.4244 | 1.26 |
| 37 | this ten-day period | each year | 60299 | 1039 | 46 | -0.005742 | 0.0007036 | -0.007121 | -0.004363 | -0.5725 | -0.7095 | -0.4353 |
| 37 | this ten-day period | each ten-day period of each year | 60299 | 1039 | 46 | -0.01286 | 0.005666 | -0.02397 | -0.001757 | -1.278 | -2.368 | -0.1755 |
| 37 | this and the previous ten-day period | each year | 60299 | 1039 | 46 | -0.006231 | 0.0006693 | -0.007543 | -0.004919 | -0.6212 | -0.7515 | -0.4907 |
| 37 | this and the previous ten-day period | each ten-day period of each year | 60299 | 1039 | 46 | -0.009423 | 0.005437 | -0.02008 | 0.001233 | -0.9379 | -1.988 | 0.1234 |
| 40 | this ten-day period | each year | 60299 | 1039 | 46 | -0.009694 | 0.001589 | -0.01281 | -0.006579 | -0.9647 | -1.273 | -0.6558 |
| 40 | this ten-day period | each ten-day period of each year | 60299 | 1039 | 46 | 0.02455 | 0.009843 | 0.005262 | 0.04385 | 2.486 | 0.5276 | 4.482 |
| 40 | this and the previous ten-day period | each year | 60299 | 1039 | 46 | -0.01149 | 0.001418 | -0.01427 | -0.008706 | -1.142 | -1.416 | -0.8668 |
| 40 | this and the previous ten-day period | each ten-day period of each year | 60299 | 1039 | 46 | 0.02568 | 0.01066 | 0.004786 | 0.04657 | 2.601 | 0.4798 | 4.767 |

## Cotton and maize separately (37 °C, this and the previous ten-day period, year effects)

| crop | n | cells | clusters | b | se | lo | hi | pct | pct_lo | pct_hi |
|---|---|---|---|---|---|---|---|---|---|---|
| cotton | 53761 | 934 | 40 | -0.006008 | 0.0006819 | -0.007344 | -0.004671 | -0.599 | -0.7317 | -0.466 |
| maize | 6538 | 105 | 18 | -0.00777 | 0.00173 | -0.01116 | -0.004378 | -0.774 | -1.11 | -0.4369 |

## Exposure: crop area in squares with at least 10 days at or above 37 °C in June to September

| year | region_id | region_name | cotton_ha | cotton_ha_exposed | maize_ha | maize_ha_exposed | mean_hot_days |
|---|---|---|---|---|---|---|---|
| 2019 | EL611 | Karditsa, Trikala | 41,633 | 0 | 9,195 | 0 | 7.9 |
| 2019 | EL612 | Larisa | 12,945 | 3,614 | 2,645 | 699 | 6.8 |
| 2019 | EL613 | Magnisia, Sporades | 606 | 0 | 103 | 0 | 0.8 |
| 2020 | EL611 | Karditsa, Trikala | 41,633 | 0 | 9,195 | 0 | 5.7 |
| 2020 | EL612 | Larisa | 12,945 | 0 | 2,645 | 0 | 4.2 |
| 2020 | EL613 | Magnisia, Sporades | 606 | 0 | 103 | 0 | 0.9 |
| 2021 | EL611 | Karditsa, Trikala | 41,633 | 41,633 | 9,195 | 9,195 | 21.5 |
| 2021 | EL612 | Larisa | 12,945 | 12,945 | 2,645 | 2,645 | 20.6 |
| 2021 | EL613 | Magnisia, Sporades | 606 | 508 | 103 | 95 | 11.4 |
| 2022 | EL611 | Karditsa, Trikala | 41,633 | 29,985 | 9,195 | 5,978 | 9.2 |
| 2022 | EL612 | Larisa | 12,945 | 4,818 | 2,645 | 845 | 8.3 |
| 2022 | EL613 | Magnisia, Sporades | 606 | 0 | 103 | 0 | 1.6 |
| 2023 | EL611 | Karditsa, Trikala | 41,633 | 41,633 | 9,195 | 9,195 | 16.7 |
| 2023 | EL612 | Larisa | 12,945 | 11,799 | 2,645 | 2,274 | 15.2 |
| 2023 | EL613 | Magnisia, Sporades | 606 | 282 | 103 | 36 | 6.8 |
| 2024 | EL611 | Karditsa, Trikala | 41,633 | 41,633 | 9,195 | 9,195 | 28.3 |
| 2024 | EL612 | Larisa | 12,945 | 12,568 | 2,645 | 2,573 | 25.6 |
| 2024 | EL613 | Magnisia, Sporades | 606 | 282 | 103 | 36 | 10.1 |
| 2025 | EL611 | Karditsa, Trikala | 41,633 | 41,633 | 9,195 | 9,195 | 21.9 |
| 2025 | EL612 | Larisa | 12,945 | 12,568 | 2,645 | 2,573 | 20.5 |
| 2025 | EL613 | Magnisia, Sporades | 606 | 282 | 103 | 36 | 9.2 |

## Limits

- The crop map is of 2022; crops rotate, so a square counted as cotton may have grown another crop in another year. The cotton class of the map is the class of other non-permanent industrial crops, which in Thessaly is mostly cotton; its 2022 area is 19% above the Eurostat cotton area.
- Temperature is a 10 km grid and soil moisture a model at about 2 km; neither sees the irrigation of a single field.
- Greenness is not yield. A lower NDVI shows stress or earlier ageing of the canopy, not tonnes lost.
- The years 2019 to 2025 are few; a result can depend on one unusual summer.
