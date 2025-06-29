import fitz  # PyMuPDF
import re
import csv
import json
import os
import unicodedata
import uuid

# ----------------------- Utilities -----------------------

def sanitize(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"�", "", text)
    return re.sub(r"\s+", " ", text).strip()

def is_valid_uuid(u):
    try:
        uuid.UUID(str(u))
        return True
    except:
        return False

# ----------------------- MCQ Extraction -----------------------

def extract_mcqs_from_generic_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    pattern = re.compile(
        r"""
        (?:Question\s*)?(?P<number>\d{1,3}(?:\.\d{1,2})?)\s*[\.:]?\s*         # Match 'Question 1' or '1.02'
        (?P<question>.*?)                                                    # Question text
        (?:\(?[Aa]\)?\.?|[Aa]\.)\s*(?P<option_a>.*?)\s+                      # Option A
        (?:\(?[Bb]\)?\.?|[Bb]\.)\s*(?P<option_b>.*?)\s+                      # Option B
        (?:\(?[Cc]\)?\.?|[Cc]\.)\s*(?P<option_c>.*?)\s+                      # Option C
        (?:\(?[Dd]\)?\.?|[Dd]\.)\s*(?P<option_d>.*?)\s+                      # Option D
        (?:Ans(?:wer)?\s*[:.\-]?\s*\(?([A-Da-d])\)?)                         # Match Ans: A or Answer: (a)
        """,
        re.DOTALL | re.VERBOSE
    )

    mcqs = []
    for match in pattern.finditer(full_text):
        g = match.groupdict()
        mcqs.append({
            "question_number": g["number"],
            "question": sanitize(g["question"]),
            "option_a": sanitize(g["option_a"]),
            "option_b": sanitize(g["option_b"]),
            "option_c": sanitize(g["option_c"]),
            "option_d": sanitize(g["option_d"]),
            "correct_option": match.group(6).upper(),  # Answer group
            "description": "",  # Add solution OCR parsing if needed
        })

    print(f"✅ Extracted {len(mcqs)} MCQs from {os.path.basename(pdf_path)}")
    return mcqs

# ----------------------- Save Output -----------------------

def save_to_csv(mcqs, filename):
    if not mcqs:
        print(f"⚠️ No MCQs to save in {filename}")
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=mcqs[0].keys())
        writer.writeheader()
        writer.writerows(mcqs)
    print(f"✅ Saved to CSV: {filename}")

# ----------------------- Runner -----------------------

if __name__ == "__main__":
    file_chapter_map = [
        {"filename": "units and measurements.pdf", "chapter_id": "b89cc0b0-2acd-4003-9c61-dbc771402574"},
        {"filename": "kinetic theory.pdf", "chapter_id": "b89cc0b0-2acd-4003-9c61-dbc771402575"},
        {"filename": "thermodynamics.pdf", "chapter_id": "b89cc0b0-2acd-4003-9c61-dbc771402576"}
    ]

    for entry in file_chapter_map:
        filename = entry["filename"]
        chapter_id = entry["chapter_id"]

        if not os.path.exists(filename):
            print(f"❌ File not found: {filename}")
            continue
        if not is_valid_uuid(chapter_id):
            print(f"❌ Invalid UUID: {chapter_id}")
            continue

        try:
            mcqs = extract_mcqs_from_generic_pdf(filename)
            chapter_name = os.path.splitext(filename)[0]
            for mcq in mcqs:
                mcq["chapter_id"] = chapter_id
                mcq["chapter_name"] = chapter_name
                mcq["user_id"] = None

            save_to_csv(mcqs, f"{filename}.csv")

        except Exception as e:
            print(f"❌ Failed to process {filename}: {e}")
