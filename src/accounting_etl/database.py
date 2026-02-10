"""SQLite database for storing vendor-to-GL code mappings."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VendorMapping:
    """Maps a vendor name to GL codes."""
    vendor: str
    gl_account: str
    location: str
    program: str
    funder: str
    department: str


class Database:
    """Manages SQLite database for vendor mappings."""

    def __init__(self, db_path: Path = None):
        if db_path is None:
            # Default to data/accounting.db relative to script location
            script_dir = Path(__file__).parent.parent.parent
            db_path = script_dir / "data" / "accounting.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def initialize(self) -> None:
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create vendor mappings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendor_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT UNIQUE NOT NULL,
                gl_account TEXT,
                location TEXT,
                program TEXT,
                funder TEXT,
                department TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on vendor name for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vendor_name 
            ON vendor_mappings(vendor)
        """)
        
        conn.commit()
    
    def get_vendor_mapping(self, vendor: str) -> Optional[VendorMapping]:
        """
        Get GL code mapping for a vendor.
        
        Uses fuzzy matching for vendor names.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Try exact match first
        cursor.execute(
            "SELECT * FROM vendor_mappings WHERE vendor = ?",
            (vendor,)
        )
        row = cursor.fetchone()
        
        if row:
            return VendorMapping(
                vendor=row['vendor'],
                gl_account=row['gl_account'],
                location=row['location'],
                program=row['program'],
                funder=row['funder'],
                department=row['department']
            )
        
        # Try fuzzy match (case-insensitive, partial match)
        cursor.execute(
            "SELECT * FROM vendor_mappings WHERE LOWER(vendor) LIKE LOWER(?)",
            (f"%{vendor}%",)
        )
        row = cursor.fetchone()
        
        if row:
            return VendorMapping(
                vendor=row['vendor'],
                gl_account=row['gl_account'],
                location=row['location'],
                program=row['program'],
                funder=row['funder'],
                department=row['department']
            )
        
        return None
    
    def save_vendor_mapping(self, mapping: VendorMapping) -> None:
        """Save or update vendor mapping."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO vendor_mappings 
            (vendor, gl_account, location, program, funder, department)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(vendor) DO UPDATE SET
                gl_account = excluded.gl_account,
                location = excluded.location,
                program = excluded.program,
                funder = excluded.funder,
                department = excluded.department,
                updated_at = CURRENT_TIMESTAMP
        """, (
            mapping.vendor,
            mapping.gl_account,
            mapping.location,
            mapping.program,
            mapping.funder,
            mapping.department
        ))
        
        conn.commit()
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
