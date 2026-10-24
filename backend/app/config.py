from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        extra="ignore",
        case_sensitive=False,
        validate_assignment=True,
    )

    openai_api_key: SecretStr | None = None
    ripple_live_models: bool = False
    ripple_decisions_model: str = "gpt-6-luna"
    # Intentionally no implicit paid model: pin this after the team's smoke test.
    ripple_agent_model: str = ""
    ripple_decisions_timeout_s: float = Field(default=2, gt=0)
    ripple_decisions_retries: int = Field(default=1, ge=0, le=1)
    ripple_agent_timeout_s: float = Field(default=15, gt=0)
    ripple_confidence_threshold: float = Field(default=0.70, ge=0, le=1)
    ripple_spasm_window_ms: int = Field(default=400, gt=0)
    ripple_cancel_window_s: float = Field(default=5, gt=0)
    ripple_approval_timeout_s: float = Field(default=600, gt=0)
    ripple_tool_timeout_s: float = Field(default=10, gt=0)
    ripple_demo_approval: bool = False
    ripple_database_path: str = str(BACKEND_DIR / "app/data/ripple.sqlite3")
    ripple_input_timeout_s: float = Field(default=300, gt=0)
    ripple_user_token: SecretStr | None = None
    ripple_caregiver_token: SecretStr | None = None
    ripple_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    user_display_name: str = "Alex"
    home_phone: str = ""
    caregiver_phone: str = ""
    emergency_contact: str = ""
    ripple_live_twilio: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: SecretStr | None = None
    twilio_from_number: str = ""
    public_base_url: str = ""
    demo_fallback_lat: float = Field(default=37.7749, ge=-90, le=90)
    demo_fallback_lng: float = Field(default=-122.4194, ge=-180, le=180)

    @field_validator(
        "openai_api_key",
        "twilio_auth_token",
        "ripple_user_token",
        "ripple_caregiver_token",
        mode="before",
    )
    @classmethod
    def empty_secret(cls, value):
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        return None if isinstance(raw, str) and not raw.strip() else value

    @property
    def models_configured(self) -> bool:
        return self.ripple_live_models and bool(self.openai_api_key)
