import image_slicer
from PIL import Image
import PIL
from os import listdir
from os import remove
from os.path import isfile, join
import numpy as np
d = image_slicer.slice('album.jpg',100,save = False)
image_slicer.save_tiles(d, directory='./slices',prefix = 'slice',format = 'png')
onlyfiles = [f for f in listdir('slices') if isfile(join('slices', f))]
print(onlyfiles)

colorarray = np.zeros((10,10,3),dtype = np.uint8)
x = 0
y = 0
for file in onlyfiles:
    filepath = join('slices',file)
    image = Image.open(filepath)
    data = np.asarray(image)
    avg_of_row = np.average(data,axis = 0)
    avg_color = np.average(avg_of_row,axis = 0)
    #print(avg_color)
    colorarray[y,x] = avg_color
    x += 1
    if x == 10:
        y += 1
        x = 0
#print(colorarray)
Image.fromarray(colorarray).save('10x10.png')
#.rotate(-90).transpose(PIL.Image.FLIP_LEFT_RIGHT).save('10x10.png')
print(colorarray[0])
for x in onlyfiles:
    delfile = join('slices',x)
    print(f'Deleted file {delfile}')
    remove(delfile)

