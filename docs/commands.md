
python3 -m venv venv
source venv/bin/activate     # op Linux/macOS
venv\Scripts\activate        # op Windows

pip install -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 5062 --reload













==================


## frontend

oud
npx create-react-app frontend --template typescript

nieuw
npm create vite@latest frontend -- --template react-ts



==== 
## docker

(venv) joost@laptop:~/v2x/code/v2x/backend$ docker-compose up --build


docker-compose down --volumes --remove-orphans

docker-compose build

docker-compose up


# 1) Bouw en start de containers
docker compose up --build

# 2) De backend draait nu in een container maar is BUITEN
#    nog steeds via poort 5062 bereikbaar:
#    • Front-end:      http://localhost:5062/…
#    • ABB-lader:      ws://<LAN-IP-PC>:5062/api/ws/ocpp
#    • IAMMeter sim:   ws://172.17.0.1:5062/api/ws/ocpp
#
#   (Bij Linux is 172.17.0.1 standaard het host-IP vanuit Docker.)
#
# 3) Stoppen doe je met:
# docker compose down




tree -I '__pycache__|node_modules|venv'


influxdb
http://localhost:8086
login: admin
password: adminadmin


3. Inloggen op PgAdmin

    Open http://localhost:5050
    (gebruik het e-mailadres en wachtwoord uit de env-vars hierboven)

    Create Server → tab Connection

        Host name: v2x_postgres

        Port: 5432

        Username: v2x

        Password: v2xpw

    Opslaan – je ziet nu alle tabellen en kunt data browsen of queries uitvoeren.



    # Laat alle meta-settings zien (handig!)
\set

# Toon query-resultaat als verticale records (fijn bij brede tabellen)
\x on   -- of  \x auto

# Resultaat wegschrijven naar CSV
\copy (SELECT * FROM charge_point_settings) TO 'settings.csv' CSV HEADER



handige commands:
docker-compose ps