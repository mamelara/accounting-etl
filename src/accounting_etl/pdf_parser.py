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

    Uses pdfplumber's positional word extraction (extract_words()) instead of
    plain text extraction (extract_text()). Each word comes with its bounding
    box coordinates (x0, x1, top, bottom), which lets us determine *which
    column* a dollar amount sits in -- something plain text cannot do because
    it flattens both columns into one string.

    Algorithm overview (per page):

        1. _find_column_positions()  -- Locate "Credits" and "Charges" header
           words and read their right-edge x-coordinates (x1).
        2. Compute column_threshold  -- Midpoint between the two x1 values.
           Amounts left of this line are credits; right are charges.
        3. _find_header_top()        -- Find the "Trans  Post  Reference..."
           sub-header row to know where actual data rows begin.
        4. _group_words_into_rows()  -- Cluster all words below the header
           into horizontal rows based on vertical proximity.
        5. _parse_row()              -- For each row, extract the date, vendor
           description, and amount, then classify credit vs charge.

    Wells Fargo PDF layout (Transaction Details section):

        Trans  Post  Reference Number       Credits  Charges
        -----  ----  ---------------------- -------  -------
        01/03  01/03  2466...  AMAZON ...              39.12
        01/05  01/06  8832...  REFUND VENDOR  15.00
        01/15  01/15  9921...  PAYMENT THANK YOU      500.00  <- skipped

    Why not extract_text()?
        extract_text() produces "01/03 01/03 2466... AMAZON ... 39.12" --
        there is no way to tell if 39.12 was under Credits or Charges.
        extract_words() preserves the x-position of "39.12" so we can
        compare it to the column headers and classify it unambiguously.
    """

    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path

    def parse(self) -> List[Transaction]:
        """Parse the Wells Fargo PDF and return all transactions.

        Iterates every page of the PDF. Pages that don't contain the text
        "Transaction Details" are skipped (e.g. summary pages, disclosures).

        Each qualifying page is parsed with _parse_page_with_positions(),
        which uses word-level bounding boxes to classify amounts as credits
        or charges. Payment rows ("PAYMENT THANK YOU") are excluded.
        Credits (refunds) are returned as negative amounts.

        Returns:
            List of Transaction objects, one per line item.
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
        """Parse a single page using positional word data.

        This is the main per-page orchestrator. It:

        1. Extracts all words with bounding boxes via pdfplumber.
        2. Finds the Credits/Charges column x-positions from their headers.
        3. Computes a midpoint threshold to classify amounts by column.
        4. Locates the "Trans Post Reference..." header to find where
           transaction rows start vertically.
        5. Groups words into rows and parses each row into a Transaction.

        Returns empty list if the page has no extractable words or is
        missing the expected column headers / table header.
        """
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
        """Find the right-edge x-positions of the Credits and Charges headers.

        Wells Fargo statements have two places where "Credits" and "Charges"
        appear as words:

            1. Account Summary section (page 1 only) -- these are on
               DIFFERENT vertical lines, e.g.:
                   "Credits"  at top=120
                   "Charges"  at top=145

            2. Transaction Details section -- these are on the SAME line,
               acting as column headers above the transaction rows:
                   "Credits"  at top=210, x1=501.6
                   "Charges"  at top=210, x1=572.3

        We only want case (2). The filter requires both words to be within
        2 vertical points of each other (same line) and "Charges" to be
        to the right of "Credits".

        Returns the right-edge x-coordinate (x1) of each header:

            x0        x1
            |         |
            | Credits |         | Charges |
                      ^                   ^
                  credits_x1          charges_x1
                   (~501.6)            (~572.3)

        These x1 values are the alignment anchors. Dollar amounts in each
        column right-align to these same x-positions.

        Returns:
            (credits_x1, charges_x1) or (None, None) if not found.
        """
        credits_words = [w for w in words if w['text'] == 'Credits']
        charges_words = [w for w in words if w['text'] == 'Charges']

        for cred in credits_words:
            for chg in charges_words:
                if abs(cred['top'] - chg['top']) < 2 and chg['x1'] > cred['x1']:
                    return cred['x1'], chg['x1']

        return None, None

    def _find_header_top(self, words: list) -> Optional[float]:
        """Find the vertical position of the transaction table sub-header.

        The Transaction Details section has a sub-header row that looks like:

            Trans  Post  Reference Number  Credits  Charges

        We locate it by finding the word "Trans" and confirming that "Post"
        and "Reference" appear on the same horizontal line (within 2 points).

        Returns:
            The 'top' coordinate (vertical position from page top, in PDF
            points) of this header row. All transaction data rows appear
            below this y-value. Returns None if not found.
        """
        for w in words:
            if w['text'] == 'Trans':
                top = w['top']
                nearby = [nw['text'] for nw in words if abs(nw['top'] - top) < 2]
                if 'Post' in nearby and 'Reference' in nearby:
                    return top
        return None

    def _group_words_into_rows(self, words: list, header_top: float) -> list:
        """Group all words below the table header into horizontal rows.

        Takes every word whose 'top' is more than 5 points below the header
        (to skip the header text itself), sorts by vertical then horizontal
        position, and clusters words that are within 3 vertical points of
        each other into the same row.

        Example: given these words (simplified):

            top=220  "01/03"  "01/03"  "2466..."  "AMAZON"  "..."  "39.12"
            top=220  (all on the same line, within 3pts of each other)
            top=235  "01/05"  "01/06"  "8832..."  "REFUND"  "..."  "15.00"

        This produces two row groups:
            Row 1: [01/03, 01/03, 2466..., AMAZON, ..., 39.12]
            Row 2: [01/05, 01/06, 8832..., REFUND, ..., 15.00]

        Words within each row are sorted left-to-right by x0 (left edge).

        Args:
            words:      All words on the page (from extract_words()).
            header_top: The 'top' value of the "Trans Post Reference..."
                        header row, as returned by _find_header_top().

        Returns:
            List of rows, where each row is a list of word dicts sorted
            left-to-right. Non-data rows (footers, subtotals, page
            numbers) are included here but filtered out later in
            _parse_row() because they won't match the expected date format.
        """
        header_buffer = 5
        data_words = [w for w in words if w['top'] > header_top + header_buffer]
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
        """Parse a single row of positioned words into a Transaction.

        A valid transaction row in the PDF looks like:

            index:  [0]     [1]     [2]       [3..N-1]           [N]
            word:   01/03   01/03   2466...   AMAZON MKTPL...    39.12
                    ^date   ^post   ^ref#     ^vendor/descrip    ^amount

        Validation steps:
            1. Row must have at least 4 words.
            2. Words [0] and [1] must be dates matching MM/DD.
            3. Rightmost word matching a dollar pattern (\\d+.\\d{2}) is
               the amount. We scan right-to-left to find it.
            4. Words between index 3 and the amount index form the vendor
               description.
            5. "PAYMENT THANK YOU" descriptions are skipped entirely.

        Credit vs Charge classification:

            The amount word has an x1 (right edge) value from the PDF.
            We compare it to column_threshold (midpoint of the Credits
            and Charges header x1 values):

            PDF x-axis:
            0         credits_x1   threshold   charges_x1       page edge
            |              |           |            |                |
            |              |  <-credit | charge->   |                |
            |              |           |            |                |
            |           "15.00"        |         "39.12"             |
            |              ^           |            ^                |
            |          x1=501         536.9      x1=571             |

            amount_word['x1'] < column_threshold  -->  it's a Credit
            amount_word['x1'] >= column_threshold -->  it's a Charge

        Credits (refunds) are stored as negative amounts in the output.

        Args:
            row_words:        List of word dicts for this row, sorted
                              left-to-right.
            column_threshold: The x-coordinate midpoint between Credits
                              and Charges columns. Amounts with x1 left
                              of this value are credits.

        Returns:
            A Transaction, or None if the row is not a valid transaction
            (e.g. subtotal line, footer, payment row, or too few words).
        """
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
        """Parse a dollar amount string like '1,234.56' into a float.

        Strips any '$' signs and commas before converting. Returns None
        if the string cannot be parsed as a number.
        """
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
