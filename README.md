
---

# 📝 PDF MCQ Extractor

This script extracts **Multiple Choice Questions (MCQs)** and their correct answers from educational PDF documents. It cleans and transforms the data into a standardized format and exports it to a CSV file, ready for database import or review.

---

## 🚀 Features

* Extracts MCQs and answers from PDF files
* Supports answer parsing from an "ANSWERS" section
* Cleans and sanitizes text data
* Maps options to standard A/B/C/D format
* Validates UUID for chapter association
* Exports final MCQs to a CSV file

---

## 📁 Project Structure

```
project/
├── data/
│   └── raw_pdfs/
│       └── your_pdf_file.pdf
├── mcq_extractor.py
└── mcqs_output.csv (generated)
```

---

## 🧰 Requirements

Install required libraries using pip:

```bash
pip install pymupdf
```

---

## 🧠 How It Works

1. **PDF Text Extraction**
   The entire PDF text is extracted using `PyMuPDF`.

2. **Answer Parsing**
   Looks for a section labeled `ANSWERS` → `Multiple Choice Questions`.
   Extracts correct answers in format like `1. (a)`.

3. **MCQ Extraction**
   Parses question blocks and associated options (a, b, c, d).

4. **Transformation**
   Converts options to capital letters, adds metadata like `chapter_id`.

5. **Sanitization**
   Cleans whitespace, normalizes text, deduplicates repeated questions.

6. **Export**
   Saves the final cleaned MCQ list into a CSV file.

---

## 🧪 Example Usage

Update the following values in the script before running:

```python
pdf_path = "data/raw_pdfs/work, energy and power.pdf"
chapter_id = "b89cc0b0-2acd-4003-9c61-dbc771402574"
chapter_name = "Work, energy and power"
```

Then run:

```bash
python mcq_extractor.py
```

Output:

```
✅ Extracted 24 answers
✅ Sanitized 22 MCQs (out of 25 raw)
✅ Saved 22 MCQs to 'mcqs_output.csv'
```

---

## 📦 Output Format

The CSV will include:

| chapter\_name          | question      | option\_a | option\_b | option\_c | option\_d | correct\_option | chapter\_id                          | user\_id |
| ---------------------- | ------------- | --------- | --------- | --------- | --------- | --------------- | ------------------------------------ | -------- |
| Work, energy and power | What is work? | Option A  | Option B  | Option C  | Option D  | B               | b89cc0b0-2acd-4003-9c61-dbc771402574 | None     |

---

## 🧹 Sanitization Rules

* Unicode normalization (NFKC)
* Replaces bad characters (e.g., `�`)
* Removes MCQs with short or missing questions/options
* Ensures valid UUID for chapter\_id
* Deduplicates exact MCQs

---

## 🧩 Customization

You can extend or modify:

* The regex for MCQ or answer pattern if PDF format changes
* CSV fieldnames to match your DB schema
* Add explanations or tags per MCQ in `description`

---

## 📬 Issues or Improvements

If the parser misses questions or options:

* Check for PDF formatting inconsistencies
* Adjust regular expressions in `extract_mcqs_from_pdf()`

---

## ✅ Example PDF Requirements

* Has a **"Multiple Choice Questions"** section
* Has an **"ANSWERS"** section with answers like `12. (b)`
* Each MCQ must have options in order: **(a)**, **(b)**, **(c)**, **(d)**

---

## 🧑‍💻 Author

Script by Sunil Hanamshetty — feel free to fork and improve it!
Pull requests are welcome if you wish to support other formats or export types.

---
