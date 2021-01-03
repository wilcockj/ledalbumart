import image_slicer
from PIL import Image
import PIL
from os import listdir
from os import remove
from os.path import isfile, join
import numpy as np

numberofpixels = 100


def makeslices(filename):
    d = image_slicer.slice(filename, numberofpixels, save=False)
    image_slicer.save_tiles(d, directory="./slices", prefix="slice", format="png")
    onlyfiles = [f for f in listdir("slices") if isfile(join("slices", f))]
    return onlyfiles


def getaverageslices(onlyfiles):
    width = height = int(numberofpixels ** 0.5)

    colorarray = np.zeros((height, width, 3), dtype=np.uint8)
    col = 0
    row = 0
    for file in onlyfiles:
        filepath = join("slices", file)
        image = Image.open(filepath)
        data = np.asarray(image)
        avg_of_row = np.average(data, axis=0)
        avg_color = np.average(avg_of_row, axis=0)
        # print(avg_color)
        colorarray[row, col] = avg_color
        col += 1
        if col == 10:
            row += 1
            col = 0
    return colorarray


# print(colorarray)
onlyfiles = makeslices("cudi.jpg")
colorarray = getaverageslices(onlyfiles)
for row in colorarray:
    for pixel in row:
        # could tell the led array here
        print(pixel)

# for led dont need to save array will be enough to make image
Image.fromarray(colorarray).save("10x10.png")
# .rotate(-90).transpose(PIL.Image.FLIP_LEFT_RIGHT).save('10x10.png')
# print(colorarray[0])
# deletes the files made of the slices
for x in onlyfiles:
    delfile = join("slices", x)
    # print(f"Deleted file {delfile}")
    remove(delfile)
