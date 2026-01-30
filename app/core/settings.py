from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Lean FastAPI PocketBase"
    debug: bool = False

    pocketbase_url: str = "http://localhost:8090"
    pb_admin_email: str | None = None
    pb_admin_password: str | None = None

    # SQL Interface Configuration (direct SQLite access)
    sql_interface_url: str | None = None

    # Plant Configuration (for multi-tenant collection naming)
    plant_code: str = "DEFAULT"

    # JWT Authentication
    public_key: str | None = None

    # ERP API Configuration
    erp_api_url: str = (
        "https://aswanservice.aswan.com:8088/api/"
        "inprocessjobsBOMmaterialsDetails"
    )
    erp_txn_type: str | None = None  # Optional - only filter if set
    erp_sync_interval_minutes: int = 60
    erp_sync_days_back: int | None = None  # Optional - only use if set
    erp_sync_from_date: str | None = None  # Optional - only use if set

    class Config:
        env_file = ".env"


settings = Settings()
