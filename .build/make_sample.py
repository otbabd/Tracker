"""Generate a synthetic bank-shaped position export for testing the org chart.

Produces sample-org.csv (and an .xlsx twin) with grades, functions, the three
succession/regulatory flags, vacancies, Arabic names, and the kinds of broken
rows a real HRIS export contains.

sample-units.csv is the approved structure the chart is built on — every group,
division and department except four left out on purpose, so reconciling the two
hierarchies has something true to find.
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

# The full ladder: Group > Division > Department > Unit > Sub-unit > Section.
#
# A group is the top block under the CEO, named after its discipline and headed
# by a C-level officer — Human Resources Group under the Chief Human Capital
# Officer. Divisions sit inside it, departments inside those. The CEO Office is
# the one entry on the top rung that is not a group.
STRUCTURE = {
    "CEO Office": ("Executive", "Chief Executive Officer", {
        "Strategy & Communications Division": ["Corporate Strategy", "Corporate Communications"],
    }),
    "Retail Banking Group": ("Retail Banking", "Chief Retail Banking Officer", {
        "Branch Network Division": ["Central Region Branches", "Western Region Branches",
                                    "Eastern Region Branches"],
        "Products & Cards Division": ["Cards & Payments", "Personal Finance",
                                      "Deposits & Liabilities"],
        "Wealth & Privilege Division": ["Wealth Management", "Privilege Banking"],
        "Customer Experience Division": ["Customer Experience", "Contact Centre"],
    }),
    "Corporate Banking Group": ("Corporate Banking", "Chief Corporate Banking Officer", {
        "Corporate Coverage Division": ["Large Corporate", "Mid Corporate"],
        "SME Banking Division": ["SME Coverage", "SME Products"],
        "Transaction Banking Division": ["Trade Finance", "Cash Management"],
    }),
    "Treasury & Investments Group": ("Treasury", "Chief Treasury Officer", {
        "Treasury Division": ["Money Market & FX", "Fixed Income"],
        "Investments Division": ["Proprietary Investments", "Investment Advisory"],
    }),
    "Risk Group": ("Risk", "Chief Risk Officer", {
        "Credit Risk Division": ["Corporate Credit Risk", "Retail Credit Risk",
                                 "Credit Administration"],
        "Market & Liquidity Risk Division": ["Market Risk", "Liquidity Risk"],
        "Operational Risk Division": ["Operational Risk", "Business Continuity"],
        "Risk Analytics Division": ["Risk Modelling", "IFRS 9 & Provisioning"],
    }),
    "Compliance Group": ("Compliance", "Chief Compliance Officer", {
        "Financial Crime Division": ["AML & Sanctions", "Fraud Prevention"],
        "Regulatory Compliance Division": ["Regulatory Affairs", "Compliance Monitoring"],
    }),
    "Internal Audit Group": ("Internal Audit", "Chief Audit Executive", {
        "Business Audit Division": ["Audit - Retail & Corporate", "Audit - Treasury"],
        "Technology Audit Division": ["Audit - Technology", "Audit - Data"],
    }),
    "Finance Group": ("Finance", "Chief Financial Officer", {
        "Financial Control Division": ["Financial Control", "Regulatory Reporting"],
        "Planning & Performance Division": ["Financial Planning", "Cost & Performance"],
        "Tax & Zakat Division": ["Tax & Zakat"],
    }),
    "Technology Group": ("Technology", "Chief Technology Officer", {
        "Core Banking Division": ["Core Banking Platform", "Payments Systems"],
        "Digital Channels Division": ["Mobile & Internet Banking", "Digital Onboarding"],
        "Infrastructure Division": ["Infrastructure & Cloud", "Service Desk"],
        "Cybersecurity Division": ["Security Operations", "Identity & Access"],
        "Data & Analytics Division": ["Data Engineering", "Business Intelligence"],
    }),
    "Operations Group": ("Operations", "Chief Operations Officer", {
        "Payments Operations Division": ["Local Payments", "International Payments"],
        "Trade & Corporate Operations Division": ["Trade Operations", "Corporate Service Delivery"],
        "Branch Operations Division": ["Branch Support", "Cash Operations"],
    }),
    "Human Resources Group": ("Human Resources", "Chief Human Capital Officer", {
        "Talent Acquisition Division": ["Talent Acquisition", "Saudization & Graduate Programmes"],
        "Talent & Performance Division": ["Performance Management", "Succession & Talent"],
        "Learning & Development Division": ["Learning & Development", "Leadership Academy"],
        "HR Operations Division": ["HR Services", "Payroll & Benefits"],
    }),
    "Legal Group": ("Legal", "General Counsel", {
        "Corporate Legal Division": ["Corporate Legal", "Contracts"],
        "Litigation & Recovery Division": ["Litigation", "Legal Recoveries"],
    }),
}

# One legal entity across the whole file. A column with a single value is a
# redundant nesting level, so it is not part of the ladder — it rides as an
# unrecognised column the tool keeps and shows on the position card.
LEGAL_ENTITY = "BSF"

LOCS = ["Riyadh", "Riyadh", "Riyadh", "Jeddah", "Jeddah", "Dammam", "Khobar", "Remote"]

# Front / middle / back office by group — the operating-model read.
JOB_TYPE = {
    "CEO Office": "Front office",
    "Retail Banking Group": "Front office", "Corporate Banking Group": "Front office",
    "Treasury & Investments Group": "Front office",
    "Risk Group": "Middle office", "Compliance Group": "Middle office",
    "Finance Group": "Middle office", "Legal Group": "Middle office",
    "Internal Audit Group": "Middle office",
    "Technology Group": "Back office", "Operations Group": "Back office",
    "Human Resources Group": "Back office",
}

# The branch network hangs off the three regional departments, not off the
# ladder — a branch runs across the organisation rather than inside it.
BRANCH_REGIONS = {
    "Central Region Branches": ["BR-001 Riyadh Olaya", "BR-002 Riyadh Malaz",
                                "BR-003 Riyadh Sahafa", "BR-004 Buraidah Central"],
    "Western Region Branches": ["BR-005 Jeddah Tahlia", "BR-006 Jeddah Rawdah",
                                "BR-007 Makkah Aziziyah", "BR-008 Madinah Central",
                                "BR-009 Tabuk Central"],
    "Eastern Region Branches": ["BR-010 Dammam Corniche", "BR-011 Khobar Rakah",
                                "BR-012 Jubail Industrial"],
}

# Departments where the work splits finely enough to carry a section.
SECTIONED = {"Retail Banking Group", "Operations Group", "Technology Group"}

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

# How the bank classifies each group — the "function type" column.
FUNCTION_TYPE = {
    "CEO Office": "Governance",
    "Retail Banking Group": "Business (1st line)",
    "Corporate Banking Group": "Business (1st line)",
    "Treasury & Investments Group": "Business (1st line)",
    "Operations Group": "Business (1st line)",
    "Risk Group": "Control (2nd line)", "Compliance Group": "Control (2nd line)",
    "Finance Group": "Control (2nd line)", "Legal Group": "Control (2nd line)",
    "Internal Audit Group": "Assurance (3rd line)",
    "Technology Group": "Enabling", "Human Resources Group": "Enabling",
}

MANDATES = {
    "CEO Office": "Sets strategy and owns delivery of the bank's plan to the Board. Holds corporate strategy, transformation and corporate communications directly.",
    "Retail Banking Group": "Runs the branch network, cards, payments and wealth propositions for individual customers, owning revenue, service quality and channel migration.",
    "Corporate Banking Group": "Serves corporate and SME clients across lending, trade finance and transaction banking, owning the corporate credit portfolio and relationship coverage.",
    "Treasury & Investments Group": "Manages the bank's liquidity, funding and investment book, and prices and distributes FX and fixed income to clients within Board-approved limits.",
    "Risk Group": "Owns the bank-wide risk framework: credit, market and operational risk appetite, limit setting and stress testing, and independent challenge of first-line decisions. Reports the risk position to the Board Risk Committee.",
    "Compliance Group": "Ensures adherence to SAMA regulations and internal policy. Owns AML/CFT, sanctions screening, regulatory reporting and the non-objection process for controlled functions.",
    "Internal Audit Group": "Provides independent assurance to the Audit Committee over the effectiveness of governance, risk management and internal control.",
    "Finance Group": "Owns financial control, planning, performance and tax. Produces statutory and regulatory reporting and manages capital.",
    "Technology Group": "Delivers and runs core banking, digital channels, infrastructure and cybersecurity. Accountable for platform availability, change delivery and technology risk.",
    "Operations Group": "Processes payments, trade and branch operations with accountability for throughput, accuracy and operational loss.",
    "Human Resources Group": "Owns workforce strategy, talent acquisition, learning, Saudization targets and the succession framework for critical and controlled roles.",
    "Legal Group": "Advises on corporate legal matters, contracts and litigation, and owns legal risk.",
}

# A mandate can sit at more than one level: these divisions carry their own.
DIVISION_MANDATES = {
    "Branch Network Division": ("Retail Banking Group", "Business (1st line)", "Runs the physical network across three regions — footprint, branch profitability, service standards and cash operations at the counter."),
    "Credit Risk Division": ("Risk Group", "Control (2nd line)", "Sets credit policy and underwriting standards, approves exposures above delegated limits, and owns the credit administration and collateral records."),
    "Financial Crime Division": ("Compliance Group", "Control (2nd line)", "Owns AML, sanctions screening and fraud prevention, including suspicious transaction reporting to the SAFIU."),
    "Cybersecurity Division": ("Technology Group", "Enabling", "Runs security operations, identity and access management, and the response to cyber incidents under the SAMA Cyber Security Framework."),
    "Learning & Development Division": ("Human Resources Group", "Enabling", "Owns mandatory training and its evidence, the leadership academy, and the professional certification pathway."),
    "Treasury Division": ("Treasury & Investments Group", "Business (1st line)", "Manages funding, liquidity and the interest-rate position of the banking book within Board-approved limits."),
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


def add(pid, mgr, title, grade, group, fn, division="", dept="", vac_p=0.08,
        crit=None, sama=None, unit="", sub_unit="", section="", branch=""):
    vacant = random.random() < vac_p
    if crit is None:
        crit = grade in ("G17", "G16", "G15") or (grade == "G14" and random.random() < 0.4)
    if sama is None:
        sama = grade in ("G17", "G16") or (
            grade == "G15" and fn in ("Risk", "Compliance", "Finance", "Internal Audit"))
    has_succ = (random.random() < 0.58) if crit else (random.random() < 0.18)
    job_type = JOB_TYPE.get(group, "")
    rows.append({
        "Position ID": pid,
        "Manager ID": mgr,
        "Job Title": title,
        "Employee Name": "" if vacant else person(),
        "Grade": grade,
        "Job Code": f"JC{random.randint(1000, 9999)}",
        "Job Family": FAMILY.get(grade, "Professional"),
        "Legal Entity": LEGAL_ENTITY,
        "Function": fn,
        # Each role sits at its own rung and the ladder ends there: the CHCO
        # belongs to Human Resources Group, not to a phantom unit beneath it.
        "Group": group,
        "Division": division,
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
        "Function Type": FUNCTION_TYPE.get(group, ""),
        "Job Type": job_type,
        "Pay Basis": ("Incentive" if job_type == "Front office" and random.random() < 0.75
                      else "Bonus" if grade in ("G17", "G16", "G15", "G14", "G13")
                      else random.choice(["Bonus", "Fixed", "Fixed"])),
        "Talent Pool": (random.choice(TALENT_POOLS)
                        if random.random() < (0.30 if grade in ("G15", "G14", "G13") else 0.08)
                        else ""),
        "Work Email": "" if vacant else f"user{seq}@example.com",
        "Hire Date": f"{random.randint(2008, 2025)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        "Nationality": random.choice(["Saudi"] * 7 + ["Egyptian", "Indian", "Jordanian", "British"]),
        "Critical Role": "Yes" if crit else "No",
        "SAMA Non-Objection Role": "Yes" if sama else "No",
        "Successor Identified": "Yes" if has_succ else "No",
        "Successor Name": random.choice(names_pool) if has_succ else "",
        "Successor Readiness": random.choice(READY) if has_succ else "",
    })
    return pid


STAFF_TITLES = ["Officer", "Senior Officer", "Analyst", "Senior Analyst",
                "Specialist", "Associate"]

ceo = add(nid(), "", "Chief Executive Officer", "G17", "CEO Office", "Executive",
          vac_p=0, crit=True, sama=True)

for group, (fn, head_title, divisions) in STRUCTURE.items():
    # The CEO heads the CEO Office; every other group has its own C-level.
    head = ceo if group == "CEO Office" else add(
        nid(), ceo, head_title, "G16", group, fn, vac_p=0.05)
    for division, depts in divisions.items():
        gm = add(nid(), head, f"General Manager - {division[:-9].strip()}", "G15",
                 group, fn, division=division, vac_p=0.06)
        for dept in depts:
            d = add(nid(), gm, f"Head of {dept}", "G14", group, fn,
                    division=division, dept=dept, vac_p=0.07)
            for u_i in range(2):
                unit = f"{dept} Unit {u_i + 1}"
                m = add(nid(), d, f"Manager {dept}", "G13", group, fn,
                        division=division, dept=dept, unit=unit, vac_p=0.08)
                for s_i in range(2):
                    sub_unit = f"{unit} - Team {chr(65 + s_i)}"
                    lead = add(nid(), m, f"Team Lead {dept}", "G12", group, fn,
                               division=division, dept=dept, unit=unit,
                               sub_unit=sub_unit, vac_p=0.09)
                    for _ in range(random.randint(5, 9)):
                        add(nid(), lead,
                            f"{random.choice(STAFF_TITLES)} {dept}",
                            random.choice(["G9", "G10", "G10", "G11"]),
                            group, fn, division=division, dept=dept,
                            unit=unit, sub_unit=sub_unit,
                            section=(f"{sub_unit} / Section {random.randint(1, 2)}"
                                     if group in SECTIONED else ""),
                            branch=(random.choice(BRANCH_REGIONS[dept])
                                    if dept in BRANCH_REGIONS else ""),
                            vac_p=0.11, crit=False, sama=False)

# ── Where the reporting line and the structure disagree ─────────────────────
# Real exports carry these and nobody notices until someone compares the two
# hierarchies. They are invisible in the org view by design: the columns still
# say where the job sits, only the Manager ID says otherwise.
by_title = {}
for r in rows:
    by_title.setdefault(r["Job Title"], []).append(r)

# Two department heads reporting straight past their division head.
for dept, chief in (("Tax & Zakat", "Chief Financial Officer"),
                    ("Contact Centre", "Chief Retail Banking Officer")):
    head = by_title[f"Head of {dept}"][0]
    head["Manager ID"] = by_title[chief][0]["Position ID"]

# One department head answering sideways into another group entirely.
by_title["Head of Fraud Prevention"][0]["Manager ID"] = \
    by_title["Head of Security Operations"][0]["Position ID"]

# Three staff sitting in one group but managed from another — embedded IT and a
# secondment, both ordinary and both worth knowing about.
host = by_title["Manager Service Desk"][0]["Position ID"]
for r in [r for r in rows if r["Department"] == "Local Payments"
          and r["Grade"] in ("G9", "G10", "G11")][:3]:
    r["Manager ID"] = host

# Defects a real export contains, so the repair path is exercised. They are
# copied from ordinary staff rows spread across the file rather than from fixed
# indices, so restructuring the org never turns one of them into a duplicate of
# a group head.
staff = [r for r in rows if r["Grade"] in ("G9", "G10", "G11")]
sample = [staff[i * len(staff) // 6] for i in range(1, 6)]

rows.append({**sample[0], "Position ID": nid(), "Manager ID": "POS99999",
             "Job Title": "Consultant - Orphaned", "Employee Name": "Ghost Row"})
a, b = nid(), nid()
rows.append({**sample[1], "Position ID": a, "Manager ID": b, "Job Title": "Loop A", "Employee Name": "Cycle One"})
rows.append({**sample[1], "Position ID": b, "Manager ID": a, "Job Title": "Loop B", "Employee Name": "Cycle Two"})
rows.append({**sample[2], "Job Title": "Duplicate Seat"})
rows.append({**sample[3], "Position ID": "", "Job Title": "No ID At All"})
selfref = nid()
rows.append({**sample[4], "Position ID": selfref, "Manager ID": selfref, "Job Title": "Self Referencing"})

cols = list(rows[0].keys())
with open("sample-org.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

# ── The approved structure ──────────────────────────────────────────────────
# The org unit list is the frame the chart is built on, so it names every group,
# every division and every department — except four, deliberately left out, so
# the reconciliation has something true to find: a department that exists in the
# HR export as a tag and in nobody's approved structure.
UNDECLARED = {"Digital Onboarding", "Leadership Academy", "Cost & Performance",
              "Privilege Banking"}

# One department the list and the columns disagree about: the structure moved it
# to Talent & Performance, the HRIS still tags it under HR Operations.
MOVED = {"Payroll & Benefits": "Talent & Performance Division"}

unit_rows = [{
    "Org Unit": group, "Parent Unit": "", "Unit Code": f"ORG-{100 + i * 10}",
    "Function Type": FUNCTION_TYPE.get(group, ""), "Unit Head": "",
    "Unit Status": "Active", "Roles and Responsibilities": MANDATES.get(group, ""),
} for i, group in enumerate(STRUCTURE)]

code = 400
for group, (fn, _head, divisions) in STRUCTURE.items():
    for division, depts in divisions.items():
        code += 1
        declared = DIVISION_MANDATES.get(division)
        unit_rows.append({
            "Org Unit": division, "Parent Unit": group, "Unit Code": f"ORG-{code}",
            "Function Type": FUNCTION_TYPE.get(group, ""), "Unit Head": "",
            "Unit Status": "Active",
            "Roles and Responsibilities": declared[2] if declared else "",
        })
        for dept in depts:
            if dept in UNDECLARED:
                continue
            code += 1
            unit_rows.append({
                "Org Unit": dept, "Parent Unit": MOVED.get(dept, division),
                "Unit Code": f"ORG-{code}",
                "Function Type": FUNCTION_TYPE.get(group, ""), "Unit Head": "",
                "Unit Status": "Active", "Roles and Responsibilities": "",
            })

unit_rows += [
    {"Org Unit": "Data Governance Office", "Parent Unit": "Data & Analytics Division",
     "Unit Code": "ORG-310",
     "Function Type": "Control (2nd line)", "Unit Head": "TBA", "Unit Status": "Approved",
     "Roles and Responsibilities": "Approved in the 2026 structure to own data quality, lineage and the data catalogue. Recruitment has not started; no positions have been created yet."},
    {"Org Unit": "Climate Risk Unit", "Parent Unit": "Risk Group", "Unit Code": "ORG-230",
     "Function Type": "Control (2nd line)", "Unit Head": "TBA", "Unit Status": "Approved",
     "Roles and Responsibilities": "Established to meet SAMA climate-related financial disclosure expectations. Mandate approved, headcount pending Board approval."},
    {"Org Unit": "Shariah Audit", "Parent Unit": "Internal Audit Group", "Unit Code": "ORG-221",
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
