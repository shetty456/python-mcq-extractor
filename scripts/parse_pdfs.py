import fitz  # PyMuPDF
import re
import json
import csv
import unicodedata
import uuid
import os

# ----------------------- PDF Extraction -----------------------

def sanitize_multiline(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("�", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)

def extract_answers_and_solutions_from_pdf(full_text):
    answers = {}
    solutions = {}

    if "SOLUTIONS" not in full_text:
        print("⚠️ No SOLUTIONS section found")
        return answers, solutions

    solution_section = full_text.split("SOLUTIONS", 1)[1]

    if "Multiple Choice Questions" in solution_section:
        answer_part = solution_section.split("Multiple Choice Questions", 1)[1]
        if "Assertion-Reasoning MCQs" in answer_part:
            answer_part = answer_part.split("Assertion-Reasoning MCQs", 1)[0]

        for match in re.findall(r"(\d+)\.\s*\(([abcd])\)", answer_part, re.IGNORECASE):
            question_num = int(match[0])
            correct_option = match[1].lower()
            answers[question_num] = correct_option

    cleaned_solution_lines = []
    for line in solution_section.splitlines():
        if not re.match(r"^\s*\d{1,3}\.\s*\([abcd]\)", line.strip(), re.IGNORECASE):
            cleaned_solution_lines.append(line)

    clean_solution_text = "\n".join(cleaned_solution_lines)

    for match in re.finditer(r"(?P<number>\d{1,3})\.\s+(?P<text>(?:(?!\n\d{1,3}\.\s).)+)", clean_solution_text, re.DOTALL):
        q_num = int(match.group("number"))
        text = sanitize_multiline(match.group("text")).strip()
        if text:
            solutions[q_num] = text

    return answers, solutions

def extract_mcqs_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    answers, solutions = extract_answers_and_solutions_from_pdf(full_text)

    if "Multiple Choice Questions" in full_text:
        mcq_section = full_text.split("Multiple Choice Questions", 1)[1]
        if "Assertion-Reasoning MCQs" in mcq_section:
            mcq_section = mcq_section.split("Assertion-Reasoning MCQs", 1)[0]
    elif "Objective Questions" in full_text:
        mcq_section = full_text.split("Objective Questions", 1)[1]
    else:
        print(f"❌ No MCQ section found in {pdf_path}")
        return []

    mcq_pattern = re.compile(
        r"""
        (?P<number>\d{1,3})\.\s+(?P<question>.*?)
        (?:
            \(\s*a\s*\)\s*(?P<oa1>.*?)
            \(\s*b\s*\)\s*(?P<ob1>.*?)
            \(\s*c\s*\)\s*(?P<oc1>.*?)
            \(\s*d\s*\)\s*(?P<od1>.*?)
        |
            \n\(\s*a\s*\)\s*(?P<oa2>.*?)
            \n\(\s*b\s*\)\s*(?P<ob2>.*?)
            \n\(\s*c\s*\)\s*(?P<oc2>.*?)
            \n\(\s*d\s*\)\s*(?P<od2>.*?)
        )
        (?=\n\d{1,3}\.|\Z)
        """,
        re.DOTALL | re.VERBOSE,
    )

    def clean(text):
        return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()

    def pick(groupdict, inline, newline):
        return groupdict.get(inline) or groupdict.get(newline) or ""

    mcqs = []
    for match in mcq_pattern.finditer(mcq_section):
        g = match.groupdict()
        q_num = int(g["number"])
        mcqs.append({
            "question_number": q_num,
            "question": clean(g["question"]),
            "option_a": clean(pick(g, "oa1", "oa2")),
            "option_b": clean(pick(g, "ob1", "ob2")),
            "option_c": clean(pick(g, "oc1", "oc2")),
            "option_d": clean(pick(g, "od1", "od2")),
            "correct_option": answers.get(q_num, ""),
            "description": solutions.get(q_num, ""),
        })

    return mcqs

# ----------------------- Formatter -----------------------

def format_expression(text):
    text = re.sub(r"\[\s*([A-Z ]+)\s*\]\s*([\d\- ]+)", lambda m: format_dimensional_formula(m.group(1), m.group(2)), text)
    text = re.sub(r"([A-Za-z])\s*(-?\d+)", r"\1^\2", text)
    text = re.sub(r"\s*[x×.]\s*", " * ", text)
    text = re.sub(r"\s*/\s*", " / ", text)
    return text.strip()

def format_dimensional_formula(symbols, powers):
    base_symbols = symbols.strip().split()
    exponents = powers.strip().split()
    return "[" + " ".join(f"{s}^{e}" for s, e in zip(base_symbols, exponents) if e != "0") + "]"

# ----------------------- Transform & Sanitize -----------------------

def transform_mcqs_for_db(mcqs, chapter_id):
    option_map = {"a": "A", "b": "B", "c": "C", "d": "D"}
    return [{
        "question": mcq["question"],
        "option_a": mcq["option_a"],
        "option_b": mcq["option_b"],
        "option_c": mcq["option_c"],
        "option_d": mcq["option_d"],
        "correct_option": option_map.get(mcq.get("correct_option", "").lower(), ""),
        "description": mcq.get("description", ""),
        "chapter_id": chapter_id,
        "user_id": None,
    } for mcq in mcqs]

def is_valid_uuid(u):
    try:
        uuid.UUID(str(u))
        return True
    except ValueError:
        return False

def sanitize_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text.replace("�", "")).strip()
    return format_expression(text)

