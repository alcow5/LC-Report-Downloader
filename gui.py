import sys
import os
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QTableWidget, QTableWidgetItem, QMessageBox,
                            QProgressBar, QFileDialog, QDateEdit)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QIcon
from MVC import get_token, download_reports, generate_hmac_header, REPORT_URL_BASE, debug_logger, DEBUG_LOG_FILE
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

        # Download all button
        self.download_all_button = QPushButton("Download All")
        self.download_all_button.setEnabled(False)
        self.download_all_button.clicked.connect(self.download_all_reports)
        layout.addWidget(self.download_all_button)
        
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
        
        # Show debug log location in status bar tooltip
        # Log file is created when logger is initialized, so it should exist
        try:
            self.statusBar().setToolTip(f"Debug logs saved to: {DEBUG_LOG_DIR}\nLatest: {DEBUG_LOG_FILE.name}")
        except Exception:
            pass  # Silently fail if there's an issue
        
        # Load saved credentials if they exist
        self.load_saved_credentials()
        self.reports_data = []
        
    def load_saved_credentials(self):
        """Load saved credentials from environment variables"""
        self.username_input.setText(os.getenv("GATEWAY_USERNAME", ""))
        self.hmac_user_input.setText(os.getenv("HMAC_USER", ""))
        
    def save_credentials(self):
        """Save credentials to environment variables"""
        # Clear previous credentials first (more thorough cleanup)
        for key in ["GATEWAY_USERNAME", "GATEWAY_PASSWORD", "HMAC_USER", "HMAC_KEY"]:
            if key in os.environ:
                del os.environ[key]
        
        # Set new credentials with proper string conversion
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        hmac_user = self.hmac_user_input.text().strip()
        hmac_key = self.hmac_key_input.text().strip()
        
        os.environ["GATEWAY_USERNAME"] = username
        os.environ["GATEWAY_PASSWORD"] = password
        os.environ["HMAC_USER"] = hmac_user
        os.environ["HMAC_KEY"] = hmac_key
        
    def load_reports(self):
        """Load available reports from the API"""
        try:
            # Validate credentials before proceeding
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()
            hmac_user = self.hmac_user_input.text().strip()
            hmac_key = self.hmac_key_input.text().strip()
            
            if not all([username, password, hmac_user, hmac_key]):
                QMessageBox.warning(self, "Missing Credentials", 
                                  "Please fill in all credential fields.")
                return
            
            self.save_credentials()
            self.reports_data = []
            self.download_all_button.setEnabled(False)
            
            # Debug: Show credentials (mask password and HMAC key)
            debug_info = (
                f"Username: {username}\n"
                f"Password: {'*' * len(password)}\n"
                f"HMAC User: {hmac_user}\n"
                f"HMAC Key: {'*' * len(hmac_key)}\n"
            )
            print("[DEBUG] Credentials in use:\n" + debug_info)
            
            # Get token first
            try:
                token = get_token()
                print(f"[DEBUG] Token obtained successfully (length: {len(token)})")
            except Exception as e:
                error_text = f"Failed to obtain authentication token:\n{str(e)}\n\n[DEBUG]\n{debug_info}"
                QMessageBox.critical(self, "Authentication Error", error_text)
                self.statusBar().showMessage("Error: Failed to authenticate")
                return
            
            # Clear existing table
            self.reports_table.setRowCount(0)
            
            # Get reports - properly encode query parameters
            file_name = "all"
            # Use urlencode to ensure proper encoding of query parameters
            query_params = urllib.parse.urlencode({
                "userName": username,
                "fileName": file_name
            })
            full_url = f"{REPORT_URL_BASE}?{query_params}"
            print(f"[DEBUG] Request URL: {full_url}")
            
            try:
                hmac_header = generate_hmac_header("GET", full_url)
                print(f"[DEBUG] HMAC Header: {hmac_header}")
            except Exception as e:
                error_text = f"Failed to generate HMAC header:\n{str(e)}\n\n[DEBUG]\n{debug_info}"
                QMessageBox.critical(self, "HMAC Error", error_text)
                self.statusBar().showMessage("Error: Failed to generate HMAC")
                return
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "HMacAuthorizationHeader": hmac_header
            }
            
            # Log credential info (masked) for debugging
            debug_logger.debug("=" * 80)
            debug_logger.debug("API REQUEST - GetReportBlobs")
            debug_logger.debug("=" * 80)
            debug_logger.debug(f"Username: {username}")
            debug_logger.debug(f"HMAC User: {hmac_user}")
            debug_logger.debug(f"Password Length: {len(password)} chars")
            debug_logger.debug(f"HMAC Key Length: {len(hmac_key)} chars")
            debug_logger.debug(f"Request URL: {full_url}")
            debug_logger.debug(f"Request Headers:")
            for key, value in headers.items():
                if key == "Authorization":
                    debug_logger.debug(f"  {key}: Bearer {value.split(' ')[1][:50]}...")
                elif key == "HMacAuthorizationHeader":
                    debug_logger.debug(f"  {key}: {value}")
                else:
                    debug_logger.debug(f"  {key}: {value}")
            
            print(f"[DEBUG] Making request to: {full_url}")
            try:
                response = requests.get(full_url, headers=headers)
                debug_logger.debug(f"Response Status Code: {response.status_code}")
                debug_logger.debug(f"Response Headers: {dict(response.headers)}")
                debug_logger.debug(f"Response Body (first 500 chars): {response.text[:500]}")
                print(f"[DEBUG] Response status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                debug_logger.error(f"Request exception: {str(e)}")
                error_text = f"Network error occurred:\n{str(e)}\n\nCheck debug log: {DEBUG_LOG_FILE}"
                QMessageBox.critical(self, "Network Error", error_text)
                self.statusBar().showMessage("Network error occurred")
                return
            
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                # Log detailed error information
                debug_logger.error("=" * 80)
                debug_logger.error("API REQUEST FAILED")
                debug_logger.error("=" * 80)
                debug_logger.error(f"Status Code: {response.status_code}")
                debug_logger.error(f"Response Text: {response.text}")
                debug_logger.error(f"Request URL: {full_url}")
                debug_logger.error(f"Request Headers: {headers}")
                debug_logger.error(f"Error: {str(e)}")
                debug_logger.error("=" * 80)
                
                # Show full error details in a popup with log file location
                error_text = (
                    f"Status Code: {response.status_code}\n"
                    f"Response: {response.text[:500]}\n\n"
                    f"Error: {str(e)}\n\n"
                    f"[DEBUG INFO]\n{debug_info}"
                    f"Request URL: {full_url}\n"
                    f"Token: {token[:50]}...\n"
                    f"HMAC Header: {hmac_header}\n\n"
                    f"📋 Full debug log saved to:\n{DEBUG_LOG_FILE}\n\n"
                    f"Please share this log file for troubleshooting."
                )
                QMessageBox.critical(self, "API Error", error_text)
                self.statusBar().showMessage(f"Error loading reports: {response.status_code} - See log: {DEBUG_LOG_FILE.name}")
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
            
            self.reports_data = filtered_reports
            self.download_all_button.setEnabled(bool(filtered_reports))

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
            self.reports_data = []
            self.download_all_button.setEnabled(False)
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
            self._download_file(
                url,
                filepath,
                lambda percent: self.progress_bar.setValue(percent)
            )
            
            self.progress_bar.setVisible(False)
            QMessageBox.information(self, "Success", f"Report downloaded successfully to:\n{filepath}")
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Error", f"Failed to download report: {str(e)}")

    def download_all_reports(self):
        """Download all loaded reports to a selected directory"""
        if not self.reports_data:
            QMessageBox.information(self, "No Reports", "There are no reports to download. Please load reports first.")
            return

        save_dir = QFileDialog.getExistingDirectory(self, "Select Save Location")
        if not save_dir:
            return

        total_reports = len(self.reports_data)
        errors = []

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        for index, report in enumerate(self.reports_data):
            name = report.get("ReportName")
            url = report.get("ReportBlobUri")

            if not name or not url:
                continue

            filepath = os.path.join(save_dir, name)

            try:
                self._download_file(
                    url,
                    filepath,
                    lambda percent, idx=index: self.progress_bar.setValue(
                        int(((idx + percent / 100) / total_reports) * 100)
                    )
                )
            except Exception as e:
                errors.append(f"{name}: {str(e)}")

        self.progress_bar.setVisible(False)

        if errors:
            QMessageBox.warning(
                self,
                "Download Complete (with issues)",
                "Some reports could not be downloaded:\n\n" + "\n".join(errors)
            )
        else:
            QMessageBox.information(
                self,
                "Download Complete",
                f"All {total_reports} reports were downloaded successfully."
            )

    def _download_file(self, url, filepath, progress_callback=None):
        """Helper method to download a file with optional progress updates"""
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024 * 32
        downloaded = 0

        with open(filepath, "wb") as f:
            for data in response.iter_content(block_size):
                if not data:
                    continue
                f.write(data)
                downloaded += len(data)
                if total_size > 0 and progress_callback:
                    progress = int(downloaded / total_size * 100)
                    progress_callback(progress)

        if total_size == 0 and progress_callback:
            progress_callback(100)

def main():
    app = QApplication(sys.argv)
    window = LCReportDownloader()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 