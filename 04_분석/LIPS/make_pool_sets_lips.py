#!/usr/bin/env python3
#      + 분석용 고정 복사본 SQLite region_year(mode=ro): 일반건강검진 수검률(chk__수검률) + LIPS 분자·분모(02_패널/LIPS_Estd3s.csv, 99S, 세종 시도 머리행 포함).
#  보조 기간(2011-17): sets_LIPS_aux.json(ST_VER=aux), E = 02_패널/LIPSA_Estd3s.csv.
import os, json, sqlite3, unicodedata
import numpy as np, pandas as pd
NFC = lambda s: unicodedata.normalize("NFC", str(s))
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); PAN = os.path.join(ROOT, "02_패널"); AN = os.path.join(ROOT, "04_분석")
DB = os.path.expandvars("$ST_GPT_DATASET") + "/02_체육건강_시공간_GPT버전/02_체육건강_시공간_GPT버전.sqlite"
POOL = "EXT_canonical_pool_LIPS_261116.csv"
D = pd.read_csv(os.path.join(PAN, "EXT_canonical_pool_DIGX_261114.csv")); D = D[D.year.between(2011, 2024)].drop(columns=["digx_deaths"])
D["fbd_region"] = D.fbd_region.map(NFC)
T = pd.read_csv(os.path.join(PAN, "EXT_canonical_pool_LIPT_261111.csv"))[["year", "fbd_region", "im_specialists_per100k", "unmet_need_rate"]]; T["fbd_region"] = T.fbd_region.map(NFC)
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
RY = pd.read_sql('select year, fbd_region, "chk__수검률" as screening_uptake from region_year where year between 2011 and 2024', con); RY["fbd_region"] = RY.fbd_region.map(NFC)
E1 = pd.read_csv(os.path.join(PAN, "LIPS_Estd3s.csv")); E0 = pd.read_csv(os.path.join(PAN, "LIPSA_Estd3s.csv"))
Y = pd.concat([E0, E1])[["year", "fbd_region", "cases", "offset"]].rename(columns={"cases": "lips_cases", "offset": "lips_examinees"}); Y["fbd_region"] = Y.fbd_region.map(NFC)
P = D.merge(T, on=["year", "fbd_region"], how="left", validate="one_to_one").merge(RY, on=["year", "fbd_region"], how="left", validate="one_to_one").merge(Y, on=["year", "fbd_region"], how="left", validate="one_to_one")
assert len(P) == 229 * 14, len(P)
# 수급률 양쪽 규칙 재확인(이미 정정본이면 0)
r = P.fbd_region.map(P[P.year.isin([2020, 2024])].groupby("fbd_region").basic_livelihood_rate.mean())
bad = P.year.isin([2021, 2022, 2023]) & ((P.basic_livelihood_rate < 0.2 * r) | (P.basic_livelihood_rate > 5 * r)); print("수급률 규칙 위반 칸(정정본이면 0):", int(bad.sum()))
# 수검률: SQLite chk__수검률 = 1차 수검인원 ÷ 대상인원 × 100(KOSIS DT_35007_N001/N001_1, 종로 2018-24 일치 확인).
#  세종 2012-24 SQLite 빈칸 → 원표 시도 머리행(세종) 수검/대상으로 채움. 나머지 7칸(부천 2016, 용인·창원·천안 2011-12) → 시군구 안 선형 보간·끝은 가장 가까운 연도(기록).
SRCN = os.path.join(ROOT, "00_원천", "C_NHIS_검진보험")
U = pd.concat([pd.read_csv(os.path.join(SRCN, f), encoding="utf-8-sig", low_memory=False) for f in ["DT_35007_N001.csv", "DT_35007_N001_1.csv"]])
U = U[U.C1_NM.astype(str).str.contains("세종") & (U.C2_NM == "합계")].drop_duplicates(["PRD_DE", "ITM_NM"]).pivot(index="PRD_DE", columns="ITM_NM", values="DT").astype(float)
sju = (U["수검인원"] / U["대상인원"] * 100); print("세종 수검률(원표 시도 머리행):", sju.round(2).to_dict())
m = (P.fbd_region == NFC("세종시세종시")) & P.screening_uptake.isna(); P.loc[m, "screening_uptake"] = P.loc[m, "year"].map(sju).values
n0 = int(P.screening_uptake.isna().sum()); miss = P.loc[P.screening_uptake.isna(), ["fbd_region", "year"]].values.tolist()
P = P.sort_values(["fbd_region", "year"]); P["screening_uptake"] = P.groupby("fbd_region").screening_uptake.transform(lambda s: s.interpolate(limit_area="inside").bfill().ffill())
print(f"수검률 보간·이월 {n0}칸:", miss); P = P.sort_values(["year", "fbd_region"]).reset_index(drop=True)
print("결측 칸:", P.isna().sum()[P.isna().sum() > 0].to_dict())
print("세종 결측 열:", P[P.fbd_region == NFC("세종시세종시")].isna().sum()[lambda s: s > 0].to_dict())
P.to_csv(os.path.join(PAN, POOL), index=False, encoding="utf-8-sig")
# 비교 결과 패널(2018-24)
for t2, src in [("LIPTC", "LIPT"), ("UNDXDC", "UNDXD")]:
    S = pd.read_csv(os.path.join(AN, src, f"panel_{src}_std3.csv"), usecols=["year", "fbd_region", "cases", "E"]); S = S[S.year.between(2018, 2024)]
    os.makedirs(os.path.join(AN, t2), exist_ok=True); S[["year", "fbd_region", "cases"]].to_csv(os.path.join(AN, t2, f"panel_{t2}.csv"), index=False)
    S.rename(columns={"E": "E_std"})[["year", "fbd_region", "E_std"]].to_csv(os.path.join(PAN, f"{t2}_Estd.csv"), index=False)
    open(os.path.join(AN, t2, "README.md"), "w").write(f"# {t2}: comparison-outcome copy for LIPS(2026-11-16). 원본 = 04_분석/{src}/panel_{src}_std3.csv cases·E(2018-24). 분석 대상 아님.\n")
    print(t2, len(S), S.year.min(), S.year.max(), S.fbd_region.nunique())

