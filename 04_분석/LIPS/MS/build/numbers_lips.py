#  산출 = numbers_lips.json, gi_lips.csv. 원고 숫자의 유일한 출처.
import os, json, unicodedata, numpy as np, pandas as pd
from scipy.stats import spearmanr, norm
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.abspath(os.path.join(HERE, "..", "..")); AN = os.path.dirname(B); ROOT = os.path.dirname(AN); PAN = os.path.join(ROOT, "02_패널")
RS = lambda v="std3": os.path.join(B, f"results_{v}"); NFC = lambda s: unicodedata.normalize("NFC", str(s))
SHP = os.environ.get("ST_SHP", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "data", "boundary", "final.shp"))
VARS = {"walking_rate": "ext__walking_rate", "moderate_pa_rate": "moderate_pa_rate", "public_sport_fac": "ext__public_sport_fac_per100k", "village_sport_fac": "ext__village_sport_fac_per100k",
        "obesity_rate": "obesity_rate", "high_risk_drinking": "ext__high_risk_drinking", "smoking_rate": "ext__smoking_rate", "screening_uptake": "ext__screening_uptake",
        "im_specialists": "im_specialists_per_100k", "basic_livelihood_rate": "basic_livelihood_rate",
        "urban_population_share": "urban_population_share", "physicians_per_1000": "physicians_per_1000", "sex_ratio": "sex_ratio", "fiscal_independence": "fiscal_independence", "pop80_share": "pop80_share"}
HYP = list(VARS)[:10]; ROB = ["public_sport_fac", "screening_uptake"]
def tab(f, v="std3"):
    d = pd.read_csv(os.path.join(RS(v), f)); d["cov"] = d["cov"].astype(str); return d
def get(d, c):
    r = d[d["cov"] == c].iloc[0]; return [round(float(r.IRR), 3), round(float(r.lo), 3), round(float(r.hi), 3)]
N = {}
P = pd.read_csv(os.path.join(B, "panel_LIPS_std3.csv")); P["fbd_region"] = P.fbd_region.map(NFC)
N["n_rows"] = len(P); N["n_districts"] = P.fbd_region.nunique(); N["cases_total_m"] = round(P.cases.sum() / 1e6, 2); N["exam_total_m"] = round(P.offset.sum() / 1e6, 1)
g = P.groupby("year"); N["rate"] = {int(k): round(100 * v, 2) for k, v in (g.cases.sum() / g.offset.sum()).items()}
N["exam"] = {int(k): round(v / 1e6, 2) for k, v in g.offset.sum().items()}; N["cases"] = {int(k): round(v / 1e6, 2) for k, v in g.cases.sum().items()}
L = P.groupby("fbd_region").apply(lambda d: d.cases.sum() / d.E.sum(), include_groups=False)
N["sir_min"], N["sir_max"] = round(L.min(), 2), round(L.max(), 2); N["sir_p10"], N["sir_p90"] = round(L.quantile(.1), 2), round(L.quantile(.9), 2); N["p90p10"] = round(L.quantile(.9) / L.quantile(.1), 2)
N["sir_top"] = [[r, round(v, 2)] for r, v in L.sort_values(ascending=False).head(8).items()]; N["sir_bottom"] = [[r, round(v, 2)] for r, v in L.sort_values().head(8).items()]
P["dens"] = P.population / (P.area_m2 / 1e6)
D = P.groupby("fbd_region").agg(sf=("ext__public_sport_fac_per100k_raw", "mean"), up=("ext__screening_uptake_raw", "mean"), dens=("dens", "mean"), p80=("pop80_share_raw", "mean"))
N["rho_sf_dens"] = round(spearmanr(D.sf, D.dens).correlation, 2); N["rho_sf_p80"] = round(spearmanr(D.sf, D.p80).correlation, 2)
N["rho_sir_sf"] = round(spearmanr(L.reindex(D.index), D.sf).correlation, 2); N["rho_sir_up"] = round(spearmanr(L.reindex(D.index), D.up).correlation, 2)
# 창별 기술(Table 1)
WIN = {"2018-2019": (2018, 2019), "2020-2024": (2020, 2024), "2018-2024": (2018, 2024)}
raw = {k: (VARS[k] + "_raw") for k in VARS}; assert all(c in P for c in raw.values()), [c for c in raw.values() if c not in P]
T1 = {}
for w, (a, b) in WIN.items():
    s = P[P.year.between(a, b)]; sw = s.groupby("fbd_region").apply(lambda d: d.cases.sum() / d.E.sum(), include_groups=False)
    T1[w] = dict(n=len(s), cases=float(s.cases.sum()), exam=float(s.offset.sum()), rate=float(s.cases.sum() / s.offset.sum()), sir_med=float(sw.median()), sir_p10=float(sw.quantile(.1)), sir_p90=float(sw.quantile(.9)),
                 cov={k: [float(s[raw[k]].mean()), float(s[raw[k]].std())] for k in VARS})
