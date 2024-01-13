import os
import discord
from discord.ext import commands
import json
from fuzzywuzzy import  process

intents = discord.Intents().all()
intents.members = True
intents.guild_messages = True
intents.guilds = True
intents.message_content = True


def has_required_role():
    async def predicate(ctx):
        required_roles = [1195672328911212557]  # Replace with your role IDs
        return any(role.id in required_roles for role in ctx.author.roles)
    return commands.check(predicate)

bot = commands.Bot(command_prefix='!', intents=intents)
bot.add_check(has_required_role())

bot.help_command = None

@bot.command()
async def help(ctx):
    help_text = """
    Here are the available commands:

    - `!dm <message>`: envoie un message direct à l'utilisateur associé au canal.
    - `!logs <user_id>`: envoie les logs de l'id utilisateur spécifié.
    - `!dellogs <user_id>`: supprime les logs de l'id utilisateur spécifié. (Tout les logs)
    - `!close <delay>`: ferme le canal après le délai spécifié (en secondes). Le délai peut être spécifié en secondes (s), minutes (m) ou heures (h). Par exemple, `!close 10m` fermera le canal après 10 minutes.
    - `!new <user_id>`: crée un nouveau canal pour l'utilisateur spécifié.
    - `!move <category_name>`: déplace le canal vers la catégorie spécifiée. (un nom approximatif peut être utilisé mais peut ne pas fonctionner correctement)
    - `!setrole <role_name_or_id>`: définit le rôle de l'utilisateur. Le rôle peut être spécifié par son nom ou son ID.
    - `!clearrole`: supprime le rôle de l'utilisateur.
    - `!role`: affiche le rôle de l'utilisateur.
    - `!remindme <delay> <message>`: envoie un message à l'utilisateur après le délai spécifié. Le délai peut être spécifié en secondes (s), minutes (m), heures (h) ou jours (d). Par exemple, `!remindme 10s` enverra un message après 10 secondes.
    - `!alert`: vous avertit lorsque l'utilisateur associé à ce canal envoie un message. Vous devez utiliser cette commande dans le canal associé à l'utilisateur.
    
    """
    await ctx.send(help_text)

# Load user-channel associations from file
try:
    with open('user_channel_dict.json', 'r') as f:
        if f.read().strip():
            f.seek(0)  # Reset file read position
            user_channel_dict = json.load(f)
        else:
            user_channel_dict = {}
except FileNotFoundError:
    user_channel_dict = {}

def save_user_channel_dict():
    with open('user_channel_dict.json', 'w') as f:
        json.dump(user_channel_dict, f)

async def get_channel_by_user_id(guild, user_id):
   
    if user_id in user_channel_dict:
        return guild.get_channel(user_channel_dict[user_id])
    return None

async def load_existing_channels(guild):
    for channel in guild.text_channels:
        if channel.topic and channel.topic.startswith("User ID: "):
            user_id = int(channel.topic.split(' ')[2])
            user_channel_dict[user_id] = channel.id

# A dictionary to store user-role associations
user_role_dict = {}

# A dictionary to store users who want to be notified on the next message from a specific user
users_to_notify = {}

#-------------------------------------------------------------------------------------------

@bot.command()
async def remindme(ctx, delay: str, *, message: str = ''):
    # Parse the delay string
    delay_seconds = 0
    if delay.endswith('s'):
        delay_seconds = int(delay[:-1])
    elif delay.endswith('m'):
        delay_seconds = int(delay[:-1]) * 60
    elif delay.endswith('h'):
        delay_seconds = int(delay[:-1]) * 3600
    elif delay.endswith('d'):
        delay_seconds = int(delay[:-1]) * 86400
    else:
        await ctx.send("Invalid delay format. Please specify the delay in seconds (s), minutes (m), hours (h), or days (d). For example, '10s' for 10 seconds.")
        return

    # Send a message to the user to confirm the reminder
    await ctx.send(f"Reminder set for {delay} from now.")

    # Wait for the specified number of seconds
    await asyncio.sleep(delay_seconds)
    # Send a message to the user
    if message:
        await ctx.send(f"{ctx.author.mention}, Rappel ! Message: {message}")
    else:
        await ctx.send(f"{ctx.author.mention}, Rappel !")

#-------------------------------------------------------------------------------------------

@bot.command()
async def setrole(ctx, *, role_name_or_id: str):
    # Try to convert the argument to an integer to see if it's an ID
    try:
        role_id = int(role_name_or_id)
        role = discord.utils.get(ctx.guild.roles, id=role_id)
    except ValueError:
        # If the argument is not an ID, treat it as a name
        role = discord.utils.get(ctx.guild.roles, name=role_name_or_id)

    if role is not None:
        # Associate the role with the user
        user_role_dict[ctx.author.id] = role.name
        await ctx.send(f"Role '{role.name}' set for user {ctx.author.display_name}.")
    else:
        await ctx.send("Role not found.")

