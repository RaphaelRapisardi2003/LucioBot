import discord
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

queue = []
is_playing = False
current = None
idle_task = None 

@bot.event
async def on_ready():
    print(f'Logado como {bot.user}')


def search_yt(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android']
            }
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        return {
            'source': info['url'],
            'title': info['title']
        }


async def idle_disconnect(ctx):
    await asyncio.sleep(60)

    if ctx.voice_client and not ctx.voice_client.is_playing():
        await ctx.voice_client.disconnect()
        await ctx.send("⏳ Fiquei sem música, saindo do canal...")


async def play_next(ctx):
    global is_playing, current, idle_task

    if len(queue) > 0:
        is_playing = True
        current = queue.pop(0)

        if idle_task:
            idle_task.cancel()

        source = discord.FFmpegPCMAudio(
            current['source'],
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            options='-vn'
        )

        ctx.voice_client.play(
            source,
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        )

        await ctx.send(f"🎶 Tocando: **{current['title']}**")

    else:
        is_playing = False
        current = None
        idle_task = asyncio.create_task(idle_disconnect(ctx))


@bot.command()
async def play(ctx, *, query):
    global idle_task

    if not ctx.author.voice:
        await ctx.send("Você precisa estar em um canal de voz!")
        return

    channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await channel.connect()
    else:
        await ctx.voice_client.move_to(channel)

    if idle_task:
        idle_task.cancel()

    await ctx.send(f"🔎 Buscando: {query}...")

    data = search_yt(query)
    queue.append(data)

    await ctx.send(f"➕ Adicionado: **{data['title']}**")

    if not is_playing:
        await play_next(ctx)


@bot.command()
async def skip(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏭️ Pulando...")


@bot.command()
async def pause(ctx):
    if ctx.voice_client:
        ctx.voice_client.pause()
        await ctx.send("⏸️ Pausado")


@bot.command()
async def resume(ctx):
    if ctx.voice_client:
        ctx.voice_client.resume()
        await ctx.send("▶️ Retomado")


@bot.command()
async def stop(ctx):
    global queue
    queue = []

    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Parado e limpei a fila")

@bot.command(name="queue")
async def show_queue(ctx):
    if current is None and len(queue) == 0:
        await ctx.send("📭 Fila vazia")
        return

    msg = ""

    if current:
        msg += f"🎶 Tocando agora:\n**{current['title']}**\n\n"

    if len(queue) > 0:
        msg += "📃 Próximas músicas:\n"
        for i, song in enumerate(queue[:10]):  
            msg += f"{i+1}. {song['title']}\n"

    await ctx.send(msg)

TOKEN = os.getenv("DISCORD_TOKEN")

with open(TOKEN) as file:
    token = file.read().strip()

bot.run(token)