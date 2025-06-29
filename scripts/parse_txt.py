import re
import json
import csv
import unicodedata
import uuid

# ----------------------- Text Extraction -----------------------

def sanitize_multiline(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("�", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)

def extract_answers_and_solutions_from_text(full_text):
    answers = {}
    solutions = {}

    if "SOLUTIONS" not in full_text:
        print("⚠️ No SOLUTIONS section found in text")
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

def extract_mcqs_from_text(full_text):
    answers, solutions = extract_answers_and_solutions_from_text(full_text)

    if "Multiple Choice Questions" in full_text:
        mcq_section = full_text.split("Multiple Choice Questions", 1)[1]
        if "Assertion-Reasoning MCQs" in mcq_section:
            mcq_section = mcq_section.split("Assertion-Reasoning MCQs", 1)[0]
    else:
        raise ValueError("Could not find 'Multiple Choice Questions' section in the text.")

    mcq_pattern = re.compile(
        r"(?P<number>\d{1,3})\.\s+(?P<question>.*?)(?=\(\s*a\s*\))"
        r"\(\s*a\s*\)\s*(?P<option_a>.*?)(?=\(\s*b\s*\))"
        r"\(\s*b\s*\)\s*(?P<option_b>.*?)(?=\(\s*c\s*\))"
        r"\(\s*c\s*\)\s*(?P<option_c>.*?)(?=\(\s*d\s*\))"
        r"\(\s*d\s*\)\s*(?P<option_d>.*?)(?=(?:\n\d{1,3}\.\s|\Z|\n{2,}|Match|Codes|Explanation))",
        re.DOTALL,
    )

    def clean_option(opt):
        if not opt:
            return ""
        opt = opt.replace("\n", " ").strip()
        opt = re.sub(r"\s+", " ", opt)

        match = re.match(r"^\[(.*?)\]\s*([\d\-\s]+)$", opt)
        if match:
            base = match.group(1).strip()
            powers = match.group(2).strip().split()
            base_symbols = base.split()
            components = []
            for i, symbol in enumerate(base_symbols):
                exp = powers[i] if i < len(powers) else ""
                components.append(f"{symbol}^{exp}" if exp else symbol)
            return "[" + " ".join(components) + "]"

        opt = re.sub(r"(?<=\s)-\s+(\d)", r"-\1", opt)
        return opt.strip()

    mcqs = []
    for match in mcq_pattern.finditer(mcq_section):
        q_num = int(match.group("number"))
        mcq = {
            "question_number": q_num,
            "question": match.group("question").strip().replace("\n", " "),
            "option_a": clean_option(match.group("option_a")),
            "option_b": clean_option(match.group("option_b")),
            "option_c": clean_option(match.group("option_c")),
            "option_d": clean_option(match.group("option_d")),
            "correct_option": answers.get(q_num, ""),
            "description": solutions.get(q_num, ""),
        }
        mcqs.append(mcq)
    return mcqs

# ----------------------- Expression Formatter -----------------------

def format_expression(text):
    text = re.sub(r"\[\s*([A-Z ]+)\s*\]\s*([\d\- ]+)", lambda m: format_dimensional_formula(m.group(1), m.group(2)), text)
    text = re.sub(r"([A-Za-z])\s*(-?\d+)", r"\1^\2", text)
    text = re.sub(r"\s*[x×.]\s*", " * ", text)
    text = re.sub(r"\s*/\s*", " / ", text)
    return text.strip()

def format_dimensional_formula(symbols, powers):
    base_symbols = symbols.strip().split()
    exponents = powers.strip().split()
    parts = []
    for i, sym in enumerate(base_symbols):
        exp = exponents[i] if i < len(exponents) else ""
        exp = exp.replace("−", "-")
        if exp in ("0", ""):
            continue
        parts.append(f"{sym}^{exp}")
    return "[" + " ".join(parts) + "]"

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
            "description": mcq.get("description", ""),
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
    text = format_expression(text)
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
        description = sanitize_text(mcq.get("description", ""))

        if len(question) < 5 or correct_option not in {"A", "B", "C", "D"}:
            continue

        key = (question, option_a, option_b, option_c, option_d)
        if key in seen:
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

def save_to_json_format(mcqs, filename="mcqs_output.json"):
    formatted = []
    for mcq in mcqs:
        formatted.append({
            "question": mcq["question"],
            "options": {
                "A": mcq["option_a"],
                "B": mcq["option_b"],
                "C": mcq["option_c"],
                "D": mcq["option_d"],
            },
            "answer": mcq["correct_option"],
            "reason": mcq.get("description", "")
        })
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(formatted, f, indent=4, ensure_ascii=False)
    print(f"✅ Saved {len(formatted)} MCQs to '{filename}' in JSON format.")

# ----------------------- Run -----------------------

if __name__ == "__main__":
    txt_path = "law.txt"  # 🔄 Replace with your text file path
    chapter_id = "b89cc0b0-2acd-4003-9c61-dbc771402574"
    chapter_name = "Work, energy and power"

    with open(txt_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    mcqs = extract_mcqs_from_text(full_text)
    transformed = transform_mcqs_for_db(mcqs, chapter_id)
    sanitized = sanitize_mcqs(transformed, chapter_id, chapter_name)

    save_to_csv(sanitized, "mcqs_output.csv")
    save_to_json_format(sanitized, "mcqs_output.json")
