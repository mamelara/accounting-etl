# Accounting ETL - User Guide for Windows

## Quick Start Guide

### Step 1: Download the Application

1. Go to: https://github.com/mamelara/accounting-etl/releases/latest
2. Click on **AccountingETL-Windows.zip** to download it
3. Wait for the download to complete (it's about 50-100 MB)

### Step 2: Extract the Files

1. Find the downloaded file (usually in your **Downloads** folder)
2. Right-click on **AccountingETL-Windows.zip**
3. Click **Extract All...**
4. Click **Extract**
5. A new folder called **AccountingETL** will appear

### Step 3: Move to a Permanent Location (Optional but Recommended)

1. Move the **AccountingETL** folder to somewhere permanent like:
   - `C:\Users\YourName\Documents\AccountingETL`
   - Or your Desktop

### Step 4: Add Your Chart of Accounts

1. Open the **AccountingETL** folder
2. Open the **config** folder inside
3. Copy your **chart of accounts.pdf** file into this folder
4. Make sure it's named exactly: **chart of accounts.pdf** (lowercase, with spaces)

### Step 5: Download Credit Card Statements

1. Download your Wells Fargo credit card statements as PDFs from your bank
2. Save them anywhere you can find them (Desktop, Downloads, etc.)

### Step 6: Run the Application

1. Go to the main **AccountingETL** folder
2. Double-click on **AccountingETL.exe**
3. A window titled **"Accounting ETL"** will open
4. Click **Browse Files...** and select your Wells Fargo statement PDFs
   - You can select multiple files at once (hold **Ctrl** and click)
   - Or click Browse again to add more files later
5. Click **Generate Spreadsheet**
6. The status panel will show progress as each PDF is processed
7. When it finishes, the Excel file opens automatically

### Step 7: Fill Out the Spreadsheet

The Excel file has these columns:

1. **Date** - Already filled (from the statement)
2. **Vendor** - Already filled (from the statement)
3. **Description** - **YOU FILL THIS IN** - Add a description of what was purchased
4. **G/L Account** - **SELECT FROM DROPDOWN** - Click the cell, then click the dropdown arrow
5. **Location** - **SELECT FROM DROPDOWN**
6. **Program** - **SELECT FROM DROPDOWN**
7. **Funder** - **SELECT FROM DROPDOWN**
8. **Dept** - **SELECT FROM DROPDOWN**
9. **Amount** - Already filled (from the statement)
10. **Receipt_Received** - Click the checkbox when you have the receipt

### Step 8: Save and Clean Up

1. **Save your Excel file** (Ctrl+S or File > Save)
2. The Excel file is your final output - save it wherever you need it

---

## Troubleshooting

### "Windows protected your PC" message appears

This is normal for new applications:
1. Click **More info**
2. Click **Run anyway**

### "Chart of Accounts not found" message

Make sure:
- The file is in the **config** folder
- The file is named exactly: **chart of accounts.pdf** (all lowercase, with spaces)

### No transactions extracted from PDFs

Make sure:
- Your statement PDFs are downloaded directly from Wells Fargo (not scanned copies)
- The files are actually PDFs (end with .pdf)
- They are Wells Fargo credit card statements (not bank statements)

### Dropdowns are empty in Excel

This means the Chart of Accounts wasn't read correctly:
- Check that your PDF has sections labeled: "Funder Code", "EXP CODE", "LOC CODE", "PROG CODE", "DEPT CODE"
- Make sure the PDF is readable (not a scanned image)

### Excel file doesn't open automatically

The file is saved in the **downloads** folder inside the **AccountingETL** folder. Look for a file named like: **credit_card_transactions_20250210_143015.xlsx** (the numbers are the date and time it was created).

---

## Tips

- **Run it regularly**: Process statements monthly or weekly
- **Keep old Excel files**: Save them with descriptive names like "January_2025_Statements.xlsx"
- **Check your work**: Always review the Excel file before submitting it
- **Contact support**: If something isn't working, create an issue at: https://github.com/mamelara/accounting-etl/issues

---

## Folder Structure

After setup, your folder should look like this:

```
AccountingETL/
├── AccountingETL.exe          <- Double-click this to run
├── config/
│   └── chart of accounts.pdf  <- Your GL codes (you provide this)
├── downloads/
│   └── transactions_*.xlsx    <- Generated Excel files (output)
├── data/                      <- Database (created automatically)
└── README.txt
```

---

## Need Help?

If you run into issues:
1. Check the troubleshooting section above
2. Ask your husband
3. Create an issue on GitHub: https://github.com/mamelara/accounting-etl/issues
