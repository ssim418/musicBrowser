import sys
import os
import time
import shutil
import subprocess

# chcp 65001
# python C:\Users\Shbl\PycharmProjects\musicBrowser3\musicbrowser\flac_convert.py %1
# pause

src_dir = sys.argv[1]
dest_dir = os.path.join('D:\\', str('flac_' + str(int(time.time()))), os.path.basename(src_dir))

if not os.path.isdir(src_dir):
    raise AssertionError('argument must be a folder: ' + src_dir)

os.makedirs(dest_dir)
print('saving converted files to :' + dest_dir)

convert = lambda src, dst: subprocess.call([r'C:\ffmpeg\bin\ffmpeg.exe', '-hide_banner', '-loglevel', 'error', '-i', src, dst])

for root, dirs, files in os.walk(src_dir):
    for name in files:
        src = os.path.join(root, name)
        dst = src.replace(src_dir, dest_dir)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if dst.lower().endswith('.flac'):
            dst = dst[:-4] + 'mp3'
            convert(src, dst)
            # if not os.path.isfile(src):
            #     tmp_src = os.path.join('%Temp%', str(time.time()) + '.flac')
            #     tmp_dst = tmp_src.replace('.flac', '.mp3')
            #     shutil.copy(src, tmp_src)
            #     convert(tmp_src, tmp_dst)
            #     shutil.copy(tmp_dst, dst)
            #     os.remove(tmp_src)
            #     os.remove(tmp_dst)
            if os.path.getsize(dst) < (10*1000):
                raise AssertionError('conversion failed: ' + dst)
        else:
            shutil.copy(src, dst)
        print('created ' + dst)

print('conversion complete')