
python3 -m venv venv
source venv/bin/activate     # op Linux/macOS
venv\Scripts\activate        # op Windows

pip install -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 5062 --reload













==================


## frontend

npx create-react-app frontend --template typescript




