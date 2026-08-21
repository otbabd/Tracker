"""Generate a synthetic bank-shaped position export for testing the org chart.

Produces sample-org.csv (and an .xlsx twin) with grades, functions, the three
succession/regulatory flags, vacancies, Arabic names, and the kinds of broken
rows a real HRIS export contains.
"""
import csv
import random
import sys

random.seed(11)

AR_FIRST = ["أحمد", "نورة", "خالد", "سارة", "فيصل", "ريم", "عبدالله", "لطيفة",
            "سلطان", "هند", "ماجد", "دانة"]
AR_LAST = ["الحربي", "القحطاني", "الدوسري", "العتيبي", "الشمري", "الغامدي",
           "السبيعي", "المطيري", "الزهراني"]
EN_FIRST = ["Omar", "Layla", "Yusuf", "Huda", "Tariq", "Dana", "Sami", "Rana", "Bilal",
            "Maya", "Adel", "Noor", "Karim", "Salma", "Nasser", "Aisha", "Rami", "Jana",
            "Waleed", "Lina", "Hassan", "Mona", "Ziad", "Amal"]
EN_LAST = ["Nasser", "Haddad", "Karim", "Mansour", "Aziz", "Rashed", "Farouk", "Idris",
           "Osman", "Younes", "Saleh", "Baker", "Qureshi", "Darwish", "Fahmy", "Khan",
           "Siddiqui", "Bakr"]

FUNCTIONS = {
    "Retail Banking":    ["Branch Network", "Cards & Payments", "Wealth Management", "Customer Experience"],
    "Corporate Banking": ["Large Corporate", "SME Banking", "Trade Finance", "Transaction Banking"],
    "Risk":              ["Credit Risk", "Market Risk", "Operational Risk", "Risk Analytics"],
    "Compliance":        ["AML & Sanctions", "Regulatory Affairs", "Financial Crime"],
    "Internal Audit":    ["Audit - Banking", "Audit - Technology"],
    "Technology":        ["Core Banking", "Digital Channels", "Infrastructure", "Cybersecurity", "Data & Analytics"],
    "Finance":           ["Financial Control", "Treasury", "Financial Planning", "Tax"],
    "Operations":        ["Payments Operations", "Trade Operations", "Branch Operations"],
    "Human Resources":   ["Talent Acquisition", "HR Operations", "Learning & Development"],
    "Legal":             ["Corporate Legal", "Litigation"],
}
LOCS = ["Riyadh", "Riyadh", "Riyadh", "Jeddah", "Jeddah", "Dammam", "Khobar", "Remote"]

# The full ladder: Group > Division > Department > Unit > Sub-unit > Section.
# Legal entities within the group, so the top rung carries more than one value —
# a column with a single value everywhere is a redundant level and the tool
# skips it.
GROUPS = {
    "Technology": "Example Digital",
    "Human Resources": "Example Shared Services",
    "Operations": "Example Shared Services",
}
DEFAULT_GROUP = "Example Bank"

# Front / middle / back office by function — the operating-model read.
JOB_TYPE = {
    "Retail Banking": "Front office", "Corporate Banking": "Front office",
    "Risk": "Middle office", "Compliance": "Middle office", "Finance": "Middle office",
    "Legal": "Middle office", "Internal Audit": "Middle office",
    "Technology": "Back office", "Operations": "Back office",
    "Human Resources": "Back office", "Executive": "Front office",
}

# Branch network, for the retail branches only.
BRANCHES = [f"BR-{n:03d} {city}" for n, city in enumerate(
    ["Riyadh Olaya", "Riyadh Malaz", "Riyadh Sahafa", "Jeddah Tahlia", "Jeddah Rawdah",
     "Dammam Corniche", "Khobar Rakah", "Makkah Aziziyah", "Madinah Central",
     "Abha Downtown", "Tabuk Central", "Buraidah Central"], start=1)]

TALENT_POOLS = ["Emerging Leaders", "Future Executives", "Specialist Bench", "Saudi Graduates"]

