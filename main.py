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
import math
import platform

# platform.machine = armv7l
if platform.machine == "armv7l":
    import board
    import neopixel

    onraspi = True
else:
    onraspi = False
if onraspi:
    pixels = neopixel.NeoPixel(board.D18, 100)
numberofpixels = 100
sys.stdout.reconfigure(encoding="utf-8")
logger.add("log.log", rotation="1 week", level="INFO", encoding="utf-8")

# when paused but playing a known song overlay pause symbol on top


# image slicing code breaks when there are too many pixels?
# 64x64 ie 4096 pixels seemed to break
# 50*50 ie 2500 works
# 40*40 ie 1600 pixels seemed to break
# from this does not necessarily have to do with just number of pictures

# if can avoid saving the album art image would be ideal
# for this look at returning in save temp function

# TODO
# Make progress bar opposite color of average color of album art in order to contrast


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


def round_down(n, decimals):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier


def getspotifyart(spotifyObject):
    track = spotifyObject.current_user_playing_track()
    playback = spotifyObject.current_playback()
    if track:
        tracktype = track["currently_playing_type"]
    else:
        tracktype = "unknown"
    if tracktype == "episode":
        # case if podcast
        return "", 0
    progress = 0
    #'progress_ms' for how far in song
    # print(json.dumps(track, sort_keys=True, indent=4))
    try:
        if not track["item"]:
            return "", progress
        artist = track["item"]["artists"][0]["name"]
        trackduration = spotifyObject.audio_features(playback["item"]["id"])[0][
            "duration_ms"
        ]
        trackprog = playback["progress_ms"]
        if trackprog != 0:
            progress = round_down(1 / (trackduration / trackprog), 2)
        else:
            progress = 0
        logger.debug(f"{trackprog}, {trackduration}")
        logger.debug(f"Current progress is {progress}")

    except TypeError:
        if track:
            progress = round_down(
                1 / (track["item"]["duration_ms"] / track["progress_ms"]), 2
            )
            if track["is_playing"]:
                return "playingofflinetrack", progress
            else:
                return "offlinetrack", progress
        return "", progress
    if not playback["is_playing"]:
        logger.debug("Not playing anything on spotify")
        # if returned pause should just put pause symbol over image
        return "paused", progress
    song = track["item"]["name"]
    try:
        albumarturl = track["item"]["album"]["images"][0]["url"]
    except IndexError:
        if track:
            if track["is_playing"]:
                progress = round_down(
                    1 / (track["item"]["duration_ms"] / track["progress_ms"]), 2
                )
                logger.debug("Banned album art on Spotify")
                return "playingofflinetrack", progress
        logger.debug("Unable to get album art url")
        return "", progress
    if artist != "":
        logger.info("Currently playing " + artist + " - " + song)
    return albumarturl, progress


def makeslices(filename):
    files = image_slicer.slice(filename, numberofpixels, save=False)
    # image_slicer.save_tiles(files, directory="./slices", prefix="slice", format="png")
    return files


def getaverageslices(onlyfiles, progress):
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
    coloraverage = np.mean(np.mean(colorarray, axis=0), axis=0)
    coloraverage = [int(x) for x in coloraverage]
    for x in range(int(width * progress)):
        # here should be instead opposite color of average of whole image
        colorarray[width - 1, x] = complementarycolor(coloraverage)
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
    if onraspi:
        logger.debug("Not saving blownupimage")
        return
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


def complementarycolor(rgbcolor):
    r = rgbcolor[0]
    g = rgbcolor[1]
    b = rgbcolor[2]
    if -10 <= r - g <= 10 and -10 <= r - b <= 10 and -10 <= g - b <= 10:
        compcolor = [3, 234, 252]
    else:
        compcolor = [255 - x for x in rgbcolor]

    return compcolor


def showpause(progress):
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
                # rowcount - 2 * 1/7
                fixedrgb = hsv2rgb((rowcount - 2) * 1 / 7, 1, 1)
                colorarray[rowcount, colcount] = fixedrgb
    if progress > 1 / width:
        for x in range(int(width * progress)):
            colorarray[width - 1, x] = [255, 255, 255]

    # need to do hsv color in order to get rainbow
    # send paused image to led array
    # each row should have same color
    logger.debug("Returning Pause picture")
    return colorarray