#-------------------------------------------------------------------------------------------

@bot.command()
async def clearrole(ctx):
    # Check if the user has a role set
    if ctx.author.id in user_role_dict:
        # Remove the role from the user
        del user_role_dict[ctx.author.id]
        await ctx.send("Your role has been removed.")
    else:
        await ctx.send("You do not have a role set.")

#-------------------------------------------------------------------------------------------

@bot.command()
async def role(ctx):
    # Get the role of the user, if any
    role = user_role_dict.get(ctx.author.id)
    if role is None:
        # If the user has not used the 'setrole' command, use their top role
        role = ctx.author.top_role.name if ctx.author.top_role != ctx.guild.default_role else ""
    if role:
        await ctx.send(f"Your current role is '{role}'.")
    else:
        await ctx.send("You do not have a role.")

#-------------------------------------------------------------------------------------------

@bot.command()
async def dm(ctx, *, message: str):
    # Extract the user ID from the channel name
    user_id = int(ctx.channel.topic.split(' ')[2])  # Assuming the user ID is the third word in the channel topic
    user = bot.get_user(user_id)
    if user is not None:
        # Get the role of the user, if any
        role = user_role_dict.get(ctx.author.id)
        if role is None:
            # If the user has not used the 'setrole' command, use their top role
            role = ctx.author.top_role.name if ctx.author.top_role != ctx.guild.default_role else ""
        role_str = f" ({role})" if role else ""
        # Prefix the message with the display name of the person who used the command and their role
        message = f"{ctx.author.display_name}{role_str}: {message}"
        await user.send(message)
    else:
        await ctx.send("User not found.")

#-------------------------------------------------------------------------------------------

@bot.command()
@commands.has_permissions(manage_channels=True)
async def move(ctx, category_name: str):
    # Check if the channel was created by the bot
    if ctx.channel.id not in user_channel_dict.values():
        await ctx.send("This channel was not created by the bot.")
        return

    category = discord.utils.get(ctx.guild.categories, name=category_name)
    if category is None:
        # If the category doesn't exist, find the closest match
        names = [cat.name for cat in ctx.guild.categories]
        closest_name, _ = process.extractOne(category_name, names)
        category = discord.utils.get(ctx.guild.categories, name=closest_name)
        if category is None:
            await ctx.send(f"No category found close to '{category_name}'.")
            return
    await ctx.channel.edit(category=category)
    await ctx.send(f"Channel moved to {category.name} category.")

#-------------------------------------------------------------------------------------------

channel_created_by_new_command = False

@bot.command()
async def new(ctx, user_id: int, *, reason=None):
    global channel_created_by_new_command
    channel_created_by_new_command = True

    # Get the user
    user = bot.get_user(user_id)
    if user is None:
        await ctx.send(f"No user found with ID {user_id}.")
        return

    # Get the 'MP à trier' category
    category = discord.utils.get(ctx.guild.categories, name='MP à trier')
    if category is None:
        await ctx.send("No category 'MP à trier' found.")
        return

    # Create a new channel with the user's name, in the 'MP à trier' category
    channel = await ctx.guild.create_text_channel(name=user.name, category=category, topic=f"User ID: {user_id}")

    # Save the user-channel association
    user_channel_dict[user_id] = channel.id
    save_user_channel_dict()

    await ctx.send(f"Channel '{user.name}' created in the 'MP à trier' category.")

#-------------------------------------------------------------------------------------------

import os

@bot.command()
async def dellogs(ctx, user_id: int):
    # Get the list of log files for the specified user ID
    log_files = [f for f in os.listdir('.') if os.path.isfile(f) and str(user_id) in f and f.endswith('.html')]

    if log_files:
        for file in log_files:
            os.remove(file)
        await ctx.send(f"Deleted {len(log_files)} log files for user ID {user_id}.")
    else:
        await ctx.send("Plus aucun log de disponible.")

    # Get the 'liste-des-logs' channel
    log_channel = discord.utils.get(ctx.guild.channels, name='liste-des-logs')

    if log_channel is not None:
        # Delete all messages in the 'liste-des-logs' channel that contain the user ID
        async for message in log_channel.history():
            if str(user_id) in message.content:
                await message.delete()

#-------------------------------------------------------------------------------------------

