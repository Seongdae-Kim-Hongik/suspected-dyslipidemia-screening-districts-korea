import os, json
import pandas as pd
from build_jcl_lips import TX, put_table, OUT, N, to_pdf, TITLE, th
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.abspath(os.path.join(HERE, "..", "..")); RS = os.path.join(B, "results_std3")
VARS = {"walking_rate": "ext__walking_rate", "moderate_pa_rate": "moderate_pa_rate", "public_sport_fac": "ext__public_sport_fac_per100k", "village_sport_fac": "ext__village_sport_fac_per100k",
        "obesity_rate": "obesity_rate", "high_risk_drinking": "ext__high_risk_drinking", "smoking_rate": "ext__smoking_rate", "screening_uptake": "ext__screening_uptake",
        "im_specialists": "im_specialists_per_100k", "basic_livelihood_rate": "basic_livelihood_rate", "urban_population_share": "urban_population_share", "physicians_per_1000": "physicians_per_1000",
        "sex_ratio": "sex_ratio", "fiscal_independence": "fiscal_independence", "pop80_share": "pop80_share"}
LAB = {"walking_rate": "Walking rate", "moderate_pa_rate": "Moderate-or-higher physical activity", "public_sport_fac": "Public sports facilities", "village_sport_fac": "Village sports facilities",
       "obesity_rate": "Obesity", "high_risk_drinking": "High-risk drinking", "smoking_rate": "Current smoking", "screening_uptake": "Screening uptake", "im_specialists": "Internal medicine specialists",
       "basic_livelihood_rate": "Public assistance recipients", "urban_population_share": "Urban population share", "physicians_per_1000": "Physicians", "sex_ratio": "Sex ratio",
       "fiscal_independence": "Fiscal autonomy", "pop80_share": "Aged 80 years or older"}
KEY3 = [("public_sport_fac", "Sports facilities"), ("screening_uptake", "Screening uptake"), ("walking_rate", "Walking rate")]
f3 = lambda r: f"{r[0]:.3f} ({r[1]:.3f}-{r[2]:.3f})" if r else "–"
def row(d, c):
    x = d[d["cov"].astype(str) == c]
    return f3([float(x.IRR.iloc[0]), float(x.lo.iloc[0]), float(x.hi.iloc[0])]) if len(x) else "–"
S1 = [("Walking rate", "Physical activity", "Adults walking at least 30 minutes on at least 5 days a week, age-standardized, %", "Community Health Survey", "−"),
      ("Moderate-or-higher physical activity", "Physical activity", "Adults meeting moderate or vigorous physical activity criteria, age-standardized, %", "Community Health Survey", "−"),
      ("Public sports facilities", "Physical activity", "Public sports facilities per 100,000 residents", "National public sports facility register", "−"),
      ("Village sports facilities", "Physical activity", "Village (neighborhood) sports facilities per 100,000 residents", "National public sports facility register", "−"),
      ("Obesity", "Lipid risk behavior", "Adults with self-reported body mass index of 25 kg/m² or more, age-standardized, %", "Community Health Survey", "+"),
      ("High-risk drinking", "Lipid risk behavior", "Adults drinking 7 or more standard drinks (women 5) at least twice a week, age-standardized, %", "Community Health Survey", "+"),
      ("Current smoking", "Lipid risk behavior", "Adults currently smoking cigarettes, age-standardized, %", "Community Health Survey", "+"),
      ("Screening uptake", "Screening and care reach", "First-stage general health screening attendees as a share of those invited, %", "National Health Insurance Service via KOSIS", "−"),
      ("Internal medicine specialists", "Screening and care reach", "Internal medicine specialists per 100,000 residents", "Health Insurance Review and Assessment Service", "−"),
      ("Public assistance recipients", "Screening and care reach", "Basic livelihood security recipients per 100 residents; implausible 2021-2023 values set to missing and interpolated", "Ministry of Health and Welfare via KOSIS", "+"),
      ("Urban population share", "Fixed adjustment", "Residents in urban zones, % of population", "Ministry of Land via KOSIS", "–"),
      ("Physicians", "Fixed adjustment", "Physicians working in medical institutions per 1,000 residents", "KOSIS e-local indicators", "–"),
      ("Sex ratio", "Fixed adjustment", "Men per 100 women", "Resident registration", "–"),
      ("Fiscal autonomy", "Fixed adjustment", "Fiscal autonomy ratio of the local government, %", "Ministry of the Interior and Safety via KOSIS", "–"),
      ("Aged 80 years or older", "Fixed adjustment", "Residents aged 80 years or older, % of population", "Resident registration", "–"),
      ("Hit-and-run crashes", "Negative control", "Hit-and-run crashes per 100 traffic crashes", "KOSIS e-local indicators", "none"),
      ("Traffic culture index", "Negative control", "Traffic culture index score", "Korea Transportation Safety Authority via KOSIS", "none"),
      ("Fires", "Negative control", "Fires per 10,000 residents", "National Fire Agency via KOSIS", "none")]
