"""
pdf_import.py
Reads a UPI-app PDF statement (e.g. PhonePe -> History -> Download Statement)
and turns it into the same row shape the CSV import uses, so the rows go
through the existing categorisation + budget-check pipeline unchanged.

How it works
- Text is pulled out of every page and read line by line.
- A line counts as a transaction when it has a date AND an amount.
- Only DEBIT (money going out) lines are imported; CREDIT lines are skipped,
  because this is an expense tracker.
- Extra lines under a transaction (time, transaction ID, UTR number,
  "Paid by ...") have no date+amount, so they are ignored automatically.
- If the PDF is password protected, the caller passes the password.

Honest limitation: statement layouts differ between apps and change over
time. The result reports how many lines were recognised so a layout this
parser does not understand is obvious instead of silently importing nothing.
"""

import io
import re
from datetime import datetime

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from pdfplumber.utils.exceptions import PdfminerException

MAX_PAGES = 200

MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"

# (regex, list of strptime formats to try on the matched text)
DATE_PATTERNS = [
    (rf"\b({MONTHS}\s+\d{{1,2}},?\s+\d{{4}})\b", ["%b %d %Y", "%B %d %Y"]),   # Sep 01, 2026
    (rf"\b(\d{{1,2}}\s+{MONTHS}\s+\d{{4}})\b", ["%d %b %Y", "%d %B %Y"]),     # 01 Sep 2026
    (r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b", ["%d/%m/%Y", "%d-%m-%Y"]),         # 01/09/2026
    (r"\b(\d{4}-\d{2}-\d{2})\b", ["%Y-%m-%d"]),                               # 2026-09-01
]

CURRENCY_AMOUNT = re.compile("(?:Rs\\.?|INR|\u20b9)\\s?([\\d,]+(?:\\.\\d{1,2})?)", re.IGNORECASE)
TRAILING_AMOUNT = re.compile(r"([\d,]+\.\d{2})\s*$")
TIME_TEXT = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\s?(?:am|pm)?\b", re.IGNORECASE)

PAID_PHRASES = ("paid to", "paid via", "sent to", "you paid")
RECEIVED_PHRASES = ("received from", "you received", "refund", "cashback")


class PdfImportError(Exception):
    """kind is 'password' (needs/has wrong password) or 'unreadable' (not a usable PDF)."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message


def _find_date(line: str):
    """Returns (iso_date, matched_text) or (None, None)."""
    for pattern, formats in DATE_PATTERNS:
        match = re.search(pattern, line, re.IGNORECASE)
        if not match:
            continue
        raw = re.sub(r"\s+", " ", match.group(1).replace(",", "").replace(".", "")).strip()
        raw = re.sub(r"\bSept\b", "Sep", raw, flags=re.IGNORECASE)  # only the standalone short form
        for fmt in formats:
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d"), match.group(0)
            except ValueError:
                continue
    return None, None


def _direction(line: str):
    """Returns 'debit', 'credit' or None when the line does not say."""
    lower = line.lower()
    has_debit = re.search(r"\bdebit(ed)?\b", lower) is not None
    has_credit = re.search(r"\bcredit(ed)?\b", lower) is not None
    paid = any(p in lower for p in PAID_PHRASES)
    received = any(p in lower for p in RECEIVED_PHRASES)

    if has_debit and not has_credit:
        return "debit"
    if has_credit and not has_debit:
        # "Paid to HDFC Credit Card" is money going out even though it says credit
        return "debit" if paid and not received else "credit"
    if paid and not received:
        return "debit"
    if received and not paid:
        return "credit"
    return None


def _find_amount(line: str, has_type_word: bool):
    """Returns (amount_float, matched_text) or (None, None)."""
    match = CURRENCY_AMOUNT.search(line)
    if match:
        text = match.group(1).replace(",", "")
    elif has_type_word:
        # Some PDFs lose the rupee symbol; accept a number at the end of a typed line.
        match = TRAILING_AMOUNT.search(line)
        if not match:
            return None, None
        text = match.group(1).replace(",", "")
    else:
        return None, None
    try:
        return float(text), match.group(0)
    except ValueError:
        return None, None


def _clean_description(line: str, date_text: str, amount_text: str) -> str:
    text = line.replace(date_text, " ", 1).replace(amount_text, " ", 1)
    text = TIME_TEXT.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -:|,")
    # Drop the Type column label only when it is the last word, so a merchant
    # name like "HDFC Credit Card" keeps its own "Credit".
    text = re.sub(r"\s+(DEBIT|CREDIT|DEBITED|CREDITED)$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*(paid to|paid via|sent to|you paid)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" -:|,")
    return text or "UPI Transaction"


def parse_pdf_bytes(file_bytes: bytes, password: str = None) -> dict:
    """
    Returns:
      rows            list of {date, description, amount} for each DEBIT
      credits_skipped number of money-received lines left out on purpose
      unclear_lines   lines with a date and amount but no debit/credit info
    Raises PdfImportError for a wrong/missing password or an unreadable file.
    """
    rows = []
    credits_skipped = 0
    unclear_lines = 0
    open_kwargs = {"password": password} if password else {}

    try:
        with pdfplumber.open(io.BytesIO(file_bytes), **open_kwargs) as pdf:
            for page in pdf.pages[:MAX_PAGES]:
                text = page.extract_text() or ""
                for line in text.split("\n"):
                    date_iso, date_text = _find_date(line)
                    if not date_iso:
                        continue

                    direction = _direction(line)
                    has_type_word = re.search(r"\b(debit|credit)(ed)?\b", line, re.IGNORECASE) is not None
                    amount, amount_text = _find_amount(line, has_type_word)
                    if amount is None or amount <= 0:
                        continue

                    if direction == "credit":
                        credits_skipped += 1
                        continue
                    if direction is None:
                        unclear_lines += 1
                        continue

                    rows.append({
                        "date": date_iso,
                        "description": _clean_description(line, date_text, amount_text),
                        "amount": str(amount),
                    })
    except (PDFPasswordIncorrect, PdfminerException) as err:
        # pdfplumber wraps pdfminer's own error inside PdfminerException
        inner = err.args[0] if isinstance(err, PdfminerException) and err.args else err
        if isinstance(inner, PDFPasswordIncorrect):
            if password:
                raise PdfImportError("password", "That password did not open the PDF. Check it and try again.")
            raise PdfImportError("password", "This PDF is password protected. Enter the password and try again.")
        raise PdfImportError("unreadable", "Could not read this file as a PDF statement.")
    except Exception:
        raise PdfImportError("unreadable", "Could not read this file as a PDF statement.")

    return {"rows": rows, "credits_skipped": credits_skipped, "unclear_lines": unclear_lines}
