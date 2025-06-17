"""
Centrale runtime-instellingen (Influx + Postgres).

Alles komt uit env-vars zodat je probleemloos kunt wisselen tussen
lokaal, staging of productie zonder code-aanpassing.
"""
from functools import lru_cache
import os


class _Settings:
    # Influx
    INFLUX_URL: str = os.getenv("INFLUX_URL", "https://influx-playground.sendlab.nl")
    INFLUX_TOKEN: str = os.getenv("INFLUX_TOKEN", "nUUDW9_TvfwX1vRVuUyVzW1lBiyGBoYTtrK6CyXU-l_Hn5RYbvppAsrnOdEPJn3RfoFsFRzC6DvVDNB8PggNfg==")
    INFLUX_ORG: str = os.getenv("INFLUX_ORG", "Sendlab")
    INFLUX_BUCKET: str = os.getenv("INFLUX_BUCKET", "CSMS_Gateway")

    # Postgres (asyncpg DSN)
    POSTGRES_DSN: str = os.getenv(
        "POSTGRES_DSN",
        "postgresql://v2x:v2xpw@localhost:5432/v2x_db",
    )


@lru_cache(maxsize=1)
def settings() -> _Settings:      # singleton
    return _Settings()