def showquestionmark(progress):
    width = height = int(numberofpixels ** 0.5)
    if width != 10:
        return showpause(progress)
    else:
        colorarray = np.zeros((height, width, 3), dtype=np.uint8)
        # make list of points to color for a question mark
        questionmark = [
            [1, 4],
            [1, 5],
            [1, 6],
            [1, 7],
            [2, 7],
            [3, 7],
            [4, 4],
            [4, 5],
            [4, 6],
            [4, 7],
            [5, 4],
            [6, 4],
            [8, 4],
        ]
        for x in questionmark:
            colorarray[x[0], x[1] - 1] = [127, 34, 214]
    if progress > 1 / width:
        for x in range(int(width * progress)):
            colorarray[width - 1, x] = [255, 255, 255]
    logger.debug("returning questionmark")
    return colorarray


def setleds(colorarray, progress):
    counter = 0
    width = 10
    playbackpixels = int(progress * width)
    playbackpixels = list(range(playbackpixels))
    playbackpixels = [x + 90 for x in playbackpixels]
    print(playbackpixels)
    for row in colorarray:
        for pixel in row:
            # need to mirror image
            # get the tens
            tens = counter // 10 * 10
            # reverses row ie 99 would become 90
            mirroredcounter = 9 - counter + 2 * tens
            brightnessdivisor = 10
            if counter not in playbackpixels:
                pixels[mirroredcounter] = (
                    pixel[0] / brightnessdivisor,
                    pixel[1] / brightnessdivisor,
                    pixel[2] / brightnessdivisor,
                )
            else:
                pixels[mirroredcounter] = (pixel[0] / 4, pixel[1] / 4, pixel[2] / 4)
            counter += 1

    logger.debug("finished setting pixels")


def overlaypause(colorarray, progress):
    width = height = int(numberofpixels ** 0.5)
    print(width)
    for rowcount, line in enumerate(colorarray):
        for colcount, pixel in enumerate(line):
            if (colcount % 10 == 3 or colcount % 10 == 6) and (
                rowcount > 1 and rowcount < 8
            ):
                # set color piece of rainbow in relation to
                # rowcount 2 = 0
                # rowcount 8 = 1
                # rowcount - 2 * 1/7
                fixedrgb = hsv2rgb((rowcount - 2) * 1 / 7, 1, 1)
                colorarray[rowcount, colcount] = fixedrgb
    if progress > 1 / width:
        for x in range(int(width * progress)):
            colorarray[width - 1, x] = [255, 255, 255]
    logger.debug("overlaying pause onto album art")
    return colorarray


# print(colorarray)
if __name__ == "__main__":
    spotifyobject = initspotipy()
    lasturl = "start"
    colorarray = []
    lastprogress = 99
    while True:
        start_time = time.time()
        try:
            try:
                albumarturl, progress = getspotifyart(spotifyobject)
            except (
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError,
            ):
                logger.debug("No internet connection")
                continue
            # for testing
            # raise spotipy.exceptions.SpotifyException(401, 401, "ouch!")
        except (spotipy.exceptions.SpotifyException, requests.exceptions.HTTPError):
            # catches exception when spotify token needs to be refreshed
            logger.warning("Refreshing token")
            spotifyobject = initspotipy()
            albumarturl, progress = getspotifyart(spotifyobject)
        # could download into directory
        if albumarturl == "offlinetrack" or albumarturl == "playingofflinetrack":
            if lastprogress != progress:
                if albumarturl == "playingofflinetrack":
                    colorarray = showquestionmark(progress)
                else:
                    colorarray = showpause(progress)
                blownup(colorarray)
            # make special case for unknown track maybe question mark
        elif albumarturl == "paused":
            # overlay pause symbol on picture
            if len(colorarray) > 0:
                colorarray = overlaypause(colorarray, progress)
            else:
                colorarray = showpause(progress)
        elif albumarturl != "":
            if lastprogress != progress or lasturl != albumarturl:
                savetemp(albumarturl, lasturl)
                onlyfiles = makeslices("temp.jpg")
                colorarray = getaverageslices(onlyfiles, progress)
                blownup(colorarray)
        else:
            if lasturl != albumarturl:
                colorarray = showpause(progress)
                blownup(colorarray)
        lastprogress = progress
        lasturl = albumarturl
        # tenbyten = Image.fromarray(colorarray).save("10x10.png")
        # img = Image.open("10x10.png")

        # HERE is where I would iterate through colorarray and set led to those colors
        if onraspi:
            setleds(colorarray, progress)
        logger.debug(f"Loop took {round(time.time() - start_time,2)}s")
        time.sleep(2)
        logger.debug("Looping in check album art loop")
