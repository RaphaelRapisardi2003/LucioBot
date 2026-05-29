import discord
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os
import random

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Per-guild state to support multiple servers simultaneously
guilds = {}


def get_state(guild_id):
    if guild_id not in guilds:
        guilds[guild_id] = {
            'queue': [],
            'is_playing': False,
            'current': None,
            'idle_task': None,
            'loop': False,
            'volume': 0.5,
        }
    return guilds[guild_id]


@bot.event
async def on_ready():
    print(f'Logado como {bot.user}')


def _search_yt(query):
    is_url = query.startswith('http://') or query.startswith('https://')
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
        search = query if is_url else f"ytsearch:{query}"
        info = ydl.extract_info(search, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        return {
            'source': info['url'],
            'title': info['title'],
            'duration': info.get('duration', 0),
        }


def format_duration(seconds):
    if not seconds:
        return "?"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


async def idle_disconnect(ctx):
    await asyncio.sleep(300)
    if ctx.voice_client and not ctx.voice_client.is_playing():
        await ctx.voice_client.disconnect()
        await ctx.send("⏳ Fiquei sem música por 5 minutos, saindo do canal...")


async def play_next(ctx):
    state = get_state(ctx.guild.id)

    if state['loop'] and state['current']:
        state['queue'].insert(0, state['current'])

    if len(state['queue']) > 0:
        state['is_playing'] = True
        state['current'] = state['queue'].pop(0)

        if state['idle_task']:
            state['idle_task'].cancel()
            state['idle_task'] = None

        source = discord.FFmpegPCMAudio(
            state['current']['source'],
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            options='-vn'
        )

        volume_source = discord.PCMVolumeTransformer(source, volume=state['volume'])

        ctx.voice_client.play(
            volume_source,
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        )

        duration = format_duration(state['current'].get('duration', 0))
        await ctx.send(f"🎶 Tocando: **{state['current']['title']}** `[{duration}]`")

    else:
        state['is_playing'] = False
        state['current'] = None
        state['idle_task'] = asyncio.create_task(idle_disconnect(ctx))


@bot.command()
async def play(ctx, *, query):
    state = get_state(ctx.guild.id)

    if not ctx.author.voice:
        await ctx.send("❌ Você precisa estar em um canal de voz!")
        return

    channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)

    if state['idle_task']:
        state['idle_task'].cancel()
        state['idle_task'] = None

    await ctx.send(f"🔎 Buscando: **{query}**...")

    try:
        data = await asyncio.get_event_loop().run_in_executor(None, _search_yt, query)
    except Exception as e:
        await ctx.send(f"❌ Erro ao buscar: {e}")
        return

    state['queue'].append(data)
    duration = format_duration(data.get('duration', 0))
    position = len(state['queue'])

    if state['is_playing']:
        await ctx.send(f"➕ Adicionado na posição {position}: **{data['title']}** `[{duration}]`")
    else:
        await ctx.send(f"➕ Adicionado: **{data['title']}** `[{duration}]`")
        await play_next(ctx)


@bot.command()
async def skip(ctx):
    state = get_state(ctx.guild.id)
    if ctx.voice_client and ctx.voice_client.is_playing():
        state['loop'] = False
        ctx.voice_client.stop()
        await ctx.send("⏭️ Pulando...")
    else:
        await ctx.send("❌ Nada tocando no momento.")


@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Pausado")
    else:
        await ctx.send("❌ Nada tocando no momento.")


@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Retomado")
    else:
        await ctx.send("❌ Nada pausado no momento.")


@bot.command()
async def stop(ctx):
    state = get_state(ctx.guild.id)
    state['queue'] = []
    state['loop'] = False
    state['is_playing'] = False
    state['current'] = None

    if state['idle_task']:
        state['idle_task'].cancel()
        state['idle_task'] = None

    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Parado e fila limpa")


@bot.command(name="queue")
async def show_queue(ctx):
    state = get_state(ctx.guild.id)

    if state['current'] is None and len(state['queue']) == 0:
        await ctx.send("📭 Fila vazia")
        return

    msg = ""
    loop_label = " 🔁" if state['loop'] else ""

    if state['current']:
        duration = format_duration(state['current'].get('duration', 0))
        msg += f"🎶 **Tocando agora{loop_label}:**\n{state['current']['title']} `[{duration}]`\n\n"

    if len(state['queue']) > 0:
        msg += f"📃 **Próximas músicas ({len(state['queue'])}):**\n"
        for i, song in enumerate(state['queue'][:10]):
            duration = format_duration(song.get('duration', 0))
            msg += f"`{i+1}.` {song['title']} `[{duration}]`\n"
        if len(state['queue']) > 10:
            msg += f"*...e mais {len(state['queue']) - 10} músicas*"

    await ctx.send(msg)


