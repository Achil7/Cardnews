from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from loguru import logger

from config import PROJECT_ROOT, settings

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PATH = PROJECT_ROOT / "token.json"


def _get_credentials() -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(PROJECT_ROOT / settings.google_credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds


def _get_or_create_folder(service, name: str, parent_id: str) -> str:
    query = (
        f"name='{name}' and '{parent_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_post_to_drive(output_dir: Path) -> str | None:
    """output_dir 구조: data/output/{date}/{account}/{region_category}/

    Drive 폴더 구조: root/{date}/{account}/{region_category}/slide_*.jpg + caption.txt
    """
    if not settings.google_drive_folder_id:
        logger.warning("GOOGLE_DRIVE_FOLDER_ID not set, skipping upload")
        return None

    creds = _get_credentials()
    service = build("drive", "v3", credentials=creds)

    category_folder_name = output_dir.name
    account_folder_name = output_dir.parent.name
    date_folder_name = output_dir.parent.parent.name

    date_folder_id = _get_or_create_folder(
        service, date_folder_name, settings.google_drive_folder_id
    )
    account_folder_id = _get_or_create_folder(
        service, account_folder_name, date_folder_id
    )
    category_folder_id = _get_or_create_folder(
        service, category_folder_name, account_folder_id
    )

    uploaded = []
    for file_path in sorted(output_dir.iterdir()):
        if not file_path.is_file():
            continue

        mime = "image/jpeg" if file_path.suffix in (".jpg", ".jpeg") else "image/png"
        if file_path.suffix == ".txt":
            mime = "text/plain"

        metadata = {"name": file_path.name, "parents": [category_folder_id]}
        media = MediaFileUpload(str(file_path), mimetype=mime)
        service.files().create(body=metadata, media_body=media, fields="id").execute()
        uploaded.append(file_path.name)

    drive_url = f"https://drive.google.com/drive/folders/{date_folder_id}"
    logger.info(f"Uploaded {len(uploaded)} files to Drive: {drive_url}")
    return drive_url