FORCED = ["urban_population_share", "physicians_per_1000", "sex_ratio", "fiscal_independence", "pop80_share"]
NEG = ["hit_and_run_rate", "traffic_culture_index", "fires_per_10000"]
SENS = ["tertiary_educated_share", "unmet_need_rate", "living_alone_elderly"]
HYP = ["walking_rate", "moderate_pa_rate", "public_sport_fac_per100k", "village_sport_fac_per100k",
       "obesity_rate", "high_risk_drinking", "smoking_rate", "screening_uptake", "im_specialists_per100k", "basic_livelihood_rate"]
OBES = "kchs__DT_H_OBE_OBE__SR"   # 비만율은 마스터 KCHS 열 이름으로(풀 obesity_rate와 값 동일, 2019 미조사 해는 80이 시군구 안 보간) → _st_config 자동 S1b(비만 추가 민감도)가 중복 변수로 특이해지는 것을 막음
X = lambda L: [OBES if v == "obesity_rate" else "ext__" + v for v in L]
XK = lambda v: OBES if v == "obesity_rate" else "ext__" + v
EXPECT = {
 "walking_rate": "- (walking rate)", "moderate_pa_rate": "- (moderate-or-higher physical activity)", "public_sport_fac_per100k": "- (public sports facilities)",
 "village_sport_fac_per100k": "- (village sports facilities)", "obesity_rate": "+ (self-reported obesity)", "high_risk_drinking": "+ (high-risk drinking)", "smoking_rate": "+ (current smoking)",
 "screening_uptake": "- (screening uptake)", "im_specialists_per100k": "- (internal medicine specialists)", "basic_livelihood_rate": "+ (public assistance recipients)",
}
SETS = {"S1_narrative_full": X(HYP),
        "S2_core": X(["walking_rate", "public_sport_fac_per100k", "obesity_rate", "screening_uptake", "im_specialists_per100k", "basic_livelihood_rate"]),
        "S3_physical_activity": X(["walking_rate", "moderate_pa_rate", "public_sport_fac_per100k", "village_sport_fac_per100k"]),
        "S4_lipid_risk_behaviour": X(["obesity_rate", "high_risk_drinking", "smoking_rate"]),
        "S5_detection_care": X(["screening_uptake", "im_specialists_per100k", "basic_livelihood_rate"]),
        "S6_risk_detection": X(["obesity_rate", "high_risk_drinking", "smoking_rate", "screening_uptake", "im_specialists_per100k", "basic_livelihood_rate"])}
