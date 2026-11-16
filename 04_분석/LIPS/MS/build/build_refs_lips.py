import json, os, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__)); AN = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LT = json.load(open(os.path.join(AN, "LIPT/MS/build/refs_lipt.json"))); H = json.load(open(os.path.join(AN, "HCUV/MS/build/refs_hcuv.json"))); A = json.load(open(os.path.join(AN, "HTND/MS_AJPM/build/refs_htnd.json")))
PM = {"ncdrisc2020repositioning": 32493750 if False else None}
PM = {"lee2014serum": 24572249, "han2021regional2": 33440700, "ahn2015treatment": 26339166, "suh2017impact": 28886857, "cakmak2024association": 39267049,
      "lee2021objectively": 33672927, "rimm1999moderate": 10591709, "craig1989cigarette": 2496857, "vekic2019obesity": 30447223}
FROM_LT = ["ncdrisc2020repositioning", "ctt2010efficacy", "kwon2025dyslipidemia", "lee2025national", "rhee2019guidelines", "cheolseong2017data", "han2021regional",
           "kodama2007effect", "smart2025effect", "inskip1983methods", "kang2015korea", "riebler2016intuitive", "simpson2017penalising", "rue2009approximate", "knorrheld2000bayesian",
           "steegen2016increasing", "dupont2022spatial", "lipsitch2010negative", "vanderweele2017sensitivity", "bell2015explaining", "morgenstern1995ecologic", "vonelm2007strengthening",
           "heidari2016sex", "web:rcore2026"]
FROM_H = ["besag1991bayesian", "gelman2014understanding", "ord1995local"]
R = {}
ids = ",".join(str(v) for v in PM.values())
d = json.loads(urllib.request.urlopen("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + urllib.parse.urlencode(dict(db="pubmed", id=ids, retmode="json")), timeout=60).read())["result"]
for k, p in PM.items():
    x = d[str(p)]; doi = next((a["value"] for a in x.get("articleids", []) if a["idtype"] == "doi"), "")
    au = [a["name"] for a in x.get("authors", []) if a.get("authtype") == "Author"]
    R[k] = dict(type="journal", authors=au, title=x["title"].rstrip("."), journal=x["source"], year=int(x["pubdate"][:4]), vol=x.get("volume", ""), issue=x.get("issue", ""),
                pages=x.get("pages", ""), doi=doi, pmid=str(p), verified="PubMed esummary 2026-11-17")
for k in FROM_LT: R[k] = dict(LT[k]); R[k].setdefault("verified", "verified earlier reference set")
for k in FROM_H: R[k] = dict(H[k]); R[k].setdefault("verified", "verified earlier reference set")
for k, j in {"besag1991bayesian": "Ann Inst Stat Math", "gelman2014understanding": "Stat Comput", "ord1995local": "Geogr Anal"}.items(): R[k]["journal"] = j
R["han2021regional2"]["pages"] = "538"; R["lee2021objectively"]["pages"] = "1861"
R["web:mois2026population"] = dict(A["web:mois2026population"], accessed="November 17, 2026")
R["web:yonhap2023screening"] = dict(type="web", authors="Yonhap News Agency", title="Dyslipidemia rose 2.4-fold in 5 years; health screening interval should be shortened to 2 years (in Korean). Republished by the Ministry of Health and Welfare Bokjiro portal, October 1, 2023", url="https://www.bokjiro.go.kr/ssis-tbu/cms/pc/news/news/1305603_1114.html", year=2023, accessed="November 17, 2026")
R["web:rcore2026"]["accessed"] = "November 17, 2026"
R["web:kosis2026screening"] = dict(type="web", authors="National Health Insurance Service", title="National general health screening statistics: examinees with judgement results (DT_35007_N098), suspected disease by type (DT_35007_N103), national examinees and suspected disease by sex and age (DT_35007_N099, DT_35007_N104), and first-stage screening targets and attendees (DT_35007_N001), 2011-2024. Korean Statistical Information Service", url="https://kosis.kr", year=2026, accessed="November 17, 2026")
for k, r in R.items():
    if r.get("type") == "journal": assert r.get("doi") or r.get("pmid"), k
json.dump(R, open(os.path.join(HERE, "refs_lips.json"), "w"), ensure_ascii=False, indent=1)
for k, r in R.items(): print(k, "|", r.get("journal"), r.get("year"), r.get("vol"), r.get("pages"), r.get("doi"), "|", (r["authors"][:2] if isinstance(r["authors"], list) else r["authors"]))
print(len(R))
