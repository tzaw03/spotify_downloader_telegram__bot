from telethon import Button
from spotify import SPOTIFY
import yt_dlp
import os
import eyed3
import requests
from song import Song  # Corrected import path

# Create folders if they don't exist
if not os.path.exists('covers'):
    os.makedirs('covers')
if not os.path.exists('songs'):
    os.makedirs('songs')

class Playlist:
    def __init__(self, link):
        self.spotify = SPOTIFY.playlist(link)
        self.id = self.spotify['id']
        self.spotify_link = self.spotify['external_urls']['spotify']
        self.playlist_name = self.spotify['name']
        self.description = self.spotify['description']
        self.owner_name = self.spotify['owner']['display_name']
        self.followers_count = self.spotify['followers']['total']
        self.track_count = len(self.spotify['tracks']['items'])
        self.playlist_image = self.spotify['images'][0]['url'] if self.spotify['images'] else None
        self.uri = self.spotify['uri']
        self.path = 'songs'

    async def playlist_template(self):
        message = f'''
▶️Playlist: {self.playlist_name}
📝Description: {self.description or "No description available"}
👤Owner: {self.owner_name}
🩷Followers: {self.followers_count}
🔢Total Track: {self.track_count}

[IMAGE]({self.playlist_image})
{self.uri}  
'''

        buttons = [
            [Button.inline(f'📩Download Playlist Tracks!', data=f"download_playlist_songs:{self.id}")],
            [Button.inline(f'🖼️Download Playlist Image!', data=f"download_playlist_image:{self.id}")],
            [Button.url(f'🎵Listen on Spotify', self.spotify_link)],
        ]
        return message, buttons

    @staticmethod
    def get_playlist_tracks(link):
        return SPOTIFY.playlist_tracks(link, limit=50)['items']

    def download_playlist_tracks(self):
        tracks = self.get_playlist_tracks(self.spotify_link)
        downloaded_files = []
        
        cookies_content = os.environ.get("YOUTUBE_COOKIES")
        if cookies_content:
            with open("cookies.txt", "w") as f:
                f.write(cookies_content)
            print("[DEBUG] cookies.txt generated successfully")

        ydl_opts = {
            'format': 'bestaudio/best',
            'keepvideo': True,
            'outtmpl': f'{self.path}/%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'geo_bypass': True,
            'cookiefile': 'cookies.txt' if cookies_content else None,
            'no_check_certificate': True,
            'ffmpeg_location': '/usr/bin/ffmpeg',  # Default path for ffmpeg
            'proxy': os.environ.get('YOUTUBE_PROXY', None),  # Optional proxy support
        }

        for item in tracks:
            track = item['track']
            track_id = track['id']
            song = Song(f"https://open.spotify.com/track/{track_id}")
            yt_link = song.yt_link()
            if not yt_link:
                print(f"[ERROR] No YouTube link found for {track['name']} by {track['artists'][0]['name']}")
                continue

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    print(f"[YOUTUBE] Downloading {track['name']} by {track['artists'][0]['name']}...")
                    ydl.download([yt_link])
                    print(f"[YOUTUBE] Download completed for {track['name']}")
                    file_path = f"{self.path}/{track_id}.mp3"
                    if os.path.exists(file_path):
                        self.update_metadata(file_path, track)
                        downloaded_files.append(file_path)
            except yt_dlp.utils.DownloadError as e:
                print(f"[WARNING] Failed to download {track['name']}: {str(e)}")
            except Exception as e:
                print(f"[ERROR] Unexpected error for {track['name']}: {str(e)}")

        return downloaded_files

    def update_metadata(self, file_path, track):
        mp3 = eyed3.load(file_path)
        if mp3 is None:
            print(f"[ERROR] Failed to load {file_path} for metadata")
            return
        mp3.tag.artist = track['artists'][0]['name']
        mp3.tag.title = track['name']
        mp3.tag.album = self.playlist_name
        mp3.tag.track_num = track['track_number'] if 'track_number' in track else 0

        # Download and set cover image
        response = requests.get(self.playlist_image)
        with open(f"covers/{self.id}.png", "wb") as image:
            image.write(response.content)
        with open(f"covers/{self.id}.png", 'rb') as cover_file:
            mp3.tag.images.set(3, cover_file.read(), 'image/png')

        mp3.tag.save()
        print(f"[SPOTIFY] Metadata updated for {track['name']}")
