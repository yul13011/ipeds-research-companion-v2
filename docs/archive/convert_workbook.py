"""ONE-OFF, ALREADY RUN (2026-11-15). Kept only as a record of how the dictionary tables were first made.

It turned docs/dictionary_review.xlsx into the CSV tables in dictionary/, applying the owner's
decisions of 2026-11-15. Nothing reads this script or the workbook any more: the tables in
dictionary/ are the only source of conventions. Do not re-run it; it would overwrite later edits.
"""
import csv
import re
import sqlite3
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import config

OUT = ROOT / "dictionary"
OUT.mkdir(exist_ok=True)
wb = openpyxl.load_workbook(Path(__file__).with_name("dictionary_review.xlsx"), read_only=True, data_only=True)
db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
LOCAL = {s.upper(): l for l, s in db.execute("SELECT local_table, source_table FROM _tables")}


def tab(name):
    return [[("" if c is None else str(c).strip()) for c in r] for r in list(wb[name].iter_rows(values_only=True))[1:]]


def loc(ref):
    """'DRVGR2024.GBA6RTT' -> 'DRVGR.GBA6RTT'; 'HD2024' -> 'HD'."""
    table, _, var = ref.strip().partition(".")
    return LOCAL[table.upper()] + ("." + var if var else "")


def write(name, header, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


# ---------------------------------------------------------------- measures
codebook = {(t.upper(), v.upper()): (d or "", (ld or "").strip()) for t, v, d, ld in
            db.execute("SELECT TableName, VarName, DataType, LongDescription FROM VARTABLE")}
rows = []
for pri, table, var, title, fmt, per_school, also, plain, include in tab("Measures"):
    dtype, long_desc = codebook[(table.upper(), var.upper())]
    in_first = include.lower() if include else ("yes" if pri == "1" else "no")
    own_year = re.search(r"(\d{4}-\d{2})\s*$", title)          # the title names its own year (net price, tuition)
    rows.append([loc(table), var, title, long_desc, fmt, dtype, per_school, pri, in_first,
                 own_year.group(1) if own_year else "", plain, also])
write("measures.csv", ["table", "variable", "title", "long_description", "format", "data_type", "rows_per_school",
                       "priority", "in_first_version", "period", "plain_name", "synonyms"], rows)

# ---------------------------------------------------------------- terms (one row per reading and measure)
T = []


def term(name, words, always_ask="no", statement="", kind="measure"):
    def add(reading, measure="", shown_as="", default="no", default_for="", condition="", status="in use", note=""):
        T.append([name, words, kind, reading, shown_as or reading, measure, condition, default, default_for,
                  always_ask, statement, status, note])
    return add


a = term("graduation rate", "graduation rate; completion rate", statement="State which graduation rate was used.")
a("Bachelor's degree within six years", "DRVGR.GBA6RTT", default="yes", default_for="Four or more years")
a("Total cohort within 150% of normal time", "DRVGR.GRRTTOT", default="yes", default_for="At least 2 but less than 4 years")
a("Total cohort within 150% of normal time", "DRVGR.GRRTTOT", default="yes", default_for="Less than 2 years (below associate)")
a("Bachelor's degree within four years", "DRVGR.GBA4RTT")

a = term("net price", "net price", statement="State that the latest net price year is 2023-24.")
NP = "Average net price, students awarded grant or scholarship aid"
a("Students awarded grant or scholarship aid", "COST2_NETPRICE.NPIST2", NP, default="yes", note="Public schools report this field")
a("Students awarded grant or scholarship aid", "COST2_NETPRICE.NPGRN2", NP, default="yes", note="Private schools report this field")
NP4 = "Average net price, students awarded Title IV federal aid"
a("All students awarded Title IV federal aid", "COST2_NETPRICE.NPIS42", NP4, note="Public schools report this field")
a("All students awarded Title IV federal aid", "COST2_NETPRICE.NPT42", NP4, note="Private schools report this field")

a = term("enrollment", "enrollment; students; headcount")
a("Fall total headcount", "DRVEF.ENRTOT", default="yes")
a("Undergraduate fall enrollment", "DRVEF.EFUG")
a("Graduate fall enrollment", "DRVEF.EFGRAD")
a("12-month unduplicated headcount", "DRVEF12.UNDUP", note="Use only when the user says annual, 12-month or unduplicated")
a("Full-time equivalent fall enrollment", "DRVEF.FTE")

a = term("faculty", "faculty; how many faculty", always_ask="yes")
a("Instructional staff", "EAP.EAPTOT", condition="EAPCAT = 21000", status="pending owner approval",
  note="From version 1's Yale faculty check. Yale: 3,800")
a("All staff with faculty status", "EAP.EAPTOT", condition="EAPCAT = 10010", status="pending owner approval",
  note="From version 1's Yale faculty check. Yale: 5,735")

a = term("faculty salary", "faculty salary; average salary",
         statement="Full-time instructional staff, salary equated to nine months. Add the caveat about medical-school staff.")
a("All ranks", "DRVHR.SALTOTL", default="yes")
for var, rank in [("SalProf", "Professors"), ("SalAssc", "Associate professors"), ("SalAsst", "Assistant professors"),
                  ("SalInst", "Instructors"), ("Sallect", "Lecturers"), ("SALNRNK", "No academic rank")]:
    a("By rank", "DRVHR." + var, rank)

a = term("cost", "cost; cost of attendance; how much does it cost")
a("Cost profile", "DRVCOST.CINSON", "Total price, in-state students living on campus", default="yes")
a("Cost profile", "DRVCOST.COTSON", "Total price, out-of-state students living on campus", default="yes")
a("Cost profile", "DRVCOST.TUFEYR3", "Tuition and fees", default="yes")
a("Cost profile", "COST2_NETPRICE.NPIST2", NP, default="yes")
a("Cost profile", "COST2_NETPRICE.NPGRN2", NP, default="yes")

a = term("tuition", "tuition")
a("Published tuition and fees, in-state or in-district rate", "DRVCOST.TUFEYR3", default="yes",
  note="Out-of-state tuition is in COST1")

a = term("retention", "retention; persistence")
a("Full-time retention rate", "EFD.RET_PCF", default="yes")
a("Part-time retention rate", "EFD.RET_PCP", note="Use when the user says part-time")

a = term("admission rate", "admission rate; acceptance rate; selectivity")
a("Percent admitted, total", "DRVADM.DVADM01", default="yes")

a = term("degrees", "degrees; degrees awarded")
for var, level in [("ASCDEG", "Associate's degrees"), ("BASDEG", "Bachelor's degrees"), ("MASDEG", "Master's degrees"),
                   ("DOCDEGRS", "Doctor's degrees, research/scholarship"), ("DOCDEGPP", "Doctor's degrees, professional practice")]:
    a("Degrees by level", "DRVC." + var, level, default="yes")

a = term("financial aid", "financial aid; aid", always_ask="yes")
a("Grant or scholarship aid, all undergraduates", "SFA.UAGRNTP")
a("Any financial aid, full-time first-time undergraduates", "SFA.ANYAIDP")

a = term("Pell", "Pell")
a("Percent of undergraduates awarded Pell grants", "SFA.UPGRNTP", default="yes")
a("Average Pell grant amount", "SFA.UPGRNTA")
a("Number of undergraduates awarded Pell grants", "SFA.UPGRNTN")

FORMS = [("1", "Public schools (GASB form)"), ("2", "Private nonprofit schools (FASB form)"), ("3", "For-profit schools")]
a = term("revenue", "revenue", statement="State the fiscal year. Finance is reported on three forms; a school has values on only one.")
for n, form in FORMS:
    a("Core revenues", f"DRVF.F{n}CORREV", default="yes", note=form)
a = term("expenses", "expenses; spending", statement="State the fiscal year. Finance is reported on three forms; a school has values on only one.")
for n, form in FORMS:
    a("Core expenses", f"DRVF.F{n}COREXP", default="yes", note=form)

a = term("endowment", "endowment")
a("Endowment assets at the end of the fiscal year", "F_F1A.F1H02", default="yes", note=FORMS[0][1])
a("Endowment assets at the end of the fiscal year", "F_F2.F2H02", default="yes", note=FORMS[1][1])
a("Endowment assets per FTE student", "DRVF.F1ENDMFT", note=FORMS[0][1])
a("Endowment assets per FTE student", "DRVF.F2ENDMFT", note=FORMS[1][1])

a = term("student-faculty ratio", "student-faculty ratio")
a("Student-to-faculty ratio", "EFD.STUFACR", default="yes")

a = term("enrollment by major", "enrollment by major; enrollment by program; enrollment by field",
         statement="IPEDS collects fall enrollment by major for nine selected fields only: education, engineering, "
                   "biological sciences, mathematics, physical sciences, business, law, dentistry and medicine. "
                   "For other majors, degrees awarded by program is the nearest measure.")
a("Fall enrollment in nine selected fields", "EFCP.EFTOTLT", default="yes")

a = term("peers", "peers; peer institutions", always_ask="yes", kind="group")
a("The school's own IPEDS comparison group", condition="comparison group", note="Available for 2,845 of 6,072 schools")
a("Schools in the same state and sector", condition="same state and sector")
a("Schools you name", condition="user named")

a = term("selective", "selective; highly selective; elite schools", always_ask="yes", kind="group",
         statement="Selective is not an IPEDS category. State the admission-rate cut-off used.")
for cut in (10, 25, 50):
    a(f"Admission rate under {cut}%", "DRVADM.DVADM01", condition=f"< {cut}")

write("terms.csv", ["term", "words", "kind", "reading", "shown_as", "measure", "condition", "is_default", "default_for",
                    "always_ask", "statement", "status", "note"], T)

# ---------------------------------------------------------------- school groups
G = []
HEAD = ["group", "kind", "words", "table", "column", "codes", "statement", "caveat", "status", "priority", "note"]


def group(name, kind, words="", table="", column="", codes="", statement="", caveat="", status="in use", priority="1", note=""):
    G.append([name, kind, words, table, column, codes, statement, caveat, status, priority, note])


BEA = {"0": "U.S. service schools", "1": "New England", "2": "Mid East", "3": "Great Lakes", "4": "Plains",
       "5": "Southeast", "6": "Southwest", "7": "Rocky Mountains", "8": "Far West", "9": "Other U.S. jurisdictions"}
CENSUS = {"Northeast": "CT, ME, MA, NH, RI, VT, NJ, NY, PA",
          "Midwest": "IL, IN, MI, OH, WI, IA, KS, MN, MO, NE, ND, SD",
          "South": "DE, DC, FL, GA, MD, NC, SC, VA, WV, AL, KY, MS, TN, AR, LA, OK, TX",
          "West": "AZ, CO, ID, MT, NV, NM, UT, WY, AK, CA, HI, OR, WA"}
SIZE = {"1": ("Very small", "very small schools", "Fewer than 1,000 students"),
        "3": ("Mid-sized", "mid-sized schools", "5,000 to 9,999 students"),
        "5": ("Very large", "very large schools", "20,000 students or more")}
CONF = "CONFNO1, CONFNO2, CONFNO3, CONFNO4"
CONF_NOTE = "Matches a school whose football, basketball, baseball or track conference is this one"
DROP_WORDS = {"the South", "state schools", "universities", "public universities", "private colleges"}
done = set()

for pri, kind, words, ref, code, label, n, note, _ in tab("School groups"):
    words = "; ".join(w for w in (x.strip() for x in words.split(";")) if w and w not in DROP_WORDS)
    if "PROPOSED" in label:                                     # B1: replaced by Census regions below
        continue
    if kind == "Not a ready-made IPEDS category":
        if "Hispanic" in words or "minority-serving" in words or "women" in words or "AAU" in words:
            words = words.replace("; Seven Sisters", "")       # Seven Sisters is a member list in use
            group(words.split(";")[0].strip(), "none", words, statement="IPEDS has no flag for this group.", status="decline")
        continue                                                # flagships: member list; selective: terms; others: no rule
    table, _, column = (loc(ref.split(";")[0]) if ref != "none" else "").partition(".")
    if column == "OBEREG":
        group(BEA[code], "column", words, table, column, code, label + " (BEA region)")
    elif column == "STABBR":
        group("State", "any value", 'a state by name or abbreviation', table, column, "any", "State")
    elif column == "CITY":
        group("City", "any value", "a city by name", "HD", "CITY", "any", "City", priority=pri)
        group("County", "any value", "a county by name", "HD", "COUNTYNM", "any", "County", priority=pri)
    elif column == "CBSA":
        group("Metro area", "any value", "a metro area by name", table, column, "any", "Core Based Statistical Area", priority=pri)
    elif column == "F1SYSNAM":
        group("System", "any value", "a system by name", table, column, "any", "Multi-institution or multi-campus system")
    elif column == "RELAFFIL":
        if "RELAFFIL" not in done:                              # B17: all 63 affiliations, not six
            group("Religious affiliation", "any value", "a religious affiliation by name", table, column, "any",
                  "Religious affiliation", priority=pri)
            done.add("RELAFFIL")
    elif column == "CONFNO1":
        if "98 conferences" in code:
            group("Athletic conference", "any value", "an athletic conference by name", table, CONF, "any",
                  "NCAA/NAIA athletic conference", note=CONF_NOTE)
        elif "Ivy" not in label:                                # Ivy League is a member list (owner decision)
            group(label, "column", words, table, CONF, code, label, caveat="Membership as reported for 2024-25; conferences realign", note=CONF_NOTE)
    elif column == "INSTSIZE":
        if code in SIZE:
            name, w, statement = SIZE[code]
            group(name, "column", w, table, column, code, statement + " (IPEDS size category, total enrollment)")
    elif column == "CONTROL":
        statement = label + ('. "Private" alone means private nonprofit.' if code == "2" else "")
        group(label, "column", words, table, column, code, statement)
    elif column == "SECTOR":
        words = words + ("; state schools" if code == "1" else "")
        statement = label + ('. "State schools" means public four-year.' if code == "1" else "")
        caveat = ("Community colleges that now award bachelor's degrees are classified by IPEDS as four-year, "
                  "so they are not in this group.") if code == "4" else ""
        group(label, "column", words, table, column, code, statement, caveat)
    elif table == "CUSTOMCGIDS":
        group("IPEDS comparison group", "per school", words, table, "CGUNITID", "", label, caveat=note)
    elif column == "DFRCGID":
        group("NCES comparison group", "per school", words, table, column, "", label, caveat=note, priority=pri)
    elif column == "C21BASIC":
        statement = label + " (Carnegie 2021 basic classification)"
        if code == "21":
            statement += '. "Liberal arts colleges" has no exact IPEDS category; this is the stand-in.'
        if code in ("15", "16"):
            words = ""                                          # B8: R1/R2 default to 2025; the 2021 rows are found by name
            statement += ". Used for R1 and R2 only when the user asks for the 2021 definition."
        group(label + (" (2021)" if code in ("15", "16", "33") else ""), "column", words, table, column, code, statement, priority=pri)
    else:
        codes = code
        statement = label
        if column in ("CARNEGIEIC", "CARNEGIESAEC", "CARNEGIERSCH"):
            statement += " (Carnegie 2025)"
        name = label if kind.startswith(("Carnegie", "Degree level", "Level")) or not words else words.split(";")[0].strip()
        group(name, "column", words, table, column, codes, statement, priority=pri)

for name, states in CENSUS.items():                             # B1, B2
    group(name, "column", "the " + name, "HD", "STABBR", states, f"{name} (Census region): {states}")
group("Small", "column", "small; small schools", "HD", "INSTSIZE", "1, 2", "Fewer than 5,000 students (IPEDS size category, total enrollment)")
group("Large", "column", "large; big; large schools", "HD", "INSTSIZE", "4, 5", "10,000 students or more (IPEDS size category, total enrollment)")

US = ("AL, AK, AZ, AR, CA, CO, CT, DE, DC, FL, GA, HI, ID, IL, IN, IA, KS, KY, LA, ME, MD, MA, MI, MN, MS, MO, MT, NE, NV, "
      "NH, NJ, NM, NY, NC, ND, OH, OK, OR, PA, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI, WY")
UNIVERSE = "National universe"
U_STATEMENT = "U.S. institutions: the 50 states and DC, Title IV participating, excluding administrative offices"
group(UNIVERSE, "universe", "", "HD", "STABBR", US, U_STATEMENT, note="All rows of this group must hold. 5,626 schools; matches NCES")
group(UNIVERSE, "universe", "", "HD", "PSET4FLG", "1, 3", U_STATEMENT)
group(UNIVERSE, "universe", "", "HD", "SECTOR", "1, 2, 3, 4, 5, 6, 7, 8, 9, 99", U_STATEMENT)

group("Ivy League", "member list", "Ivy League; the Ivies", statement="The eight Ivy League schools")
group("Ivy Plus", "member list", "Ivy Plus", statement="The eight Ivy League schools plus MIT, Stanford, Johns Hopkins and the University of Chicago")
group("Seven Sisters", "member list", "Seven Sisters", statement="Barnard, Bryn Mawr, Mount Holyoke, Smith, Vassar and Wellesley")
group("Flagship universities", "member list", "flagship universities; state flagships; flagships",
      statement="Flagship is not an IPEDS category. This is a hand-kept list of 53 state flagship universities.",
      status="in use, list under owner review")
write("school_groups.csv", HEAD, G)

# ---------------------------------------------------------------- group members and nicknames (from version 1)
sys.path.insert(0, str(ROOT.parent / "agent-redesign" / "prototype"))
NAMES = dict(db.execute("SELECT UNITID, INSTNM FROM HD"))
IVY = [130794, 166027, 186131, 217156, 190150, 215062, 182670, 190415]
LISTS = {"Ivy League": IVY, "Ivy Plus": IVY + [166683, 243744, 162928, 144050],
         "Seven Sisters": [189097, 211273, 166939, 167835, 197133, 168218],
         "Flagship universities": [
             100751, 102614, 104179, 106397, 110635, 126614, 129020, 130943, 134130, 139959, 141574, 142285, 145637,
             151351, 243780, 153658, 155317, 157085, 159391, 161253, 163286, 166629, 170976, 174066, 176017, 178396,
             180489, 181464, 182290, 183044, 186380, 187985, 196088, 196097, 199120, 200280, 204796, 207500, 209551,
             214777, 217484, 218663, 219471, 221759, 228778, 228723, 230764, 231174, 234076, 236948, 238032, 240444, 240727]}
write("group_members.csv", ["group", "unitid", "name"], [[g, u, NAMES[u]] for g, ids in LISTS.items() for u in ids])

NICK = {'yale': (130794, 'direct'), 'harvard': (166027, 'direct'), 'princeton': (186131, 'direct'),
        'dartmouth': (182670, 'direct'), 'upenn': (215062, 'direct'), 'mit': (166683, 'direct'), 'ucla': (110662, 'direct'),
        'brown': (217156, 'alias'), 'columbia': (190150, 'alias'), 'penn': (215062, 'alias'),
        'university of pennsylvania': (215062, 'alias'), 'cornell': (190415, 'alias'),
        'umich': ('university of michigan', 'picker'), 'uw madison': ('university of wisconsin madison', 'picker'),
        'uconn': ('university of connecticut', 'picker'), 'umass': ('university of massachusetts', 'picker'),
        'cal': ('university of california berkeley', 'picker'), 'berkeley': ('university of california berkeley', 'picker'),
        'ut austin': ('university of texas austin', 'picker'), 'georgia tech': ('georgia institute of technology', 'picker'),
        'virginia tech': ('virginia polytechnic institute', 'picker'), 'ole miss': ('university of mississippi', 'picker'),
        'penn state': ('pennsylvania state university', 'picker')}
write("school_nicknames.csv", ["nickname", "kind", "unitid", "name", "search_phrase"],
      [[k, kind, v if kind != "picker" else "", NAMES[v] if kind != "picker" else "", v if kind == "picker" else ""]
       for k, (v, kind) in NICK.items()])

# ---------------------------------------------------------------- rates
rows = []
for rate, ready, num, den, cat, national, nces, status, _ in tab("Rates and counts"):
    def split(expr):
        m = re.match(r"(\S+)(?: where \w+=(\d+))?$", expr)
        return loc(m.group(1)), m.group(2) or ""
    (n_ref, n_code), (d_ref, d_code) = split(num), split(den)
    if "Outcome Measures" in rate:                              # C3: the total row is OMCHRT 50
        n_code = d_code = "50"
    rows.append([rate, loc(ready) if ready else "", n_ref, d_ref, "" if cat == "none" else cat, n_code, d_code, nces, status])
write("rates.csv", ["rate", "rate_measure", "numerator", "denominator", "category_column", "numerator_code",
                    "denominator_code", "nces_figure", "status"], rows)

# ---------------------------------------------------------------- category codes, year meaning, outside IPEDS
write("category_codes.csv", ["table", "column", "code", "label", "role"],
      [[loc(t), c, code, label, role] for t, c, code, label, role, _ in tab("Category codes")])

rows = []
for table, title, period, kind, _ in tab("Year meaning"):
    if kind == "needs review":                                  # C1: the two salary tables
        kind, period = "academic year", "Academic year 2024-25"
    rows.append([loc(table), 2024, kind, period, title])
write("year_meaning.csv", ["table", "year", "kind", "period", "title"], rows)

rows = []
for topic, example, in_ipeds, say, pointer, _ in tab("Outside IPEDS"):
    if topic.startswith("Enrollment by major"):                 # C5: IPEDS does collect it; now a term
        continue
    if topic.startswith("Faculty salary by academic field"):    # C4
        say, pointer = "IPEDS has salaries by rank and gender, not by field.", ""
    if pointer.lower().startswith(("none", "no federal source")):
        pointer = ""
    rows.append([topic, example, in_ipeds, say, pointer])
write("outside_ipeds.csv", ["topic", "example_wording", "in_ipeds", "what_to_say", "pointer"], rows)

# ---------------------------------------------------------------- special codes (label rules moved from build/, plus A4 and A5)
rows = []
SHOWN = {"-1": "Not reported", "-2": "Not applicable", "-3": "Not available", "-9": "Not active"}
with open(ROOT / "build" / "special_code_labels.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        note = r["note"].replace(". Awaiting owner decision", "").replace("Awaiting owner decision", "")
        rows.append(["codebook label", "", "", r["code"], r["label"], r["decision"],
                     SHOWN[r["code"]] if r["decision"] == "missing" else "", note])
BY_COLUMN = [("HD", "F1SYSNAM", "-2", "School is not part of a system"), ("HD", "F1SYSNAM", "-1", ""),
             ("HD", "CLOSEDAT", "-2", "School has not closed"), ("HD", "OPEID", "-2", ""), ("HD", "EIN", "-1", ""),
             ("COST1", "PRGMOFR", "-2", "Number of programs offered"), ("HD", "NEWID", "-2", "No merged-school ID")]
BY_COLUMN += [("FLAGS", c, "-2", "No parent institution for this survey component") for c in
              ["IDX_C", "IDX_E12", "IDX_COS", "IDX_SFA", "IDX_GR", "IDX_GR2", "IDX_OM", "IDX_ADM", "IDX_HR", "IDX_EF", "IDX_F", "IDX_AL"]]
for table, column, code, note in BY_COLUMN:
    rows.append(["table and column", table, column, code, "", "missing", SHOWN[code], note])
write("special_codes.csv", ["applies_by", "table", "column", "code", "label", "decision", "shown_as", "note"], rows)
