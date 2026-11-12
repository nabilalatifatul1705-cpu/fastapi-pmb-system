import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Contoh MySQL: mysql+pymysql://user:pass@localhost:3306/pmb
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./pmb.db")


settings = Settings()