def sanitize_mcqs(mcqs, chapter_id, chapter_name):
    clean_mcqs = []
    seen = set()

    if not is_valid_uuid(chapter_id):
        raise ValueError("❌ Invalid chapter_id UUID")

    for mcq in mcqs:
        question = sanitize_text(mcq["question"])
        option_a = sanitize_text(mcq["option_a"])
        option_b = sanitize_text(mcq["option_b"])
        option_c = sanitize_text(mcq["option_c"])
        option_d = sanitize_text(mcq["option_d"])
        correct_option = mcq.get("correct_option", "").strip().upper()
        description = sanitize_text(mcq.get("description", ""))

        if len(question) < 5 or correct_option not in {"A", "B", "C", "D"}:
            print(f"⚠️ Skipping Q{mcq.get('question_number')} — Reason:", end=" ")
            if len(question) < 5:
                print("Too short question.")
            else:
                print(f"Invalid correct option: '{correct_option}'")
            continue

        key = (question, option_a, option_b, option_c, option_d)
        if key in seen:
            print(f"⚠️ Skipping Q{mcq.get('question_number')} — Duplicate detected.")
            continue
        seen.add(key)

        clean_mcqs.append({
            "chapter_name": chapter_name,
            "question": question,
            "option_a": option_a,
            "option_b": option_b,
            "option_c": option_c,
            "option_d": option_d,
            "correct_option": correct_option,
            "description": description,
            "chapter_id": chapter_id,
            "user_id": None,
        })

    print(f"✅ Sanitized {len(clean_mcqs)} MCQs (out of {len(mcqs)} raw)")
    return clean_mcqs


# ----------------------- Output -----------------------

def save_to_csv(mcqs, filename):
    if not mcqs:
        print(f"⚠️ No MCQs to save in {filename}")
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=mcqs[0].keys())
        writer.writeheader()
        writer.writerows(mcqs)
    print(f"✅ Saved to CSV: {filename}")

def save_to_json_format(mcqs, filename):
    formatted = [{
        "question": mcq["question"],
        "options": {
            "A": mcq["option_a"],
            "B": mcq["option_b"],
            "C": mcq["option_c"],
            "D": mcq["option_d"],
        },
        "answer": mcq["correct_option"],
        "reason": mcq.get("description", "")
    } for mcq in mcqs]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(formatted, f, indent=4, ensure_ascii=False)
    print(f"✅ Saved to JSON: {filename}")

# ----------------------- Main Runner -----------------------

if __name__ == "__main__":
    pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
    chapter_id = "b89cc0b0-2acd-4003-9c61-dbc771402574"

    for pdf_path in pdf_files:
        try:
            print(f"\n📄 Processing {pdf_path}")
            chapter_name = os.path.splitext(os.path.basename(pdf_path))[0]
            mcqs = extract_mcqs_from_pdf(pdf_path)
            if not mcqs:
                print("⚠️ No MCQs extracted.")
                continue
            transformed = transform_mcqs_for_db(mcqs, chapter_id)
            sanitized = sanitize_mcqs(transformed, chapter_id, chapter_name)
            save_to_csv(sanitized, f"{chapter_name}.csv")
            save_to_json_format(sanitized, f"{chapter_name}.json")
        except Exception as e:
            print(f"❌ Failed to process {pdf_path}: {e}")
