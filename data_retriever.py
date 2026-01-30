import requests
import urllib.parse
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("RIOT_API_KEY")
if not API_KEY:
    print("❌ ERREUR CRITIQUE : La clé API n'a pas été trouvée dans le fichier .env")
    exit()

REGION_ROUTING = "europe"  # Pour Account-V1 (Riot ID)
PLATFORM_ROUTING = "euw1"  # Pour Summoner-V4 et League-V4 (EUW)
PATH_FILE = "static/data.json"
DATE_DEBUT_EVENT = "04/12/2025 20:00"
DATE_FIN_EVENT = "07/12/2025 23:59"
DPM_URL = "https://dpm.lol/"

start_dt = datetime.strptime(DATE_DEBUT_EVENT, "%d/%m/%Y %H:%M")
end_dt = datetime.strptime(DATE_FIN_EVENT, "%d/%m/%Y %H:%M")

START_TIMESTAMP = int(start_dt.timestamp())
END_TIMESTAMP = int(end_dt.timestamp())


accounts_list = [
    {"gameName": "LeGreedou", "tagLine": "PLATE"},
    {"gameName": "Byron Love", "tagLine": "Yoshi"},
    {"gameName": "ArkoSs", "tagLine": "akali"},
    {"gameName": "Soreoe", "tagLine": "oeoeo"},
    {"gameName": "Gambling2Vladi", "tagLine": "CANNA"},
]

headers = {
    "X-Riot-Token": API_KEY
}

# --- VALEURS POUR LE CALCUL DES LP ABSOLUS ---
TIER_VALUES = {
    "IRON": 0,
    "BRONZE": 400,
    "SILVER": 800,
    "GOLD": 1200,
    "PLATINUM": 1600,
    "EMERALD": 2000,
    "DIAMOND": 2400,
    "MASTER": 2800,
    "GRANDMASTER": 2800,
    "CHALLENGER": 2800
}

RANK_VALUES = {
    "IV": 0,
    "III": 100,
    "II": 200,
    "I": 300,
    "": 0 # Pour les Master+ qui n'ont pas de rang I, II...
}

def get_latest_version():
    try:
        url = "https://ddragon.leagueoflegends.com/api/versions.json"
        response = requests.get(url)
        return response.json()[0]
    except:
        return "14.1.1"

CURRENT_VERSION = get_latest_version()
IMAGE_URL = f"https://ddragon.leagueoflegends.com/cdn/{CURRENT_VERSION}/img/champion/"


def calculer_score_absolu(tier, rank, lp):
    """Convertit le rang complet en un score unique pour comparer facile."""
    base = TIER_VALUES.get(tier, 0)
    division = RANK_VALUES.get(rank, 0)
    return base + division + lp


def dpm_url(summoner_name, tag_line):
    """Construit l'URL DPM pour un joueur donné."""
    full_name = f"{summoner_name}-{tag_line}"
    return f"{DPM_URL}{full_name}"


def load_data():
    """Charge le JSON existant ou crée une structure vide"""
    if os.path.exists(PATH_FILE):
        try:
            with open(PATH_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"event_ended": False, "accounts": []}
    return {"event_ended": False, "accounts": []}


def save_securely(data):
    """Sauvegarde"""
    temp_path = PATH_FILE + ".tmp"
    with open(temp_path, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, PATH_FILE)

