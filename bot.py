
import discord
from discord.ext import tasks, commands
import socket
import json
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

with open("config.json","r") as f:
    config = json.load(f)

TOKEN = config["discord_token"]
CHANNEL_ID = config["channel_id"]
SERVER_IP = config["server_ip"]
SERVER_PORT = config["server_port"]
LOGO_URL = config["logo_url"]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

message_id = None

# --- Simple Web Server for Render ---
class WebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write(b"SCUM Discord Status Bot is running.")

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), WebServer)
    server.serve_forever()

def a2s_info(address):
    ip, port = address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3.0)

    payload = b'\xFF\xFF\xFF\xFFTSource Engine Query\x00'
    s.sendto(payload, (ip, port))
    data, _ = s.recvfrom(4096)

    if data.startswith(b'\xFF\xFF\xFF\xFFI'):
        data = data[5:]
        parts = data.split(b'\x00')

        name = parts[0].decode(errors="ignore")
        map_name = parts[1].decode(errors="ignore")

        players = data[-7]
        max_players = data[-6]

        return {
            "name": name,
            "map": map_name,
            "players": players,
            "max_players": max_players
        }

    return None

def ping_server(ip, port):
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((ip, port))
        sock.close()
        return int((time.time() - start) * 1000)
    except:
        return None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    update_status.start()

@tasks.loop(seconds=30)
async def update_status():
    global message_id

    channel = bot.get_channel(CHANNEL_ID)

    info = None
    ping = None

    try:
        info = a2s_info((SERVER_IP, SERVER_PORT))
        ping = ping_server(SERVER_IP, SERVER_PORT)
    except:
        info = None

    if info:
        status = "🟢 Online"
        players = f"{info['players']} / {info['max_players']}"
        map_name = info["map"]
        color = 0x2ecc71
    else:
        status = "🔴 Offline"
        players = "0 / 0"
        map_name = "Unknown"
        color = 0xe74c3c

    embed = discord.Embed(
        title="SCUM Server Status",
        description="Live Server Information",
        color=color
    )

    embed.add_field(name="🟢 Status", value=status, inline=True)
    embed.add_field(name="👥 Players", value=players, inline=True)
    embed.add_field(name="📡 Ping", value=f"{ping} ms" if ping else "N/A", inline=True)
    embed.add_field(name="🗺️ Map", value=map_name, inline=False)

    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)

    embed.set_footer(text="Auto refresh every 30 seconds")

    if message_id:
        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=embed)
            return
        except:
            message_id = None

    msg = await channel.send(embed=embed)
    message_id = msg.id

def start_bot():
    bot.run(TOKEN)

# Start web server thread (needed for Render)
threading.Thread(target=run_web).start()

# Start bot
start_bot()
