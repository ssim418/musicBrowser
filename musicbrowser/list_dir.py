import os
import random

dir = input("Enter path (e.g. D:\picard: ")
print('listing directory: ' + dir)

result = list()

for root, dirs, files in os.walk(dir):
    for name in files:
        full_path = os.path.join(root, name)
        result.append('"' + full_path + '";"' + name + '"')

output = os.path.join('directory_list_' + str(random.randint(1, 100000)) + '.csv')
print('found ' + str(len(result)) + ' files')
print('saving result in: ' + os.path.abspath(output))

with open(output, 'w', encoding='utf-16') as f:
    f.write('"sep=;"\n')
    f.write('\n'.join(result))
