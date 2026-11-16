#!/usr/bin/env python3
import os, sqlite3, unicodedata, pandas as pd, numpy as np
NFC = lambda s: unicodedata.normalize("NFC", str(s)); HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.expandvars("$ST_GPT_DATASET") + "/02_체육건강_시공간_GPT버전/02_체육건강_시공간_GPT버전.sqlite"
MAP = {"ext__walking_rate_raw": "kchs__DT_H_EX_WALK__SR", "moderate_pa_rate_raw": "kchs__DT_H_EX_PHY__SR", "obesity_rate_raw": "kchs__DT_H_OBE_OBE__SR",
       "ext__high_risk_drinking_raw": "kchs__DT_H_DR_HIGH__SR", "ext__smoking_rate_raw": "kchs__DT_H_SM__SR", "ext__screening_uptake_raw": "chk__수검률",
       "sex_ratio_raw": "eloc__DT_1YL20701__남녀성비＜br＞(A÷B×100)", "fiscal_independence_raw": "eloc__DT_1YL20891__재정자주도(세입과목개편전)",
       "physicians_per_1000_raw": "eloc__DT_1YL20981__인구천명당의료기관종사의사수＜br＞(A÷B×1000)", "hit_and_run_rate_raw": "eloc__DT_1YL13901__뺑소니교통사고율＜br＞(A÷B×100)",
       "fires_per_10000_raw": "eloc__DT_1YL21081__주민만명당화재발생건수＜br＞(A÷B×10000)", "cases": "chk__질환의심_이상지질혈증", "offset": "chk__검진수검"}
P = pd.read_csv(os.path.join(HERE, "panel_LIPS_std3.csv")); P["fbd_region"] = P.fbd_region.map(NFC)
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
R = pd.read_sql("select year, fbd_region, " + ", ".join(f'"{c}"' for c in MAP.values()) + " from region_year where year between 2018 and 2024", con); R["fbd_region"] = R.fbd_region.map(NFC)
M = P.merge(R, on=["year", "fbd_region"], how="left", validate="one_to_one", suffixes=("", "_sq")); rows = []
for pc, sc in MAP.items():
    a = M[pc].astype(float); b = M[sc + ("_sq" if sc in P.columns else "")].astype(float) if (sc + "_sq") in M.columns else M[sc].astype(float)
    both = a.notna() & b.notna(); d = (a[both] - b[both]).abs()
    rows.append(dict(panel_col=pc, sqlite_col=sc, n_both=int(both.sum()), n_sqlite_missing=int(b.isna().sum()), n_equal_1e6=int((d <= 1e-6 * np.maximum(1, b[both].abs())).sum()),
                     max_abs_diff=float(d.max()) if both.any() else np.nan, pearson=float(np.corrcoef(a[both], b[both])[0, 1]) if both.sum() > 2 else np.nan,
                     diff_cells="; ".join(f"{r.fbd_region}{r.year}" for r in M.loc[both[both].index[(d > 1e-6 * np.maximum(1, b[both].abs())).values]].itertuples())[:400]))
R2 = pd.read_sql('select year, fbd_region, population as pop_sq, "fac__total" as ft, "vil__계" as vt, "eloc__DT_1YL20421E__1인당도시지역면적현황__도시지역인구" as upop from region_year where year between 2018 and 2024', con); R2["fbd_region"] = R2.fbd_region.map(NFC)
M2 = P.merge(R2, on=["year", "fbd_region"], how="left", validate="one_to_one")
for pc, b in (("ext__public_sport_fac_per100k_raw", M2.ft / M2.pop_sq * 1e5), ("ext__village_sport_fac_per100k_raw", M2.vt / M2.pop_sq * 1e5), ("urban_population_share_raw", M2.upop / M2.pop_sq * 100)):
    a = M2[pc].astype(float); both = a.notna() & b.notna(); d = (a[both] - b[both]).abs()
    rows.append(dict(panel_col=pc, sqlite_col="derived count / population", n_both=int(both.sum()), n_sqlite_missing=int(b.isna().sum()), n_equal_1e6=int((d <= 1e-3).sum()), max_abs_diff=float(d.max()), pearson=float(np.corrcoef(a[both], b[both])[0, 1]),
                     diff_cells="; ".join(f"{r.fbd_region}{r.year}" for r in M2.loc[both[both].index[(d > 1e-3).values]].itertuples())[:400]))
O = pd.DataFrame(rows); O.to_csv(os.path.join(HERE, "gate_sqlite_crosscheck_LIPS_261116.csv"), index=False, encoding="utf-8-sig"); print(O.drop(columns="diff_cells").to_string()); print(O[["panel_col", "diff_cells"]].to_string())
