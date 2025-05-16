# --------------------------------------------------------------
# CSMS backend – container-image
# --------------------------------------------------------------
#  • gebaseerd op Python 3.12 (slim)
#  • installeert alle requirements
#  • start uvicorn op poort 5062
# --------------------------------------------------------------
    FROM python:3.12-slim AS runtime

    # Sneller install-gedrag & minder disk-usage
    ENV PYTHONUNBUFFERED=1 \
        PYTHONDONTWRITEBYTECODE=1 \
        PIP_NO_CACHE_DIR=1
    
    WORKDIR /app
    
    # ---------------- dependencies
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    
    # ---------------- codebase
    COPY . .
    
    EXPOSE 5062
    
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5062"]
    