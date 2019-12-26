import os
import random
import mutagen
import datetime

dir = input("Enter path (e.g. D:\picard: ")
print('listing directory: ' + dir)

result = list()

for root, dirs, files in os.walk(dir):
    for name in files:
        lowername = name.lower()
        full_path = os.path.join(root, name)
        filename, extension = os.path.splitext(name)
        extension = extension.replace('.', '').lower()
        length = None
        length_pretty = ''
        if extension.endswith('mp3') or extension.endswith('flac'):
            try:
                length = mutagen.File(full_path).info.length
            except:
                pass
            if length is not None:
                try:
                    length_pretty = str(datetime.timedelta(seconds=length)).split('.')[0]
                    split = length_pretty.split(':')
                    if len(split) == 3:
                        if int(split[0]) == 0:
                            if split[1].startswith('0'):
                                split[1] = split[1][1:]
                                pass
                            length_pretty = ':'.join(split[1:])
                except:
                    pass
        if length is not None:
            result.append('"{}";"{}";"{}";"{}";"{}"'.format(root, filename, extension, length_pretty, int(length)))
        else:
            result.append('"{}";"{}";"{}"'.format(root, filename, extension))
        print(result[-1])

output = os.path.join('directory_list_' + str(random.randint(1, 100000)) + '.csv')
print('found ' + str(len(result)) + ' files')
print('saving result in: ' + os.path.abspath(output))

with open(output, 'w', encoding='utf-16') as f:
    f.write('"sep=;"\n')
    f.write('\n'.join(result))
