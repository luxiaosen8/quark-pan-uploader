from __future__ import annotations


def is_quark_cookie_domain(domain: str) -> bool:
    value = (domain or "").lstrip(".").lower()
    return value == "quark.cn" or value.endswith(".quark.cn")


def format_cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{name}={value}" for name, value in cookies.items() if name and value)
