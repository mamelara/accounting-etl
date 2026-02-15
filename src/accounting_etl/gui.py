"""
Accounting ETL - GUI Application
Tkinter-based interface for processing credit card statement PDFs.
"""

import os
import sys
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext
from pathlib import Path

from accounting_etl.pdf_parser import StatementParser, ChartOfAccountsParser, get_base_path
from accounting_etl.database import Database
from accounting_etl.excel_builder import ExcelBuilder
from accounting_etl.update_checker import UpdateChecker


class PipelineRunner:
    """Runs the ETL pipeline with status callbacks instead of print()."""

    def __init__(self, pdf_paths: list[Path], status_callback):
        self.pdf_paths = pdf_paths
        self.log = status_callback

    def run(self) -> Path:
        """
        Execute the full pipeline and return the output Excel path.

        Raises Exception on failure.
        """
        base_dir = get_base_path()

        # Initialize database
        db = Database()
        db.initialize()

        # Step 1: Load chart of accounts
        self.log("[1/4] Loading Chart of Accounts...")
        coa_parser = ChartOfAccountsParser()
        funder_codes, gl_codes, location_codes, program_codes, dept_codes = coa_parser.parse()

        code_summary = []
        if gl_codes:
            code_summary.append(f"{len(gl_codes)} GL")
        if funder_codes:
            code_summary.append(f"{len(funder_codes)} Funder")
        if location_codes:
            code_summary.append(f"{len(location_codes)} Location")
        if program_codes:
            code_summary.append(f"{len(program_codes)} Program")
        if dept_codes:
            code_summary.append(f"{len(dept_codes)} Dept")

        if code_summary:
            self.log(f"  Loaded {', '.join(code_summary)} codes")
        else:
            self.log("  Warning: No codes loaded. Dropdowns will be empty.")

        # Step 2: Process each PDF
        self.log(f"\n[2/4] Processing {len(self.pdf_paths)} PDF(s)...")
        all_transactions = []

        for pdf_path in self.pdf_paths:
            self.log(f"  Parsing: {pdf_path.name}")
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
            self.log(f"    Extracted {len(transactions)} transactions")

        self.log(f"\n[3/4] Total transactions: {len(all_transactions)}")

        if len(all_transactions) == 0:
            raise ValueError(
                "No transactions were extracted from the PDFs.\n"
                "Please check that the files are valid Wells Fargo credit card statements."
            )

        # Step 3: Generate Excel
        self.log("\n[4/4] Generating Excel spreadsheet...")
        downloads_dir = base_dir / "downloads"
        downloads_dir.mkdir(exist_ok=True)

        builder = ExcelBuilder()
        output_path = builder.build(
            all_transactions, downloads_dir,
            funder_codes, gl_codes, location_codes, program_codes, dept_codes
        )

        self.log(f"\nSaved to: {output_path.name}")
        return output_path


def open_file_with_default_app(filepath: Path):
    """Open a file with the system's default application."""
    if platform.system() == "Windows":
        os.startfile(filepath)
    elif platform.system() == "Darwin":
        subprocess.run(["open", str(filepath)])
    else:
        subprocess.run(["xdg-open", str(filepath)])


