from waitress import serve
from app import app

print("Serveur Web lancé sur le port 5000 (Production)")
serve(app, host='0.0.0.0', port=5000)