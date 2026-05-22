from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    project_root: Path
    documents_dir: Path
    vector_store_dir: Path
    sqlite_db_path: Path
    chroma_collection_name: str
    embedding_model_name: str
    ollama_model: str
    ollama_host: str
    default_user_id: str

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_number: str
    your_whatsapp_number: str
    twilio_sms_number: str
    your_phone_number: str

    email_address: str
    email_app_password: str
    receiver_email: str

    @classmethod
    def from_env(cls) -> "Settings":
        project_root = Path(__file__).resolve().parent
        env_path = project_root / ".env"
        load_dotenv(dotenv_path=env_path, override=False)

        email_password_raw = os.getenv("EMAIL_APP_PASSWORD") or os.getenv("EMAIL_PASSWORD", "")
        normalized_email_password = "".join(email_password_raw.split()).strip("\"'")

        return cls(
            project_root=project_root,
            documents_dir=Path(os.getenv("DOCUMENTS_DIR", project_root / "documents")),
            vector_store_dir=Path(os.getenv("VECTOR_STORE_DIR", project_root / "vector_store")),
            sqlite_db_path=Path(os.getenv("SQLITE_DB_PATH", project_root / "summaries.db")),
            chroma_collection_name=os.getenv("CHROMA_COLLECTION_NAME", "documents"),
            embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
            ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            default_user_id=os.getenv("DEFAULT_USER_ID", "default_user"),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", "").strip(),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", "").strip(),
            twilio_whatsapp_number=os.getenv("TWILIO_WHATSAPP_NUMBER", "").strip(),
            your_whatsapp_number=os.getenv("YOUR_WHATSAPP_NUMBER", "").strip(),
            twilio_sms_number=os.getenv("TWILIO_SMS_NUMBER", "").strip(),
            your_phone_number=os.getenv("YOUR_PHONE_NUMBER", "").strip(),
            email_address=os.getenv("EMAIL_ADDRESS", "").strip(),
            email_app_password=normalized_email_password,
            receiver_email=os.getenv("RECEIVER_EMAIL", "").strip(),
        )

    def ensure_paths(self) -> None:
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_db_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings.from_env()
    settings.ensure_paths()
    return settings
