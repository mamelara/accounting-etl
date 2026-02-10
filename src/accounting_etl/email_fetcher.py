"""Email fetching module for downloading credit card statements from Outlook."""

import imaplib
import email
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta


class OutlookEmailFetcher:
    """Fetches credit card statements from Outlook via IMAP."""
    
    def __init__(self, email: str, password: str, 
                 imap_server: str = "outlook.office365.com"):
        self.email = email
        self.password = password
        self.imap_server = imap_server
        self.connection: Optional[imaplib.IMAP4_SSL] = None
    
    def connect(self) -> None:
        """Connect to Outlook IMAP server."""
        self.connection = imaplib.IMAP4_SSL(self.imap_server)
        self.connection.login(self.email, self.password)
        self.connection.select('INBOX')
    
    def search_statements(self, 
                         sender_filter: str = "wellsfargo.com",
                         subject_keywords: Optional[List[str]] = None) -> List[str]:
        """
        Find emails matching credit statement criteria.
        
        Returns list of email IDs.
        """
        if subject_keywords is None:
            subject_keywords = ["statement", "credit card", "mastercard"]
        
        # Search last 30 days
        date_since = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
        
        # Build search criteria
        search_criteria = f'(SINCE "{date_since}" FROM "{sender_filter}")'
        
        _, message_ids = self.connection.search(None, search_criteria)
        email_ids = message_ids[0].split()
        
        # Filter by subject keywords
        matching_ids = []
        for email_id in email_ids:
            _, msg_data = self.connection.fetch(email_id, '(RFC822)')
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            subject = email_message['Subject'].lower()
            if any(keyword in subject for keyword in subject_keywords):
                matching_ids.append(email_id.decode())
        
        return matching_ids
    
    def download_attachments(self, email_id: str, 
                            base_download_dir: Path) -> List[Path]:
        """
        Download PDF attachments from email to month-organized folder.
        
        Returns list of downloaded file paths.
        """
        _, msg_data = self.connection.fetch(email_id.encode(), '(RFC822)')
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)
        
        # Create month-based folder: downloads/2024-01/
        current_month = datetime.now().strftime("%Y-%m")
        download_dir = base_download_dir / current_month
        download_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded_files = []
        
        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            
            filename = part.get_filename()
            if filename and filename.lower().endswith('.pdf'):
                # Check if already exists
                filepath = download_dir / filename
                if filepath.exists():
                    print(f"  Skipping {filename} - already exists")
                    continue
                
                # Download PDF
                with open(filepath, 'wb') as f:
                    f.write(part.get_payload(decode=True))
                downloaded_files.append(filepath)
                print(f"  Downloaded: {filepath}")
        
        return downloaded_files
    
    def disconnect(self) -> None:
        """Close IMAP connection."""
        if self.connection:
            self.connection.close()
            self.connection.logout()
