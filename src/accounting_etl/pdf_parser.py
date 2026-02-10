"""PDF parsing for credit card statements and GL code lookups."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import pdfplumber


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
    """Parses Wells Fargo credit card statement PDFs to extract transactions."""

    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path

    def parse(self) -> List[Transaction]:
        """
        Parse the Wells Fargo PDF and extract all transactions.

        Expected format (text, not table):
        Trans Post Reference Number Description Credits Charges
        01/02 01/03 5543286QJ5WN288J6 AMAZON MKTPL*KA0S393X3 SEATTLE WA 39.12

        Returns list of Transaction objects.
        """
        transactions = []

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                # Extract text from the page
                text = page.extract_text()
                if not text or "Transaction Details" not in text:
                    continue

                # Split into lines and find transaction section
                lines = text.split('\n')

                # Find the start of transaction data
                in_transactions = False
                for line in lines:
                    # Start parsing after the header row
                    if "Transaction Details" in line:
                        in_transactions = True
                        continue

                    # Skip the column header row
                    if in_transactions and "Trans Post Reference Description" in line:
                        continue

                    # Parse transaction lines
                    if in_transactions:
                        txn = self._parse_transaction_line(line)
                        if txn:
                            transactions.append(txn)

        return transactions

    def _parse_transaction_line(self, line: str) -> Optional[Transaction]:
        """
        Parse a Wells Fargo transaction line into a Transaction.

        Expected format:
        01/02 01/03 5543286QJ5WN288J6 AMAZON MKTPL*KA0S393X3 SEATTLE WA 39.12

        Format breakdown:
        - Trans date (MM/DD)
        - Post date (MM/DD)
        - Reference number
        - Description (multiple words)
        - Amount (last number on line, could be in Credits or Charges column)
        """
        import re

        if not line or not line.strip():
            return None

        # Skip empty or header-like lines
        line = line.strip()
        if len(line) < 10:
            return None

        # Match pattern: date date reference_num description amount
        # Pattern: MM/DD MM/DD ALPHANUMERIC [words] NUMBER
        pattern = r'^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(\S+)\s+(.+?)\s+([\d,]+\.?\d*)$'
        match = re.match(pattern, line)

        if not match:
            return None

        trans_date = match.group(1)
        post_date = match.group(2)
        reference_num = match.group(3)
        description = match.group(4).strip()
        amount_str = match.group(5)

        # Skip payment rows
        if "PAYMENT THANK YOU" in description.upper():
            return None

        # Skip if no description
        if not description or len(description) < 3:
            return None

        # Parse amount
        amount = self._parse_amount(amount_str)
        if amount is None:
            return None

        return Transaction(
            date=post_date,  # Use post date
            vendor=description,
            amount=amount
        )

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string to float."""
        # Remove dollar signs, commas, and whitespace
        cleaned = amount_str.replace('$', '').replace(',', '').strip()

        try:
            return float(cleaned)
        except ValueError:
            return None


class ChartOfAccountsParser:
    """Parses the Chart of Accounts PDF for funder, GL, and location codes."""

    def __init__(self):
        # Hardcoded path relative to script location
        script_dir = Path(__file__).parent.parent.parent
        self.pdf_path = script_dir / "config" / "chart of accounts.pdf"

    def parse(self) -> tuple:
        """
        Parse the Chart of Accounts PDF and extract all code types.

        Returns tuple of (funder_codes, gl_codes, location_codes)
        Each is a dict of {code: name}
        """
        import re

        funder_codes = {}
        gl_codes = {}
        location_codes = {}

        if not self.pdf_path.exists():
            print(f"Warning: Chart of Accounts PDF not found at {self.pdf_path}")
            return funder_codes, gl_codes, location_codes

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

        return funder_codes, gl_codes, location_codes