class AccountingETLApp:
    """Main GUI application."""

    WINDOW_WIDTH = 600
    WINDOW_HEIGHT = 520
    PAD = 12
    BG_COLOR = "#f0f0f0"
    ACCENT_COLOR = "#366092"
    BUTTON_FG = "#ffffff"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Accounting ETL")
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_COLOR)

        self.pdf_paths: list[Path] = []
        self.processing = False

        self._build_ui()

    # -- UI construction ---------------------------------------------------

    def _build_ui(self):
        pad = self.PAD

        # Title
        title = tk.Label(
            self.root, text="Credit Card Statement Processor",
            font=("Arial", 14, "bold"), bg=self.BG_COLOR, fg=self.ACCENT_COLOR
        )
        title.pack(pady=(pad, 4))

        subtitle = tk.Label(
            self.root, text="Add Wells Fargo statement PDFs, then generate your spreadsheet.",
            font=("Arial", 9), bg=self.BG_COLOR, fg="#666666"
        )
        subtitle.pack(pady=(0, pad))

        # -- File list -----------------------------------------------------
        list_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        list_frame.pack(fill=tk.X, padx=pad)

        tk.Label(
            list_frame, text="PDF Files:", font=("Arial", 10, "bold"),
            bg=self.BG_COLOR, anchor="w"
        ).pack(fill=tk.X)

        listbox_frame = tk.Frame(list_frame, bd=1, relief=tk.SUNKEN)
        listbox_frame.pack(fill=tk.X, pady=(4, 0))

        self.file_listbox = tk.Listbox(
            listbox_frame, height=6, font=("Arial", 9),
            selectmode=tk.EXTENDED, activestyle="none"
        )
        scrollbar = tk.Scrollbar(listbox_frame, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # -- Buttons row ---------------------------------------------------
        btn_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        btn_frame.pack(fill=tk.X, padx=pad, pady=(8, 0))

        self.browse_btn = tk.Button(
            btn_frame, text="Browse Files...", command=self._browse_files,
            font=("Arial", 9), padx=12, pady=4
        )
        self.browse_btn.pack(side=tk.LEFT)

        self.clear_btn = tk.Button(
            btn_frame, text="Clear All", command=self._clear_files,
            font=("Arial", 9), padx=12, pady=4
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.remove_btn = tk.Button(
            btn_frame, text="Remove Selected", command=self._remove_selected,
            font=("Arial", 9), padx=12, pady=4
        )
        self.remove_btn.pack(side=tk.LEFT, padx=(8, 0))

        # -- Status log ----------------------------------------------------
        log_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=pad, pady=(pad, 0))

        tk.Label(
            log_frame, text="Status:", font=("Arial", 10, "bold"),
            bg=self.BG_COLOR, anchor="w"
        ).pack(fill=tk.X)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=8, font=("Consolas", 9), state=tk.DISABLED,
            wrap=tk.WORD, bd=1, relief=tk.SUNKEN
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # -- Generate button -----------------------------------------------
        self.generate_btn = tk.Button(
            self.root, text="Generate Spreadsheet", command=self._generate,
            font=("Arial", 11, "bold"), bg=self.ACCENT_COLOR, fg=self.BUTTON_FG,
            activebackground="#2a4d75", activeforeground=self.BUTTON_FG,
            padx=20, pady=8, relief=tk.RAISED, bd=1
        )
        self.generate_btn.pack(pady=pad)

        self._log_status("Ready. Add PDF files to get started.")

    # -- Actions -----------------------------------------------------------

    def _browse_files(self):
        filepaths = filedialog.askopenfilenames(
            title="Select Credit Card Statement PDFs",
            filetypes=[("PDF Files", "*.pdf")],
        )
        if filepaths:
            for fp in filepaths:
                path = Path(fp)
                if path not in self.pdf_paths:
                    self.pdf_paths.append(path)
                    self.file_listbox.insert(tk.END, path.name)
            self._log_status(f"{len(self.pdf_paths)} file(s) ready.")

    def _clear_files(self):
        self.pdf_paths.clear()
        self.file_listbox.delete(0, tk.END)
        self._log_status("File list cleared.")

    def _remove_selected(self):
        selected = list(self.file_listbox.curselection())
        if not selected:
            return
        # Remove in reverse order so indices stay valid
        for idx in reversed(selected):
            self.file_listbox.delete(idx)
            del self.pdf_paths[idx]
        self._log_status(f"{len(self.pdf_paths)} file(s) ready.")

    def _generate(self):
        if self.processing:
            return
        if not self.pdf_paths:
            self._log_status("Please add at least one PDF file first.")
            return

        self.processing = True
        self._set_buttons_enabled(False)
        self._clear_log()
        self._log_status("Starting processing...\n")

        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def _run_pipeline(self):
        """Runs the pipeline on a background thread."""
        try:
            runner = PipelineRunner(
                pdf_paths=list(self.pdf_paths),
                status_callback=lambda msg: self.root.after(0, self._log_status, msg),
            )
            output_path = runner.run()

            def on_success():
                self._log_status("\nOpening spreadsheet...")
                try:
                    open_file_with_default_app(output_path)
                except Exception as e:
                    self._log_status(f"Could not open file automatically: {e}")
                    self._log_status(f"File is at: {output_path}")
                self._log_status("\nDone!")
                self.processing = False
                self._set_buttons_enabled(True)

            self.root.after(0, on_success)

        except Exception as e:
            def on_error():
                self._log_status(f"\nError: {e}")
                self.processing = False
                self._set_buttons_enabled(True)

            self.root.after(0, on_error)

    # -- Helpers -----------------------------------------------------------

    def _log_status(self, message: str):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_buttons_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.browse_btn.configure(state=state)
        self.clear_btn.configure(state=state)
        self.remove_btn.configure(state=state)
        self.generate_btn.configure(state=state)

    def run(self):
        self.root.mainloop()


def main():
    app = AccountingETLApp()
    app.run()


if __name__ == "__main__":
    main()
