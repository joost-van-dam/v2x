# --------------------------------------------------------------
# CSMS backend – container-image
# --------------------------------------------------------------
#  • gebaseerd op Python 3.12-slim
#  • installeert alle requirements
#  • draait als non-root gebruiker
# --------------------------------------------------------------

    FROM python:3.12-slim AS runtime

    # Sneller install-gedrag & minder disk-usage
    ENV PYTHONUNBUFFERED=1 \
        PYTHONDONTWRITEBYTECODE=1 \
        PIP_NO_CACHE_DIR=1
    
    # Niet-privileged user aanmaken
    RUN adduser --disabled-password --gecos '' --home /app appuser
    
    WORKDIR /app
    
    # ---------------- dependencies
    COPY --chown=appuser:appuser requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    # ---------------- codebase
    # Kopieer álles wat niet is uitgesloten via .dockerignore
    COPY --chown=appuser:appuser . .
    
    # Draai container als non-root
    USER appuser
    
    EXPOSE 5062
    
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5062"]
    