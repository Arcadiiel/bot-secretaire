import discord
from discord.ext import commands
import json

intents = discord.Intents().all()
intents.members = True
intents.guild_messages = True
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Load user-channel associations from file
try:
    with open('user_channel_dict.json', 'r') as f:
        user_channel_dict = json.load(f)
except FileNotFoundError:
    user_channel_dict = {}

# Save user-channel associations to file
def save_user_channel_dict():
    with open('user_channel_dict.json', 'w') as f:
        json.dump(user_channel_dict, f)

# Create a dictionary to store user-channel associations
user_channel_dict = {}

async def get_channel_by_user_id(guild, user_id):
    # Check if user already has a channel
    if user_id in user_channel_dict:
        return guild.get_channel(user_channel_dict[user_id])
    return None


@bot.command()
async def dm(ctx, *, message: str):
    # Extract the user ID from the channel name
    user_id = int(ctx.channel.topic.split(' ')[2])  # Assuming the user ID is the third word in the channel topic
    user = bot.get_user(user_id)
    if user is not None:
        await user.send(message)
    else:
        await ctx.send("User not found.")

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if isinstance(message.channel, discord.DMChannel) and message.author != bot.user:
        guild = bot.get_guild(1190316577925632090)  # Replace with your guild ID
        channel = await get_channel_by_user_id(guild, message.author.id)

        if not channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            # Generate a unique channel number
            channel_number = len(user_channel_dict) + 1
            channel = await guild.create_text_channel(f"channel-{channel_number}", overwrites=overwrites)
            # Store the association between the user and the channel
            user_channel_dict[message.author.id] = channel.id
            await channel.edit(topic=f"User ID: {message.author.id}")  # Set the user ID as the channel topic

        await channel.send(f"{message.author.name}: {message.content}")

bot.run('MTE5NTMyODExMzA3MzIwOTQyNg.GcwjI2.HAWMOKBWJkmufpXlgqWEgC9puTNTl8okaZB-Mo') 

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
import time
import schedule
import pickle

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def job():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    file_metadata = {'name': 'MyFile.json'}
    media = MediaFileUpload('user_channel_dict.json', 
                            mimetype='application/json',
                            resumable=True)
    created = service.files().create(body=file_metadata,
                                     media_body=media,
                                     fields='id').execute()
    print('File ID: {}'.format(created.get('id')))

schedule.every(10).seconds.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)