N["T1"] = T1
mo = pd.read_csv(os.path.join(RS(), "S6_moran_year.csv")); N["moran_min"], N["moran_max"] = round(mo.moran_I.min(), 2), round(mo.moran_I.max(), 2)
N["kendall_w"] = round(float(pd.read_csv(os.path.join(RS(), "S12_persistence.csv")).iloc[0].kendall_W), 2)
Y = P.pivot_table(index="fbd_region", columns="year", values="SIR"); N["rho_2018_2024"] = round(spearmanr(Y[2018], Y[2024]).correlation, 2)
# Gi*(593 그래프, 자기 포함) — 7년 log SIR
import geopandas as gpd
G = open(os.path.join(B, "graph_593.graph")).read().split("\n"); nreg = int(G[0]); nb = {}
for line in G[1:]:
    t = line.split()
    if len(t) >= 2: nb[int(t[0])] = [int(x) for x in t[2:]]
area = pd.DataFrame({"fbd_region": gpd.read_file(SHP)["region"].values}); area["fbd_region"] = area.fbd_region.map(NFC); assert len(area) == nreg
id2r = dict(zip(range(1, nreg + 1), area.fbd_region))
x = np.log(L.reindex([id2r[i] for i in range(1, nreg + 1)]).values); assert not np.isnan(x).any(); xb, sd = x.mean(), x.std(); gi = []
for i in range(1, nreg + 1):
    w = np.zeros(nreg); w[i - 1] = 1; w[[j - 1 for j in nb.get(i, [])]] = 1; W = w.sum()
    gi.append(((w * x).sum() - xb * W) / (sd * np.sqrt((nreg * (w ** 2).sum() - W ** 2) / (nreg - 1))))
GI = pd.DataFrame({"fbd_region": [id2r[i] for i in range(1, nreg + 1)], "SIR": np.exp(x), "z": gi}); GI["p"] = 2 * norm.sf(GI.z.abs())
GI["cls"] = np.where((GI.p < 0.05) & (GI.z > 0), "hot", np.where((GI.p < 0.05) & (GI.z < 0), "cold", "other"))
S6 = pd.read_csv(os.path.join(RS(), "S6_spatial_RR.csv")); S6["fbd_region"] = S6.fbd_region.map(NFC); GI = GI.merge(S6[["fbd_region", "sigungu_cd"]], on="fbd_region", validate="one_to_one")
GI.to_csv(os.path.join(HERE, "gi_lips.csv"), index=False, encoding="utf-8-sig")
SIDO = {"서울": "Seoul", "부산": "Busan", "대구": "Daegu", "인천": "Incheon", "광주": "Gwangju", "대전": "Daejeon", "울산": "Ulsan", "세종": "Sejong", "경기": "Gyeonggi", "강원": "Gangwon", "충청북": "Chungbuk",
        "충청남": "Chungnam", "전라북": "Jeonbuk", "전라남": "Jeonnam", "경상북": "Gyeongbuk", "경상남": "Gyeongnam", "제주": "Jeju"}
