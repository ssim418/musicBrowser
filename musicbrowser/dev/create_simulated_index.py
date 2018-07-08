import json
import os
import pprint
import random

real_root = r'G:\what freeleech'

art = list()
tracks = list()

for root, dirs, files in os.walk(real_root, topdown=False):
    for name in files:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            lwr = name.lower()
            if lwr.endswith('.mp3'):
                tracks.append(path)
            elif lwr.endswith('folder.jpg') or lwr.endswith('cover.jpg') :
                art.append(path)

print(art)
print(len(art))

with open(r'G:\index.json', 'r', encoding='utf-8') as f:
    index = json.load(f)

for artist in index:
    print('processing ' + artist)
    for album in index[artist]:
        album['tracks'] = random.sample(tracks, len(album['tracks']))
        album['art'] = random.sample(art, len(album['art']))

for artist in index:
    for album in index[artist]:
        pprint.pprint(album, width=300)

with open('index.json', 'w', encoding='utf-8') as f:
    json.dump(index, f)

