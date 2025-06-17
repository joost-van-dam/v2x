# --------------------------------------------------------------
# CSMS backend – container-image
# --------------------------------------------------------------
#  • gebaseerd op Python 3.12 (slim)
#  • installeert alle requirements
#  • draait als non-root gebruiker
#  • kopieert alléén de strikt noodzakelijke bronnen
# --------------------------------------------------------------

    FROM python:3.12-slim AS runtime

    # Sneller install-gedrag & minder disk-usage
    ENV PYTHONUNBUFFERED=1 \
        PYTHONDONTWRITEBYTECODE=1 \
        PIP_NO_CACHE_DIR=1
    
    # --------------------------------------------------------------
    # Maak een niet-privileged gebruiker aan
    # --------------------------------------------------------------
    RUN adduser --disabled-password --gecos '' --home /app appuser
    
    WORKDIR /app
    
    # ---------------- dependencies
    COPY --chown=appuser:appuser requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    # ---------------- codebase
    # Kopieer alleen de benodigde app-bronbestanden; alles dat niet nodig is
    # (bijv. .git, tests, secrets) hoort in .dockerignore uitgesloten te zijn.
    COPY --chown=appuser:appuser ./app ./app
    COPY --chown=appuser:appuser ./main.py .
    
    # Draai de container als on-privileged gebruiker
    USER appuser
    
    EXPOSE 5062
    
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5062"]
    