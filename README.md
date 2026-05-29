# LucioBot 🎵

Bot de música para Discord feito em Python com suporte a YouTube.

## Funcionalidades

- Toca músicas do YouTube por nome ou URL direta
- Fila de músicas com suporte a múltiplos servidores simultaneamente
- Controle de volume em tempo real
- Modo loop, embaralhamento e remoção de músicas
- Desconexão automática após 5 minutos sem música

## Requisitos

- Python 3.8+
- FFmpeg instalado e no PATH

## Instalação

```bash
pip install discord.py yt-dlp python-dotenv
```

Crie um arquivo `.env` na raiz do projeto:

```env
BOT_TOKEN=seu_token_aqui
```

## Uso

```bash
python main.py
```

## Comandos

| Comando | Descrição |
|---|---|
| `!play <busca ou URL>` | Toca uma música ou URL do YouTube |
| `!skip` | Pula a música atual |
| `!pause` | Pausa a reprodução |
| `!resume` | Retoma a reprodução |
| `!stop` | Para tudo, limpa a fila e sai do canal |
| `!queue` | Exibe a fila de músicas |
| `!nowplaying` | Exibe a música atual com duração e volume |
| `!volume <0-100>` | Ajusta o volume |
| `!loop` | Ativa/desativa repetição da música atual |
| `!shuffle` | Embaralha a fila |
| `!remove <nº>` | Remove uma música da fila pelo número |
| `!move <de> <para>` | Move uma música de posição na fila |
| `!clear` | Limpa a fila sem parar a música atual |
| `!help_music` | Exibe todos os comandos disponíveis |
