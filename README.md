# LC Report Downloader

A simple desktop application for downloading financial reports from the LCE Gateway portal.

## 🚀 Quick Start

### Download & Run
1. **Download** the latest `LCReportDownloader_v1.0.2.exe` from the [Releases](https://github.com/alcow5/LC-Report-Dowloader/releases) page
2. **Double-click** `LCReportDownloader_v1.0.2.exe` to run the application
3. **No installation required** - it's a standalone executable!

## 📋 How to Use

### Step 1: Enter Your Credentials
- **Username**: Your LCE Gateway username
- **Password**: Your LCE Gateway password  
- **HMAC User**: Your HMAC user ID
- **HMAC Key**: Your HMAC key

### Step 2: Select Date Range
- Choose the start and end dates for the reports you want to view
- Default range is the last 15 days

### Step 3: Load Reports
- Click **"Connect & Load Reports"** to fetch available reports
- The app will show a list of reports matching your date range

### Step 4: Download Reports
- Click **"Download"** next to any report you want
- Choose where to save the file on your computer
- The download will show a progress bar

### Switching Users
- Simply enter new credentials and click **"Connect & Load Reports"** again
- The app automatically clears previous credentials

## 🔧 Troubleshooting

**App won't start?**
- Make sure you're running Windows 10 or later
- Try running as administrator if you get permission errors

**Getting 500 errors when switching users?**
- Fixed in v1.0.1+ - the app now handles user switching properly
- Make sure you're using the latest version

**Getting 403/400 errors when downloading?**
- Fixed in v1.0.2+ - download authentication issues resolved
- Make sure you're using the latest version

**Can't download reports?**
- Verify you have write permissions to the download folder
- Check that you have enough disk space
- Make sure you're using the latest version (v1.0.2+)

## 📁 What's Included

- `LCReportDownloader_v1.0.2.exe` - The main application
- `README.md` - This documentation
- Source code (for developers)

## 🛡️ Security

- Your credentials are only stored in memory during the session
- No credentials are saved to disk
- All API communication uses secure HMAC authentication

## 📞 Support

Having issues? Contact: [alcow5@gmail.com](mailto:alcow5@gmail.com)

---

**Note**: This application requires Windows and an active internet connection to access the LCE Gateway portal.
