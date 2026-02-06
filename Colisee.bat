@echo off
title CONTROLEUR COLISEE
color 0A

echo =================================================
echo    DEMARRAGE DU SYSTEME COLISEE (MODE TUNNEL)
echo =================================================

cd "C:\Users\Proprietaire\Documents\Dev\Colisee"
call venv\Scripts\activate

echo.
echo 1. Lancement du Data Retriever (Stats LoL)...
start "Colisee - Data Retriever" cmd /k "python data_retriever.py"

echo 2. Lancement du Bot Discord...
start "Colisee - Bot Discord" cmd /k "python draven_bot.py"

echo 3. Lancement du Serveur Web (Waitress)...
start "Colisee - Web Server" cmd /k "python run_server.py"

echo 4. CREATION DU TUNNEL PUBLIC (Cloudflare)...
echo Le lien public s'affichera dans cette nouvelle fenetre.
start "Colisee - Tunnel" cmd /k "cloudflared.exe tunnel --url http://localhost:5000 --logfile static/tunnel.log"
echo.
echo ✅ TOUT EST EN LIGNE !
echo Regarde la fenetre 'PUBLIC URL' pour copier le lien https://...
pause