GI["sido"] = GI.fbd_region.map(lambda r: next(v for k, v in SIDO.items() if r.startswith(k)))
for c in ("hot", "cold"):
    s = GI[GI.cls == c]; N[f"gi_{c}"] = len(s); N[f"gi_{c}_sido"] = s.sido.value_counts().to_dict(); N[f"gi_{c}_sir_med"] = round(s.SIR.median(), 2)
    N[f"gi_{c}_gun"] = int(s.fbd_region.str.endswith("군").sum()); N[f"gi_{c}_gu"] = int(s.fbd_region.str.endswith("구").sum()); N[f"gi_{c}_si"] = len(s) - N[f"gi_{c}_gun"] - N[f"gi_{c}_gu"]
DD = D.join(GI.set_index("fbd_region").cls); N["hc"] = {c: {k: round(float(DD[DD.cls == c][k].median()), 2) for k in ("sf", "up", "dens", "p80")} for c in ("hot", "other", "cold")}
# 모형
M = tab("S3_main_IRR.csv"); N["main"] = {k: get(M, VARS[k]) for k in VARS}
F = pd.read_csv(os.path.join(RS(), "S3_main_fit.csv")).iloc[0]; N["waic_main"] = float(F.WAIC); N["phi"] = float(F.phi); N["n_hot_bym"] = int(F.n_hotspot); N["n_cold_bym"] = int(F.n_coldspot)
N["resid_moran"] = float(F.resid_moran_I); N["resid_moran_p"] = float(F.resid_moran_p); N["obs_moran"] = float(F.obs_moran_I)
LK = pd.read_csv(os.path.join(RS(), "S1_likelihood.csv")); N["waic_forced"] = float(LK[LK.family == "nbinomial"].WAIC.iloc[0]); N["waic_forced_pois"] = float(LK[LK.family == "poisson"].WAIC.iloc[0])
hy = pd.read_csv(os.path.join(RS(), "S3_main_hyper.csv")); N["hyper"] = hy.round(3).values.tolist()
NC = tab("S3_negcontrol.csv"); N["nc"] = {c.replace("ext__", ""): get(NC, c) for c in NC["cov"]}
MV = pd.read_csv(os.path.join(RS(), "S7_multiverse_summary.csv")); MV["cov"] = MV["cov"].astype(str)
N["mv"] = {k: [round(float(MV[MV["cov"] == VARS[k]].cred_frac.iloc[0]), 3), round(float(MV[MV["cov"] == VARS[k]].sign_agree.iloc[0]), 3), int(MV[MV["cov"] == VARS[k]].n_specs.iloc[0])] for k in HYP}
for t in ("KH_typeI", "KH_typeII", "KH_typeIII", "KH_typeIV"):
    f = "S9_typeI_IRR.csv" if t == "KH_typeI" else f"S43_part_{t}.csv"
    d = tab(f); N[t] = {k: get(d, VARS[k]) for k in VARS}; N[t + "_waic"] = float(d.WAIC.iloc[0])
d = pd.read_csv(os.path.join(RS(), "S50_resid_moran_by_spec.csv")).set_index("spec"); N["rm_spec"] = {s: round(float(d.loc[s, "resid_moran_I"]), 2) for s in d.index}
for a in ("E1_lag1", "E2_lag2", "D1_spatial_plus", "C4_sido_year_iid", "C1_poisson_lognormal", "G1_kchs_ma3"):
    d = tab(f"S41_part_{a}.csv"); N[a] = {k: get(d, VARS[k]) for k in VARS if (d["cov"] == VARS[k]).any()}
for a in ("no_spatial", "iid_only", "icar_besag"):
    d = tab(f"S43_part_{a}.csv"); N[a] = {k: get(d, VARS[k]) for k in VARS if (d["cov"] == VARS[k]).any()}
N["nco"] = {}
for a in ("LIPTC", "UNDXDC"):
    d = tab(f"S41_part_H1_nco_{a}.csv"); N["nco"].update({f"{a}|{k}": get(d, VARS[k]) for k in VARS})
