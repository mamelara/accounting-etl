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

### Step 5: Add Credit Card Statements

1. Download your Wells Fargo credit card statements as PDFs from your bank
2. In the **AccountingETL** folder, open the **downloads** folder
3. Copy all your statement PDFs into this folder

### Step 6: Run the Application

1. Go back to the main **AccountingETL** folder
2. Double-click on **AccountingETL.exe**
3. A black window will appear showing progress
4. Wait for it to process (usually takes 5-30 seconds)
5. When you see "✓ Success! Excel saved to:", it's done
6. Press **Enter** to close the window

### Step 7: Open Your Excel File

1. Go to the **downloads** folder
2. Look for a file named like: **credit_card_transactions_20240210_143015.xlsx**
   - The numbers are the date and time it was created
3. Double-click to open it in Excel

### Step 8: Fill Out the Spreadsheet

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
10. **Receipt_Received** - Type "Yes" or "No" for each transaction

### Step 9: Save and Clean Up

1. **Save your Excel file** (Ctrl+S or File > Save)
2. You can delete or move the PDF files from the **downloads** folder once you're done
3. The Excel file is your final output - save it wherever you need it

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

### No PDF files found

Make sure:
- Your statement PDFs are in the **downloads** folder
- The files are actually PDFs (end with .pdf)

### Dropdowns are empty in Excel

This means the Chart of Accounts wasn't read correctly:
- Check that your PDF has sections labeled: "Funder Code", "EXP CODE", "LOC CODE", "PROG CODE", "DEPT CODE"
- Make sure the PDF is readable (not a scanned image)

---

## Tips

- **Run it regularly**: Process statements monthly or weekly
- **Keep old Excel files**: Save them with descriptive names like "January_2024_Statements.xlsx"
- **Check your work**: Always review the Excel file before submitting it
- **Contact support**: If something isn't working, create an issue at: https://github.com/mamelara/accounting-etl/issues

---

## Folder Structure

After setup, your folder should look like this:

```
AccountingETL/
├── AccountingETL.exe          ← Double-click this to run
├── config/
│   └── chart of accounts.pdf  ← Your GL codes (you provide this)
├── downloads/
│   ├── statement1.pdf         ← Wells Fargo statements (you provide these)
│   ├── statement2.pdf
│   └── transactions_*.xlsx    ← Generated Excel files (output)
├── data/                      ← Database (created automatically)
└── README.txt
```

---

## Need Help?

If you run into issues:
1. Check the troubleshooting section above
2. Ask your husband
3. Create an issue on GitHub: https://github.com/mamelara/accounting-etl/issues
