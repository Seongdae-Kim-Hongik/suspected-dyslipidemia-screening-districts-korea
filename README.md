# Suspected dyslipidemia at health screening across districts of South Korea, 2018-2024

Analysis code for the manuscript

> Kim S. *Suspected dyslipidemia at Korean health screening clusters in the southwest and follows screening attendance rather than physical activity.*

Archived version: Zenodo, https://doi.org/10.5281/zenodo.24294238 (v1.0.0).

This code is released under the MIT licence.

## Contents

This repository contains code only. The processed district-year data (analytic panel, expected counts, result tables and boundary file) are not included; they are available from the author on reasonable request. All source statistics are public (see Data sources).

| Path | What it is |
|---|---|
| `01_스크립트/` | Analysis scripts (below) |
| `04_분석/LIPS/` | Covariate pool and model settings (`make_pool_sets_lips.py`, `sets_LIPS_*.json`, `config_LIPS_std3.json`), cross-check against the reference district database (`gate_sqlite_crosscheck_lips.py`), the full model chain (`run_std3_chain.sh`) and the district adjacency graph (`graph_593.graph`). Sensitivity versions: queen contiguity graph `s577`, without the share aged 80 or older `s2`, unstandardised expected counts `sc`, earlier judgement criteria 2011-2017 `aux` |
| `04_분석/LIPS/MS/build/` | Scripts that read the result tables and write every number, table and figure in the manuscript and supplementary material (`numbers_lips.py`, `figs_lips.py`, `content_lips.py`, `build_jcl_lips.py`, `esm_lips.py`, `build_refs_lips.py`) |

Folder and some column names are in Korean because the source tables are Korean; each script has a header comment describing its inputs and outputs.

## Data sources

All inputs are public, aggregated statistics. No individual-level data are included.

- Examinees judged to have suspected dyslipidemia at the first stage of the general health screening, examinees with judgement results, and first-stage screening targets and attendees: National Health Insurance Service screening statistics, KOSIS tables DT_35007_N103, DT_35007_N098 and DT_35007_N001, 2011-2024.
- National examinees and suspected dyslipidemia by sex and age: KOSIS DT_35007_N099 and DT_35007_N104.
- Population by sex and 5-year age group: Ministry of the Interior and Safety, resident registration statistics.
- District covariates: Community Health Survey (walking, moderate-or-higher physical activity, obesity, high-risk drinking, current smoking), public sports facility register, health-resource statistics (internal medicine specialists), public assistance statistics and KOSIS local indicators (fixed adjustments and negative controls).

## Pipeline

Set `ST_DATA_ROOT` and `ST_GPT_DATASET` to the local copies of the public source files and the read-only district database, then run from the repository root.

| Step | Script | Output |
|---|---|---|
| 1 | `99S_build_E_lips.py` (uses `38_build_Estd_all.py`, `40_region_crosswalk.py`, `50_build_master_panel.py`) | District suspected counts (code-based linkage; Sejong from province-level rows) and expected counts by indirect standardisation in 2 sexes x 16 age groups |
| 2 | `99c_extra_canonical_pool_digx.py`, `99c_extra_canonical_pool_lipt.py`, then `04_분석/LIPS/make_pool_sets_lips.py` | Covariate pool and model settings; comparison outcomes |
| 3 | `80_build_disease_panel_v.py LIPS` (`ST_VER=std3`) | Analytic panel |
| 4 | `81_fit_inla.R LIPS` (see `04_분석/LIPS/run_std3_chain.sh`, which wraps R jobs in `rslot.sh`) | Principal model, 200-subset multiverse, period models, sensitivity versions |
| 5 | `85_window_maps.R`, `86_yearly_maps_ehsa_lips.py`, `87_window_grid.py` | Maps and yearly smoothed ratios |
| 6 | `88g_sens_prep.py LIPS std3 LIPTC,UNDXDC`, `88g_sens_suite_lips.R` (`GROUP=1..6`), `88h_ppc_varpart.R`, `88k_struct_kh_lips.R` (nb, struct, kh, review) with `kh_constraints_lips.R`, `89g_sens_combine.py`, `88S_lips_reverse_posthoc.R` | Alternative specifications, comparison outcomes, Knorr-Held models, decomposition, post hoc models |
| 7 | `04_분석/LIPS/MS/build/` | Manuscript numbers, tables, figures and supplementary material |

The boundary file is found at `data/boundary/final.shp` by default; set `ST_SHP` to use another path.

## Software

R 4.6.0 with R-INLA 25.10.19, spdep and sf; Python 3.9 with pandas, geopandas, numpy, scipy, matplotlib and python-docx.

## Licence

MIT (see `LICENSE`).