@bot.command()
async def nowplaying(ctx):
    state = get_state(ctx.guild.id)
    if not state['current']:
        await ctx.send("❌ Nada tocando no momento.")
        return
    duration = format_duration(state['current'].get('duration', 0))
    loop_status = " | 🔁 Loop ativo" if state['loop'] else ""
    vol_pct = int(state['volume'] * 100)
    await ctx.send(
        f"🎶 **Tocando agora:**\n**{state['current']['title']}**\n"
        f"`Duração: {duration}` | `Volume: {vol_pct}%`{loop_status}"
    )


@bot.command()
async def volume(ctx, vol: int):
    state = get_state(ctx.guild.id)
    if not 0 <= vol <= 100:
        await ctx.send("❌ Volume deve ser entre 0 e 100.")
        return
    state['volume'] = vol / 100
    if ctx.voice_client and ctx.voice_client.source:
        ctx.voice_client.source.volume = state['volume']
    await ctx.send(f"🔊 Volume ajustado para **{vol}%**")


@bot.command(name="loop")
async def toggle_loop(ctx):
    state = get_state(ctx.guild.id)
    state['loop'] = not state['loop']
    status = "ativado 🔁" if state['loop'] else "desativado"
    await ctx.send(f"🔁 Loop {status}")


@bot.command()
async def shuffle(ctx):
    state = get_state(ctx.guild.id)
    if len(state['queue']) < 2:
        await ctx.send("❌ Fila precisa de ao menos 2 músicas para embaralhar.")
        return
    random.shuffle(state['queue'])
    await ctx.send("🔀 Fila embaralhada!")


@bot.command()
async def remove(ctx, index: int):
    state = get_state(ctx.guild.id)
    if index < 1 or index > len(state['queue']):
        await ctx.send(f"❌ Índice inválido. A fila tem {len(state['queue'])} música(s).")
        return
    removed = state['queue'].pop(index - 1)
    await ctx.send(f"🗑️ Removido: **{removed['title']}**")


@bot.command()
async def move(ctx, from_pos: int, to_pos: int):
    state = get_state(ctx.guild.id)
    n = len(state['queue'])
    if not (1 <= from_pos <= n and 1 <= to_pos <= n):
        await ctx.send(f"❌ Posições inválidas. A fila tem {n} música(s).")
        return
    song = state['queue'].pop(from_pos - 1)
    state['queue'].insert(to_pos - 1, song)
    await ctx.send(f"↕️ **{song['title']}** movido para posição {to_pos}")


@bot.command()
async def clear(ctx):
    state = get_state(ctx.guild.id)
    state['queue'] = []
    await ctx.send("🧹 Fila limpa!")


@bot.command(name="help_music")
async def help_music(ctx):
    embed = discord.Embed(title="🎵 Comandos do LucioBot", color=discord.Color.blue())
    embed.add_field(name="!play <busca ou URL>", value="Toca uma música ou URL do YouTube", inline=False)
    embed.add_field(name="!skip", value="Pula a música atual", inline=False)
    embed.add_field(name="!pause / !resume", value="Pausa ou retoma a reprodução", inline=False)
    embed.add_field(name="!stop", value="Para tudo, limpa a fila e sai do canal", inline=False)
    embed.add_field(name="!queue", value="Exibe a fila de músicas", inline=False)
    embed.add_field(name="!nowplaying", value="Exibe a música atual com detalhes", inline=False)
    embed.add_field(name="!volume <0-100>", value="Ajusta o volume", inline=False)
    embed.add_field(name="!loop", value="Ativa/desativa repetição da música atual", inline=False)
    embed.add_field(name="!shuffle", value="Embaralha a fila", inline=False)
    embed.add_field(name="!remove <nº>", value="Remove uma música da fila pelo número", inline=False)
    embed.add_field(name="!move <de> <para>", value="Move uma música de posição na fila", inline=False)
    embed.add_field(name="!clear", value="Limpa toda a fila sem parar a música atual", inline=False)
    await ctx.send(embed=embed)


TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN não encontrado. Verifique o arquivo .env")

bot.run(TOKEN)
