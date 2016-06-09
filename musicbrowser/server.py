import pprint
from collections import OrderedDict
from datetime import datetime
import os

import logging
import logging.config
import subprocess

import tempfile
import json
import time

# from videotrim import settings

import socket
import random
from logging.handlers import RotatingFileHandler

SIMULATED_COVER_ART = True

index = {}

try:
    import asyncio
except ImportError:
    # Trollius >= 0.3 was renamed
    import trollius as asyncio

from autobahn.asyncio.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory

video_dir = r'C:\video\sample'

trim_dir = tempfile.TemporaryDirectory()

# TODO move logging config to a different file

ffmpeg_report_logger = logging.getLogger('ffmpeg-report')
ffmpeg_logger = logging.getLogger('ffmpeg')
ws_logger = logging.getLogger('websocket')
logger = logging.getLogger('videotrim')

default_port = 5743

new_tab_data = list()

aliased_artists = {}


class MyError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def order_websocket_dict(json_str):
    # make logs easier to read by always printing command or event entries first
    ddict = json.loads(json_str)
    ordered = OrderedDict()
    if 'command' in ddict:
        ordered['command'] = ddict['command']
    if 'event' in ddict:
        ordered['event'] = ddict['event']
    for item in ddict.items():
        ordered[item[0]] = item[1]
    return json.dumps(ordered)


def create_root_navigation():
    nav_html = ''
    for artist in sorted(index):
        nav_html += '<a href="#artist/{}">{} ({})</a><br>'.format(get_artist_alias(artist), artist,
                                                                               len(index[artist]))
    return nav_html


def create_plaintext_artist_navigation(al_artist):
    nav_html = ''
    # pprint.pprint(aliased_artists)
    artist = aliased_artists[int(al_artist)]
    for album_data in index[artist]:
        nav_html += '<a onclick="navToAlbum(\'{}\', \'{}\');">{}</a><br>'.format(al_artist, album_data['alias'],
                                                                                 album_data['title'])
    return nav_html


img_width = "300px"

def display_album_art(al_artist, al_album, track_index):
    artist = aliased_artists[int(al_artist)]
    album = get_album_object(al_artist, al_album)
    # pprint.pprint(index[artist])
    for track in album['tracks']:
        nav_html += '{}<br>'.format(track)

def create_visual_artist_navigation(al_artist):
    nav_html = ''
    # pprint.pprint(aliased_artists)
    artist = aliased_artists[int(al_artist)]
    open_div = False
    count = 0
    for album_data in sorted(index[artist], key=lambda x: x['year']):
        art = None
        for img in album_data['art']:
            if SIMULATED_COVER_ART:
                art = img
            else:
                filename = os.path.split(img)[1]
                if filename.lower().startswith('cover'):
                    art = img
        if art is None:
            art = ""
        if count % 6 == 0:
            if not open_div:
                nav_html += '<div class="row">\n'
                open_div = True
            else:
                nav_html += '</div>\n'
                nav_html += '<div class="row">\n'
                open_div = True
        elif count % 6 == 0 and count != 0:
            nav_html += '</div>\n'
            open_div = False
        count += 1
        # nav_html += '<div class="col-md-3" href="#artist/{}/album/{}">' \
        #             '   {}' \
        #             '   </div>\n'.format(al_artist,
        #                                  album_data['alias'],
        #                                  album_data['title'])
        nav_html += '<a href="#artist/{}/album/{}"><div class="col-md-2">' \
                    '   <img src="file:///{}" width="100%">{} ({})' \
                    '   </div></a>\n'.format(al_artist,
                                  album_data['alias'],
                                  art.replace('\\', '/'),
                                  album_data['title'],
                                             album_data['year'])
    if open_div:
        nav_html += '</div>\n'
    # print(nav_html)
    return nav_html


def create_album_navigation(al_artist, al_album):
    nav_html = ''
    artist = aliased_artists[int(al_artist)]
    album = get_album_object(al_artist, al_album)
    # pprint.pprint(index[artist])
    for track in album['tracks']:
        nav_html += '{}<br>'.format(track)
    return nav_html