def t1():
    import re as _re
    return ("Supplementary Table S1. District characteristics, definitions, sources, and expected direction", ["Characteristic", "Group", "Definition", "Source", "Expected"], [[a, b, _re.sub(r"(\d)-(\d)", "\\1\u2013\\2", c), d, e] for a, b, c, d, e in S1],
            "Expected direction for suspected dyslipidemia, set before modeling. Survey items not collected in 2019 were interpolated within districts. All characteristics were standardized to 1 SD of district-years. KOSIS, Korean Statistical Information Service.")
def t2():
    rows = [["Panel", f"{th(N['n_rows'])} district-years = {N['n_districts']} districts × 7 years (2018-2024); unique keys; no missing outcome, expected count, or covariate"],
            ["Outcome", "First-stage judgement 'suspected dyslipidemia' (KOSIS DT_35007_N103), excluding examinees already treated for dyslipidemia; 7 district-years in cities with general districts summed from district rows"],
            ["Sejong", "Reported only at the province level in the screening tables; included from the province-level rows (7 district-years)"],
            ["Denominator", "Examinees with a judgement result by sex (DT_35007_N098)"],
            ["Expected counts", "2 sexes × 15 age groups (19 or younger, 13 five-year groups to 80-84, 85 or older); national rates from DT_35007_N104 and DT_35007_N099; district examinee age structure from resident population × national age-specific screening rates, rescaled to observed examinees by sex; yearly sum of expected = observed"],
            ["Population", "Resident registration by sex and 5-year age group; 2023 Changwon total corrected to 1,009,038"],
            ["Cross-check", "Outcome and 11 of the 15 modeled characteristics (walking, moderate activity, obesity, high-risk drinking, smoking, public sports facilities, screening uptake, urban population share, physicians, sex ratio, fiscal autonomy) and 2 negative controls matched the reference district database in every overlapping cell; village sports facilities matched in 1,586 of 1,603 cells; internal medicine specialists, public assistance, and the share aged 80 or older were taken from the same compiled public statistics; the denominator differed by at most 5 examinees in 2022 between 2 tables"],
            ["Testing schedule", f"Lipid test every 2 years for all adults until 2017, every 4 years for men aged 24+ and women aged 40+ from 2018; national share of suspected dyslipidemia {N['rate_aux']['2017']:.1f}% in 2017 and {N['rate']['2018']:.1f}% in 2018; 2011-2017 analyzed separately"]]
    import re as _re
    rows = [[a, _re.sub(r"(\d)-(\d)", "\\1\u2013\\2", b)] for a, b in rows]
    return ("Supplementary Table S2. Data checks before modeling", ["Item", "Result"], rows, "")
def t3():
    rows = []
    specs = [("Principal model", "S3_main_IRR.csv", "std3"), ("Knorr-Held type I", "S9_typeI_IRR.csv", "std3"), ("Knorr-Held type II", "S43_part_KH_typeII.csv", "std3"),
             ("Knorr-Held type III", "S43_part_KH_typeIII.csv", "std3"), ("Knorr-Held type IV", "S43_part_KH_typeIV.csv", "std3"), ("Spatial+", "S41_part_D1_spatial_plus.csv", "std3"),
             ("Province-by-year effects", "S41_part_C4_sido_year_iid.csv", "std3"), ("Characteristics lagged 1 year", "S41_part_E1_lag1.csv", "std3"), ("Characteristics lagged 2 years", "S41_part_E2_lag2.csv", "std3"),
             ("Poisson-lognormal likelihood", "S41_part_C1_poisson_lognormal.csv", "std3"), ("ICAR district effect", "S43_part_icar_besag.csv", "std3"), ("Independent district effect only", "S43_part_iid_only.csv", "std3"),
             ("No district effect", "S43_part_no_spatial.csv", "std3"), ("Queen contiguity graph (577 pairs)", "S3_main_IRR.csv", "s577"), ("Without the age-80 adjustment", "S3_main_IRR.csv", "s2"),
             ("Unstandardized expected counts", "S3_main_IRR.csv", "sc")]
    for lab, f, v in specs:
        d = pd.read_csv(os.path.join(B, f"results_{v}", f)); w = d.WAIC.iloc[0] if "WAIC" in d else (N["waic_main"] if v == "std3" else N[v + "_fit"]["waic"])
        rows.append([lab, f"{float(w):,.1f}"] + [row(d, VARS[k]) for k, _ in KEY3])
    return ("Supplementary Table S3. Rate ratios per 1 SD (95% CrI) under alternative specifications", ["Specification", "WAIC"] + [l for _, l in KEY3], rows,
            "Each row changes one element of the principal model. WAICs are comparable only among models fitted to the same data (lagged models use fewer years). CrI, credible interval; ICAR, intrinsic conditional autoregressive; WAIC, widely applicable information criterion.")