def generer_recap(data):
    """Calcule et affiche les statistiques finales de l'événement."""
    accounts = data.get("accounts", [])
    if not accounts:
        print("Aucune donnée à analyser pour le récapitulatif.")
        return

    # Initialisation avec des valeurs par défaut
    # Structure : (Nom du joueur, Valeur)
    stats = {
        "plus_games": (None, -1),
        "moins_games": (None, 99999),
        "pire_wr": (None, 101),
        "top_lp": (None, -99999)
    }
    recap_msg = ""
    for acc in accounts:
        name = acc["gameName"]
        matches = acc.get("matches", [])
        nb_games = len(matches)
        winrate = acc.get("winrate", 0)

        # Calcul des LP totaux gagnés (on ignore les "?" et les erreurs)
        total_lp_gained = 0
        for m in matches:
            lp = m.get("lp_change")
            if isinstance(lp, int): # On s'assure que c'est un nombre
                total_lp_gained += lp

        # 1. Plus de parties
        if nb_games > stats["plus_games"][1]:
            stats["plus_games"] = (name, nb_games)
        
        # 2. Moins de parties
        if nb_games < stats["moins_games"][1]:
            stats["moins_games"] = (name, nb_games)

        # 3. Pire Winrate (Il faut au moins 1 game pour être jugé, sinon c'est trop facile)
        if nb_games > 0 and winrate < stats["pire_wr"][1]:
            stats["pire_wr"] = (name, winrate)
        
        # 4. Plus de LP gagnés (au total sur la période)
        if total_lp_gained > stats["top_lp"][1]:
            stats["top_lp"] = (name, total_lp_gained)

        recap_msg += f"{name}, games: {nb_games}, WR: {winrate}%, LP gained: {total_lp_gained} \n"

    # --- AFFICHAGE DU RÉCAPITULATIF ---
    recap_msg += (
        "\n --- RÉCAPITULATIF FINAL DE L'EVENT --- \n"
        f"  La Reine Salope : {stats['moins_games'][0]} ({stats['moins_games'][1]} games)\n"
        f"  Le Fou de la Faille : {stats['plus_games'][0]} ({stats['plus_games'][1]} games)\n"
        f"  Le Cadavre : {stats['pire_wr'][0]} ({stats['pire_wr'][1]}% WR)\n"
        f"  Le Glorious Executionner : {stats['top_lp'][0]} ({'+' if stats['top_lp'][1] > 0 else ''}{stats['top_lp'][1]} LP)\n"
        "----------------------------------------------\n"
    )
    
    print(recap_msg)
    nom_propre = end_dt.strftime("%Y-%m-%d_%H-%M")
    nom_fichier = f"archive/recap_{nom_propre}.txt"
    try:
        with open(nom_fichier, "w", encoding="utf-8") as f:
            f.write(recap_msg)
        print("✅ Récapitulatif sauvegardé dans le dossier archive/")
    except:
        pass

