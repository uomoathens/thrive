# THRIVE

**Trustworthy Hazard-to-Recovery Intelligence for Vulnerability-aware Equity**

**Dimitrios Sargiotis** · National Technical University of Athens · [users.ntua.gr/dims](https://users.ntua.gr/dims/) · [uomoathens.github.io](https://uomoathens.github.io/)

Companion software to the book *AI for Resilient Cities: Predicting, Protecting, and Thriving in a Changing Climate* (Springer Nature, 2027, [doi:10.1007/978-3-032-36417-3](https://doi.org/10.1007/978-3-032-36417-3)).

Who is predicted to be hit, who is protected before the hazard, and who recovers after it? THRIVE turns the three verbs of the book's title into one closed loop: it forecasts hazard and latent vulnerability, allocates climate-adaptation resources under explicit fairness constraints, measures from satellites how fast each group recovers, certifies every allocation with a paired counterfactual audit before it is used, and feeds the measured recovery back into the next allocation.

## Status

**Design stage.** This repository holds the design. No code has been run and no result is reported yet. Modules, data pipelines and the validation study are added step by step, and every result will be reproducible from the stored data and configuration.

## Why

Europe now asks for fairness in adaptation without a way to measure it. The proposed European Climate Resilience Law (COM(2026) 730, 27 October 2026) defines *just resilience* and requires national climate-resilience plans to take into consideration people in vulnerable situations and disproportionately affected regions, but it sets out no method for assessing the distributional effects of a plan. The AI Act (Regulation (EU) 2024/1689, Article 10) requires high-risk AI systems to examine their data for biases that could affect health and safety or lead to prohibited discrimination. THRIVE is designed to produce that evidence in a form a public authority can audit.

The research it builds on solves parts of the problem separately: equity-weighted benefit-cost analysis for flood mitigation, reinforcement learning for adaptation pathways, fairness-aware prediction of post-flood aid, and nighttime-light measurement of unequal recovery. THRIVE joins them in one loop and adds a certification step.

## Architecture

| Phase | What it does | Frameworks of the book it extends |
| --- | --- | --- |
| **Predicting** | Forecasts hazard and learns latent vulnerability | HEFF-RC (Table 1.6), LSTM-AFFUW (Table 1.7), AIF-EWS (Table 1.8), VAE-LVM (Table 4.8) |
| **Protecting** | Allocates adaptation resources before the hazard, under fairness constraints and with privacy across municipalities | EA-CURA (Table 3.5), FCFL (Table 5.8), DPFL-EDA (Table 1.5) |
| **Thriving** | Measures recovery equity after the hazard and feeds it back into the policy | Extends the post-AI evaluation and social-impact feedback layer of EA-CURA |

A language model may explain decisions to planners and residents, but it never takes them. The counterfactual audit in [Who Gets Help First?](https://github.com/uomoathens/who-gets-help-first) found that open models followed a stated priority rule in full in only 7 % to 47 % of triage rankings.

## Design

### 1. Recovery equity, robust to how recovery is defined

The recovery time of group $g$ is the first day its nighttime light (urban areas, NASA Black Marble) or vegetation index (agricultural areas, Sentinel-2 NDVI) returns to a share $\alpha$ of its pre-event baseline. Because published findings on recovery inequality can reverse sign with the recovery definition, the penalty is taken over the worst case of a set of definitions $\mathcal{A}$:

```math
\tau_g(\alpha)=\min\left\{t:\ \mathrm{NTL}_g(t)\ge \alpha\,\mathrm{NTL}_g^{\mathrm{pre}}\right\},\qquad \Phi_{\tau}=\max_{\alpha\in\mathcal{A}}\ \sum_{g=1}^{G}\left|\tau_g(\alpha)-\bar{\tau}(\alpha)\right|
```

A finding of unequal recovery is accepted only if it holds under every definition in $\mathcal{A}$.

### 2. Need is separated from identity

Legitimate need $N$ (a person over 80, a disability, an infant, a patient on dialysis) may change a decision. Protected identity $A$ (origin, gender, residence status, the wealth of an area) may not, once need is held fixed:

```math
P\left(\hat{Y}_{A\leftarrow a}=y \mid X=x,\ N=n\right)=P\left(\hat{Y}_{A\leftarrow a'}=y \mid X=x,\ N=n\right)\quad \forall\, a,a'
```

This keeps the debiasing of EA-CURA from removing the information on need that a fair allocation requires.

### 3. Social value instead of property value

The reward of the allocation policy weights avoided expected annual loss by income, so that a euro of avoided loss counts more for a poorer household, and subtracts the recovery-equity penalty:

```math
R_t=\sum_{i}\omega_i\,\Delta\mathrm{EAL}_i(a_t)-\kappa\,\Phi_{\tau},\qquad \omega_i=\left(\frac{\bar{y}}{y_i}\right)^{\eta}
```

The policy is trained with Proximal Policy Optimization and the group-fairness penalty $\Phi(w)$ of FCFL. The weight $\eta$ is a political choice, not a technical one: THRIVE does not fix it, but returns the Pareto front over $\eta$ for elected bodies to choose from.

### 4. A Just Resilience Certificate before any use

Every allocation is re-posed with one identity attribute changed at a time, as in *Who Gets Help First?*, with a placebo variant as the noise floor. It is released only if no identity contrast moves it beyond the noise floor and every need contrast does:

```math
\mathrm{Deploy}\iff \max_{c\in\mathcal{C}_{\mathrm{id}}}\left(\mathrm{FR}_c-\mathrm{FR}_{\mathrm{placebo}}\right)_{\mathrm{UB}_{95}}\le\delta\ \wedge\ \min_{c\in\mathcal{C}_{\mathrm{need}}}\mathrm{Sens}_c\ge\gamma
```

$\mathrm{FR}$ is the flip rate, $\mathrm{UB}_{95}$ the upper bound of its 95 % cluster-bootstrap interval with Holm correction, and $\mathrm{Sens}$ the share of need contrasts that raise the target's priority.

### 5. Small municipalities learn without sharing data

Municipalities train locally and share only perturbed model updates (DPFL-EDA), aggregated under the fairness constraint of FCFL. All data are held at area level, on the 1 km² grid of the 2021 census, so that bias can be examined without processing special categories of personal data.

## Validation plan

| Phase | Setting | Data |
| --- | --- | --- |
| A | United States, open and reproducible | OpenFEMA Hazard Mitigation Assistance projects, CDC Social Vulnerability Index, NASA Black Marble |
| B | Thessaly, Storm Daniel (September 2023) | Copernicus EMS EMSR692 and EMSN184, 2021 census on the 1 km² grid, Sentinel-2, NASA Black Marble |
| C | Thessaly, allocation records | Anonymised state-aid records by community, requested from the General Secretariat for Natural Disaster Recovery and State Aid |
| D | Attica, prospective | Current allocation of flood and wildfire protection works, assessed before the next event |

The counterfactual outcome is never fully observed. Phase B can show whether the actual allocation was unequal; the comparison with a THRIVE allocation rests on stated assumptions; and the claim that a fairer allocation would have reduced losses requires hydraulic scenarios with and without the works.

## Layout

```
README.md      design and plan
CITATION.cff   how to cite this repository and the book
LICENSE        MIT
```

The layout grows with each step.

## Citation

The book:

> Sargiotis, D. (2027). *AI for Resilient Cities: Predicting, Protecting, and Thriving in a Changing Climate*. Springer Nature Switzerland AG. https://doi.org/10.1007/978-3-032-36417-3

The related audit:

> Sargiotis, D. (2026). *Who Gets Help First? A counterfactual audit of large language model decisions in flood response* (Version v1.0.0) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.23684889

See also [CITATION.cff](CITATION.cff).

## Licence

Code: MIT.

## Author

Dimitrios Sargiotis, National Technical University of Athens.
