"""PDF parsing for credit card statements and GL code lookups."""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import pdfplumber


def get_base_path() -> Path:
    """
    Get the base directory for the application.

    Returns the directory containing the executable when frozen (PyInstaller),
    otherwise returns the project root when running from source.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running from source
        return Path(__file__).parent.parent.parent


@dataclass
class Transaction:
    """Represents a single credit card transaction."""
    date: str
    vendor: str
    amount: float
    description: str = ""
    gl_account: str = ""
    location: str = ""
    program: str = ""
    funder: str = ""
    department: str = ""
    receipt_received: bool = False


@dataclass
class GLCodeSet:
    """Represents a set of GL codes."""
    location: str
    program: str
    funder: str
    department: str


class StatementParser:
    """Parses Wells Fargo credit card statement PDFs to extract transactions.

    Uses pdfplumber's positional word extraction to distinguish between
    the Credits and Charges columns based on x-coordinates. This allows
    proper identification of refunds (credits) vs regular charges, and
    filtering out payment rows.
    """

    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path

    def parse(self) -> List[Transaction]:
        """
        Parse the Wells Fargo PDF and extract all transactions.

        Uses positional word extraction to determine whether amounts fall
        under the Credits or Charges column. Credits (refunds) are stored
        as negative amounts. Payment rows (PAYMENT THANK YOU) are skipped.

        Returns list of Transaction objects.
        """
        transactions = []

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text or "Transaction Details" not in text:
                    continue

                page_txns = self._parse_page_with_positions(page)
                transactions.extend(page_txns)

        return transactions

    def _parse_page_with_positions(self, page) -> List[Transaction]:
        """Parse a single page using positional word data."""
        words = page.extract_words()
        if not words:
            return []

        # Find column positions dynamically from headers
        credits_x1, charges_x1 = self._find_column_positions(words)
        if credits_x1 is None or charges_x1 is None:
            return []

        # Midpoint between Credits and Charges right edges
        column_threshold = (credits_x1 + charges_x1) / 2

        # Find where transaction data begins
        header_top = self._find_header_top(words)
        if header_top is None:
            return []

        # Group words into rows and parse each one
        rows = self._group_words_into_rows(words, header_top)

        transactions = []
        for row_words in rows:
            txn = self._parse_row(row_words, column_threshold)
            if txn:
                transactions.append(txn)

        return transactions

    def _find_column_positions(self, words: list) -> tuple:
        """Find right-edge x-positions of Credits and Charges headers.

        Only matches a Credits/Charges pair that appear on the same
        horizontal line (within 2 points vertically), which ensures we
        pick up the Transaction Details column headers and not the
        Account Summary section's unrelated "Credits" / "Charges" labels.
        """
        credits_words = [w for w in words if w['text'] == 'Credits']
        charges_words = [w for w in words if w['text'] == 'Charges']

        for cred in credits_words:
            for chg in charges_words:
                if abs(cred['top'] - chg['top']) < 2 and chg['x1'] > cred['x1']:
                    return cred['x1'], chg['x1']

        return None, None

    def _find_header_top(self, words: list) -> Optional[float]:
        """Find vertical position of the 'Trans Post Reference...' header row."""
        for w in words:
            if w['text'] == 'Trans':
                top = w['top']
                nearby = [nw['text'] for nw in words if abs(nw['top'] - top) < 2]
                if 'Post' in nearby and 'Reference' in nearby:
                    return top
        return None

    def _group_words_into_rows(self, words: list, header_top: float) -> list:
        """Group words below the header into rows by vertical position."""
        data_words = [w for w in words if w['top'] > header_top + 5]
        if not data_words:
            return []

        data_words.sort(key=lambda w: (w['top'], w['x0']))

        rows = []
        current_row = [data_words[0]]
        current_top = data_words[0]['top']

        for w in data_words[1:]:
            if abs(w['top'] - current_top) < 3:
                current_row.append(w)
            else:
                rows.append(current_row)
                current_row = [w]
                current_top = w['top']

        if current_row:
            rows.append(current_row)

        return rows

    def _parse_row(self, row_words: list, column_threshold: float) -> Optional[Transaction]:
        """Parse a row of positioned words into a Transaction."""
        if not row_words or len(row_words) < 4:
            return None

        # First two words must be dates (MM/DD)
        if not re.match(r'^\d{2}/\d{2}$', row_words[0]['text']):
            return None
        if not re.match(r'^\d{2}/\d{2}$', row_words[1]['text']):
            return None

        post_date = row_words[1]['text']

        # Find the amount: rightmost word matching a dollar amount pattern
        amount_word = None
        amount_idx = None
        for i in range(len(row_words) - 1, 1, -1):
            if re.match(r'^[\d,]+\.\d{2}$', row_words[i]['text']):
                amount_word = row_words[i]
                amount_idx = i
                break

        if amount_word is None or amount_idx is None:
            return None

        # Credit vs Charge based on x-position
        is_credit = amount_word['x1'] < column_threshold

        amount = self._parse_amount(amount_word['text'])
        if amount is None:
            return None

        # Description = words between reference number and amount
        if amount_idx < 4:
            return None

        description = ' '.join(w['text'] for w in row_words[3:amount_idx])

        # Skip payment rows
        if "PAYMENT THANK YOU" in description.upper():
            return None

        if not description or len(description) < 3:
            return None

        # Credits (refunds) stored as negative
        if is_credit:
            amount = -amount

        return Transaction(
            date=post_date,
            vendor=description,
            amount=amount
        )

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string to float."""
        cleaned = amount_str.replace('$', '').replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return None


