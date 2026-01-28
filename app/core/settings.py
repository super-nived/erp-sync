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

    class Config:
        env_file = ".env"


settings = Settings()
