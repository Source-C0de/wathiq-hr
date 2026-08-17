"""Curated golden Q&A set for evaluation.

Hand-written 40+ questions spanning the topics an HR assistant for Saudi
Labour Law must handle: leave, EOSB/gratuity, probation, termination, GOSI,
WPS, Nitaqat, female-worker rights, remote work, working hours, and overtime.

Each entry has:
  id, question, language, expected_source_id, expected_article_no (optional)
"""
from __future__ import annotations

import csv
from pathlib import Path

GOLDEN: list[dict] = [
    # --- Annual leave / working hours ---
    {"id": "Q01", "question": "How many days of annual leave am I entitled to under Saudi Labour Law?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "109"},
    {"id": "Q02", "question": "Can the employer determine the timing of my annual leave?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "111"},
    {"id": "Q03", "question": "What is the maximum normal working hours per week?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "98"},
    {"id": "Q04", "question": "كم يوم إجازة سنوية أحصل عليها بموجب نظام العمل السعودي؟", "language": "ar", "expected_source_id": "m51_ar", "expected_article_no": "109"},
    # --- Probation / termination ---
    {"id": "Q05", "question": "What is the maximum probation period allowed?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "53"},
    {"id": "Q06", "question": "What is the notice period during probation?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "53"},
    {"id": "Q07", "question": "Can a contract be terminated arbitrarily under Saudi law?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "74"},
    {"id": "Q08", "question": "What compensation is owed in case of illegal termination?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "77"},
    # --- End of service benefits (EOSB) ---
    {"id": "Q09", "question": "How is end-of-service benefit calculated after 5 years?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "84"},
    {"id": "Q10", "question": "How is end-of-service benefit calculated after 10 years?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "84"},
    {"id": "Q11", "question": "What happens to EOSB if I resign before 5 years?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "85"},
    {"id": "Q12", "question": "كيف تُحسب مكافأة نهاية الخدمة بعد خمس سنوات؟", "language": "ar", "expected_source_id": "m51_ar", "expected_article_no": "84"},
    # --- GOSI ---
    {"id": "Q13", "question": "What is GOSI and what does it cover?", "language": "en", "expected_source_id": "gosi_faq_en", "expected_article_no": None},
    {"id": "Q14", "question": "Are domestic workers covered by GOSI?", "language": "en", "expected_source_id": "gosi_faq_en", "expected_article_no": None},
    {"id": "Q15", "question": "How does an employer register a new employee with GOSI?", "language": "en", "expected_source_id": "gosi_faq_en", "expected_article_no": None},
    # --- Wage Protection System (WPS) ---
    {"id": "Q16", "question": "What does WPS require from employers?", "language": "en", "expected_source_id": "wps_en", "expected_article_no": None},
    {"id": "Q17", "question": "What happens if an employer fails to pay salaries through WPS?", "language": "en", "expected_source_id": "wps_en", "expected_article_no": None},
    # --- Nitaqat ---
    {"id": "Q18", "question": "What are the Nitaqat bands and how are they calculated?", "language": "en", "expected_source_id": "nitaqat_en", "expected_article_no": None},
    {"id": "Q19", "question": "What is the 'platinum' Nitaqat band?", "language": "en", "expected_source_id": "nitaqat_en", "expected_article_no": None},
    # --- Female workers ---
    {"id": "Q20", "question": "What protections exist for female workers in Saudi Arabia?", "language": "en", "expected_source_id": "female_workers_en", "expected_article_no": None},
    {"id": "Q21", "question": "Are there limits on working hours for female employees?", "language": "en", "expected_source_id": "female_workers_en", "expected_article_no": None},
    {"id": "Q22", "question": "Can a female employee take maternity leave? How long?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "151"},
    # --- Remote work ---
    {"id": "Q23", "question": "Can my employer require me to work remotely?", "language": "en", "expected_source_id": "remote_work_ar", "expected_article_no": None},
    {"id": "Q24", "question": "What expenses must the employer cover for remote workers?", "language": "en", "expected_source_id": "remote_work_ar", "expected_article_no": None},
    # --- Overtime / holidays ---
    {"id": "Q25", "question": "How is overtime pay calculated?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "107"},
    {"id": "Q26", "question": "What are the official public holidays in Saudi Arabia?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "112"},
    {"id": "Q27", "question": "How many rest days per week am I entitled to?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "104"},
    # --- Sick leave ---
    {"id": "Q28", "question": "How long is sick leave and how is it paid?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "117"},
    {"id": "Q29", "question": "Do I need a medical report to take sick leave?", "language": "en", "expected_source_id": "exec_reg_ar", "expected_article_no": None},
    # --- Workplace safety ---
    {"id": "Q30", "question": "What are the employer's obligations for workplace safety?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "121"},
    # --- Contract types ---
    {"id": "Q31", "question": "What is the difference between fixed-term and indefinite contracts?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "37"},
    {"id": "Q32", "question": "What is the maximum duration of a fixed-term contract?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "37"},
    # --- Non-compete ---
    {"id": "Q33", "question": "Can a non-compete clause be added after the contract ends?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "83"},
    {"id": "Q34", "question": "How long can a non-compete restriction last?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "83"},
    # --- Hajj leave ---
    {"id": "Q35", "question": "Am I entitled to unpaid leave for Hajj?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "115"},
    # --- Wages ---
    {"id": "Q36", "question": "When must my salary be paid each month?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "94"},
    {"id": "Q37", "question": "Can my employer deduct from my wages?", "language": "en", "expected_source_id": "m51_en", "expected_article_no": "95"},
    # --- Arabic ---
    {"id": "Q38", "question": "ما هي الحد الأقصى لساعات العمل الأسبوعية؟", "language": "ar", "expected_source_id": "m51_ar", "expected_article_no": "98"},
    {"id": "Q39", "question": "هل يحق لصاحب العمل تحديد موعد الإجازة السنوية؟", "language": "ar", "expected_source_id": "m51_ar", "expected_article_no": "111"},
    {"id": "Q40", "question": "ما هي التزامات صاحب العمل بشأن السلامة في مكان العمل؟", "language": "ar", "expected_source_id": "m51_ar", "expected_article_no": "121"},
]


def write_csv(path: str = "eval/golden.csv") -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(GOLDEN[0].keys()))
        w.writeheader()
        w.writerows(GOLDEN)
    return out


if __name__ == "__main__":
    p = write_csv()
    print(f"Wrote {len(GOLDEN)} golden Q&A to {p}")