@bot.command()
async def logs(ctx, user_id: int = None):
    # If no user_id was provided, get it from the channel topic
    if user_id is None:
        # Extract the user ID from the channel topic
        topic = ctx.channel.topic
        if topic is not None and "User ID: " in topic:
            user_id = int(ctx.channel.topic.split(' ')[2])
        else:
            await ctx.send("No user ID provided and no user ID found in channel topic.")
            return

    # Get the 'liste-des-logs' channel
    log_channel = discord.utils.get(ctx.guild.text_channels, name='liste-des-logs')

    if log_channel is None:
        await ctx.send("Le canal 'liste-des-logs' n'a pas été trouvé.")
        return

    # Get the history of the 'liste-des-logs' channel
    messages = []
    async for message in log_channel.history():
        messages.append(message)

    # Filter the messages to find those that contain the log file for the specified user ID
    log_messages = [m for m in messages if m.attachments and str(user_id) in m.content]

    if log_messages:
        for message in log_messages:
            await ctx.send(f"Log file: {message.attachments[0].url}")
    else:
        await ctx.send("No log files found for the specified user ID.")

#-------------------------------------------------------------------------------------------        

import datetime
import asyncio
import os

@bot.command()
@commands.has_permissions(manage_channels=True)
async def close(ctx, delay: str = '0.5s'):
    def convert_to_seconds(value, unit):
        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        else:
            return None

    # extrait la valeur et l'unité du délai
    delay_value = float(delay[:-1])
    delay_unit = delay[-1]

    # convertis le délai en secondes
    delay_seconds = convert_to_seconds(delay_value, delay_unit)
    if delay_seconds is None:
        await ctx.send("Invalid delay unit. Please use 's' for seconds, 'm' for minutes, or 'h' for hours.")
        return

    # si le délai est supérieur à 10 secondes, envois un message d'avertissement
    if delay_seconds > 10:
        await ctx.send(f"Attention, ce canal sera supprimé dans {delay_value}{delay_unit}. Envoyez 'annuler' pour annuler la suppression.")

    # extrait l'id utilisateur du nom du canal
    user_id = int(ctx.channel.topic.split(' ')[2])  # définis l'id utilisateur comme étant le 3ème mot du topic du canal

    # obtention de l'utilisateur
    user = bot.get_user(user_id)
    if user is None:
        await ctx.send("User not found.")
        return

    # suppressions du dictionnaire user-channel
    if user_id in user_channel_dict:
        del user_channel_dict[user_id]

    # attente du délai
    if delay_seconds > 0.5:
        if delay_seconds > 30:
            try:
                def check(m):
                    return m.content == 'annuler' and m.channel == ctx.channel

                await bot.wait_for('message', check=check, timeout=delay_seconds)
                await ctx.send("La suppression du canal a été annulée.")
                return
            except asyncio.TimeoutError:
                pass

        await asyncio.sleep(delay_seconds)

  
     # sauvegarde les logs dans un fichier html
    filename = f'{user.name}_{ctx.channel.created_at.strftime("%d%m%Y")}.html'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<html><body>\n')
        async for message in ctx.channel.history(oldest_first=True):
            f.write(f'<p>{message.created_at} - {message.author.name}: {message.content}</p>\n')
        f.write('</body></html>\n')

    # essaye d'envoyer un dm a l'utilisateur
    try:
        await user.send('ta demande a été classé !')
    except discord.Forbidden:
        await ctx.send("Failed to send a direct message to the user.")

    # supprime le canal
    await ctx.channel.delete()

    # sauvegarde le dictionnaire user-channel dans un fichier
    save_user_channel_dict()

    # trouve le canal liste-des-logs
    log_channel = discord.utils.get(ctx.guild.text_channels, name='liste-des-logs')

    # envois le fichier de log dans le canal liste-des-logs
    with open(filename, 'rb') as f:
        await log_channel.send(
            f"Le canal {ctx.channel.name} (ID Discord: {user.id}) a été supprimé. Date d'ouverture : {ctx.channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            file=discord.File(f, filename)
        )

#-------------------------------------------------------------------------------------------
        
import datetime
import asyncio
import os