COURSES = [
    ("AML & Sanctions Awareness", "Annual"),
    ("Anti-Fraud Fundamentals", "Annual"),
    ("Cyber Security Awareness", "Annual"),
    ("SAMA Consumer Protection", "Annual"),
    ("Code of Conduct", "Annual"),
    ("Credit Risk Essentials", "Every 2 years"),
    ("Operational Risk Management", "Every 2 years"),
    ("IFRS 9 Update", "Annual"),
    ("Leading Teams", "Once"),
    ("Data Privacy", "Annual"),
]
READY = ["Ready now", "Ready 1-2 years", "Ready 3+ years"]
FAMILY = {"G17": "Executive", "G16": "Executive", "G15": "Leadership",
          "G14": "Leadership", "G13": "Management", "G12": "Management"}

# How the bank classifies each function — the "function type" column.
FUNCTION_TYPE = {
    "Retail Banking": "Business (1st line)", "Corporate Banking": "Business (1st line)",
    "Operations": "Business (1st line)", "Risk": "Control (2nd line)",
    "Compliance": "Control (2nd line)", "Finance": "Control (2nd line)",
    "Legal": "Control (2nd line)", "Internal Audit": "Assurance (3rd line)",
    "Technology": "Enabling", "Human Resources": "Enabling", "Executive": "Governance",
}

MANDATES = {
    "Retail Banking": "Runs the branch network, cards, payments and wealth propositions for individual customers, owning revenue, service quality and channel migration.",
    "Corporate Banking": "Serves corporate and SME clients across lending, trade finance and transaction banking, owning the corporate credit portfolio and relationship coverage.",
    "Risk": "Owns the bank-wide risk framework: credit, market and operational risk appetite, limit setting and stress testing, and independent challenge of first-line decisions. Reports the risk position to the Board Risk Committee.",
    "Compliance": "Ensures adherence to SAMA regulations and internal policy. Owns AML/CFT, sanctions screening, regulatory reporting and the non-objection process for controlled functions.",
    "Internal Audit": "Provides independent assurance to the Audit Committee over the effectiveness of governance, risk management and internal control.",
    "Technology": "Delivers and runs core banking, digital channels, infrastructure and cybersecurity. Accountable for platform availability, change delivery and technology risk.",
    "Finance": "Owns financial control, treasury, planning and tax. Produces statutory and regulatory reporting and manages liquidity and capital.",
    "Operations": "Processes payments, trade and branch operations with accountability for throughput, accuracy and operational loss.",
    "Human Resources": "Owns workforce strategy, talent acquisition, learning, Saudization targets and the succession framework for critical and controlled roles.",
    "Legal": "Advises on corporate legal matters, contracts and litigation, and owns legal risk.",
}

rows = []
seq = 0


def nid():
    global seq
    seq += 1
    return f"POS{seq:05d}"


def person():
    if random.random() < 0.35:
        return f"{random.choice(AR_FIRST)} {random.choice(AR_LAST)}"
    return f"{random.choice(EN_FIRST)} {random.choice(EN_LAST)}"


names_pool = [person() for _ in range(400)]


