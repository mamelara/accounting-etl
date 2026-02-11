"""
Accounting ETL - Main Entry Point
Automated credit card statement processing for accountants.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from accounting_etl.config import Config
from accounting_etl.pdf_parser import StatementParser, ChartOfAccountsParser
from accounting_etl.database import Database
from accounting_etl.excel_builder import ExcelBuilder
from accounting_etl.update_checker import UpdateChecker


def main():
    """Main application entry point."""
    print("=" * 60)
    print("Accounting ETL - Credit Card Statement Processor")
    print("=" * 60)

    # Get script directory for relative paths
    script_dir = Path(__file__).parent.parent.parent

    # Check for updates
    update_checker = UpdateChecker()
    update_checker.check_and_notify()

    # Load configuration (for future config options)
    config = Config.load()
    if not config:
        print("\nWarning: Configuration not found. Using defaults.")
        config = Config()

    # Initialize database
    db = Database()
    db.initialize()

    # Load codes from Chart of Accounts
    print("\n[1/4] Loading codes from Chart of Accounts...")
    coa_parser = ChartOfAccountsParser()
    funder_codes, gl_codes, location_codes, program_codes, dept_codes = coa_parser.parse()

    print(f"  Funder codes: {len(funder_codes)}")
    if len(funder_codes) > 0:
        print(f"    Sample: {list(funder_codes.items())[:2]}")

    print(f"  GL codes: {len(gl_codes)}")
    if len(gl_codes) > 0:
        print(f"    Sample: {list(gl_codes.items())[:2]}")

    print(f"  Location codes: {len(location_codes)}")
    if len(location_codes) > 0:
        print(f"    Sample: {list(location_codes.items())[:2]}")

    print(f"  Program codes: {len(program_codes)}")
    if len(program_codes) > 0:
        print(f"    Sample: {list(program_codes.items())[:2]}")

    print(f"  Department codes: {len(dept_codes)}")
    if len(dept_codes) > 0:
        print(f"    Sample: {list(dept_codes.items())[:2]}")

    if not any([funder_codes, gl_codes, location_codes, program_codes, dept_codes]):
        print("Warning: No codes loaded. Dropdowns will be empty.")

    # Find PDFs in downloads folder
    print("\n[2/4] Scanning for credit card statement PDFs...")
    downloads_dir = script_dir / "downloads"
    downloads_dir.mkdir(exist_ok=True)

    # Find all PDFs recursively in downloads folder
    pdf_files = list(downloads_dir.rglob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in downloads/ folder.")
        print("\nPlease:")
        print("1. Download your credit card statement PDFs")
        print("2. Place them in the downloads/ folder")
        print("3. Run this program again")
        input("\nPress Enter to exit...")
        return 0

    print(f"Found {len(pdf_files)} PDF file(s)")
    for pdf in pdf_files:
        print(f"  - {pdf}")

    # Process each statement
    print("\n[3/4] Processing statements...")
    all_transactions = []

    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")
        parser = StatementParser(pdf_path)
        transactions = parser.parse()

        # Enrich with vendor mappings
        for txn in transactions:
            vendor_mapping = db.get_vendor_mapping(txn.vendor)
            if vendor_mapping:
                txn.gl_account = vendor_mapping.gl_account
                txn.location = vendor_mapping.location
                txn.program = vendor_mapping.program
                txn.funder = vendor_mapping.funder
                txn.department = vendor_mapping.department

        all_transactions.extend(transactions)
        print(f"  Extracted {len(transactions)} transactions")

    print(f"\nTotal transactions: {len(all_transactions)}")

    if len(all_transactions) == 0:
        print("\n⚠ No transactions were extracted from the PDFs.")
        print("Please check that the PDFs are valid credit card statements.")
        input("\nPress Enter to exit...")
        return 1

    # Generate Excel
    print("\n[4/4] Generating Excel spreadsheet...")
    builder = ExcelBuilder()
    output_path = builder.build(all_transactions, downloads_dir, funder_codes, gl_codes, location_codes, program_codes, dept_codes)

    print(f"\n✓ Success! Excel saved to: {output_path}")
    print("\nNext steps:")
    print("1. Open the Excel file")
    print("2. Fill in the 'Description' column")
    print("3. Select codes from dropdowns:")
    print("   - G/L Account (GL codes)")
    print("   - Location (location codes)")
    print("   - Program (program codes)")
    print("   - Funder (funder codes)")
    print("   - Dept (department codes)")
    print("4. Check 'Receipt_Received' column")
    print("5. Delete processed PDFs from downloads/ folder when done")

    input("\nPress Enter to exit...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
