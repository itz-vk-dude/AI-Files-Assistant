import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_FILE = 'promptchain-sa.json'
DOWNLOAD_DIR = "drive_downloads"
CHUNK_SIZE = 1024 * 1024 * 5  # 5MB

# MIME type mapping for Google Docs export
EXPORT_MIME_MAP = {
    'application/vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
    'application/vnd.google-apps.spreadsheet': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
    'application/vnd.google-apps.presentation': ('application/pdf', '.pdf'),
}

def authenticate():
    creds = service_account.Credentials.from_service_account_file(SERVICE_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def download_files_from_drive(folder_id):
    service = authenticate()

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    file_list = []

    def recurse_folder(fid, parent_path=""):
        query = f"'{fid}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        items = results.get('files', [])

        for item in items:
            name, file_id, mime_type = item['name'], item['id'], item['mimeType']
            target_dir = os.path.join(DOWNLOAD_DIR, parent_path)
            os.makedirs(target_dir, exist_ok=True)

            # Handle folders
            if mime_type == 'application/vnd.google-apps.folder':
                recurse_folder(file_id, os.path.join(parent_path, name))
                continue

            try:
                if mime_type in EXPORT_MIME_MAP:
                    export_mime, ext = EXPORT_MIME_MAP[mime_type]
                    exported_name = f"{name}{ext}" if not name.endswith(ext) else name
                    file_path = os.path.join(target_dir, exported_name)
                    print(f"⬇️ Exporting Google Doc: {exported_name}")
                    request = service.files().export_media(fileId=file_id, mimeType=export_mime)
                else:
                    file_path = os.path.join(target_dir, name)
                    print(f"⬇️ Downloading: {name}")
                    request = service.files().get_media(fileId=file_id)

                fh = io.FileIO(file_path, 'wb')
                downloader = MediaIoBaseDownload(fh, request, chunksize=CHUNK_SIZE)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

                file_list.append(file_path)

            except Exception as e:
                print(f"❌ Failed to process {name}: {str(e)}")

    recurse_folder(folder_id)
    print(f"✅ Downloaded {len(file_list)} files.")
    return file_list