def handle_navigation(payload):
    address = payload['address']
    split = address.split('/')
    if address == 'root' or address == '':
        return {'command': 'display_new_nav_content',
                'content': create_root_navigation()}
    elif split[0] == 'artist' and len(split) == 2:
        return {'command': 'display_new_nav_content',
                'content': create_visual_artist_navigation(split[1])}
    elif split[0] == 'artist' and split[2] == 'album' and len(split) == 4:
        return {'command': 'display_new_nav_content',
                'content': create_album_navigation(split[1], split[3])}


def get_random_track():
    def get():
        artist = random.choice(list(index.keys()))
        album = random.choice(index[artist])
        return random.choice(album['tracks'])

    while True:
        try:
            return get()
        except Exception:
            print('error random')
            pass


def web_filename(f):
    return 'file:///' + f.replace('\\', '/')


class MyServerProtocol(WebSocketServerProtocol):
    server_log = list()

    def onConnect(self, request):
        ws_logger.debug("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        ws_logger.debug("WebSocket connection open.")
        self.session = self

    def VtSendMessage(self, payload):
        dumped = json.dumps(payload)
        ws_logger.debug(">>>> " + order_websocket_dict(dumped))
        self.sendMessage(dumped.encode('utf-8'))

    def set_next_playing(self, track):
        self.factory.send_to_player({'command': 'set_next_file',
                                     'file_path': track})
        self.factory.send_to_controller({'command': 'set_next_up',
                                         'content': track})

    def force_play(self, track):
        self.factory.send_to_player({'command': 'initial_play',
                                     'file_path': track})
        self.factory.send_to_controller({'command': 'set_currently_playing',
                                         'content': track})
        self.log_track_play(track)

    def log_track_play(self, track):
        playlog.info(track)


    async def onMessage(self, payload, isBinary):
        if isBinary:
            ws_logger.error('received binary message')
            raise ValueError
        else:
            ws_logger.debug("<--- " + order_websocket_dict(payload.decode('utf8')))

        data = json.loads(payload.decode('utf8'))

        if 'event' in data.keys():
            event = data['event']
            if event == 'register_as_player':
                logger.info('registering player')
                self.factory.register_player(self)
            elif event == 'register_as_controller':
                logger.info('registering controller')
                self.factory.register_controller(self)
            elif event == 'play_pause':
                self.factory.send_to_player({'command': 'play_pause'})
            elif event == 'navigate':
                self.VtSendMessage(handle_navigation(data))
            elif event == 'need_new_tracks':
                self.force_play(web_filename(get_random_track()))
                self.set_next_playing(web_filename(get_random_track()))
            elif event == 'change_next_track':
                self.set_next_playing(web_filename(get_random_track()))
            elif event == 'skip':
                self.factory.send_to_player({'command': 'skip_to_next_file'})
                self.set_next_playing(web_filename(get_random_track()))
            elif event == 'did_skip_to_next_file':
                self.factory.send_to_controller({'command': 'set_currently_playing',
                                                 'content': data['track_skipped_to']})
                self.log_track_play(data['track_skipped_to'])
                self.set_next_playing(web_filename(get_random_track()))
            elif event == 'finished_playing_track':
                now_playing = data['new_track']
                self.factory.send_to_controller({'command': 'set_currently_playing',
                                                 'content': now_playing})
                self.set_next_playing(web_filename(get_random_track()))
                self.log_track_play(now_playing)
                # self.factory.send_to_player({'command': 'set_next_file',
                #                              'file_path': next_up})
                # self.factory.send_to_controller({'command': 'set_next_up',
                #                                  'content': next_up})

                # to_client = data
                # to_client['command'] = 'play'
                # to_client['file_path'] = 'file:///' + data['file_path']
                # logger.info('sending play data: ' + str(data))
                # self.factory.send_to_player(data)
            elif event == 'raise_exception':
                # test: start_server.bat should not close
                # https://docs.python.org/3.5/library/exceptions.html#exception-hierarchy
                raise NameError
            else:
                logger.error('undefined event in client WS message: ' + event)
        else:
            logger.error('client WS message did not contain "event" entry')

    def onClose(self, wasClean, code, reason):
        ws_logger.debug("WebSocket connection closed: {0}".format(reason))


class AudioFactory(WebSocketServerFactory):
    def __init__(self, *args, **kwargs):
        super(AudioFactory, self).__init__(*args, **kwargs)
        self.player = None
        self.controller = None

    def register_player(self, client):
        self.player = client

    def register_controller(self, client):
        self.controller = client

    def send_to_player(self, payload):
        if self.player is None:
            logger.error('no player registered')
            self.send_to_controller({'command': 'alert', 'content': 'no player found'})
        else:
            self.player.VtSendMessage(payload)

    def send_to_controller(self, payload):
        if self.player is None:
            logger.error('no controller registered')
        else:
            self.controller.VtSendMessage(payload)


def start():
    factory = AudioFactory(u'ws://127.0.0.1:' + str(default_port))
    factory.protocol = MyServerProtocol

    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    coro = loop.create_server(factory, '127.0.0.1', default_port)
    logger.info('starting server')
    server = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.close()


def get_artist_alias(artist):
    for alias in aliased_artists:
        if artist == aliased_artists[alias]:
            return alias
    raise ValueError('alias could not be resolved')


def get_album_object(al_artist, al_album):
    for album in index[aliased_artists[int(al_artist)]]:
        if int(al_album) == album['alias']:
            return album
    raise ValueError('alias could not be resolved')


def create_album_track_aliases():
    alias_count = 0
    for artist in index:
        for album in index[artist]:
            alias_count += 1
            album['alias'] = alias_count


if __name__ == '__main__':
    logFormatter = logging.Formatter("%(asctime)s %(name)-9s %(levelname)-5.5s %(message)s")

    # loggers
    ffmpeg_report_logger = logging.getLogger('ffmpeg-report')
    ffmpeg_report_logger.setLevel(logging.DEBUG)

    ffmpeg_logger = logging.getLogger('ffmpeg')
    ffmpeg_logger.setLevel(logging.DEBUG)

    ws_logger = logging.getLogger('websocket')
    ws_logger.setLevel(logging.DEBUG)

    logger = logging.getLogger('videotrim')
    logger.setLevel(logging.DEBUG)

    playlog = logging.getLogger('playlog')
    playlog.setLevel(logging.INFO)

    # handlers
    ten_megabytes = 10 ** 7

    playlogFileHandler = RotatingFileHandler('playlog.log', encoding='utf-8', maxBytes=ten_megabytes, backupCount=2)
    playlogFileHandler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    #
    # ffmpegFileHandler = RotatingFileHandler(os.path.join(log_dir(), 'ffmpeg.log'), encoding='utf-8', maxBytes=ten_megabytes, backupCount=2)
    # ffmpegFileHandler.setFormatter(logFormatter)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    consoleHandler.setLevel(logging.DEBUG)

    # add handlers to loggers
    # ffmpeg_report_logger.addHandler(ffmpegFileHandler)
    #
    # ffmpeg_logger.addHandler(ffmpegFileHandler)
    # ffmpeg_logger.addHandler(defaultFileHandler)
    ffmpeg_logger.addHandler(consoleHandler)

    # ws_logger.addHandler(defaultFileHandler)
    ws_logger.addHandler(consoleHandler)

    # logger.addHandler(defaultFileHandler)
    logger.addHandler(consoleHandler)

    playlog.addHandler(playlogFileHandler)

    if not os.path.isfile('index.json'):
        raise ValueError('index.json not found')
    with open('index.json', 'r', encoding='utf-8') as f:
        logger.info('loading index data...')
        index = json.load(f)
        logger.info('index data loaded successfully')

    alias_count = 0
    for artist in index:
        alias_count += 1
        aliased_artists[alias_count] = artist
    create_album_track_aliases()

    start()