@bot.command()
@commands.has_permissions(manage_channels=True)
async def closes(ctx, delay: str = '0.5s'):
    def convert_to_seconds(value, unit):
        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        else:
            return None

    # extrait la valeur et l'unité du délai
    delay_value = float(delay[:-1])
    delay_unit = delay[-1]

    # convertis le délai en secondes
    delay_seconds = convert_to_seconds(delay_value, delay_unit)
    if delay_seconds is None:
        await ctx.send("Invalid delay unit. Please use 's' for seconds, 'm' for minutes, or 'h' for hours.")
        return

    # si le délai est supérieur à 10 secondes, envois un message d'avertissement
    if delay_seconds > 10:
        await ctx.send(f"Attention, ce canal sera supprimé dans {delay_value}{delay_unit}. Envoyez 'annuler' pour annuler la suppression.")

    # extrait l'id utilisateur du nom du canal
    user_id = int(ctx.channel.topic.split(' ')[2])  # définis l'id utilisateur comme étant le 3ème mot du topic du canal

    # obtention de l'utilisateur
    user = bot.get_user(user_id)
    if user is None:
        await ctx.send("User not found.")
        return

    # suppressions du dictionnaire user-channel
    if user_id in user_channel_dict:
        del user_channel_dict[user_id]

    # attente du délai
    if delay_seconds > 0.5:
        if delay_seconds > 30:
            try:
                def check(m):
                    return m.content == 'annuler' and m.channel == ctx.channel

                await bot.wait_for('message', check=check, timeout=delay_seconds)
                await ctx.send("La suppression du canal a été annulée.")
                return
            except asyncio.TimeoutError:
                pass

        await asyncio.sleep(delay_seconds)

  
     # sauvegarde les logs dans un fichier html
    filename = f'{user.name}_{ctx.channel.created_at.strftime("%d%m%Y")}.html'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<html><body>\n')
        async for message in ctx.channel.history(oldest_first=True):
            f.write(f'<p>{message.created_at} - {message.author.name}: {message.content}</p>\n')
        f.write('</body></html>\n')

    # supprime le canal
    await ctx.channel.delete()

    # sauvegarde le dictionnaire user-channel dans un fichier
    save_user_channel_dict()

    # trouve le canal liste-des-logs
    log_channel = discord.utils.get(ctx.guild.text_channels, name='liste-des-logs')

    # envois le fichier de log dans le canal liste-des-logs
    with open(filename, 'rb') as f:
        await log_channel.send(
            f"Le canal {ctx.channel.name} (ID Discord: {user.id}) a été supprimé. Date d'ouverture : {ctx.channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            file=discord.File(f, filename)
        )

#-------------------------------------------------------------------------------------------   

@bot.event
async def on_ready():
    guild = bot.get_guild(1190316577925632090)  # ID du serveur
    await load_existing_channels(guild)

#-------------------------------------------------------------------------------------------

async def send_dm(user_id, message):
    user = bot.get_user(user_id)
    if user is None:
        print(f"User with ID {user_id} not found.")
        return
    try:
        await user.send(message)
    except discord.Forbidden:
        print(f"Permission denied for sending DM to user {user_id}.")

@bot.command()
async def alert(ctx):
    # Get the Discord ID from the channel topic
    discord_id = int(ctx.channel.topic.split(' ')[2])

    # Add the user to the dictionary of users to notify
    users_to_notify[ctx.author.id] = discord_id
    await ctx.send(f"tu sera avertie lors de la réponse de <@{discord_id}>.")

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if isinstance(message.channel, discord.DMChannel) and message.author != bot.user:
        guild = bot.get_guild(1190316577925632090)  # ID du serveur
        channel = await get_channel_by_user_id(guild, message.author.id)

        if not channel:
            global channel_created_by_new_command
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            category = discord.utils.get(guild.categories, name="MP à trier")  # nom de la catégorie racine
            if not category:
                await ctx.send("Category not found.")
                return
            channel = await category.create_text_channel(f"{message.author.name}", overwrites=overwrites)
            user_channel_dict[message.author.id] = channel.id
            await channel.edit(topic=f"User ID: {message.author.id}")

            if not channel_created_by_new_command:
                dm_channel = message.author.dm_channel
                if dm_channel is None:
                    dm_channel = await message.author.create_dm()
                await dm_channel.send("Votre message a été reçu et sera traité prochainement.")
            else:
                channel_created_by_new_command = False

        await channel.send(f"{message.author.name} : {message.content}")

        # If the author of the message is a user that someone wants to be notified about
        if message.author.id in users_to_notify.values():
            # Find all users who want to be notified about this user
            users_to_notify_about_this_user = [user_id for user_id, user_to_notify_about in users_to_notify.items() if user_to_notify_about == message.author.id]

            # Send a message in the channel to each user who wants to be notified
            for user_id in users_to_notify_about_this_user:
                # Mention the user
                await channel.send(f"<@{user_id}>, <@{message.author.id}> à répondu : {message.content}")
                # Remove the user from the dictionary of users to notify
                del users_to_notify[user_id]

save_user_channel_dict()  # sauvegarde user-channel associations au démarrage
import json
with open('config.json') as f:
    data = json.load(f)

#-------------------------------------------------------------------------------------------

bot_token = data["DISCORD_TOKEN"]
bot.run(bot_token)