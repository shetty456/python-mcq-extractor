import fitz  # PyMuPDF
import re
import json
import csv
import unicodedata
import uuid

# ----------------------- PDF Extraction -----------------------


def extract_answers_from_pdf(full_text):
    """Extract answers from the ANSWERS section"""
    answers = {}

    if "ANSWERS" not in full_text:
        print("⚠️ No ANSWERS section found in PDF")
        return answers

    answers_section = full_text.split("SOLUTIONS", 1)[1]

    if "Multiple Choice Questions" in answers_section:
        mcq_answers = answers_section.split("Multiple Choice Questions", 1)[1]
        if "Assertion-Reasoning MCQs" in mcq_answers:
            mcq_answers = mcq_answers.split("Assertion-Reasoning MCQs", 1)[0]

        answer_pattern = re.compile(r"(\d+)\.\s*\(([abcd])\)")
        matches = answer_pattern.findall(mcq_answers)

        for match in matches:
            question_num = int(match[0])
            correct_option = match[1]
            answers[question_num] = correct_option

    return answers


def extract_mcqs_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    answers = extract_answers_from_pdf(full_text)
    print(f"✅ Extracted {len(answers)} answers")

    if "Multiple Choice Questions" in full_text:
        mcq_section = full_text.split("Multiple Choice Questions", 1)[1]
        if "Assertion-Reasoning MCQs" in mcq_section:
            mcq_section = mcq_section.split("Assertion-Reasoning MCQs", 1)[0]
    else:
        raise ValueError(
            "Could not find 'Multiple Choice Questions' section in the PDF."
        )

    mcq_pattern = re.compile(
        r"(?P<number>\d{1,3})\.\s+(?P<question>.*?)(?=\(\s*a\s*\))"
        r"\(\s*a\s*\)\s*(?P<option_a>.*?)"
        r"\(\s*b\s*\)\s*(?P<option_b>.*?)"
        r"\(\s*c\s*\)\s*(?P<option_c>.*?)"
        r"\(\s*d\s*\)\s*(?P<option_d>.*?)(?=(\n\d{1,3}\.|$))",
        re.DOTALL,
    )

    mcqs = []
    for match in mcq_pattern.finditer(mcq_section):
        q_num = int(match.group("number"))
        mcq = {
            "question_number": q_num,
            "question": match.group("question").strip().replace("\n", " "),
            "option_a": match.group("option_a").strip().replace("\n", " "),
            "option_b": match.group("option_b").strip().replace("\n", " "),
            "option_c": match.group("option_c").strip().replace("\n", " "),
            "option_d": match.group("option_d").strip().replace("\n", " "),
        }

        if q_num in answers:
            mcq["correct_option"] = answers[q_num]

        mcqs.append(mcq)

    return mcqs


# ----------------------- Transform & Sanitize -----------------------


def transform_mcqs_for_db(mcqs, chapter_id):
    transformed = []
    option_map = {"a": "A", "b": "B", "c": "C", "d": "D"}

    for mcq in mcqs:
        transformed_mcq = {
            "question": mcq["question"],
            "option_a": mcq["option_a"],
            "option_b": mcq["option_b"],
            "option_c": mcq["option_c"],
            "option_d": mcq["option_d"],
            "correct_option": option_map.get(mcq.get("correct_option", "").lower(), ""),
            "description": "",
            "chapter_id": chapter_id,
            "user_id": None,
        }
        transformed.append(transformed_mcq)

    return transformed


def is_valid_uuid(u):
    try:
        uuid.UUID(str(u))
        return True
    except ValueError:
        return False


def sanitize_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("�", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


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

        if len(question) < 5 or correct_option not in {"A", "B", "C", "D"}:
            continue

        key = (question, option_a, option_b, option_c, option_d)
        if key in seen:
            continue
        seen.add(key)

        clean_mcqs.append(
            {
                "chapter_name": chapter_name,
                "question": question,
                "option_a": option_a,
                "option_b": option_b,
                "option_c": option_c,
                "option_d": option_d,
                "correct_option": correct_option,
                "description": "",
                "chapter_id": chapter_id,
                "user_id": None,
            }
        )

    print(f"✅ Sanitized {len(clean_mcqs)} MCQs (out of {len(mcqs)} raw)")
    return clean_mcqs


# ----------------------- Output to CSV -----------------------


def save_to_csv(mcqs, filename="mcqs_output.csv"):
    if not mcqs:
        print("⚠️ No MCQs to save.")
        return

    fieldnames = list(mcqs[0].keys())

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mcqs)

    print(f"✅ Saved {len(mcqs)} MCQs to '{filename}'")


# ----------------------- Run Script -----------------------

if __name__ == "__main__":
    pdf_path = "data/raw_pdfs/work, energy and power.pdf"  # Replace with your PDF path
    chapter_id = "b89cc0b0-2acd-4003-9c61-dbc771402574"  # Replace with valid UUID
    chapter_name = "Work, energy and power"  # Replace with your chapter name

    mcqs = extract_mcqs_from_pdf(pdf_path)
    transformed = transform_mcqs_for_db(mcqs, chapter_id)
    sanitized = sanitize_mcqs(transformed, chapter_id, chapter_name)
    save_to_csv(sanitized, "mcqs_output.csv")
