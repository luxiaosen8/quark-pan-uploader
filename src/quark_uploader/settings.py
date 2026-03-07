from pydantic import BaseModel


class AppSettings(BaseModel):
    output_dir: str = "output"
    save_cookie: bool = True
    persisted_cookie: str = ""
    request_timeout_seconds: int = 30
    max_retries: int = 3
