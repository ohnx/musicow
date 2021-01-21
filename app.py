import discord
import configparser
import sys
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re

cfg = {}

"""
Discord API stuff
"""
SPOT_PATTERN = 'https?:\\/\\/open.spotify.com\\/track\\/([A-Za-z0-9]+)(\\?si=[A-Za-z0-9]+)?'
class MusicowDiscordClient(discord.Client):
    def __init__(self, spothandle):
        super().__init__()
        self.spothandle = spothandle
    
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.guild.id == cfg['discord']['guild'] and message.channel.id == cfg['discord']['channel']:
            # got a message that we were expecting! now check if there's a spotify link
            if 'open.spotify.com/track/' in message.content:
                res = re.search(SPOT_PATTERN, message.content)
                print('Adding song ID {0} from {1.author.name}\'s message in #{1.channel.name}'.format(res.group(1), message))
                self.spothandle.add_spotify_song(res.group(1))

"""
Spotify API stuff
"""
PERMS_SCOPE = 'playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative'
# TODO: customizable
PLAYLIST_NAME = 'Discord Import'
DEFAULT_PUBLIC = False

class MusicowSpotifyClient():
    def __init__(self, client_id, client_secret, redirect_uri):
        spot_auth = SpotifyOAuth(client_id=client_id,
                                    client_secret=client_secret,
                                    redirect_uri=redirect_uri,
                                    scope=PERMS_SCOPE,
                                    open_browser=False)
        spotify = spotipy.Spotify(auth_manager=spot_auth)
        playlist_mgr = spotify.me()
        self.user_id = playlist_mgr['uri'].replace('spotify:user:', '')
        print('Managing playlists for user {} ({})'.format(self.user_id, playlist_mgr['display_name']))
        self.client = spotify
        self.known_playlist_ids = {}

    def create_playlist(self, name):
        playlist = self.client.user_playlist_create(self.user_id, name, DEFAULT_PUBLIC)
        return playlist['id']

    def find_playlist_id_by_name(self, name):
        # scan through all playlists looking for a playlist named a given name
        # returns None if no such playlist found
        playlists = {
            'limit': 50,
            'next': True,
            'offset': -50
        }
        idx_found = None
        while playlists['next'] is not None:
            playlists = self.client.user_playlists(self.user_id,
                                                    limit=playlists['limit'],
                                                    offset=playlists['limit'] + playlists['offset'])
            for playlist in playlists['items']:
                if playlist['name'] == name:
                    # found the playlist!
                    idx_found = playlist['id']
                    playlists['next'] = None
                    break

        return idx_found 

    def add_spotify_song(self, songid):
        playlist_id = None
        playlist_name = PLAYLIST_NAME

        if playlist_name in self.known_playlist_ids:
            # cache the playlist names so we don't always hit the spotify api
            playlist_id = self.known_playlist_ids[playlist_name]
        else:
            # need to API request (or even maybe make a new playlist)
            playlist_id = self.find_playlist_id_by_name(playlist_name)
        if playlist_id is None:
            playlist_id = self.create_playlist(playlist_name)

        self.client.user_playlist_add_tracks(self.user_id, playlist_id, [songid])
        print('Added song {} to playlist {}'.format(songid, playlist_id))

"""
Config parsing stuff
"""
if __name__ == '__main__':
    # load configuration values
    config = configparser.ConfigParser()
    config.read('config.ini')

    if 'spotify' in config:
        cfg['spotify'] = {}
        if 'client_id' in config['spotify']:
            cfg['spotify']['client_id'] = config['spotify']['client_id']
        else:
            sys.exit('Config missing spotify client_id')
        if 'client_secret' in config['spotify']:
            cfg['spotify']['client_secret'] = config['spotify']['client_secret']
        else:
            sys.exit('Config missing spotify client_secret')
        if 'redirect_uri' in config['spotify']:
            cfg['spotify']['redirect_uri'] = config['spotify']['redirect_uri']
        else:
            sys.exit('Config missing spotify redirect_uri')
    else:
        exit('Config missing spotify section')

    if 'discord' in config:
        cfg['discord'] = {}
        if 'bot_token' in config['discord']:
            cfg['discord']['bot_token'] = config['discord']['bot_token']
        else:
            sys.exit('Config missing discord bot_token')
        if 'guild' in config['discord']:
            cfg['discord']['guild'] = int(config['discord']['guild'])
        else:
            sys.exit('Config missing discord guild')
        if 'channel' in config['discord']:
            cfg['discord']['channel'] = int(config['discord']['channel'])
        else:
            sys.exit('Config missing discord channel')
    else:
        exit('Config missing discord section')

    # initialize tekore
    spothandle = MusicowSpotifyClient(cfg['spotify']['client_id'],
                                        cfg['spotify']['client_secret'],
                                        cfg['spotify']['redirect_uri'])

    # initialize discord bot
    client = MusicowDiscordClient(spothandle)
    # run discord bot
    client.run(cfg['discord']['bot_token'])
