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
READY = ["Ready now", "Ready 1-2 years", "Ready 3+ years"]
FAMILY = {"G17": "Executive", "G16": "Executive", "G15": "Leadership",
          "G14": "Leadership", "G13": "Management", "G12": "Management"}

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


def add(pid, mgr, title, grade, fn, dept, vac_p=0.08, crit=None, sama=None):
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
        "Department": dept,
        "Division": "Banking" if fn in ("Retail Banking", "Corporate Banking") else "Support",
        "Location": random.choice(LOCS),
        "Employment Type": "Full-time" if random.random() < 0.93 else "Contractor",
        "Position Status": "Vacant" if vacant else "Filled",
        "FTE": "1" if random.random() < 0.94 else "0.5",
        "Cost Center": f"CC-{random.randint(1000, 1060)}",
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
        for _ in range(random.randint(2, 3)):
            sm = add(nid(), d, f"Senior Manager {dept}", "G14", fn, dept, vac_p=0.07)
            for _ in range(random.randint(2, 4)):
                m = add(nid(), sm, f"Manager {dept}", "G13", fn, dept, vac_p=0.08)
                for _ in range(random.randint(6, 12)):
                    add(nid(), m,
                        random.choice(["Officer", "Senior Officer", "Analyst", "Senior Analyst",
                                       "Specialist", "Associate"]) + f" {dept}",
                        random.choice(["G9", "G10", "G10", "G11", "G12"]), fn, dept,
                        vac_p=0.11, crit=False, sama=False)

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

xlsx_path = sys.argv[1] if len(sys.argv) > 1 else None
if xlsx_path:
    import pandas as pd
    pd.DataFrame(rows).to_excel(xlsx_path, index=False)

print(f"{len(rows)} rows, {len(cols)} columns")
