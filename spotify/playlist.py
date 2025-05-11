from telethon import events
from telethon.tl import types

from consts import PROCESSING
from song import Song
from telegram import CLIENT

async def download_album_songs_callback_query(event: events.CallbackQuery.Event, song_id):
    # Process each track in the album or playlist
    await event.respond(PROCESSING)
    await Song.upload_on_telegram(event=event, song_id_or_link=song_id)

async def download_playlist_songs_callback_query(event: events.CallbackQuery.Event, playlist_id):
    # Process each track in the playlist
    await event.respond(PROCESSING)
    await Song.upload_on_telegram(event=event, song_id_or_link=f"https://open.spotify.com/playlist/{playlist_id}")

async def album_template_callback_query(event: events.CallbackQuery.Event, album_id):
    album = Song(f"https://open.spotify.com/album/{album_id}")
    message = f'''
💿 Album: `{album.album_name}`
🎤 Artist: `{album.artist_name}`
📅 Release Date: `{album.release_date}`

[IMAGE]({album.album_cover})
    '''
    buttons = [
        [types.Button.inline("📩 Download Album Songs", data=f"download_album_songs:{album_id}")]
    ]
    await event.respond(message, file=album.album_cover, buttons=buttons)

async def playlist_template_callback_query(event: events.CallbackQuery.Event, playlist_id):
    playlist = Song(f"https://open.spotify.com/playlist/{playlist_id}")
    message = f'''
📜 Playlist: `{playlist.album_name}`  # Update this to playlist name if available
🎤 Owner: `{playlist.artist_name}`  # Update this to playlist owner if available

[IMAGE]({playlist.album_cover})
    '''
    buttons = [
        [types.Button.inline("📩 Download Playlist Songs", data=f"download_playlist_songs:{playlist_id}")]
    ]
    await event.respond(message, file=playlist.album_cover, buttons=buttons)

def register_callbacks(client: CLIENT):
    @client.on(events.CallbackQuery(data=b"download_album_songs"))
    async def callback(event: events.CallbackQuery.Event):
        song_id = event.data.decode().split(":")[1]
        await download_album_songs_callback_query(event, song_id)

    @client.on(events.CallbackQuery(data=b"download_playlist_songs"))
    async def callback(event: events.CallbackQuery.Event):
        playlist_id = event.data.decode().split(":")[1]
        await download_playlist_songs_callback_query(event, playlist_id)

    @client.on(events.CallbackQuery(data=b"album"))
    async def callback(event: events.CallbackQuery.Event):
        album_id = event.data.decode().split(":")[1]
        await album_template_callback_query(event, album_id)

    @client.on(events.CallbackQuery(data=b"playlist"))
    async def callback(event: events.CallbackQuery.Event):
        playlist_id = event.data.decode().split(":")[1]
        await playlist_template_callback_query(event, playlist_id)