while True:
    if time.time() > END_TIMESTAMP:
        print("\n--- 🛑 L'ÉVÉNEMENT EST TERMINÉ ! ---")
        current_data = load_data()
        current_data["event_ended"] = True # On marque la fin
        generer_recap(current_data)
        save_securely(current_data) # On sauvegarde les DERNIÈRES données, on ne vide pas !
        print(f"✅ Résultats finaux figés dans {PATH_FILE}.")
        break

    current_data = load_data()
    players_map = {f"{p['gameName']}#{p['tagLine']}": p for p in current_data["accounts"]}
    updated_accounts = []

    for account_cfg in accounts_list:
        name = account_cfg["gameName"]
        tag = account_cfg["tagLine"]
        dpm_page = dpm_url(name, tag)
        full_id = f"{name}#{tag}"
        
        try:
            # --- 1. PUUID (Account-V1) ---
            url_acc = f"https://{REGION_ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{urllib.parse.quote(name)}/{urllib.parse.quote(tag)}"
            resp_acc = requests.get(url_acc, headers=headers)
            
            if resp_acc.status_code != 200:
                print(f"⚠️ Erreur Account pour {name}: {resp_acc.status_code} (Check API Key/Tag)")
                if full_id in players_map: updated_accounts.append(players_map[full_id])
                continue # On passe au suivant sans planter
            
            puuid = resp_acc.json().get("puuid")

            # --- 2. SummonerID (Summoner-V4) ---
            url_sum = f"https://{PLATFORM_ROUTING}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
            resp_sum = requests.get(url_sum, headers=headers)
            
            if resp_sum.status_code != 200:
                print(f"⚠️ Erreur Summoner pour {name}: {resp_sum.status_code}")
                if full_id in players_map: updated_accounts.append(players_map[full_id])
                continue

            summoner_id = resp_sum.json().get("id")

            # --- 3. Rank & LP (League-V4) ---
            url_league = f"https://{PLATFORM_ROUTING}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
            resp_league = requests.get(url_league, headers=headers)
            
            if resp_league.status_code != 200:
                print(f"⚠️ Erreur League pour {name}: {resp_league.status_code}")
                if full_id in players_map: updated_accounts.append(players_map[full_id])
                continue
                
            league_data = resp_league.json()
            
            current_lp = 0
            tier = "UNRANKED"
            rank = ""
            
            # C'est ici que ça plantait : on vérifie que c'est bien une liste
            if isinstance(league_data, list):
                for entry in league_data:
                    if entry["queueType"] == "RANKED_SOLO_5x5":
                        current_lp = entry["leaguePoints"]
                        tier = entry["tier"]
                        rank = entry.get("rank", "")
                        break
            
            current_absolute_score = calculer_score_absolu(tier, rank, current_lp)

            # --- 4. Traitement des données ---
            stored_player = players_map.get(full_id, {
                "gameName": name, "tagLine": tag, "dpm": dpm_page, "matches": [], 
                "rank_info": {"tier": tier, "rank": rank, "lp": current_lp, "absolute_score": current_absolute_score}
            })
            
            prev_info = stored_player.get("rank_info", {})
            prev_absolute = prev_info.get("absolute_score")
            
            if prev_absolute is None:
                prev_absolute = calculer_score_absolu(prev_info.get("tier", "UNRANKED"), prev_info.get("rank", ""), prev_info.get("lp", 0))

            existing_match_ids = [m["id"] for m in stored_player["matches"]]
            
            # --- 5. Match History (Match-V5) ---
            url_ids = f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&startTime={START_TIMESTAMP}&count=100"
            resp_ids = requests.get(url_ids, headers=headers)
            
            if resp_ids.status_code == 200:
                riot_match_ids = resp_ids.json()
                new_matches_found = []
                
                for m_id in reversed(riot_match_ids):
                    if m_id not in existing_match_ids:
                        new_matches_found.append(m_id)

                if new_matches_found:
                    total_diff = current_absolute_score - prev_absolute
                    
                    if abs(total_diff) > 200: 
                        lp_per_match = "?"
                    else:
                        lp_per_match = round(total_diff / len(new_matches_found))

                    for new_id in new_matches_found:
                        time.sleep(1.2)
                        resp_det = requests.get(f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/{new_id}", headers=headers)
                        if resp_det.status_code == 200:
                            det = resp_det.json()
                            part = next((p for p in det["info"]["participants"] if p["puuid"] == puuid), None)
                            
                            if part:
                                # Petite vérif de cohérence LP (inchangée)
                                is_win = part["win"]
                                final_lp = lp_per_match
                                if isinstance(final_lp, int):
                                    if is_win and final_lp < 0: final_lp = "?" 
                                    if not is_win and final_lp > 0: final_lp = "?"

                                # --- NOUVEAU : Récupération du KDA ---
                                kills = part["kills"]
                                deaths = part["deaths"]
                                assists = part["assists"]
                                kda_display = f"{kills}/{deaths}/{assists}"

                                new_match_obj = {
                                    "id": new_id,
                                    "champion": part["championName"],
                                    "icon": f"{IMAGE_URL}{part['championName']}.png",
                                    "resultat": "Victoire" if is_win else "Défaite",
                                    "kda": kda_display,
                                    "lp_change": final_lp,
                                    "timestamp": det["info"]["gameEndTimestamp"]
                                }
                                
                                stored_player["matches"].insert(0, new_match_obj)
                                print(f"   [NOUVEAU] {part['championName']} ({kda_display}) : {final_lp} LP")

                                time.sleep(0.2)
            else:
                 print(f"⚠️ Erreur Matchs pour {name}: {resp_ids.status_code}")

            total_matches = len(stored_player["matches"])
            total_wins = 0
            
            for m in stored_player["matches"]:
                if m["resultat"] == "Victoire":
                    total_wins += 1
            
            # On évite la division par 0 si pas de matchs
            if total_matches > 0:
                winrate = int((total_wins / total_matches) * 100)
            else:
                winrate = 0
            
            stored_player["winrate"] = winrate
            # Mise à jour
            stored_player["rank_info"] = {
                "tier": tier, "rank": rank, "lp": current_lp, "absolute_score": current_absolute_score
            }
            updated_accounts.append(stored_player)
            print(f"✅ {name} : {tier} {rank} ({current_lp} LP)")
            
            # Anti-Spam API
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ GROS CRASH sur {name}: {e}")
            if full_id in players_map: updated_accounts.append(players_map[full_id])

    save_securely({
        "event_ended": False, 
        "accounts": updated_accounts
    })

    print("--- Pause de 5 minutes ---")
    time.sleep(300)