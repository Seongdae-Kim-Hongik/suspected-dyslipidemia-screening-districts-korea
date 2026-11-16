#!/usr/bin/env python3
# 38 — 9개 질환 시군구 간접 연령표준화 기대건수 E_std (36·37 일반화, 공간 선별 std 재판정용, 2026-10-19)
#  ① 298분류 → 질환 매핑: KOSIS 298분류 명칭(축 15350AF5) + 건강보험통계 「298 질병분류참조표」(00_원천/NHIS_전국_질병분류_연령/2019·2020 .hwp, 코드별 ICD 범위)
#     → 코드의 ICD 범위가 질환 정의 범위 안에 완전히 들어가면 포함, 일부만 겹치면 '부분 겹침'으로 표시·제외(판단 근거 열에 기록)
#     → 04_분석/00_298코드_질환매핑.csv
#     질환 정의(건보 지역별의료이용통계 주요질환 정의와 동일): PERIO K00-K01,K03-K08 · INFECT A00-B99 · ARTH M00-M19,M22-M25 · HTN I10-I15
#                  · MENTAL F00-F99(37과 동일, 112~119) · DM E10-E14 · LIVER K70-K77 · BRCA C50 · GCA C16.  METS 제외(검진 판정 인원, 분모=수검자; 진료 연령 프로파일 부적합)
#  ② 전국 연령별 진료실인원(진료형태 계): 2011-17 KOSIS 350/TX_35001_A061, 2018 DT_35001_A0611, 2019-24 엑셀(36의 파서 재사용, 연령 합=총계 assert)
#     세부 분류 합 = 한 사람이 둘 이상 분류로 진료받으면 중복 계산 → 실인원이 아니라 '연령 프로파일' 용도(연도별 ΣE=Σcases 재척도로 수준은 관측에 맞춤)
#  ③ rate[y,a] = 진료실인원 합 / 전국 연령별 분모(패널 시군구 합). 분모: 패널 offset 열(질환 분모: 인구, GCA 주민등록인구, BRCA 여성 주민등록인구) × 연령 비율
#     연령 비율: ST_agepop(10세 8구간, 성 구분 없음); 누락 시군구-연도는 같은 시군구 가장 가까운 연도 비율(37과 같은 규칙)
#     BRCA: 여성 연령 비율 = FBD_DATA_ZIP/<연도>.csv(주민등록 성·5세) 여자 열에서 시군구별로 계산(누락은 가장 가까운 연도) × 패널 offset(여성 인구);
#           전국 rate 분모도 여성 연령별 인구(298분류 표는 성별이 없으므로 C50 진료실인원 전체 ÷ 여성 인구 — 남성 유방암(전체의 1% 미만)이 분자에 섞이는 한계 기록)
#  ④ E_std[d,y] = Σ_a pop[d,y,a] × rate[y,a], 연도별 Σ_d E_std = Σ_d cases 로 재척도
#  산출: 02_패널/<TAG>_Estd.csv (MENTAL 은 기존 파일 유지, 재생성 안 함 — 대신 같은 코드로 재현해 기존 파일과 대조 assert)
#        02_패널/ALL_national_agerates_std.csv(질환×연도×연령 rate), 04_분석/00_298코드_질환매핑.csv
import os, re, sys, glob, json, importlib.util, struct, zlib
import numpy as np, pandas as pd
from scipy.stats import spearmanr
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("m36", os.path.join(HERE, "36_build_national_agerates.py")); m36 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m36)
spec40 = importlib.util.spec_from_file_location("m40", os.path.join(HERE, "40_region_crosswalk.py")); m40 = importlib.util.module_from_spec(spec40); spec40.loader.exec_module(m40)
NFC = m36.NFC; AGES = m36.AGES
SRC = os.path.join(ROOT, "00_원천", "NHIS_전국_질병분류_연령")
FBDZIP = os.environ.get("ST_FBDZIP") or os.path.expandvars("$ST_DATA_ROOT") + "/기타/R_Studio/FBD_DATA_ZIP"   # 2026-11-04: ST_FBDZIP=교정 사본 폴더(창원 2023 2022값 복사 결함, BRCA population_final_audit/raw_corrected)
TAGS = ["PERIO", "INFECT", "ARTH", "HTN", "MENTAL", "DM", "LIVER", "BRCA", "GCA"]
DEF = {  # 질환 정의 ICD 범위(포함 구간 목록) — 건보 주요질환 정의
    "PERIO": [("K00", "K01"), ("K03", "K08")], "INFECT": [("A00", "B99")], "ARTH": [("M00", "M19"), ("M22", "M25")], "HTN": [("I10", "I15")],
    "MENTAL": [("F00", "F99")], "DM": [("E10", "E14")], "LIVER": [("K70", "K77")], "BRCA": [("C50", "C50")], "GCA": [("C16", "C16")]}
