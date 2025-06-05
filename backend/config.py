"""
Centrale runtime-instellingen.

Je kunt eenvoudig wisselen via omgevingsvariabelen of een `.env`-bestand
zonder code aan te passen.
"""
from functools import lru_cache
import os

class _Settings:
    INFLUX_URL: str = os.getenv("INFLUX_URL", "http://localhost:8086")
    INFLUX_TOKEN: str = os.getenv("INFLUX_TOKEN", "my-token")
    INFLUX_ORG: str = os.getenv("INFLUX_ORG", "v2x_org")
    INFLUX_BUCKET: str = os.getenv("INFLUX_BUCKET", "v2x_bucket")

@lru_cache(maxsize=1)
def settings() -> _Settings:
    return _Settings()  # singleton-achtig
