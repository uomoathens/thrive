# Phase A: who gets flood protection in the United States?

Generated automatically by `thrive phase-a`. `sources.json` records what was downloaded and when.

Counties with flood risk and a vulnerability score: 3,131.
Money counted: flood-related FEMA Hazard Mitigation Assistance grants with a funded status, fiscal year 2000 onwards, $13.80 billion placed in counties. Where a grant has no obligated amount, its federal share is used ($2.40 billion).
Flood risk: expected annual loss from inland and coastal flooding, National Risk Index December 2025.

| Vulnerability quintile | Money per dollar of expected annual flood loss | Same, without the largest counties | Median county | Counties with no flood money |
| --- | --- | --- | --- | --- |
| 1 (least vulnerable) | $0.141 | $0.141 | $0.033 | 8% |
| 2 | $0.163 | $0.110 | $0.031 | 9% |
| 3 | $0.192 | $0.146 | $0.029 | 10% |
| 4 | $0.377 | $0.201 | $0.026 | 13% |
| 5 (most vulnerable) | $0.338 | $0.216 | $0.028 | 14% |

Coverage ratio, most vulnerable fifth against least vulnerable fifth:

- all money: 2.40
- without the 20 counties that received the most (37% of all the money): 1.54
- median county: 0.85
- median county among those that received any flood money: 1.17
- obligated money only, without the federal share used for grants that record no obligated amount: 2.18

Direction across all 5 measures: **not robust**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.

Money that could not be placed in a county: statewide $1,855.9 million, county name not matched $505.3 million (3.4% of the money meant for named counties), of which $326.1 million in 295 grants whose counties mostly do not belong to the state recorded for them, which are left unplaced rather than given to a county of the same name in that state.
Left out: Connecticut ($78.1 million). Since 2022 the National Risk Index describes Connecticut by nine planning regions, while its grants still name the eight former counties, which do not map one to one onto the regions.
Possible duplicates: 469 grants share their state, their counties and their amount to the cent with another grant under a different identifier. They are counted as recorded and listed in the Excel file for checking with FEMA.

Limits: a grant that names several counties is split equally between them, statewide grants are left out, money obligated is not always money spent, and expected annual loss is a model estimate. A grant counts as flood-related when one of its hazards mentions flooding, it comes from the Flood Mitigation Assistance programme, or its main activity is a flood measure (acquisition, elevation, flood control, floodproofing, drainage, stormwater). The Excel file lists the largest grants so that any of them can be checked by hand.
