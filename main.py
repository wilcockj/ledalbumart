import image_slicer
from PIL import Image
import PIL
from os import listdir
from os import remove
from os.path import isfile, join
import numpy as np
import os
import sys
import json
import spotipy
import webbrowser
import spotipy.util as util
from json.decoder import JSONDecodeError
import configparser
import spotipy.oauth2 as oauth2
import requests
import time

numberofpixels = 100


def initspotipy():
    username = "2chainzbear"
    scope = "user-read-private user-read-playback-state user-modify-playback-state"
    config = configparser.ConfigParser()
    config.read("config.cfg")
    client_id = config.get("SPOTIFY", "CLIENT_ID")
    client_secret = config.get("SPOTIFY", "CLIENT_SECRET")
    redirect_uri = config.get("SPOTIFY", "REDIRECT_URI")
    token = util.prompt_for_user_token(
        username, scope, client_id, client_secret, redirect_uri
    )
    # Create Spotify object
    spotifyObject = spotipy.Spotify(auth=token)
    return spotifyObject


def getspotifyart(spotifyObject):
    track = spotifyObject.current_user_playing_track()
    # print(json.dumps(track, sort_keys=True, indent=4))
    print()
    artist = track["item"]["artists"][0]["name"]
    song = track["item"]["name"]
    albumarturl = track["item"]["album"]["images"][0]["url"]
    if artist != "":
        print("Currently playing " + artist + " - " + song)
    return albumarturl


def makeslices(filename):
    files = image_slicer.slice(filename, numberofpixels, save=False)
    image_slicer.save_tiles(files, directory="./slices", prefix="slice", format="png")
    return files


def getaverageslices(onlyfiles):
    width = height = int(numberofpixels ** 0.5)

    colorarray = np.zeros((height, width, 3), dtype=np.uint8)
    col = 0
    row = 0
    counter = 0
    for file in onlyfiles:
        counter += 1
        data = np.asarray(file.image)
        # print(data)
        avg_of_row = np.average(data, axis=0)
        avg_color = np.average(avg_of_row, axis=0)
        # print(avg_color)
        colorarray[row, col] = avg_color
        col += 1
        if col == 10:
            row += 1
            col = 0
    return colorarray


def savetemp(albumarturl):
    print(albumarturl)
    image = requests.get(albumarturl)
    with open("temp.jpg", "wb") as f:
        f.write(image.content)


def blownup(colorarray):
    blownarray = np.zeros((1000, 1000, 3), dtype=np.uint8)
    # row,col
    # if 0,0 we want from 0,0 to 100,100 to be that color
    # if 1,0 we from 100,0 to 200,100 to be that color
    for rowcount, row in enumerate(colorarray):
        for colcount, pixel in enumerate(row):
            for x in range(
                int(1000 / len(row) * rowcount),
                int(1000 / len(row) * rowcount + (1000 / len(row))),
            ):
                for y in range(
                    int(1000 / len(row) * colcount),
                    int(1000 / len(row) * colcount + (1000 / len(row))),
                ):
                    blownarray[x, y] = pixel
    enlarged = Image.fromarray(blownarray).save('englarged.png')
    # reverse slicing in order to make big version of low info
    # picture


# print(colorarray)
spotifyobject = initspotipy()

while True:
    albumarturl = getspotifyart(spotifyobject)
    # could download into directory
    savetemp(albumarturl)
    onlyfiles = makeslices("temp.jpg")
    colorarray = getaverageslices(onlyfiles)
    tenbyten = Image.fromarray(colorarray).save("10x10.png")
    img = Image.open("10x10.png")
    blownup(colorarray)
    time.sleep(5)
"""
for row in colorarray:
    for pixel in row:
        # could tell the led array here
        #print(pixel)
"""

# for led dont need to save array will be enough to make image

# deletes the files made of the slices
"""
onlyfiles = [f for f in listdir("slices") if isfile(join("slices", f))]
for x in onlyfiles:
    delfile = join("slices", x)
    # print(f"Deleted file {delfile}")
    remove(delfile)
"""
