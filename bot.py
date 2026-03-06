import discord
from discord.ext import tasks, commands
import socket
import time
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ENV Variablen von Render
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SERVER_IP = os.getenv("SERVER_IP")
SERVER_PORT = int(os.getenv("SERVER_PORT", 27015))
LOGO_URL = os.getenv("LOGO_URL")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

message_id = None


# kleiner Webserver damit Render den Service aktiv hält
class WebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"SCUM Status Bot Running")


def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), WebServer)
    server.serve_forever()


# SCUM Server Query
def query_server(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(3)

        payload = b"\xFF\xFF\xFF\xFFTSource Engine Query\x00"
        s.sendto(payload, (ip, port))
        data, _ = s.recvfrom(4096)

        if data.startswith(b"\xFF\xFF\xFF\xFFI"):
            data = data[5:]
            parts = data.split(b"\x00")

            name = parts[0].decode(errors="ignore")
            map_name = parts[1].decode(errors="ignore")

            players = data[-7]
            max_players = data[-6]

            return name, map_name, players, max_players
    except:
        pass

    return None


# Ping messen
def get_ping(ip, port):
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
    print(f"Bot gestartet als {bot.user}")
    update_status.start()


@tasks.loop(seconds=30)
async def update_status():
    global message_id

    channel = bot.get_channel(CHANNEL_ID)

    info = query_server(SERVER_IP, SERVER_PORT)
    ping = get_ping(SERVER_IP, SERVER_PORT)

    if info:
        name, map_name, players, max_players = info
        status = "🟢 Online"
        player_text = f"{players}/{max_players}"
        color = 0x2ecc71
    else:
        status = "🔴 Offline"
        player_text = "0/0"
        map_name = "Unknown"
        color = 0xe74c3c

    embed = discord.Embed(
        title="SCUM Server Status",
        description="Live Server Informationen",
        color=color
    )

    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Spieler", value=player_text, inline=True)
    embed.add_field(name="Ping", value=f"{ping} ms" if ping else "N/A", inline=True)
    embed.add_field(name="Map", value=map_name, inline=False)

    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)

    embed.set_footer(text="Auto Update alle 30 Sekunden")

    try:
        if message_id:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=embed)
        else:
            msg = await channel.send(embed=embed)
            message_id = msg.id
    except:
        msg = await channel.send(embed=embed)
        message_id = msg.id


def start_bot():
    bot.run(TOKEN)


threading.Thread(target=run_web).start()
start_bot()
