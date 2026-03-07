from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        merged_params = dict(self.base_params)
        if params:
            merged_params.update(params)
        response = self.http.request(
            method=method,
            url=self.make_url(path),
            headers=self.headers,
            params=merged_params,
            json=json,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()