pov = [{"year": 2023, "fbd_region": "경상남도창원시", "population": 1009038, "source": "KOSIS DT_1YL20651E 2023 통합창원시 계(유방암 11/4 population_final_audit)"}]
allv = ["lips_cases", "lips_examinees"] + FORCED + NEG + SENS + [v for v in HYP if v != "obesity_rate"]
def make(ver, efile, years, windows, post, elabel, note_extra):
    return {
     "tag": "LIPS", "outcome_column": "ext__lips_cases",
     "outcome_label_en": "Examinees classified as 'suspected dyslipidaemia' at the first-stage National General Health Screening (not already under treatment; NHIS health screening statistics DT_35007_N103, annual)",
     "disease_en": "Screen-detected suspected dyslipidaemia (untreated, newly flagged at screening)",
     "disease_ko": "검진 이상지질혈증 의심(1차 판정 질환의심, 유질환자 제외)",
     "offset": "ext__lips_examinees", "exclude_years": [],
     "forced": X(FORCED), "negative_controls": X(NEG),
     "offset_E_column": "E_std", "offset_E_file": efile, "offset_E_label": elabel,
     "graph": "593-edge contact graph, ST_GRAPH=04_분석/LIPS/graph_593.graph",
     "population_override": pov, "sensitivity_only_extra": X(SENS),
     "version": f"std3 physical-activity pathway (screen-detected suspected dyslipidaemia: physical activity and sport facilities, lipid risk behaviours, detection and care reach, deprivation), {years[0]}-{years[1]}" + note_extra,
     "sets": SETS, "transform": {XK(v): "none" for v in FORCED + NEG + SENS + HYP},
     "expected_direction": {XK(k): v for k, v in EXPECT.items()},
     "rules": {"likelihood": "forced-only 모형 WAIC 낮은 쪽(Poisson/NB)", "set_choice": "WAIC 최소, 4 이내면 변수 적은 세트", "credible": "95% CrI 1 제외", "vif_drop": 10, "multiverse_specs": 200,
               "main_model_note": "주모형 = S1_narrative_full(가설 10 + 강제통제 5). 세트를 다시 바꾸지 않음. VIF>10 유지·보고.",
               "years": list(years), "windows": windows, "covid_post_from": post,
               "windows_note": "7년 패널(2018-24): 시간 효과 rw1 7점, 창 = 코로나 전(2018-19)·후(2020-24) 2개(결과 전 고정). 2018 판정 정의 단절을 가로지르지 않는다."},
     "note": "Outcome: suspected dyslipidemia at the first-stage general health screening (NHIS), 229 districts; expected counts standardised for sex and 16 age groups.",
     "extra_columns": {"ext__" + v: [POOL, v] for v in allv}}
w_main = {"W1_2018-19": [2018, 2019], "W2_2020-24": [2020, 2024]}
LAB_M = "sex-and-age-standardised expected suspected-dyslipidaemia cases, 2 sexes x 15 age bands (<=19, 20-24 to 80-84, 85+) (national screening rates DT_35007_N104/N099; district examinee age structure approximated from resident population x national uptake, sex totals observed), 2018-2024"
for ver in ["std3", "s577", "s2", "sc"]:
    j = make(ver, "LIPS_Estd3s.csv", (2018, 2024), w_main, 2020, LAB_M, "")
    if ver == "s577": j["sens_note"] = "민감도: 그래프만 queen 577"
    if ver == "s2": j["sens_note"] = "민감도: 80세 이상 비율 강제통제 없음"; j["forced"] = X(FORCED[:4])
    if ver == "sc": j["sens_note"] = "민감도: 비표준화(조) E(수검자 × 전국 연도 의심 율)"; j["offset_E_column"] = "E_crude"; j["offset_E_label"] = "crude E (examinees x national annual suspected-dyslipidaemia rate)"
    json.dump(j, open(os.path.join(HERE, f"sets_LIPS_{ver}.json"), "w"), ensure_ascii=False, indent=1)
w_aux = {"W1_2011-14": [2011, 2014], "W2_2015-17": [2015, 2017]}
j = make("aux", "LIPSA_Estd3s.csv", (2011, 2017), w_aux, 2015, LAB_M.replace("2018-2024", "2011-2017"), " [aux: pre-2018 judgement definition]")
j["rules"]["windows_note"] = "보조 기간 2011-17(2018 판정 정의 단절 이전). S5 COVID 단계는 해당 없음(placeholder로 건너뜀)."
json.dump(j, open(os.path.join(HERE, "sets_LIPS_aux.json"), "w"), ensure_ascii=False, indent=1)
print("sets 저장: std3, s577, s2, sc, aux")
