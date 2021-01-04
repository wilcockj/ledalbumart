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
from loguru import logger
import colorsys

numberofpixels = 100
logger.add("log.log", rotation="1 week", level="INFO")

# image slicing code breaks when there are too many pixels?
# 64x64 ie 4096 pixels seemed to break
# 50*50 ie 2500 works
# 40*40 ie 1600 pixels seemed to break
# from this does not necessarily have to do with just number of pictures

# if can avoid saving the album art image would be ideal
# for this look at returning in save temp function


def initspotipy():
    scope = "user-read-private user-read-playback-state user-modify-playback-state"
    config = configparser.ConfigParser()
    config.read("config.cfg")
    username = config.get("SPOTIFY", "USERNAME")
    client_id = config.get("SPOTIFY", "CLIENT_ID")
    client_secret = config.get("SPOTIFY", "CLIENT_SECRET")
    redirect_uri = config.get("SPOTIFY", "REDIRECT_URI")
    os.environ["SPOTIPY_CLIENT_ID"] = client_id
    os.environ["SPOTIPY_CLIENT_SECRET"] = client_secret
    os.environ["SPOTIPY_REDIRECT_URI"] = redirect_uri
    token = util.prompt_for_user_token(
        username, scope, client_id, client_secret, redirect_uri
    )
    # Create Spotify object
    spotifyObject = spotipy.Spotify(auth=token)
    return spotifyObject


def getspotifyart(spotifyObject):
    track = spotifyObject.current_user_playing_track()
    playback = spotifyObject.current_playback()
    # print(json.dumps(track, sort_keys=True, indent=4))
    try:
        artist = track["item"]["artists"][0]["name"]
    except TypeError:
        logger.debug("Not currently listening to anything")
        return ""
    if not playback["is_playing"]:
        logger.debug("Not currently listening to anything")
        return ""
    song = track["item"]["name"]
    try:
        albumarturl = track["item"]["album"]["images"][0]["url"]
    except IndexError:
        logger.debug("Unable to get album art url")
        return ""
    if artist != "":
        logger.info("Currently playing " + artist + " - " + song)
    return albumarturl


def makeslices(filename):
    files = image_slicer.slice(filename, numberofpixels, save=False)
    # image_slicer.save_tiles(files, directory="./slices", prefix="slice", format="png")
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
        if col == height:
            row += 1
            col = 0
    return colorarray


def savetemp(albumarturl, lasturl):
    if albumarturl == lasturl:
        logger.debug("Same song skipping download")
        return
    logger.debug(f"Downloading image from {albumarturl}")
    image = requests.get(albumarturl)
    with open("temp.jpg", "wb") as f:
        f.write(image.content)
    logger.debug("Image download complete")


def blownup(colorarray):
    pictureside = 600
    blownarray = np.zeros((pictureside, pictureside, 3), dtype=np.uint8)
    # row,col
    # if 0,0 we want from 0,0 to 100,100 to be that color
    # if 1,0 we from 100,0 to 200,100 to be that color
    for rowcount, row in enumerate(colorarray):
        for colcount, pixel in enumerate(row):
            for x in range(
                int(pictureside / len(row) * rowcount),
                int(pictureside / len(row) * rowcount + (pictureside / len(row))),
            ):
                for y in range(
                    int(pictureside / len(row) * colcount),
                    int(pictureside / len(row) * colcount + (pictureside / len(row))),
                ):
                    blownarray[x, y] = pixel
    enlarged = Image.fromarray(blownarray).save("englarged.png")
    logger.info("Finished saving blownup image")
    # reverse slicing in order to make big version of low info
    # picture


def hsv2rgb(h, s, v):
    return tuple(round(i * 255) for i in colorsys.hsv_to_rgb(h, s, v))


def showpause():
    width = height = int(numberofpixels ** 0.5)
    colorarray = np.zeros((height, width, 3), dtype=np.uint8)
    col = 0
    row = 0
    counter = 0
    for rowcount, line in enumerate(colorarray):
        for colcount, pixel in enumerate(line):
            if (colcount % 10 == 3 or colcount % 10 == 6) and (
                rowcount > 1 and rowcount < 8
            ):
                # set color piece of rainbow in relation to
                # rowcount 2 = 0
                # rowcount 8 = 1
                # rowcount - 2 * 1/7?
                test_color = colorsys.hsv_to_rgb((rowcount - 2) * 1 / 7, 1, 1)
                fixedrgb = hsv2rgb((rowcount - 2) * 1 / 7, 1, 1)
                colorarray[rowcount, colcount] = fixedrgb

    # need to do hsv color in order to get rainbow
    # send paused image to led array
    # each row should have same color
    logger.debug("Returning Pause picture")
    return colorarray


# print(colorarray)
if __name__ == "__main__":
    spotifyobject = initspotipy()
    lasturl = ""
    while True:
        try:
            albumarturl = getspotifyart(spotifyobject)
            # for testing
            # raise spotipy.exceptions.SpotifyException(401, 401, "ouch!")
        except (spotipy.exceptions.SpotifyException, requests.exceptions.HTTPError):
            logger.warning("Refreshing token")
            spotifyobject = initspotipy()
            albumarturl = getspotifyart(spotifyobject)
        # could download into directory
        if albumarturl != "":
            savetemp(albumarturl, lasturl)
            onlyfiles = makeslices("temp.jpg")
            colorarray = getaverageslices(onlyfiles)
            if lasturl != albumarturl:
                blownup(colorarray)
            lasturl = albumarturl
        else:
            colorarray = showpause()
            blownup(colorarray)
        tenbyten = Image.fromarray(colorarray).save("10x10.png")
        img = Image.open("10x10.png")
        # optional / debug maybe add as commandline option
        # do check for last url here

        time.sleep(5)
        logger.debug("Looping in check album art loop")
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