def t4():
    rows = [["__H__", "Comparison outcomes (principal model refitted)"]]
    for k, l in KEY3:
        rows.append([f"  {l}", f3(N["main"][k]), f3(N["nco"][f"LIPTC|{k}"]), f3(N["nco"][f"UNDXDC|{k}"])])
    rows.append(["__H__", "Negative-control exposures"])
    for k, l in (("hit_and_run_rate", "Hit-and-run crashes"), ("traffic_culture_index", "Traffic culture index"), ("fires_per_10000", "Fires")): rows.append([f"  {l}", f3(N["nc"][k]), "–", "–"])
    rows.append(["__H__", "Post hoc models (after the results were seen)"])
    PH = N["ph"]; SF, UP = "ext__public_sport_fac_per100k", "ext__screening_uptake"
    for lab, a, c1, c2 in (("Adding education, unmet need, older adults living alone", "P1_plus_sensitivity_vars", SF, UP), ("Characteristic alone with fixed adjustments", "P2a_sportfac_alone", SF, None),
                           ("Adding population density (log)", "P3_plus_popdens", SF, UP), ("Between-district component", "P4_between_within", SF + "__B", UP + "__B"), ("Within-district component", "P4_between_within", SF + "__W", UP + "__W"),
                           ("Sports facilities per km² (log) instead of per 100,000", "P5_sportfac_per_km2", "sportfac_per_km2_log", UP), ("Without the other characteristic", "P6_drop_uptake", SF, None), ("Excluding 2020-2021", "P8_excl_2020_2021", SF, UP), ("Log-transformed sports facilities", "P9_sportfac_log", "sportfac_log", UP)):
        rows.append([f"  {lab}", f3(PH.get(f"{a}|{c1}")), f3(PH.get(f"{a}|{c2}")) if c2 else (f3(PH.get("P2b_uptake_alone|" + UP)) if a == "P2a_sportfac_alone" else f3(PH.get("P7_drop_sportfac|" + UP))), "–"])
    rows.append(["__H__", "E-values (CrI limit)"]); rows.append(["  E-value", f"{N['evalue']['public_sport_fac'][0]:.2f} ({N['evalue']['public_sport_fac'][1]:.2f})", f"{N['evalue']['screening_uptake'][0]:.2f} ({N['evalue']['screening_uptake'][1]:.2f})", "\u2013"])
    return ("Supplementary Table S4. Comparison outcomes, negative-control exposures, post hoc models, and E-values", ["Characteristic or model", "Suspected dyslipidemia\nor sports facilities", "Treated dyslipidemia\nor screening uptake", "Suspected diabetes"], rows,
            "Comparison-outcome rows give rate ratios per 1 SD (95% CrI) for suspected dyslipidemia, treated dyslipidemia, and suspected diabetes. Post hoc and E-value rows give values for sports facilities (second column) and screening uptake (third column). E-values treat the rate ratio per 1 SD as a risk ratio. E-value: minimum strength of association, on the risk ratio scale, that an unmeasured confounder would need with both the characteristic and the outcome to explain away the association (in parentheses, for the CrI limit closer to 1).")
def t5():
    W = pd.read_csv(os.path.join(RS, "S4_window_IRR.csv")); A = pd.read_csv(os.path.join(B, "results_aux", "S3_main_IRR.csv")); M = pd.read_csv(os.path.join(RS, "S3_main_IRR.csv"))
    rows = [[LAB[k], row(M, c), row(W[W.window == "W1_2018-19"], c), row(W[W.window == "W2_2020-24"], c), row(A, c)] for k, c in VARS.items()]
    return ("Supplementary Table S5. Principal model by period and under the earlier judgement criteria (2011-2017), rate ratios per 1 SD (95% CrI)", ["Characteristic", "2018-2024", "2018-2019", "2020-2024", "2011-2017"], rows,
            f"The 2011-2017 model used the same characteristics, adjustments, and standardization ({th(N['n_rows_aux'])} district-years; observed Moran's I {N['aux_fit']['obs_moran']:.2f}). CrI, credible interval.")
if __name__ == "__main__":
    J = TX(cite="bracket"); J.para("<b>Supplementary material</b>"); J.para(TITLE)
    for t in (t1(), t2(), t3(), t4(), t5()):
        J.page_break(); put_table(J, t, fs=8)
    J.doc_title = "Supplementary material"; p = os.path.join(OUT, "Supplementary_Material.docx"); J.save(p); to_pdf(p); print("supplementary ok")