DEF_TXT = {"PERIO": "K00-K01,K03-K08 (건보 치주질환 정의; K02 치아우식증 제외)", "INFECT": "A00-B99", "ARTH": "M00-M19,M22-M25", "HTN": "I10-I15", "MENTAL": "F00-F99",
           "DM": "E10-E14", "LIVER": "K70-K77", "BRCA": "C50", "GCA": "C16"}

# ── 298 질병분류참조표(.hwp) 텍스트 추출(최소 CFB/HWP5 리더; 외부 패키지 없음) ──
def hwp_text(path):
    b = open(path, "rb").read(); assert b[:8] == bytes.fromhex("D0CF11E0A1B11AE1")
    ss = 1 << struct.unpack_from("<H", b, 30)[0]; mss = 1 << struct.unpack_from("<H", b, 32)[0]
    nfat, dir0 = struct.unpack_from("<I", b, 44)[0], struct.unpack_from("<I", b, 48)[0]
    cutoff, mfat0 = struct.unpack_from("<I", b, 56)[0], struct.unpack_from("<I", b, 60)[0]
    difat0, ndifat = struct.unpack_from("<I", b, 68)[0], struct.unpack_from("<I", b, 72)[0]
    sec = lambda i: b[512 + i * ss:512 + (i + 1) * ss]
    difat = list(struct.unpack_from("<109I", b, 76)); d = difat0
    for _ in range(ndifat): v = struct.unpack("<%dI" % (ss // 4), sec(d)); difat += v[:-1]; d = v[-1]
    fat = []
    for i in difat[:nfat]: fat += struct.unpack("<%dI" % (ss // 4), sec(i))
    def chain(s):
        o = []
        while s < 0xFFFFFFFA: o.append(s); s = fat[s]
        return o
    read = lambda s: b"".join(sec(i) for i in chain(s))
    dd = read(dir0); ents = []
    for k in range(len(dd) // 128):
        e = dd[k * 128:(k + 1) * 128]; nl = struct.unpack_from("<H", e, 64)[0]
        ents.append((e[:max(nl - 2, 0)].decode("utf-16le"), e[66], struct.unpack_from("<I", e, 116)[0], struct.unpack_from("<Q", e, 120)[0]))
    mini = read(ents[0][2]); minifat = []
    for i in chain(mfat0): minifat += struct.unpack("<%dI" % (ss // 4), sec(i))
    def mread(s, z):
        o = b""
        while s < 0xFFFFFFFA: o += mini[s * mss:(s + 1) * mss]; s = minifat[s]
        return o[:z]
    def stream(nm):
        for n, t, s, z in ents:
            if n == nm and t == 2: return read(s)[:z] if z >= cutoff else mread(s, z)
    comp = stream("FileHeader")[36] & 1; out = []
    for nm in sorted([n for n, t, s, z in ents if n.startswith("Section") and t == 2], key=lambda n: int(n[7:])):
        data = stream(nm); data = zlib.decompress(data, -15) if comp else data; i = 0
        while i < len(data):
            h = struct.unpack_from("<I", data, i)[0]; tag = h & 0x3FF; size = (h >> 20) & 0xFFF; i += 4
            if size == 0xFFF: size = struct.unpack_from("<I", data, i)[0]; i += 4
            if tag == 67:   # HWPTAG_PARA_TEXT
                raw = data[i:i + size]; t = ""; j = 0
                while j + 1 < len(raw):
                    c = struct.unpack_from("<H", raw, j)[0]
                    if c < 32 and c not in (9, 10, 13): j += 2 if c in (0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31) else 16; continue
                    t += chr(c); j += 2
                out.append(t)
            i += size
    return out
def ref_table(path):
    L = [l.strip() for l in hwp_text(path) if l.strip()]; idx = [i for i, l in enumerate(L) if re.fullmatch(r"\d{3}", l)]; rows = {}
    for k, i in enumerate(idx):
        seg = L[i + 1:(idx[k + 1] if k + 1 < len(idx) else len(L))]
        icd = "".join(s for s in seg if re.match(r"^[A-Z]\d\d", s)).replace(" ", "").rstrip(","); nm = " ".join(s for s in seg if not re.match(r"^[A-Z]\d\d", s))
        rows.setdefault(int(L[i]), (re.sub(r"\s+", " ", nm).strip(), icd))
    return rows
def icd_ranges(s):   # "A02,A04-A05" → [("A02","A02"),("A04","A05")]
    out = []
    for p in [x for x in s.split(",") if x]:
        a, _, b = p.partition("-"); out.append((a[:3], (b or a)[:3]))
    return out
def overlap(r, D):   # r 구간이 정의 D 안에 완전히 / 일부 / 전혀
    a, b = r
    if any(lo <= a and b <= hi for lo, hi in D): return "full"
    return "part" if any(not (b < lo or a > hi) for lo, hi in D) else "none"

def build_mapping():
    r19 = ref_table(os.path.join(SRC, "2019_298 질병분류참조표.hwp")); r20 = ref_table(os.path.join(SRC, "2020_298 질병분류참조표.hwp"))
    assert sorted(r19) == list(range(1, 299)) and sorted(r20) == list(range(1, 299))
    assert all(r19[c][1] == r20[c][1] for c in r19), "2019·2020 참조표 ICD 불일치"
    import kosis_api as K
    meta = [x for x in K.table_meta("350", "TX_35001_A061", "ITM") if x.get("OBJ_ID") == "15350AF5"]
    assert meta[0]["ITM_NM"] == "총계" and len(meta) >= 299
    kn = {i: (meta[i]["ITM_ID"], re.sub(r"\s+", "", meta[i]["ITM_NM"])) for i in range(1, 299)}
    rows = []
    for c in range(1, 299):
        nm, icd = r20[c]; hg = lambda x: re.sub(r"[^가-힣]", "", re.sub(r"\([^()]*[A-Za-z][^()]*\)", "", x))
        same = hg(nm)[:6] == hg(kn[c][1])[:6]   # 한글 명칭 앞 6자 대조(영문 괄호 제거)
        for T in TAGS:
            st = [overlap(r, DEF[T]) for r in icd_ranges(icd)]
            if all(s == "none" for s in st): continue
            inc = all(s == "full" for s in st)
            why = (f"참조표 ICD {icd} 가 정의 {DEF_TXT[T]} 안에 완전히 포함" if inc else
                   f"참조표 ICD {icd} 중 일부만 정의와 겹침 → 제외(정의 밖 코드가 섞임)")
            rows.append(dict(TAG=T, 질환정의_ICD=DEF_TXT[T], code298=c, kosis_itm_id=kn[c][0], kosis_명칭=kn[c][1], 참조표_명칭=nm, 참조표_ICD=icd,
                             명칭일치=same, 포함=inc, 판단근거=why))
    # 명칭만 보면 헷갈릴 수 있는 경계 코드(정의 밖): 판단 근거를 남김
    BND = {"PERIO": {180: "치아우식증 K02 — 건보 치주질환 정의(K00~K01,K03~K08)가 K02를 빼므로 제외", 182: "기타 구강·타액선·턱 K09-K14 — K08 바깥"},
           "ARTH": {202: "사지의 후천성 변형 M20-M21 — 정의가 M20-M21을 건너뜀", 204: "전신성 결합조직 장애 M30-M36(루푸스 등) — 관절염 정의 밖"},
           "INFECT": {250: "선천성 감염·기생충 질환 P35-P37 — 이름은 감염이나 ICD P장(주산기)", 251: "출생전후기 특이 감염 P38-P39 — P장", 291: "무증상 HIV 감염 상태 Z21 — Z장", 292: "전염성 질환 관련 건강위험 Z20,Z22-Z29 — Z장",
                      198: "피부·피하조직 감염 L00-L08 — L장", 165: "급성 인두염·편도염 J02-J03 — 호흡기 J장", 168: "인플루엔자 J09-J11 — J장", 169: "폐렴 J12-J18 — J장"},
           "HTN": {237: "임신 중 고혈압성 장애 O10-O16 — O장"}, "DM": {111: "기타 내분비·영양·대사 E15-E35 등 — E10-E14 바깥"},
           "LIVER": {63: "간 및 간내담관 악성신생물 C22 — 간암은 C장", 38: "기타 바이러스 간염 B15,B17-B19 — 감염병 장(INFECT에 포함)", 37: "급성 B형 간염 B16 — 감염병 장", 195: "담석·담낭염 K80-K81 — K77 바깥"},
           "BRCA": {91: "유방의 양성신생물 D24 — 악성 아님", 223: "유방의 장애 N60-N64 — 악성 아님", 89: "자궁경부 상피내암 D06 — 유방 아님"},
           "GCA": {183: "위·십이지장궤양 K25-K27 — 악성 아님", 59: "식도 악성신생물 C15", 65: "기타 소화기관 악성신생물 C17,C23-C24,C26"},
           "MENTAL": {122: "알쯔하이머병 G30 — 신경계 G장(치매 F00-F03은 112에 포함)", 121: "파킨슨병 G20 — G장"}}
    for T, dd in BND.items():
        for c, why in dd.items():
            nm, icd = r20[c]
            rows.append(dict(TAG=T, 질환정의_ICD=DEF_TXT[T], code298=c, kosis_itm_id=kn[c][0], kosis_명칭=kn[c][1], 참조표_명칭=nm, 참조표_ICD=icd,
                             명칭일치=hg(nm)[:6] == hg(kn[c][1])[:6], 포함=False, 판단근거="경계 코드 제외: " + why))
    M = pd.DataFrame(rows).sort_values(["TAG", "포함", "code298"], ascending=[True, False, True])
    M["용도"] = "전국 연령별 기준율(연령 프로파일) 산출 전용 — 세부 분류 진료실인원 합은 한 사람이 여러 분류로 진료받으면 중복 계산되므로 실인원이 아님; 수준은 연도별 ΣE_std=Σcases 재척도로 관측에 맞춤"
    assert M["명칭일치"].all(), M[~M["명칭일치"]]
    assert not M[M["포함"]].duplicated(["TAG", "code298"]).any()
    # 정의에 닿지만 참조표에 없는 정의 구간 확인(누락 검사): 정의 ICD 를 3자리로 펼쳐 포함 코드의 ICD 로 덮이는지
    def expand(D):
        s = set()
        for lo, hi in D:
            L0, L1 = lo[0], hi[0]
            for ch in range(ord(L0), ord(L1) + 1):
                a = int(lo[1:]) if chr(ch) == L0 else 0; z = int(hi[1:]) if chr(ch) == L1 else 99
                s |= {f"{chr(ch)}{n:02d}" for n in range(a, z + 1)}
        return s
    cover = {}
    for T in TAGS:
        cov = set()
        for icd in M[(M.TAG == T) & M["포함"]]["참조표_ICD"]: cov |= expand(icd_ranges(icd))
        cover[T] = sorted(expand(DEF[T]) - cov)
    return M, cover

# ── 전국 연령별 진료실인원(코드 묶음) ──
def kosis_codes(codes):
    import kosis_api as K
    items, objs = K.meta_codes("350", "TX_35001_A061"); dz = objs["15350AF5"]; cmap = {dz[c]: c for c in codes}; out = []; kdiff = []
    for tbl, y0, y1 in (("TX_35001_A061", 2011, 2017), ("DT_35001_A0611", 2018, 2018)):
        parts = []
        for k in range(0, len(codes), 40):   # 40,000셀 한도 여유
            p = {"method": "getList", "orgId": "350", "tblId": tbl, "itmId": "16350AAB1", "prdSe": "Y", "startPrdDe": str(y0), "endPrdDe": str(y1), "format": "json", "jsonVD": "Y",
                 "objL1": "+".join(dz[c] for c in codes[k:k + 40]), "objL2": "15350AB300", "objL3": "ALL"}
            parts.append(pd.DataFrame(K._get(K.BASE + "/Param/statisticsParameterData.do", p)))
        d = pd.concat(parts); assert (d.ITM_ID == "16350AAB1").all() and (d.C2 == "15350AB300").all()
        d["code"] = d.C1.map(cmap); d["DT"] = pd.to_numeric(d.DT.replace("-", 0)); assert d.code.notna().all()
        assert sorted(d.PRD_DE.astype(int).unique()) == list(range(y0, y1 + 1)) and set(d.code) == set(codes), (tbl, sorted(set(codes) - set(d.code)))
        for (yr, code), g in d.groupby(["PRD_DE", "code"]):
            tot = g.loc[g.C3_NM.str.replace(" ", "").isin(["합계", "계"]), "DT"]
            ag = g[~g.C3_NM.str.replace(" ", "").isin(["합계", "계"])]
            if len(tot) == 0 and ag.DT.sum() == 0: tot = pd.Series([0.0]); kdiff.append((int(yr), int(code), "총계 행 없음·연령 전부 0 → 0"))   # 예: 2013 디프테리아(14)
            assert len(tot) == 1, (tbl, yr, code); dif = ag.DT.sum() - tot.iloc[0]
            assert abs(dif) <= max(20, 1e-3 * tot.iloc[0]), f"KOSIS {tbl} {yr} {code}: 연령 합 {ag.DT.sum()} ≠ 총계 {tot.iloc[0]}"
            if dif: kdiff.append((int(yr), int(code), int(dif)))   # 실인원 집계라 연령 합≠총계 가능: 희귀 코드는 절대차 20명, 그 외 상대 1e-3까지 허용·기록
            for nm, v in zip(ag.C3_NM, ag.DT): out.append((int(yr), int(code), m36.age10(int(re.findall(r"\d+", nm)[0])), float(v)))
            out.append((int(yr), int(code), "TOTAL", float(tot.iloc[0])))
        print(f"[38] KOSIS {tbl} {y0}-{y1}: 코드 {d.code.nunique()}개 · 연령 {d.C3_NM.nunique()-1}구간")
    return out, kdiff
def excel_codes(codes):
    out = []
    for f in sorted(glob.glob(os.path.join(SRC, "*_298 질병분류.xlsx"))):
        yr = int(os.path.basename(f)[:4]); vals = m36.excel_year(f)
        assert sorted({c for c, _ in vals}) == list(range(1, 299))
        ages = sorted({a for _, a in vals if a != "TOTAL"}); assert len(ages) == 17
        for c in codes:
            s = sum(vals[(c, a)] for a in ages); assert s == vals[(c, "TOTAL")], f"{yr} {c}: 연령 합 ≠ 총계"
            for a in ages: out.append((yr, c, m36.age10(a), vals[(c, a)]))
            out.append((yr, c, "TOTAL", vals[(c, "TOTAL")]))
        print(f"[38] {yr} 엑셀: 코드 {len(codes)}개 연령 합=총계 확인")
    return out

# ── 시군구 연령 비율 ──
def shares_total():
    a = pd.read_csv(m36.AGEPOP); a["region"] = a.region.map(NFC); a["age10"] = a.age10.map(NFC)
    a["share"] = a["pop"] / a.groupby(["region", "year"])["pop"].transform("sum")
    return a.pivot_table(index=["region", "year"], columns="age10", values="share")[AGES]
MATCH = {}
def shares_female(regions):
    """FBD_DATA_ZIP/<연도>.csv(주민등록, 시군구×5세×성) → fbd_region×연도 여성 10세 비율. 70세 이상 = 계 − 0~69세 합(열린 구간 중복 회피)."""
    fbd = set(regions); rows = []; unmatched = {}
    mk = pd.read_csv(os.path.join(ROOT, "02_패널", "시군구_마스터키.csv"), dtype=str); KEY2REG = {NFC(k): NFC(r) for k, r in zip(mk.key, mk.fbd_region)}   # 예: 인천시|미추홀구 → 인천시남구
    SIDO = set(m40.SIDO_STD) - {"서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주", "제주도"}
    for y in range(2011, 2025):
        d = pd.read_csv(os.path.join(FBDZIP, f"{y}.csv"), encoding="cp949"); d.columns = [c.strip() for c in d.columns]
        assert list(d.columns[:6]) == ["행정구역별", "연령별", "시점", "전체", "여자", "남자"], d.columns
        sido = None; cur = {}
        for nm, ag, v in zip(d["행정구역별"].astype(str).str.strip(), d["연령별"].astype(str).str.strip(), d["여자"]):
            if nm == "전국": sido = None; continue
            if nm in SIDO:
                sido = nm
                if not nm.startswith("세종"): continue   # 세종특별자치시는 시도 행 자체가 시군구(하위 행 없음)
            if sido is None: continue
            sg = nm.split("-", 1)[1] if "-" in nm else nm
            v = pd.to_numeric(str(v).replace(",", ""), errors="coerce")
            if pd.isna(v): continue
            key = m40.make_key(sido, sg); sd, s2 = key.split("|"); reg = KEY2REG.get(NFC(key), NFC(sd + s2))
            if reg not in fbd and s2 == "청원군" and sd == "충청북도": reg = NFC("충청북도청주시")   # 2014 청주 통합 전: 청주+청원 합산
            if reg not in fbd and s2.endswith("군") and NFC(sd + s2[:-1] + "시") in fbd: reg = NFC(sd + s2[:-1] + "시")   # 여주·당진 등 시 승격 전
            if reg not in fbd: unmatched[(y, sd + s2)] = 1; continue
            MATCH.setdefault((y, reg), set()).add(nm)
            cur.setdefault(reg, {}); cur[reg][ag] = cur[reg].get(ag, 0.0) + float(v)
        for reg, A in cur.items():
            if "계" not in A or A["계"] <= 0: continue
            five = {int(re.findall(r"\d+", k)[0]): x for k, x in A.items() if re.fullmatch(r"\d+-\d+세", k)}
            if not all(lo in five for lo in range(0, 70, 5)): continue
            p = [five[lo] + five[lo + 5] for lo in range(0, 70, 10)] + [A["계"] - sum(five[lo] for lo in range(0, 70, 5))]
            assert p[-1] >= 0; tot = A["계"]
            rows += [(reg, y, ag, x / tot, tot) for ag, x in zip(AGES, p)]
    S = pd.DataFrame(rows, columns=["region", "year", "age10", "share", "female_total"])
    return S.pivot_table(index=["region", "year"], columns="age10", values="share")[AGES], S.groupby(["region", "year"]).female_total.first(), unmatched
def agepop(P, W):
    """P: 패널(year, fbd_region, offset) → 시군구-연도-연령 분모 = offset × 연령 비율(W); 누락은 같은 시군구 가장 가까운 연도."""
    rows, fb = [], []; regs = set(W.index.get_level_values(0))
    for r, y, off in zip(P.fbd_region, P.year, P.offset):
        if (r, y) in W.index: s = W.loc[(r, y)].values
        else:
            assert r in regs, f"연령 비율 없음: {r}"; ys = W.loc[r].index.values; src = int(ys[np.argmin(np.abs(ys - y))]); s = W.loc[(r, src)].values; fb.append((r, y, src))
        rows += [(y, r, ag, off * sh) for ag, sh in zip(AGES, s)]
    return pd.DataFrame(rows, columns=["year", "fbd_region", "age10", "pop"]), fb

if __name__ == "__main__":
    M, cover = build_mapping()
    M.to_csv(os.path.join(ROOT, "04_분석", "00_298코드_질환매핑.csv"), index=False, encoding="utf-8-sig")
    print("[38] 매핑 포함 코드:", {T: M[(M.TAG == T) & M["포함"]].code298.tolist() for T in TAGS})
    print("[38] 부분 겹침(제외):", M[~M["포함"]][["TAG", "code298", "참조표_ICD"]].values.tolist())
    print("[38] 정의 구간 중 포함 코드로 덮이지 않는 3자리 ICD(298 목록에 없는 코드 포함):", {T: v for T, v in cover.items() if v})
    CODES = {T: M[(M.TAG == T) & M["포함"]].code298.astype(int).tolist() for T in TAGS}
    assert CODES["MENTAL"] == list(range(112, 120)) and CODES["PERIO"] == [181] and CODES["ARTH"] == [200, 201, 203] and CODES["HTN"] == [145, 146] \
        and CODES["LIVER"] == [193, 194] and CODES["DM"] == [104] and CODES["BRCA"] == [73] and CODES["GCA"] == [60] and CODES["INFECT"] == list(range(1, 58))
    allc = sorted({c for v in CODES.values() for c in v})
    ko, kdiff = kosis_codes(allc)
    L = pd.DataFrame(ko + excel_codes(allc), columns=["year", "code", "age10", "patients"]).groupby(["year", "code", "age10"], as_index=False).patients.sum()
    print(f"[38] KOSIS 연령 합-총계 차이(허용·기록): {kdiff if kdiff else '없음'}")
    A = L[L.age10 != "TOTAL"]; assert sorted(A.year.unique()) == list(range(2011, 2025))
    WT = shares_total(); WF = None; RATES = []; SUMMARY = []
    for T in TAGS:
        PAN = os.path.join(ROOT, "04_분석", T, f"panel_{T}.csv")
        P = pd.read_csv(PAN, encoding="utf-8-sig"); P["fbd_region"] = P.fbd_region.map(NFC)
        if T == "BRCA":
            WF, FT, um = shares_female(P.fbd_region.unique())
            FT.index.names = ["fbd_region", "year"]; chk = P.set_index(["fbd_region", "year"]).offset; j = chk.to_frame().join(FT, how="inner"); rr = (j.female_total / j.offset)
            print(f"[38] BRCA 여성 연령 비율: 시군구-연도 {WF.shape[0]}/{len(P)} 매칭 · FBD 여성 총계/패널 offset 비 중앙 {rr.median():.4f} (P1 {rr.quantile(.01):.3f}, P99 {rr.quantile(.99):.3f}; 청주 2011-13은 청원 합산 1.22, 세종은 원자료 중복행으로 2.0 — 비율만 쓰므로 무영향) · 미매칭 이름 {len(um)}건(폐지 지명·통합시 하위 구)")
            W = WF
        else: W = WT
        AP, fb = agepop(P, W)
        num = A[A.code.isin(CODES[T])].groupby(["year", "age10"]).patients.sum()
        den = AP.groupby(["year", "age10"])["pop"].sum()
        rate = (num / den).rename("rate").reset_index(); rate["TAG"] = T; rate["patients_sum"] = num.values; rate["denom_nat"] = den.reindex(num.index).values
        RATES.append(rate)
        X = AP.merge(rate[["year", "age10", "rate"]], on=["year", "age10"], how="left"); assert X.rate.notna().all()
        X["e"] = X["pop"] * X.rate; E = X.groupby(["year", "fbd_region"], as_index=False).e.sum()
        D = P[["year", "fbd_region", "cases", "E", "older_adult_share_raw"]].merge(E, on=["year", "fbd_region"], how="left", validate="one_to_one"); assert D.e.notna().all()
        D["E_std"] = D.e * D.groupby("year").cases.transform("sum") / D.groupby("year").e.transform("sum")
        assert (D.groupby("year").E_std.sum() - D.groupby("year").cases.sum()).abs().max() < 1e-6 * D.cases.sum()
        D["SIR_crude"] = D.cases / D.E; D["SIR_std"] = D.cases / D.E_std
        out = D[["year", "fbd_region", "E_std", "SIR_crude", "SIR_std"]]
        f = os.path.join(ROOT, "02_패널", f"{T}_Estd.csv")
        if T == "MENTAL":   # 기존 파일 유지: 같은 코드로 재현한 값과 대조만
            old = pd.read_csv(f, encoding="utf-8-sig"); old["fbd_region"] = old.fbd_region.map(NFC)
            cmp = old.merge(out, on=["year", "fbd_region"], suffixes=("_old", "_new")); rel = (cmp.E_std_new / cmp.E_std_old - 1).abs().max()
            print(f"[38] MENTAL 재현 대조: {len(cmp)}행, E_std 최대 상대차 {rel:.2e} (기존 02_패널/MENTAL_Estd.csv 그대로 사용)"); assert rel < 1e-6
        else:
            out.to_csv(f, index=False, encoding="utf-8-sig")
        G = D.groupby("fbd_region").agg(cases=("cases", "sum"), E=("E", "sum"), Es=("E_std", "sum"), old=("older_adult_share_raw", "mean"))
        rc, _ = spearmanr(G.cases / G.E, G.old); rs, _ = spearmanr(G.cases / G.Es, G.old)
        SUMMARY.append((T, CODES[T], len(fb), round(rc, 3), round(rs, 3), round(float((D.E_std / D.E).min()), 3), round(float((D.E_std / D.E).max()), 3)))
        print(f"[38] {T}: 코드 {CODES[T] if len(CODES[T]) < 10 else str(CODES[T][0])+'~'+str(CODES[T][-1])} · 연령 비율 대체 {len(fb)}건 · SIR–고령 rho crude {rc:+.3f} → std {rs:+.3f} · E_std/E {SUMMARY[-1][5]}~{SUMMARY[-1][6]}")
    R = pd.concat(RATES); R["age10"] = pd.Categorical(R.age10, AGES, ordered=True)
    R.sort_values(["TAG", "year", "age10"])[["TAG", "year", "age10", "patients_sum", "denom_nat", "rate"]].to_csv(os.path.join(ROOT, "02_패널", "ALL_national_agerates_std.csv"), index=False, encoding="utf-8-sig")
    print("[38] 저장: 02_패널/<TAG>_Estd.csv(8개, MENTAL 기존 유지) · 02_패널/ALL_national_agerates_std.csv · 04_분석/00_298코드_질환매핑.csv")
    print(R[R.year == 2024].pivot(index="age10", columns="TAG", values="rate").mul(1e3).round(2).to_string())