def add(pid, mgr, title, grade, fn, dept, vac_p=0.08, crit=None, sama=None,
        unit="", sub_unit="", section="", branch=""):
    vacant = random.random() < vac_p
    if crit is None:
        crit = grade in ("G17", "G16", "G15") or (grade == "G14" and random.random() < 0.4)
    if sama is None:
        sama = grade in ("G17", "G16") or (
            grade == "G15" and fn in ("Risk", "Compliance", "Finance", "Internal Audit"))
    has_succ = (random.random() < 0.58) if crit else (random.random() < 0.18)
    rows.append({
        "Position ID": pid,
        "Manager ID": mgr,
        "Job Title": title,
        "Employee Name": "" if vacant else person(),
        "Grade": grade,
        "Job Code": f"JC{random.randint(1000, 9999)}",
        "Job Family": FAMILY.get(grade, "Professional"),
        "Function": fn,
        "Group": GROUPS.get(fn, DEFAULT_GROUP),
        # The division rung of the ladder is the function itself — Retail
        # Banking, Risk, Compliance. Most HR exports carry both columns with
        # the same value, and the org unit list is keyed on these names.
        "Division": fn,
        "Department": dept,
        "Unit": unit,
        "Sub-unit": sub_unit,
        "Section": section,
        "Branch": branch,
        "Location": random.choice(LOCS),
        "Employment Type": "Full-time" if random.random() < 0.93 else "Contractor",
        "Position Status": "Vacant" if vacant else "Filled",
        "FTE": "1" if random.random() < 0.94 else "0.5",
        "Cost Center": f"CC-{random.randint(1000, 1060)}",
        "Function Type": FUNCTION_TYPE.get(fn, ""),
        "Job Type": JOB_TYPE.get(fn, ""),
        "Pay Basis": ("Incentive" if JOB_TYPE.get(fn) == "Front office" and random.random() < 0.75
                      else "Bonus" if grade in ("G17", "G16", "G15", "G14", "G13")
                      else random.choice(["Bonus", "Fixed", "Fixed"])),
        "Talent Pool": (random.choice(TALENT_POOLS)
                        if random.random() < (0.30 if grade in ("G15", "G14", "G13") else 0.08)
                        else ""),
        "Work Email": "" if vacant else f"user{seq}@examplebank.com.sa",
        "Hire Date": f"{random.randint(2008, 2025)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        "Nationality": random.choice(["Saudi"] * 7 + ["Egyptian", "Indian", "Jordanian", "British"]),
        "Critical Role": "Yes" if crit else "No",
        "SAMA Non-Objection Role": "Yes" if sama else "No",
        "Successor Identified": "Yes" if has_succ else "No",
        "Successor Name": random.choice(names_pool) if has_succ else "",
        "Successor Readiness": random.choice(READY) if has_succ else "",
    })
    return pid


ceo = add(nid(), "", "Chief Executive Officer", "G17", "Executive", "Executive Office",
          vac_p=0, crit=True, sama=True)

for fn, depts in FUNCTIONS.items():
    top = f"Head of {fn}" if fn in ("Legal", "Internal Audit") else f"Chief {fn} Officer"
    head = add(nid(), ceo, top, "G16", fn, depts[0], vac_p=0.05)
    for dept in depts:
        d = add(nid(), head, f"Head of {dept}", "G15", fn, dept, vac_p=0.06)
        for u_i in range(random.randint(2, 3)):
            unit = f"{dept} Unit {u_i + 1}"
            sm = add(nid(), d, f"Senior Manager {dept}", "G14", fn, dept, vac_p=0.07,
                     unit=unit)
            for s_i in range(random.randint(2, 4)):
                sub_unit = f"{unit} — Team {chr(65 + s_i)}"
                m = add(nid(), sm, f"Manager {dept}", "G13", fn, dept, vac_p=0.08,
                        unit=unit, sub_unit=sub_unit)
                for _ in range(random.randint(6, 12)):
                    section = f"{sub_unit} / Section {random.randint(1, 2)}"
                    branch = (random.choice(BRANCHES)
                              if dept == "Branch Network" else "")
                    add(nid(), m,
                        random.choice(["Officer", "Senior Officer", "Analyst", "Senior Analyst",
                                       "Specialist", "Associate"]) + f" {dept}",
                        random.choice(["G9", "G10", "G10", "G11", "G12"]), fn, dept,
                        vac_p=0.11, crit=False, sama=False,
                        unit=unit, sub_unit=sub_unit, section=section, branch=branch)

# Defects a real export contains, so the repair path is exercised.
rows.append({**rows[50], "Position ID": nid(), "Manager ID": "POS99999",
             "Job Title": "Consultant - Orphaned", "Employee Name": "Ghost Row"})
