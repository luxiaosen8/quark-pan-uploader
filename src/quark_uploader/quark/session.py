from __future__ import annotations

from dataclasses import dataclass, field

import requests

BASE_URL = "https://drive-pc.quark.cn"


def build_cookie_headers(cookie: str) -> dict[str, str]:
    return {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
    }


@dataclass(slots=True)
class QuarkSession:
    cookie: str
    timeout_seconds: int = 30
    base_url: str = BASE_URL
    http: requests.Session = field(default_factory=requests.Session)

    @property
    def headers(self) -> dict[str, str]:
        return build_cookie_headers(self.cookie)

    @property
    def base_params(self) -> dict[str, str]:
        return {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}

    def make_url(self, path: str) -> str:
        return f"{self.base_url}{path}"
