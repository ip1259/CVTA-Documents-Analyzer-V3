from enum import Enum, auto
from pathlib import Path
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from infrastructure.logger import info, warning, error
from config.settings import GOOGLE_KEY_PATH, GOOGLE_CLIENT_SECRET_PATH, GOOGLE_TOKEN_PATH


class ConflictChoice(Enum):
    SKIP = "略過"
    OVERWRITE = "更新"
    NEW_VERSION = "上傳"


class UnauthenticatedError(Exception):
    """未通過 Google 認證的自訂例外"""

    def __init__(self, message="Google API 未認證"):
        self.message = message
        super().__init__(self.message)


class GoogleServiceAccount:
    """Google Workspace 服務帳戶管理"""

    def __init__(
        self,
        service_account_path: str = GOOGLE_KEY_PATH,
        client_secret_path: str = GOOGLE_CLIENT_SECRET_PATH,
        token_path: str = GOOGLE_TOKEN_PATH,
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
            self._cred_general = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=general_scopes
            )
            self._cred_user = None
            self._project_id = project_id or self._cred_general.project_id
            self._service_account_email = self._cred_general.service_account_email

            # 2. 建立用於檔案上傳的專用憑證 (使用 OAuth 2.0 User Flow)
            # 使用 User OAuth 2.0 可以解決服務帳戶 (Service Account) 沒有儲存空間配額的問題。
            if client_secret_path and token_path:
                upload_scopes = ["https://www.googleapis.com/auth/drive.file"]
                self._cred_user = None

                # 嘗試載入現有的 token
                t_path = Path(token_path)
                if t_path.exists():
                    self._cred_user = Credentials.from_authorized_user_file(
                        str(t_path), upload_scopes)

                # 如果 token 無效或不存在，則執行 OAuth2 授權流程
                if not self._cred_user or self._cred_user.expired:
                    if self._cred_user and self._cred_user.expired and self._cred_user.refresh_token:
                        self._cred_user.refresh(Request())
                    else:
                        cs_path = Path(client_secret_path)
                        if not cs_path.exists():
                            raise FileNotFoundError(
                                f"找不到 OAuth 2.0 Client Secret 檔案：{client_secret_path}")

                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(cs_path), upload_scopes)
                        self._cred_user = flow.run_local_server(port=0)

                    # 儲存 token 供下次使用
                    with open(token_path, 'w', encoding='utf-8') as token:
                        token.write(self._cred_user.to_json())

            self._token_path = token_path or ""
            self._client_secret_path = client_secret_path or ""
            self._auth_success = True
            info(f"Google API 認證成功 (帳戶：{self._service_account_email})")
        except Exception as e:
            warning(f"Google API 認證失敗 (非阻擋性): {e}")
            self._auth_success = False

    def refresh_or_reauth(self) -> bool:
        """
        檢查並更新上傳服務的 OAuth token。
        若 token 過期且有 refresh_token，則自動刷新；否則執行完整的重新授權流程。
        回傳 True 表示認證成功，False 表示失敗。

        Returns:
            bool: 認證是否成功
        """
        if not self._cred_user or not self._cred_user.valid:
            t_path = Path(self._token_path)
            if t_path.exists():
                cred_user = Credentials.from_authorized_user_file(
                    str(t_path), ["https://www.googleapis.com/auth/drive.file"])
                if cred_user and cred_user.expired and cred_user.refresh_token:
                    try:
                        cred_user.refresh(Request())
                        self._cred_user = cred_user  # 更新記憶體中的憑證
                        with open(self._token_path, 'w', encoding='utf-8') as token:
                            token.write(self._cred_user.to_json())
                        info("Google API token 已自動更新")
                        return True
                    except Exception as e:
                        error(f"Token 刷新失敗：{e}")

            return self._perform_oauth_flow()

        return True

    def _perform_oauth_flow(self) -> bool:
        """執行完整的 OAuth2 授權流程並儲存 token"""
        cs_path = Path(self._client_secret_path)
        if not cs_path.exists():
            error(f"找不到 OAuth 2.0 Client Secret 檔案：{self._client_secret_path}")
            return False

        upload_scopes = ["https://www.googleapis.com/auth/drive.file"]
        flow = InstalledAppFlow.from_client_secrets_file(
            str(cs_path), upload_scopes)
        self._cred_user = flow.run_local_server(port=0)

        with open(self._token_path, 'w', encoding='utf-8') as token:
            token.write(self._cred_user.to_json())

        self._auth_success = True
        info(f"Google API 重新認證成功 (帳戶：{self._service_account_email})")
        return True

    @property
    def drive_service(self):
        return build("drive", "v3", credentials=self._cred_general)

    @property
    def sheets_service(self):
        return build("sheets", "v4", credentials=self._cred_general)

    @property
    def upload_drive_service(self):
        return build("drive", "v3", credentials=self._cred_user)

    @property
    def authenticated(self):
        return self._auth_success

    @property
    def service_account_email(self):
        return self._service_account_email

    @property
    def token_path(self) -> str:
        """取得 token 檔案路徑"""
        return self._token_path

    @property
    def client_secret_path(self) -> str:
        """取得 client secret 檔案路徑"""
        return self._client_secret_path

    @property
    def refresh_token(self) -> bool:
        """檢查是否有可用的 refresh_token"""
        t_path = Path(self._token_path)
        if not t_path.exists():
            return False
        cred_user = Credentials.from_authorized_user_file(
            str(t_path), ["https://www.googleapis.com/auth/drive.file"])
        return cred_user and cred_user.refresh_token is not None
