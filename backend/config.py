"""
Centrale runtime-instellingen (Influx + Postgres).

Alles komt uit env-vars zodat je probleemloos kunt wisselen tussen
lokaal, staging of productie zonder code-aanpassing.
"""
from functools import lru_cache
import os


class _Settings:
    # Influx
    INFLUX_URL: str = os.getenv("INFLUX_URL", "http://localhost:8086")
    INFLUX_TOKEN: str = os.getenv("INFLUX_TOKEN", "my-token")
    INFLUX_ORG: str = os.getenv("INFLUX_ORG", "v2x_org")
    INFLUX_BUCKET: str = os.getenv("INFLUX_BUCKET", "v2x_bucket")

    # Postgres (asyncpg DSN)
    POSTGRES_DSN: str = os.getenv(
        "POSTGRES_DSN",
        "postgresql://v2x:v2xpw@localhost:5432/v2x_db",
    )


@lru_cache(maxsize=1)
def settings() -> _Settings:      # singleton
    return _Settings()
