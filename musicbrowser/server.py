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
        nav_html += '<a onclick="navToArtist(\'{}\');">{} ({})</a><br>'.format(artist, artist, len(index[artist]))
    return nav_html


def create_artist_navigation(artist):
    nav_html = ''
    # pprint.pprint(index[artist])
    for album_data in index[artist]:
        nav_html += '<a onclick="navToAlbum(\'{}\', \'{}\');">{}</a><br>'.format(artist, album_data['title'], album_data['title'])
    return nav_html


def create_album_navigation(artist, album):
    nav_html = ''
    # pprint.pprint(index[artist])
    for album_data in index[artist]:
        if album_data['title'] == album:
            for track in album_data['tracks']:
                nav_html += '{}<br>'.format(track)
    return nav_html


def handle_navigation(payload):
    address = payload['address']
    if address == 'root':
        return {'command': 'display_new_nav_content',
                'content': create_root_navigation()}
    elif address == 'artist':
        return {'command': 'display_new_nav_content',
                'content': create_artist_navigation(payload['params'][0])}
    elif address == 'album':
        return {'command': 'display_new_nav_content',
                'content': create_album_navigation(payload['params'][0], payload['params'][1])}



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

    # handlers
    ten_megabytes = 10**7

    # defaultFileHandler = RotatingFileHandler(os.path.join(log_dir(), 'log.log'), encoding='utf-8', maxBytes=ten_megabytes, backupCount=2)
    # defaultFileHandler.setFormatter(logFormatter)
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

    if not os.path.isfile('index.json'):
        raise ValueError('index.json not found')
    with open('index.json', 'r', encoding='utf-8') as f:
        logger.info('loading index data...')
        index = json.load(f)
        logger.info('index data loaded successfully')

    start()
