import requests
import urllib.parse
import discord
from discord import app_commands, EntityType, PrivacyLevel, FFmpegPCMAudio, EntityType, PrivacyLevel
from discord.ext import commands, tasks
import json
import os
from dotenv import load_dotenv
from datetime import datetime
import asyncio
import re

load_dotenv()
VOICE_CHANNEL_ID = 1445727100563886206
MUSIC_PATH = "static/entrance.mp3"
FFMPEG_EXE = "ffmpeg.exe" if os.path.exists("ffmpeg.exe") else "ffmpeg"
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
TOKEN = os.getenv("DISCORD_TOKEN")
PATH_PLAYERS = "static/players.json"

event_started_triggered = False

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        # On lance la vérification en arrière-plan
        self.check_event_start.start()
        print(f"✅ Tâche de fond lancée (FFmpeg utilisé : {FFMPEG_EXE})")

    # Vérification toutes les 30 secondes
    @tasks.loop(seconds=30)
    async def check_event_start(self):
        global event_started_triggered
        
        config_path = "static/config.json"
        
        # On vérifie d'abord si le fichier existe
        if os.path.exists(config_path):
            try:
                # Lecture sécurisée : on lit le texte d'abord
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                
                # Si le fichier est vide, on s'arrête là pour ce tour
                if not content:
                    return

                config = json.loads(content)
                
                # Conversion de la date
                start_dt = datetime.strptime(config["start_date"], "%d/%m/%Y %H:%M")
                now = datetime.now()

                if now >= start_dt and not event_started_triggered:
                    event_started_triggered = True
                    await self.launch_opening_ceremony()
                    
            except json.JSONDecodeError:
                # On ignore silencieusement les erreurs de JSON (fichier en cours d'écriture)
                pass
            except Exception as e:
                print(f"Erreur bot check_event : {e}")

    async def launch_opening_ceremony(self):
        # 1. Message de guerre dans le salon textuel
        # On cherche un salon nommé "général" ou utilise un ID précis
        channel_text = discord.utils.get(self.get_all_channels(), name="général")
        if channel_text:
            await channel_text.send("⚔️ **LE COLISÉE EST OUVERT ! QUE LE MASSACRE COMMENCE !** ⚔️ @everyone")

        # 2. Musique dans le salon vocal
        voice_channel = self.get_channel(VOICE_CHANNEL_ID)
        if voice_channel:
            try:
                vc = await voice_channel.connect()
                print("🔊 Lecture de l'intro musicale...")
                
                # On lance la musique
                audio_source = FFmpegPCMAudio(executable=FFMPEG_EXE, source=MUSIC_PATH)
                vc.play(audio_source)
                
                # On attend 60 secondes (ajuste selon la durée de ton mp3)
                await asyncio.sleep(60) 
                
                await vc.disconnect()
                print("🔇 Cérémonie terminée, bot déconnecté.")
            except Exception as e:
                print(f"Erreur lors de la cérémonie vocale : {e}")

bot = MyBot()

