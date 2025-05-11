import sys
import os
import asyncio

# Add the /app directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram import BOT_TOKEN, CLIENT, song_callback_query, \
    album_callback_query, new_message, artist_callback_query, \
    playlist_callback_query

async def main():
    print('[BOT] Starting...')
    await CLIENT.start(bot_token=BOT_TOKEN)
    song_callback_query.register_callbacks(CLIENT)
    album_callback_query.register_callbacks(CLIENT)
    artist_callback_query.register_callbacks(CLIENT)
    playlist_callback_query.register_callbacks(CLIENT)
    new_message.register_handlers(CLIENT)
    await CLIENT.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
