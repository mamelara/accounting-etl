# Accounting ETL

Automated credit card statement processing for accountants. Extracts transaction data from PDF statements and generates pre-populated Excel spreadsheets.

## Features

- **PDF Parsing**: Extracts Date, Vendor, and Amount from credit card statement PDFs
- **Smart GL Coding**: Remembers vendor-to-GL code mappings for faster processing
- **Excel Generation**: Creates ready-to-review spreadsheets with all required columns
- **Receipt Tracking**: Tracks which transactions have receipts
- **Auto-Updates**: Checks for new versions automatically

## Installation

### Option 1: Development (with uv)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone <repo-url>
cd accounting-etl
uv sync

# Run
uv run python src/accounting_etl/main.py
```

### Option 2: Windows (Pre-built)

1. Download the latest release from GitHub Releases
2. Extract the `AccountingETL` folder to your computer
3. Place your `chart of accounts.pdf` file in the `config/` folder
4. Double-click `AccountingETL.exe` to run

## Configuration

The application requires a **Chart of Accounts PDF** file:

1. Place your Chart of Accounts PDF in the `config/` folder
2. Name it exactly: `chart of accounts.pdf`
3. The PDF should contain five types of codes with headers:
   - **Funder Code** - 4-digit codes (e.g., `0000 GENERAL UNRESTRICTED`)
   - **EXP CODE** - 5-digit GL codes (e.g., `51000 Office Supplies`)
   - **LOC CODE** - 2-digit location codes (e.g., `01 Main Office`)
   - **PROG CODE** - Program codes (e.g., `100 Youth Services`)
   - **DEPT CODE** - Department codes (e.g., `200 Administration`)

No config.json file is needed - all paths are relative to the application directory.

## Usage

1. **Download statements** - Manually download your credit card statement PDFs
2. **Place in downloads folder** - Put them in the `downloads/` folder
3. **Run the application** - It will process all PDFs in the downloads folder
4. **Review the Excel file** - Check the generated spreadsheet
5. **Fill in descriptions** - Add descriptions for each transaction
6. **Select codes from dropdowns** - Choose GL Account, Location, Program, Funder, and Dept from dropdowns
7. **Check receipts** - Mark which transactions have receipts
8. **Clean up** - Delete processed PDFs from `downloads/` folder when done

## Excel Output Format

The generated Excel file contains these columns:

- **Date** - Transaction date (from PDF)
- **Vendor** - Vendor name (from PDF)
- **Description** - Empty (you fill this in)
- **G/L Account** - Dropdown with GL codes from Chart of Accounts
- **Location** - Dropdown with location codes from Chart of Accounts
- **Program** - Dropdown with program codes from Chart of Accounts
- **Funder** - Dropdown with funder codes from Chart of Accounts
- **Dept** - Dropdown with department codes from Chart of Accounts
- **Amount** - Transaction amount (from PDF)
- **Receipt_Received** - Checkbox (you check these)

## Building for Windows

To build the Windows executable:

```bash
# Install build dependencies
uv sync --extra build

# Build with PyInstaller
uv run pyinstaller build/AccountingETL.spec

# Output will be in dist/AccountingETL/
```

## Project Structure

```
accounting-etl/
├── src/accounting_etl/     # Source code
│   ├── main.py            # Entry point
│   ├── pdf_parser.py      # PDF text extraction
│   ├── database.py        # SQLite vendor mappings
│   ├── excel_builder.py   # Excel generation
│   └── update_checker.py  # Version checking
├── config/                # Configuration files
├── downloads/             # Place your PDFs here
├── data/                  # SQLite database
├── build/                 # PyInstaller spec
└── dist/                  # Built executables
```

## License

MIT
