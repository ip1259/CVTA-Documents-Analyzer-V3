from pathlib import Path
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from src.infrastructure.logger import info, warning


class GoogleServiceAccount:
    """Google Workspace 服務帳戶管理"""

    def __init__(
        self,
        service_account_path: str,
        client_secret_path: str = None,
        token_path: str = None,
        project_id: str = None
    ):
        try:
            if not Path(service_account_path).exists():
                raise FileNotFoundError(f"找不到服務帳戶檔案：{service_account_path}")

            # 1. 建立用於一般操作 (Drive, Sheets) 的憑證
            # 包含廣泛的 Drive 權限，足以進行檔案的讀寫、管理等操作
            general_scopes = [
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/spreadsheets"
            ]
            cred_general = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=general_scopes
            )
            self._project_id = project_id or cred_general.project_id
            self._service_account_email = cred_general.service_account_email
            self._drive_service = build(
                "drive", "v3", credentials=cred_general)
            self._sheets_service = build(
                "sheets", "v4", credentials=cred_general)

            # 2. 建立用於檔案上傳的專用憑證 (使用 OAuth 2.0 User Flow)
            # 使用 User OAuth 2.0 可以解決服務帳戶 (Service Account) 沒有儲存空間配額的問題。
            self._upload_drive_service = None
            if client_secret_path and token_path:
                upload_scopes = ["https://www.googleapis.com/auth/drive.file"]
                cred_user = None

                # 嘗試載入現有的 token
                t_path = Path(token_path)
                if t_path.exists():
                    cred_user = Credentials.from_authorized_user_file(
                        str(t_path), upload_scopes)

                # 如果 token 無效或不存在，則執行 OAuth2 授權流程
                if not cred_user or not cred_user.valid:
                    if cred_user and cred_user.expired and cred_user.refresh_token:
                        cred_user.refresh(Request())
                    else:
                        cs_path = Path(client_secret_path)
                        if not cs_path.exists():
                            raise FileNotFoundError(
                                f"找不到 OAuth 2.0 Client Secret 檔案：{client_secret_path}")

                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(cs_path), upload_scopes)
                        cred_user = flow.run_local_server(port=0)

                    # 儲存 token 供下次使用
                    with open(token_path, 'w', encoding='utf-8') as token:
                        token.write(cred_user.to_json())

                self._upload_drive_service = build(
                    "drive", "v3", credentials=cred_user)

            self._auth_success = True
            info(f"Google API 認證成功 (帳戶: {self._service_account_email})")
        except Exception as e:
            warning(f"Google API 認證失敗 (非阻擋性): {e}")
            self._drive_service = None
            self._sheets_service = None
            self._auth_success = False
            self._upload_drive_service = None

    @property
    def drive_service(self):
        return self._drive_service

    @property
    def sheets_service(self):
        return self._sheets_service

    @property
    def upload_drive_service(self):
        return self._upload_drive_service

    @property
    def authenticated(self):
        return self._auth_success

    @property
    def service_account_email(self):
        return self._service_account_email
