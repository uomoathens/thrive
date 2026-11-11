# Phase A: who gets flood protection in the United States?

Generated automatically by `thrive phase-a`. `sources.json` records what was downloaded and when.

Counties with flood risk and a vulnerability score: 3,140.
Money counted: flood-related FEMA Hazard Mitigation Assistance grants with a funded status, fiscal year 2000 onwards, $13.72 billion placed in counties. Where a grant has no obligated amount, its federal share is used ($2.41 billion).
Flood risk: expected annual loss from inland and coastal flooding, National Risk Index December 2025.

| Vulnerability quintile | Money per dollar of expected annual flood loss | Same, without the largest counties | Median county | Counties with no flood money |
| --- | --- | --- | --- | --- |
| 1 (least vulnerable) | $0.141 | $0.141 | $0.033 | 8% |
| 2 | $0.158 | $0.107 | $0.031 | 10% |
| 3 | $0.188 | $0.148 | $0.029 | 10% |
| 4 | $0.371 | $0.191 | $0.026 | 12% |
| 5 (most vulnerable) | $0.335 | $0.215 | $0.028 | 14% |

Coverage ratio, most vulnerable fifth against least vulnerable fifth:

- all money: 2.38
- without the 20 counties that received the most (36% of all the money): 1.53
- median county: 0.85
- median county among those that received any flood money: 1.11

Direction across all four measures: **not robust**. Following THRIVE's own rule, a direction is reported as a finding only when every measure agrees.

Money that could not be placed in a county: statewide $1,899.3 million, county name not matched $506.1 million (3.5% of the money meant for named counties).

Limits: a grant that names several counties is split equally between them, statewide grants are left out, money obligated is not always money spent, and expected annual loss is a model estimate. A grant counts as flood-related when one of its hazards mentions flooding, it comes from the Flood Mitigation Assistance programme, or its main activity is a flood measure (acquisition, elevation, flood control, floodproofing, drainage). The Excel file lists the largest grants so that any of them can be checked by hand.
