import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, Button, View
import requests
import time
import asyncio
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv non installé. Utilisation des variables d'environnement système.")

class DmallModal(Modal):
    def __init__(self):
        super().__init__(title="Configuration du Dmall", timeout=180)
        
        self.add_item(TextInput(
            label="Entrez le token",
            placeholder="Votre token Discord...",
            style=discord.TextStyle.long,
            required=True
        ))
        
        self.add_item(TextInput(
            label="Entrez le message",
            placeholder="Exemple: Bonjour {user} cv ?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        ))
    
    async def on_submit(self, interaction: discord.Interaction):
        token = self.children[0].value
        message = self.children[1].value
        
        # Envoyer le message de confirmation
        embed = discord.Embed(
            title="🚀 Confirmation",
            description=f"**Message:** {message}\n\nÊtes-vous sûr de vouloir envoyer ce message à tous vos amis ?",
            color=0xED4245
        )
        
        confirm_view = View(timeout=60)
        
        async def send_messages_callback(interaction):
            try:
                await interaction.response.edit_message(
                    content="🔍 Envoi en cours...", 
                    embed=None, 
                    view=None
                )
                
                success, result = await send_messages_to_friends(token, message, 2)
                
                if success:
                    embed = discord.Embed(
                        title="🎉 Succès",
                        description=result,
                        color=0x57F287
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Erreur",
                        description=result,
                        color=0xED4245
                    )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as e:
                await interaction.followup.send(f"❌ Erreur: {str(e)}", ephemeral=True)
        
        async def cancel_callback(interaction):
            try:
                await interaction.response.edit_message(
                    content="❌ Annulé", 
                    embed=None, 
                    view=None
                )
            except:
                pass
        
        send_btn = Button(label="Envoyer", style=discord.ButtonStyle.green)
        send_btn.callback = send_messages_callback
        confirm_view.add_item(send_btn)
        
        cancel_btn = Button(label="Annuler", style=discord.ButtonStyle.red)
        cancel_btn.callback = cancel_callback
        confirm_view.add_item(cancel_btn)
        
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class DmallBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.dm_messages = True
        
        super().__init__(command_prefix="+", intents=intents, help_command=None)
        
    async def on_ready(self):
        print(f'✅ Bot connecté en tant que {self.user}')
        print('🤖 Bot prêt à recevoir les commandes /dmall')
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/dmall"))
        
        # Synchroniser les slash commands
        try:
            synced = await self.tree.sync()
            print(f"📋 {len(synced)} commandes slash synchronisées")
        except Exception as e:
            print(f"❌ Erreur de synchronisation: {e}")
    
    async def on_message(self, message):
        # Plus de commandes préfixes, uniquement les slash commands
        await self.process_commands(message)

async def send_messages_to_friends(token, message, delay):
    """Envoie des messages à tous les amis"""
    try:
        headers = {'Authorization': token.strip()}
        
        # Vérifier le token
        response = requests.get('https://discord.com/api/v10/users/@me', headers=headers)
        if response.status_code != 200:
            return False, "Token invalide"
        
        user_info = response.json()
        
        # Récupérer les amis
        response = requests.get('https://discord.com/api/v10/users/@me/relationships', headers=headers)
        if response.status_code != 200:
            return False, "Impossible de récupérer les amis"
        
        relationships = response.json()
        friends = [rel for rel in relationships if rel['type'] == 1]
        
        if not friends:
            return False, "Aucun ami trouvé"
        
        # Envoyer les messages
        success_count = 0
        for friend in friends:
            try:
                user_id = friend['id']
                username = friend['user']['username']
                
                # Personnaliser le message
                personalized_message = message.replace("{user}", username)
                
                # Créer le channel DM
                dm_response = requests.post(
                    f'https://discord.com/api/v10/users/@me/channels',
                    headers=headers,
                    json={'recipient_id': str(user_id)}
                )
                
                if dm_response.status_code == 200:
                    channel_data = dm_response.json()
                    channel_id = channel_data['id']
                    
                    # Envoyer le message
                    message_response = requests.post(
                        f'https://discord.com/api/v10/channels/{channel_id}/messages',
                        headers=headers,
                        json={'content': personalized_message}
                    )
                    
                    if message_response.status_code == 200:
                        success_count += 1
                
                time.sleep(delay)
                
            except Exception as e:
                print(f"❌ Erreur avec {friend['user']['username']}: {e}")
        
        return True, f"Messages envoyés à {success_count}/{len(friends)} amis"
        
    except Exception as e:
        return False, f"Erreur: {str(e)}"

def main():
    # Token du bot Discord depuis les variables d'environnement
    BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    bot = DmallBot()
    
    # Ajouter la commande slash
    @bot.tree.command(name="dmall", description="Ouvre la configuration pour envoyer des messages à tous vos amis")
    async def dmall_slash(interaction: discord.Interaction):
        """Commande slash /dmall"""
        
        # Vérifier si l'utilisateur a la permission
        if interaction.user.id != interaction.guild.owner_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Seuls les administrateurs peuvent utiliser cette commande !", ephemeral=True)
            return
        
        # Ouvrir directement le modal
        modal = DmallModal()
        await interaction.response.send_modal(modal)
    
    if not BOT_TOKEN or BOT_TOKEN == "TON_TOKEN_BOT_ICI":
        print("❌ Mets le token de ton bot Discord dans la variable DISCORD_BOT_TOKEN")
        print("📖 Crée un bot sur https://discord.com/developers/applications")
    else:
        bot.run(BOT_TOKEN)

if __name__ == "__main__":
    main()
