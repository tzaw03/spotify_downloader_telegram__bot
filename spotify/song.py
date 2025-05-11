import datetime
import os

import requests
from telethon.tl import types
from telethon.tl.types import PeerUser
from youtube_search import YoutubeSearch
import yt_dlp
import eyed3
from telethon import Button, events

from consts import DOWNLOADING, UPLOADING, PROCESSING, ALREADY_IN_DB, NOT_IN_DB, SONG_NOT_FOUND
from models import session, User, SongRequest
from spotify import SPOTIFY, GENIUS
from telegram import DB_CHANNEL_ID, CLIENT, BOT_ID

# covers နဲ့ songs ဆိုတဲ့ folder တွေ မရှိရင် ဖန်တီးမယ်
if not os.path.exists('covers'):
    os.makedirs('covers')
if not os.path.exists('songs'):
    os.makedirs('songs')

class Song:
    def __init__(self, link):
        self.spotify = SPOTIFY.track(link)
        self.id = self.spotify['id']
        self.spotify_link = self.spotify['external_urls']['spotify']
        self.track_name = self.spotify['name']
        self.artists_list = self.spotify['artists']
        self.artist_name = self.artists_list[0]['name']
        self.artists = self.spotify['artists']
        self.track_number = self.spotify['track_number']
        self.album = self.spotify['album']
        self.album_id = self.album['id']
        self.album_name = self.album['name']
        self.release_date = int(self.spotify['album']['release_date'][:4])
        self.duration = int(self.spotify['duration_ms'])
        self.duration_to_seconds = int(self.duration / 1000)
        self.album_cover = self.spotify['album']['images'][0]['url']
        self.path = 'songs'
        self.file = f'{self.path}/{self.id}.mp3'
        self.uri = self.spotify['uri']

    def features(self):
        if len(self.artists) > 1:
            features = "(Ft."
            for artistPlace in range(0, len(self.artists)):
                try:
                    if artistPlace < len(self.artists) - 2:
                        artistft = self.artists[artistPlace + 1]['name'] + ", "
                    else:
                        artistft = self.artists[artistPlace + 1]['name'] + ")"
                    features += artistft
                except:
                    pass
        else:
            features = ""
        return features

    def convert_time_duration(self):
        target_datetime_ms = self.duration
        base_datetime = datetime.datetime(1900, 1, 1)
        delta = datetime.timedelta(0, 0, 0, target_datetime_ms)
        return base_datetime + delta

    def download_song_cover(self):
        response = requests.get(self.album_cover)
        image_file_name = f'covers/{self.id}.png'
        with open(image_file_name, "wb") as image:
            image.write(response.content)
        return image_file_name

    def yt_link(self):
        results = list(YoutubeSearch(str(self.track_name + " " + self.artist_name)).to_dict())
        time_duration = self.convert_time_duration()
        yt_url = None

        for yt in results:
            yt_time = yt["duration"]
            try:
                # H:MM:SS ပုံစံလား MM:SS ပုံစံလား စစ်မယ်
                if yt_time.count(":") == 2:  # H:MM:SS ပုံစံဆိုရင်
                    yt_time = datetime.datetime.strptime(yt_time, '%H:%M:%S')
                else:  # MM:SS ပုံစံဆိုရင်
                    yt_time = datetime.datetime.strptime(yt_time, '%M:%S')
                difference = abs((yt_time - time_duration).total_seconds())
                if difference <= 3:
                    yt_url = yt['url_suffix']
                    break
            except ValueError as e:
                print(f"[ERROR] Failed to parse duration {yt_time}: {str(e)}")
                continue

        if yt_url is None:
            return None

        yt_link = str("https://www.youtube.com/" + yt_url)
        return yt_link

    def yt_download(self, yt_link=None):
        # YOUTUBE_COOKIES ကနေ cookies.txt ဖိုင်ကို runtime မှာ ဖန်တီးမယ်
        cookies_content = os.environ.get("YOUTUBE_COOKIES")
        if cookies_content:
            with open("cookies.txt", "w") as f:
                f.write(cookies_content)
            print("[DEBUG] cookies.txt generated successfully")

        ydl_opts = {
            'format': 'bestaudio/best',  # အကောင်းဆုံး audio ကို အရင်စမ်းမယ်
            'keepvideo': True,
            'outtmpl': f'{self.path}/{self.id}',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'geo_bypass': True,
            'cookiefile': 'cookies.txt' if cookies_content else None,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as mp3:
                print(f"[YOUTUBE] Downloading {self.track_name} by {self.artist_name}...")
                mp3.download([yt_link or self.yt_link()])
                print(f"[YOUTUBE] Download completed for {self.track_name}")
        except yt_dlp.utils.DownloadError as e:
            print(f"[WARNING] Best audio format not available: {str(e)}")
            # အကယ်၍ မရရင် အခြား format နဲ့ ထပ်စမ်းမယ်
            ydl_opts['format'] = 'bestaudio/best'
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as mp3:
                    print(f"[YOUTUBE] Retrying download with fallback format for {self.track_name}...")
                    mp3.download([yt_link or self.yt_link()])
                    print(f"[YOUTUBE] Fallback download completed for {self.track_name}")
            except Exception as e2:
                print(f"[ERROR] Failed to download {self.track_name}: {str(e2)}")
                return None
        except Exception as e:
            print(f"[ERROR] Failed to download {self.track_name}: {str(e)}")
            return None

    def lyrics(self):
        try:
            return GENIUS.search_song(self.track_name, self.artist_name).lyrics
        except:
            return None

    def song_meta_data(self):
        mp3 = eyed3.load(self.file)
        if mp3 is None:
            print(f"[ERROR] Failed to load {self.file} for metadata")
            return
        mp3.tag.artist = self.artist_name
        mp3.tag.album = self.album_name
        mp3.tag.album_artist = self.artist_name
        mp3.tag.title = self.track_name + self.features()
        mp3.tag.track_num = self.track_number
        mp3.tag.year = self.release_date  # ဒီမှာ track_number အစား release_date ကို သုံးလိုက်တယ်

        lyrics = self.lyrics()
        if lyrics is not None:
            mp3.tag.lyrics.set(lyrics)

        cover_path = self.download_song_cover()
        with open(cover_path, 'rb') as cover_file:
            mp3.tag.images.set(3, cover_file.read(), 'image/png')
        mp3.tag.save()
        print(f"[SPOTIFY] Metadata updated for {self.track_name}")

    def download(self, yt_link=None):
        if os.path.exists(self.file):
            print(f'[SPOTIFY] Song Already Downloaded: {self.track_name} by {self.artist_name}')
            return self.file
        print(f'[YOUTUBE] Downloading {self.track_name} by {self.artist_name}...')
        if self.yt_download(yt_link=yt_link) is None:
            return None
        print(f'[SPOTIFY] Updating Metadata: {self.track_name} by {self.artist_name}')
        self.song_meta_data()
        print(f'[SPOTIFY] Song Downloaded: {self.track_name} by {self.artist_name}')
        return self.file

    async def song_telethon_template(self):
        message = f'''
🎧 Title : `{self.track_name}`
🎤 Artist : `{self.artist_name}{self.features()}`
💿 Album : `{self.album_name}`
📅 Release Date : `{self.release_date}`

[IMAGE]({self.album_cover})
{self.uri}   
        '''

        buttons = [
            [Button.inline(f'📩Download Track!', data=f"download_song:{self.id}")],
            [Button.inline(f'🖼️Download Track Image!', data=f"download_song_image:{self.id}")],
            [Button.inline(f'👀View Track Album!', data=f"album:{self.album_id}")],
            [Button.inline(f'🧑‍🎨View Track Artists!', data=f"track_artist:{self.id}")],
            [Button.inline(f'📃View Track Lyrics!', data=f"track_lyrics:{self.id}")],
            [Button.url(f'🎵Listen on Spotify', self.spotify_link)],
        ]

        return message, self.album_cover, buttons

    async def artist_buttons_telethon_templates(self):
        message = f"{self.track_name} track Artist's"
        buttons = [[Button.inline(artist['name'], data=f"artist:{artist['id']}")]
                   for artist in self.artists_list]
        return message, buttons

    def save_db(self, user_id: int, song_id_in_group: int):
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            user = User(telegram_id=user_id)
            session.add(user)
            session.commit()
        session.add(SongRequest(
            spotify_id=self.id,
            user_id=user.id,
            song_id_in_group=song_id_in_group,
            group_id=DB_CHANNEL_ID
        ))
        session.commit()

    @staticmethod
    async def progress_callback(processing, sent_bytes, total):
        percentage = sent_bytes / total * 100
        await processing.edit(f"Uploading: {percentage:.2f}%")

    @staticmethod
    async def upload_on_telegram(event: events.CallbackQuery.Event, song_id):
        processing = await event.respond(PROCESSING)

        # သီချင်းက database ထဲမှာ ရှိမရှိ အရင်စစ်မယ်
        song_db = session.query(SongRequest).filter_by(spotify_id=song_id).first()
        if song_db:
            db_message = await processing.edit(ALREADY_IN_DB)
            message_id = song_db.song_id_in_group
        else:
            # မရှိရင် database ထဲမှာ အသစ်ထည့်မယ်
            song = Song(song_id)
            db_message = await event.respond(NOT_IN_DB)
            await processing.edit(DOWNLOADING)
            yt_link = song.yt_link()
            if yt_link is None:
                print(f'[YOUTUBE] Song not found: {song.uri}')
                await processing.delete()
                await event.respond(f"{song.track_name}\n{SONG_NOT_FOUND}")
                return
            file_path = song.download(yt_link=yt_link)
            if file_path is None:
                await processing.delete()
                await event.respond(f"Failed to download {song.track_name} due to YouTube restrictions")
                return
            await processing.edit(UPLOADING)

            upload_file = await CLIENT.upload_file(file_path)
            new_message = await CLIENT.send_file(
                DB_CHANNEL_ID,
                caption=BOT_ID,
                file=upload_file,
                supports_streaming=True,
                attributes=(
                    types.DocumentAttributeAudio(title=song.track_name, duration=song.duration_to_seconds,
                                                performer=song.artist_name),
                ),
            )
            await processing.delete()
            song.save_db(event.sender_id, new_message.id)
            message_id = new_message.id

        # မက်ဆေ့ချ်ကို forward လုပ်မယ်
        await CLIENT.forward_messages(
            entity=event.chat_id,
            messages=message_id,
            from_peer=PeerUser(int(DB_CHANNEL_ID))
        )
        await db_message.delete()
