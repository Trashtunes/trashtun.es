from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth, SpotifyPKCE
from spotipy.exceptions import SpotifyException
import spotipy
import os
import sys
import yaml


def manage_playlist():

    playlist_id = os.environ["PLAYLIST_ID"]
    refresh_token = os.environ["SPOTIFY_REFRESH_TOKEN"]

    scope = "playlist-modify-public"

    manager = SpotifyOAuth(scope=scope)
    manager.refresh_access_token(refresh_token)

    tracklist = []

    sp = spotipy.Spotify(auth_manager=manager)

    with open("./_data/trash.yml") as file:
        trash_list = yaml.load(file, Loader=yaml.FullLoader)

        for title in trash_list:
            try:
                uri = title["spotify_uri"]
                tracklist.append(uri)
                api_res = sp.track(uri)
                print(api_res["name"])
            except SpotifyException as error:
                print("Error with track: {}".format(title["songname"]))
                raise error

    results = sp.playlist_replace_items(playlist_id, tracklist)


manage_playlist()