class ChartOfAccountsParser:
    """Parses the Chart of Accounts PDF for funder, GL, and location codes."""

    def __init__(self):
        # Get base directory (works for both exe and source)
        base_dir = get_base_path()
        self.pdf_path = base_dir / "config" / "chart of accounts.pdf"

    def parse(self) -> tuple:
        """
        Parse the Chart of Accounts PDF and extract all code types.

        Returns tuple of (funder_codes, gl_codes, location_codes, program_codes, dept_codes)
        Each is a dict of {code: name}
        """
        funder_codes = {}
        gl_codes = {}
        location_codes = {}
        program_codes = {}
        dept_codes = {}

        if not self.pdf_path.exists():
            print(f"Warning: Chart of Accounts PDF not found at {self.pdf_path}")
            return funder_codes, gl_codes, location_codes, program_codes, dept_codes

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                # Extract tables from page
                tables = page.extract_tables()
                if not tables:
                    continue

                # Process each table
                for table in tables:
                    if not table or len(table) == 0:
                        continue

                    # Determine what type of codes this table contains by checking headers
                    table_type = None

                    # Check first few rows for headers
                    for row in table[:3]:  # Check first 3 rows for header
                        if not row:
                            continue

                        # Join all cells in the row and check for keywords
                        row_text = ' '.join([str(cell).upper() if cell else '' for cell in row])

                        if 'FUNDER CODE' in row_text or 'FUNDER' in row_text:
                            table_type = 'funder'
                            print(f"  Found Funder Code table")
                            break
                        elif 'EXP CODE' in row_text or 'GL CODE' in row_text or ('EXP' in row_text and 'CODE' in row_text):
                            table_type = 'gl'
                            print(f"  Found GL/EXP Code table")
                            break
                        elif 'LOC CODE' in row_text or 'LOCATION CODE' in row_text or ('LOC' in row_text and 'CODE' in row_text):
                            table_type = 'location'
                            print(f"  Found Location Code table")
                            break
                        elif 'PROG CODE' in row_text or 'PROGRAM CODE' in row_text or ('PROG' in row_text and 'CODE' in row_text):
                            table_type = 'program'
                            print(f"  Found Program Code table")
                            break
                        elif 'DEPT CODE' in row_text or 'DEPARTMENT CODE' in row_text or ('DEPT' in row_text and 'CODE' in row_text):
                            table_type = 'dept'
                            print(f"  Found Department Code table")
                            break

                    if not table_type:
                        continue

                    # Parse rows based on table type
                    for row in table:
                        if not row or len(row) == 0:
                            continue

                        # First column should be the code
                        code_cell = str(row[0]).strip() if row[0] else ''
                        # Second column (or rest) should be the name
                        name_cell = str(row[1]).strip() if len(row) > 1 and row[1] else ''

                        # Skip empty or header rows
                        if not code_cell or not name_cell:
                            continue
                        if 'CODE' in code_cell.upper() or 'CODE' in name_cell.upper():
                            continue

                        # Parse based on table type
                        if table_type == 'funder':
                            # 4-digit funder codes
                            if re.match(r'^\d{4}$', code_cell):
                                funder_codes[code_cell] = name_cell

                        elif table_type == 'gl':
                            # 5-digit GL codes
                            if re.match(r'^\d{5}$', code_cell):
                                gl_codes[code_cell] = name_cell

                        elif table_type == 'location':
                            # 2-digit location codes
                            if re.match(r'^\d{2}$', code_cell):
                                location_codes[code_cell] = name_cell

                        elif table_type == 'program':
                            # Program codes (flexible length, numeric)
                            if re.match(r'^\d+$', code_cell):
                                program_codes[code_cell] = name_cell

                        elif table_type == 'dept':
                            # Department codes (flexible length, numeric)
                            if re.match(r'^\d+$', code_cell):
                                dept_codes[code_cell] = name_cell

        return funder_codes, gl_codes, location_codes, program_codes, dept_codes
