import requests
import urllib.parse
import discord
from discord import app_commands, EntityType, PrivacyLevel
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
TOKEN = os.getenv("DISCORD_TOKEN")
PATH_PLAYERS = "static/players.json"

class MyBot(commands.Bot):
    def __init__(self):
        # On définit les intentions
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True 

        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Commandes Slash synchronisées")

bot = MyBot()

def load_players():
    if os.path.exists(PATH_PLAYERS):
        with open(PATH_PLAYERS, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_players(players):
    with open(PATH_PLAYERS, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=4, ensure_ascii=False)

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
    # 1. On utilise defer car la création d'un événement avec image est lente
    await interaction.response.defer(ephemeral=True)

    try:
        # 2. Validation ET assignation des variables
        local_tz = datetime.now().astimezone().tzinfo
        
        start_dt = datetime.strptime(debut, "%d/%m/%Y %H:%M").replace(tzinfo=local_tz)
        end_dt = datetime.strptime(fin, "%d/%m/%Y %H:%M").replace(tzinfo=local_tz)
        
        # 3. Sauvegarde dans config.json
        config = {
            "start_date": debut,
            "end_date": fin
        }
        with open("static/config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

        # 4. Lecture de l'image pour la bannière
        banner_bytes = None
        if os.path.exists("static/colisee.jpg"):
            print("ok")
            with open("static/colisee.jpg", "rb") as f:
                banner_bytes = f.read()

        # 5. Création de l'événement Discord
        await interaction.guild.create_scheduled_event(
            name="🏆 Colisée de la Reine Salope.",
            description="Le tournoi commence !",
            start_time=start_dt,
            end_time=end_dt,
            entity_type=EntityType.external,
            location="http://ton-ip-serveur:5000",
            privacy_level=PrivacyLevel.guild_only,
            image=banner_bytes
        )
            
        # 6. Confirmation pour l'admin
        message_admin = (
            f"**Événement créé et configuration sauvegardée !**\n"
            f"Début : `{debut}`\n"
            f"Fin : `{fin}`"
        )
        await interaction.followup.send(message_admin, ephemeral=True)

        # 7. Annonce publique
        annonce = f"@everyone 📢 Le Colisée s'ouvrira le **{debut}** jusqu'à **{fin}**. Que le sang coule !"
        await interaction.channel.send(annonce)
        
    except ValueError:
        await interaction.followup.send(
            "❌ **Erreur de format !** Utilise bien : `JJ/MM/AAAA HH:MM`.", 
            ephemeral=True 
        )
    except Exception as e:
        print(f"Erreur critique setup_event : {e}")
        await interaction.followup.send(
            f"💥 Une erreur est survenue : {e}", 
            ephemeral=True
        )

bot.run(TOKEN)