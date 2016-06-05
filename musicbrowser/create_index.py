import os
import json

picard_dir = r'E:\picard-mp3_only'


def parse_album(album_folder_name):
    year = int(album_folder_name[:4])
    title = album_folder_name[5:].strip()
    if len(title) > 0:
        return {'year': year, 'title': title}
    raise ValueError


def parse_album_files(album_folder):
    tracks = []
    art = []
    for file in os.listdir(album_folder):
        path = os.path.join(album_folder, file)
        lower_name = file.lower()
        if os.path.isfile(path):
            if lower_name.endswith('.mp3'):
                tracks.append(path)
            elif lower_name.endswith('.jpg') or lower_name.endswith('.jpeg') or lower_name.endswith('.png'):
                art.append(path)
    return {'tracks': tracks, 'art': art}


def create():
    ignored = 0
    total_albums = 0
    index = {}
    for artist in os.listdir(picard_dir):
        print('processing ' + artist)
        artist_path = os.path.join(picard_dir, artist)
        if os.path.isdir(artist_path):
            albums = []
            for album in os.listdir(artist_path):
                album_path = os.path.join(artist_path, album)
                if os.path.isdir(album_path):
                    total_albums += 1
                    try:
                        album_data = parse_album(album)
                        album_data.update(parse_album_files(album_path))
                        albums.append(album_data)
                    except ValueError:
                        ignored += 1
                        print('ignoring ' + album_path)
            if len(albums) > 0:
                index[artist] = albums
    with open('index.json', 'w', encoding='utf-8') as f:
        json.dump(index, f)
        print('saved index to %s' % os.path.abspath('index.json'))

    print('ignored {} of {} albums ({:.2%})'.format(ignored, total_albums, ignored/total_albums))
    # for root, dirs, files in os.walk(picard_dir, topdown=False):
    #     for name in files:
    #         file = os.path.join(root, name)
    #         print(file)

if __name__ == '__main__':
    create()