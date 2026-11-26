# Heat and summer crops in Thessaly: checks fixed before they were run

Fixed on 26 November 2026, before any of the checks below was computed.

## Why a second step

The first run of `thrive crops-heat` gave **not robust**. Its specifications with a common effect of each ten-day period of each year remove 93 to 95% of the variation in hot days, because the temperature grid is 10 km and a heatwave covers the whole plain at once; what is left is the difference between neighbouring 10 km cells within one ten-day period, which follows where the irrigated fields are. This decision, to judge heat only by how each square changes over time with a common effect of each year, is taken after seeing the first run, for that design reason, and is stated here rather than hidden.

## The checks

1. **Main estimates.** Log greenness on hot days at 35, 37 and 40°C, in the same ten-day period and in the same plus the previous one, with soil moisture, a separate normal for each square and ten-day period of the year, and a common effect of each year. Standard errors clustered on 10 km blocks. Six estimates.
2. **Placebo.** Each of the six is estimated again with the hot days of the next ten-day period added. Heat that has not happened yet cannot make a crop less green; if any next-period coefficient has a 95% interval that excludes zero, the estimates are confounded by something that moves with the season.
3. **Unseen Summers.** The model is fitted on the Summers of 2019 to 2022 and asked to predict 2023, 2024 and 2025, each on its own, with and without hot days, for each threshold with the window of this and the previous ten-day period. Heat must lower the prediction error in every test Summer for every threshold.

## The rule

A finding of lower greenness after hot days is reported only if all six main estimates are below zero with intervals below zero, the placebo shows nothing, and heat improves every unseen Summer. Otherwise the result is **not robust**, and the report says which check failed. Squares flooded by Storm Daniel stay out from September 2023 to the end of 2024, as in the first run.