W = tab("S4_window_IRR.csv"); N["win"] = {f"{k}|{w}": get(W[W.window == w], VARS[k]) for k in VARS for w in W.window.unique()}
RET = pd.read_csv(os.path.join(RS(), "S41_retention_by_cov.csv")); N["ret"] = {k: [int(RET[RET["cov"] == VARS[k]].kept.iloc[0]), int(RET[RET["cov"] == VARS[k]].n_specs.iloc[0])] for k in ROB if (RET["cov"] == VARS[k]).any()}
EV = pd.read_csv(os.path.join(RS(), "S41_evalues.csv")); N["evalue"] = {k: [float(EV[EV["cov"] == VARS[k]].E_point.iloc[0]), float(EV[EV["cov"] == VARS[k]].E_limit.iloc[0])] for k in ROB if (EV["cov"] == VARS[k]).any()}
VP = pd.read_csv(os.path.join(RS(), "S42_variance_partition.csv")).set_index("component"); N["vp"] = {k: round(100 * float(v), 1) for k, v in VP.share_of_linear_predictor_var.items()}
PPC = pd.read_csv(os.path.join(RS(), "S42_ppc.csv")).iloc[0]; N["ppc95"] = round(100 * PPC.coverage95, 1)
OOS = pd.read_csv(os.path.join(RS(), "S41_oos2024.csv")).iloc[0]; N["oos_cov"] = round(100 * OOS.coverage95, 1); N["oos_mape"] = round(OOS.median_abs_pct_error, 1)
RG = pd.read_csv(os.path.join(RS(), "S50_region_slopes.csv")); N["reg"] = {f"{r.covariate}|{r.region}": [r.IRR, r.lo, r.hi] for r in RG.itertuples()}
PH = pd.read_csv(os.path.join(RS(), "S46_lips_posthoc.csv")); N["ph"] = {f"{r.analysis}|{r.cov}": [round(r.IRR, 3), round(r.lo, 3), round(r.hi, 3)] for r in PH.itertuples()}
for v in ("s577", "s2", "sc", "aux"):
    d = tab("S3_main_IRR.csv", v); N[v] = {k: get(d, VARS[k]) for k in VARS if (d["cov"] == VARS[k]).any()}
    f = pd.read_csv(os.path.join(RS(v), "S3_main_fit.csv")).iloc[0]; N[v + "_fit"] = dict(phi=float(f.phi), obs_moran=float(f.obs_moran_I), n=int(f.n_obs), waic=float(f.WAIC))
A = pd.read_csv(os.path.join(B, "panel_LIPS_aux.csv")); ga = A.groupby("year"); N["rate_aux"] = {int(k): round(100 * v, 2) for k, v in (ga.cases.sum() / ga.offset.sum()).items()}
N["cases_aux_m"] = round(A.cases.sum() / 1e6, 2); N["n_rows_aux"] = len(A)
for t2, key in (("LIPTC", "rho_lipt"), ("UNDXDC", "rho_undxd")):   # 비교 결과와 7년 SIR 지역 상관
    c2 = pd.read_csv(os.path.join(AN, t2, f"panel_{t2}.csv")).merge(pd.read_csv(os.path.join(PAN, f"{t2}_Estd.csv")), on=["year", "fbd_region"]); c2["fbd_region"] = c2.fbd_region.map(NFC)
    S2 = c2.groupby("fbd_region").apply(lambda d: d.cases.sum() / d.E_std.sum(), include_groups=False); j = pd.concat([L, S2], axis=1).dropna(); N[key] = [round(spearmanr(j[0], j[1]).correlation, 2), len(j)]
S6r = pd.read_csv(os.path.join(RS(), "S6_spatial_RR.csv")); N["rr_s"] = [round(S6r.RR.min(), 2), round(S6r.RR.max(), 2), round(S6r.RR.quantile(.1), 2), round(S6r.RR.quantile(.9), 2)]
N["n_hyp"] = 10; N["chance_n"] = round(10 * 0.05, 2); N["mv_n"] = 200
json.dump(N, open(os.path.join(HERE, "numbers_lips.json"), "w"), ensure_ascii=False, indent=1, default=float)
if __name__ == "__main__":
    print({k: N[k] for k in ("cases_total_m", "exam_total_m", "rate", "sir_p10", "sir_p90", "p90p10", "gi_hot", "gi_cold", "gi_hot_sido", "gi_cold_sido", "hc", "kendall_w", "rho_2018_2024", "moran_min", "moran_max", "rm_spec", "vp", "ppc95", "oos_cov", "evalue", "rate_aux", "rho_sf_dens")})