a, b = nid(), nid()
rows.append({**rows[60], "Position ID": a, "Manager ID": b, "Job Title": "Loop A", "Employee Name": "Cycle One"})
rows.append({**rows[60], "Position ID": b, "Manager ID": a, "Job Title": "Loop B", "Employee Name": "Cycle Two"})
rows.append({**rows[70], "Job Title": "Duplicate Seat"})
rows.append({**rows[80], "Position ID": "", "Job Title": "No ID At All"})
selfref = nid()
rows.append({**rows[90], "Position ID": selfref, "Manager ID": selfref, "Job Title": "Self Referencing"})

cols = list(rows[0].keys())
with open("sample-org.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

# The companion org unit list: structure, classification and mandates, plus
# three units that exist on paper with nobody mapped to them.
unit_rows = [{
    "Org Unit": fn, "Parent Unit": "", "Unit Code": f"ORG-{100 + i * 10}",
    "Function Type": FUNCTION_TYPE.get(fn, ""), "Unit Head": "",
    "Unit Status": "Active", "Roles and Responsibilities": MANDATES.get(fn, ""),
} for i, fn in enumerate(FUNCTIONS)]

unit_rows += [
    {"Org Unit": "Data Governance Office", "Parent Unit": "Technology", "Unit Code": "ORG-310",
     "Function Type": "Control (2nd line)", "Unit Head": "TBA", "Unit Status": "Approved",
     "Roles and Responsibilities": "Approved in the 2026 structure to own data quality, lineage and the data catalogue. Recruitment has not started; no positions have been created yet."},
    {"Org Unit": "Climate Risk Unit", "Parent Unit": "Risk", "Unit Code": "ORG-230",
     "Function Type": "Control (2nd line)", "Unit Head": "TBA", "Unit Status": "Approved",
     "Roles and Responsibilities": "Established to meet SAMA climate-related financial disclosure expectations. Mandate approved, headcount pending Board approval."},
    {"Org Unit": "Shariah Audit", "Parent Unit": "Internal Audit", "Unit Code": "ORG-221",
     "Function Type": "Assurance (3rd line)", "Unit Head": "", "Unit Status": "Approved",
     "Roles and Responsibilities": "Independent assurance over Shariah compliance of products and processes."},
]

# Mandatory training, attached to job codes rather than to individual seats.
course_rows = []
seen_codes = {}
for r in rows:
    code = r.get("Job Code")
    if not code or code in seen_codes:
        continue
    seen_codes[code] = True
    required = [("Code of Conduct", "Annual"), ("Cyber Security Awareness", "Annual")]
    fn = r.get("Function", "")
    if fn in ("Retail Banking", "Corporate Banking", "Compliance", "Operations"):
        required.append(("AML & Sanctions Awareness", "Annual"))
    if fn in ("Risk", "Finance"):
        required.append(("IFRS 9 Update", "Annual"))
    if r.get("Grade") in ("G17", "G16", "G15", "G14", "G13"):
        required.append(("Leading Teams", "Once"))
    if random.random() < 0.3:
        required.append(random.choice(COURSES))
    for course, freq in required:
        course_rows.append({
            "Job Code": code, "Course": course,
            "Mandatory": "Yes", "Frequency": freq,
        })

with open("sample-courses.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(course_rows[0].keys()))
    w.writeheader()
    w.writerows(course_rows)

with open("sample-units.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(unit_rows[0].keys()))
    w.writeheader()
    w.writerows(unit_rows)

xlsx_path = sys.argv[1] if len(sys.argv) > 1 else None
if xlsx_path:
    import pandas as pd
    with pd.ExcelWriter(xlsx_path) as writer:
        pd.DataFrame(rows)[cols].to_excel(writer, sheet_name="Positions", index=False)
        pd.DataFrame(unit_rows).to_excel(writer, sheet_name="Org Units", index=False)
        pd.DataFrame(course_rows).to_excel(writer, sheet_name="Mandatory Courses", index=False)

print(f"{len(rows)} position rows, {len(cols)} columns; {len(unit_rows)} org units; "
      f"{len(course_rows)} course requirements")
