
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth, SpotifyPKCE
import spotipy
import os
import yaml

tracklist = []

playlist_id = os.environ['PLAYLIST_ID']
refresh_token = os.environ['SPOTIFY_REFRESH_TOKEN']


scope = 'playlist-modify-public'

manager = SpotifyOAuth(scope=scope)
manager.refresh_access_token(refresh_token)

sp = spotipy.Spotify(auth_manager=manager)

with open('./_data/trash.yml') as file:
    trash_list = yaml.load(file, Loader=yaml.FullLoader)

    for item in trash_list:
        tracklist.append(item["spotify_uri"])


results = sp.playlist_replace_items(playlist_id, tracklist)

