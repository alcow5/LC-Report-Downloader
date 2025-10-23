import sys
import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QTableWidget, QTableWidgetItem, QMessageBox,
                            QProgressBar, QFileDialog, QDateEdit)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QIcon
from MVC import get_token, download_reports, generate_hmac_header, REPORT_URL_BASE
import requests
import json

class LCReportDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LC Report Downloader")
        self.setMinimumSize(800, 600)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Credentials section
        cred_layout = QHBoxLayout()
        
        # Username
        username_layout = QVBoxLayout()
        username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        cred_layout.addLayout(username_layout)
        
        # Password
        password_layout = QVBoxLayout()
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        cred_layout.addLayout(password_layout)
        
        # HMAC User
        hmac_user_layout = QVBoxLayout()
        hmac_user_label = QLabel("HMAC User:")
        self.hmac_user_input = QLineEdit()
        hmac_user_layout.addWidget(hmac_user_label)
        hmac_user_layout.addWidget(self.hmac_user_input)
        cred_layout.addLayout(hmac_user_layout)
        
        # HMAC Key
        hmac_key_layout = QVBoxLayout()
        hmac_key_label = QLabel("HMAC Key:")
        self.hmac_key_input = QLineEdit()
        self.hmac_key_input.setEchoMode(QLineEdit.Password)
        hmac_key_layout.addWidget(hmac_key_label)
        hmac_key_layout.addWidget(self.hmac_key_input)
        cred_layout.addLayout(hmac_key_layout)
        
        layout.addLayout(cred_layout)
        
        # Date range selection
        date_layout = QHBoxLayout()
        start_date_label = QLabel("Start Date:")
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addDays(-15))
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setMaximumDate(QDate.currentDate())
        self.start_date_edit.setMinimumDate(QDate.currentDate().addYears(-5))
        
        end_date_label = QLabel("End Date:")
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setMaximumDate(QDate.currentDate())
        self.end_date_edit.setMinimumDate(QDate.currentDate().addYears(-5))
        
        date_layout.addWidget(start_date_label)
        date_layout.addWidget(self.start_date_edit)
        date_layout.addWidget(end_date_label)
        date_layout.addWidget(self.end_date_edit)
        date_layout.addStretch()
        layout.addLayout(date_layout)
        
        # Connect button
        connect_button = QPushButton("Connect & Load Reports")
        connect_button.clicked.connect(self.load_reports)
        layout.addWidget(connect_button)
        
        # Reports table
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(2)
        self.reports_table.setHorizontalHeaderLabels(["Report Name", "Download"])
        self.reports_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.reports_table)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Load saved credentials if they exist
        self.load_saved_credentials()
        
    def load_saved_credentials(self):
        """Load saved credentials from environment variables"""
        self.username_input.setText(os.getenv("GATEWAY_USERNAME", ""))
        self.hmac_user_input.setText(os.getenv("HMAC_USER", ""))
        
    def save_credentials(self):
        """Save credentials to environment variables"""
        # Clear previous credentials first
        if "GATEWAY_USERNAME" in os.environ:
            del os.environ["GATEWAY_USERNAME"]
        if "GATEWAY_PASSWORD" in os.environ:
            del os.environ["GATEWAY_PASSWORD"]
        if "HMAC_USER" in os.environ:
            del os.environ["HMAC_USER"]
        if "HMAC_KEY" in os.environ:
            del os.environ["HMAC_KEY"]
            
        # Set new credentials
        os.environ["GATEWAY_USERNAME"] = self.username_input.text()
        os.environ["GATEWAY_PASSWORD"] = self.password_input.text()
        os.environ["HMAC_USER"] = self.hmac_user_input.text()
        os.environ["HMAC_KEY"] = self.hmac_key_input.text()
        
    def load_reports(self):
        """Load available reports from the API"""
        try:
            self.save_credentials()
            # Debug: Show credentials (mask password and HMAC key)
            debug_info = (
                f"Username: {self.username_input.text()}\n"
                f"Password: {'*' * len(self.password_input.text())}\n"
                f"HMAC User: {self.hmac_user_input.text()}\n"
                f"HMAC Key: {'*' * len(self.hmac_key_input.text())}\n"
            )
            print("[DEBUG] Credentials in use:\n" + debug_info)
            token = get_token()
            print(f"[DEBUG] Token: {token}")
            
            # Clear existing table
            self.reports_table.setRowCount(0)
            
            # Get reports
            file_name = "all"
            full_url = f"{REPORT_URL_BASE}?userName={self.username_input.text()}&fileName={file_name}"
            hmac_header = generate_hmac_header("GET", full_url)
            print(f"[DEBUG] HMAC Header: {hmac_header}")
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "HMacAuthorizationHeader": hmac_header
            }
            
            response = requests.get(full_url, headers=headers)
            try:
                response.raise_for_status()
            except Exception as e:
                # Show full error details in a popup
                error_text = f"Status Code: {response.status_code}\nResponse: {response.text}\n\n{str(e)}\n\n[DEBUG]\n" + debug_info + f"Token: {token}\nHMAC Header: {hmac_header}"
                QMessageBox.critical(self, "API Error", error_text)
                self.statusBar().showMessage("Error loading reports (see popup)")
                return
            
            report_list = json.loads(response.json())
            
            if not isinstance(report_list, list):
                raise Exception("Invalid response format")
            
            # Filter reports based on selected date range in filename
            start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
            end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
            def extract_date_from_filename(name):
                # Assumes format ..._YYYY-MM-DD.csv
                if name.endswith('.csv') and '_' in name:
                    return name.rsplit('_', 1)[-1].replace('.csv', '')
                return ''
            def in_range(date_str):
                return start_date <= date_str <= end_date
            filtered_reports = [
                report for report in report_list
                if in_range(extract_date_from_filename(report.get("ReportName", "")))
            ]
            
            # Populate table
            self.reports_table.setRowCount(len(filtered_reports))
            for i, report in enumerate(filtered_reports):
                name = report.get("ReportName", "")
                url = report.get("ReportBlobUri", "")
                
                # Add report name
                self.reports_table.setItem(i, 0, QTableWidgetItem(name))
                
                # Add download button
                download_btn = QPushButton("Download")
                download_btn.clicked.connect(lambda checked, url=url, name=name: self.download_report(url, name))
                self.reports_table.setCellWidget(i, 1, download_btn)
            
            self.statusBar().showMessage(f"Loaded {len(filtered_reports)} reports from {start_date} to {end_date}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load reports: {str(e)}")
            self.statusBar().showMessage("Error loading reports")
    
    def download_report(self, url, name):
        """Download a single report"""
        try:
            # Get save location
            save_dir = QFileDialog.getExistingDirectory(self, "Select Save Location")
            if not save_dir:
                return
                
            filepath = os.path.join(save_dir, name)
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Get fresh token and HMAC header for download
            token = get_token()
            hmac_header = generate_hmac_header("GET", url)
            
            # Download file with proper authentication headers
            headers = {
                "Authorization": f"Bearer {token}",
                "HMacAuthorizationHeader": hmac_header
            }
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    progress = int((downloaded / total_size) * 100)
                    self.progress_bar.setValue(progress)
            
            self.progress_bar.setVisible(False)
            QMessageBox.information(self, "Success", f"Report downloaded successfully to:\n{filepath}")
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Error", f"Failed to download report: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = LCReportDownloader()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 