def load_players():
    if os.path.exists(PATH_PLAYERS):
        with open(PATH_PLAYERS, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_players(players):
    with open(PATH_PLAYERS, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=4, ensure_ascii=False)

def get_tunnel_url():
    """Cherche l'URL Cloudflare dans le fichier de log"""
    log_path = "static/tunnel.log"
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()
                # On cherche un pattern qui ressemble à https://blabla.trycloudflare.com
                match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", content)
                if match:
                    return match.group(0)
        except Exception as e:
            print(f"Erreur lecture URL tunnel : {e}")
    
    return "http://ton-ip-serveur:5000" # Valeur par défaut si échec

@bot.event
async def on_ready():
    print(f"🚀 Bot prêt : {bot.user}")

@bot.tree.command(name="join", description="S'inscrire au rush avec vérification Riot")
@app_commands.describe(pseudo="Ton pseudo LoL", tag="Ton tag (ex: EUW)")
async def join(interaction: discord.Interaction, pseudo: str, tag: str):
    # 1. On prévient l'utilisateur qu'on vérifie (ça peut prendre 1-2 sec)
    await interaction.response.defer(ephemeral=True) 

    # 2. Nettoyage du tag
    clean_tag = tag.replace("#", "")
    
    # 3. Requête à l'API Riot (Account-V1)
    url_check = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{urllib.parse.quote(pseudo)}/{urllib.parse.quote(clean_tag)}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    
    try:
        response = requests.get(url_check, headers=headers)
        
        if response.status_code == 200:
            # Le compte existe !
            players = load_players()
            
            # Vérification des doublons locaux
            if any(p['gameName'].lower() == pseudo.lower() and p['tagLine'].lower() == clean_tag.lower() for p in players):
                await interaction.followup.send(f"⚠️ **{pseudo}#{clean_tag}** est déjà inscrit !")
                return

            # On enregistre
            players.append({"gameName": pseudo, "tagLine": clean_tag})
            save_players(players)
            
            await interaction.followup.send(f"✅ Compte vérifié !")
            await interaction.channel.send(f"**{pseudo}#{clean_tag}** a rejoint le Colisée ! Préparez-vous au massacre !")
            
        elif response.status_code == 404:
            await interaction.followup.send(f"❌ Erreur : Le compte **{pseudo}#{clean_tag}** n'existe pas chez Riot Games. Vérifie l'orthographe !")
        else:
            await interaction.followup.send(f"⚠️ Problème technique avec l'API Riot (Code: {response.status_code}). Réessaie plus tard.")

    except Exception as e:
        await interaction.followup.send(f"💥 Une erreur est survenue lors de la vérification : {e}")

# --- COMMANDE SLASH /PLAYERS ---
@bot.tree.command(name="players", description="Afficher la liste des inscrits au Collisée")
async def players_list(interaction: discord.Interaction):
    players = load_players()
    
    if not players:
        await interaction.response.send_message("Personne n'est encore inscrit pour le moment.", ephemeral=True)
        return

    # Création d'un Embed stylisé
    embed = discord.Embed(
        title="🏆 Participants au Collisée",
        description=f"Il y a actuellement **{len(players)}** guerriers prêts à en découdre !",
        color=discord.Color.gold()
    )

    liste_noms = "\n".join([f"• **{p['gameName']}**#{p['tagLine']}" for p in players])
    
    embed.add_field(name="Liste des joueurs :", value=liste_noms, inline=False)
    embed.set_footer(text="Que le meilleur gagne !")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_event", description="[ADMIN] Configurer les dates du rush")
@app_commands.describe(
    debut="Format: JJ/MM/AAAA HH:MM (ex: 04/12/2025 20:00)",
    fin="Format: JJ/MM/AAAA HH:MM (ex: 07/12/2025 23:59)"
)
@app_commands.checks.has_permissions(administrator=True)
async def setup_event(interaction: discord.Interaction, debut: str, fin: str):
    await interaction.response.defer(ephemeral=True)

    try:
        local_tz = datetime.now().astimezone().tzinfo
        start_dt = datetime.strptime(debut, "%d/%m/%Y %H:%M").replace(tzinfo=local_tz)
        end_dt = datetime.strptime(fin, "%d/%m/%Y %H:%M").replace(tzinfo=local_tz)

        global event_started_triggered
        event_started_triggered = False
        
        # Sauvegarde config
        config = {"start_date": debut, "end_date": fin}
        with open("static/config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

        # Image
        event_args = {
            "name": "🏆 Colisée de la Reine Salope.",
            "description": "Le tournoi commence ! Suivez les scores en direct sur le lien ci-dessous.",
            "start_time": start_dt,
            "end_time": end_dt,
            "entity_type": EntityType.external,
            "privacy_level": PrivacyLevel.guild_only
        }
        
        # --- RÉCUPÉRATION AUTOMATIQUE DE L'URL ---
        tunnel_url = get_tunnel_url()
        event_args["location"] = tunnel_url
        print(f"🔗 URL détectée pour l'événement : {tunnel_url}")
        # -----------------------------------------

        if os.path.exists("static/colisee.jpg"):
            with open("static/colisee.jpg", "rb") as f:
                event_args["image"] = f.read()

        await interaction.guild.create_scheduled_event(**event_args)
            
        message_admin = (
            f"✅ **Événement créé !**\n"
            f"📅 Début : `{debut}`\n"
            f"🔗 Lien : `{tunnel_url}`"
        )
        await interaction.followup.send(message_admin, ephemeral=True)

        annonce = f"@everyone 📢 Le Colisée ouvrira le **{debut}**. Stats en direct ici : {tunnel_url}"
        await interaction.channel.send(annonce)
        
    except ValueError:
        await interaction.followup.send("❌ Format date invalide ! (JJ/MM/AAAA HH:MM)", ephemeral=True)
    except Exception as e:
        print(f"Erreur setup_event : {e}")
        await interaction.followup.send(f"💥 Erreur : {e}", ephemeral=True)

bot.run(TOKEN)