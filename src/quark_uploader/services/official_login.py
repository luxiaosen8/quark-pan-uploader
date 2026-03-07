from __future__ import annotations

from urllib.parse import urlencode
from uuid import uuid4

import requests

OFFICIAL_LOGIN_PAGE_URL = "https://pan.quark.cn/"
OFFICIAL_SCAN_PAGE_URL = "https://su.quark.cn/4_eMHBJ"
OFFICIAL_MOBILE_LOGIN_URL = "https://uop.quark.cn/cas/custom/login?custom_login_type=mobile&client_id=532&display=pc"
OFFICIAL_QR_TOKEN_URL = "https://uop.quark.cn/cas/ajax/getTokenForQrcodeLogin"
OFFICIAL_QR_STATUS_URL = "https://uop.quark.cn/cas/ajax/getServiceTicketByQrcodeToken"
OFFICIAL_SCAN_QUERY = {
    "client_id": "532",
    "ssb": "weblogin",
    "uc_param_str": "",
    "uc_biz_str": "S:custom|OPT:SAREA@0|OPT:IMMERSIVE@1|OPT:BACK_BTN_STYLE@0",
}


def build_official_scan_url(token: str) -> str:
    query = {"token": token, **OFFICIAL_SCAN_QUERY}
    return f"{OFFICIAL_SCAN_PAGE_URL}?{urlencode(query)}"


class OfficialQrLoginApi:
    def __init__(self, http: requests.Session | None = None) -> None:
        self.http = http or requests.Session()

    def fetch_qr_token(self, request_id: str | None = None) -> str:
        rid = request_id or str(uuid4())
        response = self.http.get(
            OFFICIAL_QR_TOKEN_URL,
            params={"client_id": "532", "v": "1.2", "request_id": rid},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("data", {}).get("members", {}).get("token", "")

    def poll_service_ticket(self, token: str) -> dict:
        response = self.http.get(
            OFFICIAL_QR_STATUS_URL,
            params={"token": token},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
