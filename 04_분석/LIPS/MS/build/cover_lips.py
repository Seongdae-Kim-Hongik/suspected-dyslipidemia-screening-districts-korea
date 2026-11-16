import os, re, datetime, subprocess
from docx import Document
from docx.shared import Pt, Cm
import content_lips as C
from build_jcl_lips import TITLE, ZENODO, ADDRESS
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(HERE), "out")
N = C.N; W = dict(l.split("=") for l in open(os.path.join(OUT, "wordcount_jcl.txt")).read().split()); th = C.th; tc = C.tc
assert ZENODO.startswith("10.5281/zenodo.")
_d = datetime.date.today(); cl = [f"{_d:%B} {_d.day}, {_d.year}", "The Editor-in-Chief", "Journal of Clinical Lipidology", "",
      "Dear Editor,",
      f"Please find enclosed the manuscript entitled \"{TITLE}\" by Seongdae Kim, for consideration as an Original Article in the Journal of Clinical Lipidology.",
      f"Korea's national general health screening labels every attendee whose lipid results exceed the judgement criteria and who is not already treated as having suspected dyslipidemia, the point at which untreated dyslipidemia is found. Using 7 years of screening statistics under the current criteria for all {N['n_districts']} Korean districts ({N['cases_total_m']:.1f} million suspected judgements, 2018-2024), sex- and age-standardized expected counts, and Bayesian spatio-temporal models, the study shows that suspected dyslipidemia is moderately more common in southwestern districts and less common in the inland east, with a stable ranking. District counts rose with screening uptake, an association that held with space-time interactions and within districts and had the opposite direction for dyslipidemia already under treatment, consistent with case finding. Walking and moderate physical activity were not associated, and a positive association with public sports facilities did not withstand province-by-year effects.",
      "The work fits the journal's interest in the detection and management of dyslipidemia in clinical and public health practice: it shows that district counts of untreated dyslipidemia found at screening partly reflect how many people screening reaches, which matters for how such counts are used to plan follow-up and treatment.",
      "The manuscript is original research, has not been published previously, and is not under consideration for publication elsewhere; the author has approved its submission.",
      f"The text contains {th(int(W['body_words']))} words, with an abstract of {int(W['abstract_words'])} words, two tables, two figures, and {W['refs']} references. Highlights and supplementary material are provided. The analysis code is openly available on Zenodo (https://doi.org/{ZENODO}).",
      "Thank you for considering this manuscript.", "", "Sincerely,", "",
      "Seongdae Kim, PhD", ADDRESS, "Email: kimsd@hongik.ac.kr"]
d = Document(); st = d.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11); st.paragraph_format.space_after = Pt(4); st.paragraph_format.line_spacing = 1.0
for s in d.sections: s.page_width, s.page_height = Cm(21), Cm(29.7); s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.54)
gap = False
for t in cl:
    if t == "": gap = True; continue
    p = d.add_paragraph(t)
    if gap: p.paragraph_format.space_before = Pt(10); gap = False
d.core_properties.author = "Seongdae Kim"; d.core_properties.last_modified_by = "Seongdae Kim"; d.core_properties.title = "Cover Letter"; d.core_properties.comments = ""
fp = os.path.join(OUT, "Cover_Letter.docx"); d.save(fp)
subprocess.run(["/opt/homebrew/bin/soffice", "--headless", "-env:UserInstallation=file:///tmp/lo_lips_cl", "--convert-to", "pdf", "--outdir", OUT, fp], capture_output=True)
txt = subprocess.run(["pdftotext", fp.replace(".docx", ".pdf"), "-"], capture_output=True, text=True).stdout
assert not re.search(r"\b(we|our|us|I)\b", txt) and "—" not in txt and not re.search(r"(?i)funding|competing|overlap|previously submitted|Chun|reviewer", txt), "문체·금지 항목"
pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", fp.replace(".docx", ".pdf")], capture_output=True, text=True).stdout).group(1)); assert pages == 1, pages
open(os.path.join(OUT, "Cover_Letter_paste.txt"), "w").write("\n\n".join(t for t in cl if t))
print("saved", fp)
