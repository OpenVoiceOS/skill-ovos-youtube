# The MIT License (MIT)
#
# Copyright (c) 2016 Ethan Ward
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
import subprocess
import os
from adapt.intent import IntentBuilder
from os.path import dirname
import youtube_dl
import urllib
import urllib2
from bs4 import BeautifulSoup

#mycroft
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from mycroft.skills.audioservice import AudioService
__author__ = 'jarbas'

LOGGER = getLogger(__name__)


class MP3DemoSkill(MycroftSkill):

    def __init__(self):
        super(MP3DemoSkill, self).__init__(name="MusicSkill")
        ## Storage
        try:
            self.savedir = self.config["save"]
        except:
            self.savedir = os.path.dirname(__file__) + "/music"

        if not os.path.exists(self.savedir):
            os.makedirs(self.savedir)

        ## Search Terns
        path = os.path.dirname(__file__) + '/searchterms.txt'
        with open(path) as f:
            self.search = f.readlines()

    def initialize(self):

        prefixes = [
            'youtube', 'play', 'play from youtube','youtube play','pm']
        self.__register_prefixed_regex(prefixes, "(?P<Title>.*)")


       # initialize audio service
        self.audio_service = AudioService(self.emitter)

        play_song_intent = IntentBuilder("PlaySongIntent").require("Title").build()
        self.register_intent(play_song_intent, self.handle_play_song_intent)

    def __register_prefixed_regex(self, prefixes, suffix_regex):
        for prefix in prefixes:
            self.register_regex(prefix + ' ' + suffix_regex)

    def handle_play_song_intent(self, message):
        # Play the song requested
        title = message.data.get("Title")
        # TODO seperate artist and song
        artist = "youtube-dl"
        video_links = self.search(title)
        song_path = self.download(artist, title, video_links[0])
        self.audio_service.play([song_path], "")


    @staticmethod
    def get_url(video):
        return youtube_dl.YoutubeDL().extract_info('http://www.youtube.com/watch?v=' + video, False).get("formats")[
            0].get("url")

    def search(self, text):
        query = urllib.quote(text)
        url = "https://www.youtube.com/results?search_query=" + query
        response = urllib2.urlopen(url)
        html = response.read()
        soup = BeautifulSoup(html)
        vid = soup.findAll(attrs={'class': 'yt-uix-tile-link'})
        videos = []
        if vid:
            for video in vid:
                videos.append(video['href'].replace("/watch?v=", ""))
        return videos

    def download(self, artist, title, link):
        # create YouTube downloader
        options = {
            'format': 'bestaudio/best',  # choice of quality
            'extractaudio': True,  # only keep the audio
            'audioformat': "mp3",  # convert to mp3
            'outtmpl': '%(id)s',  # name the file the ID of the video
            'noplaylist': True, }  # only download single song, not playlist
        ydl = youtube_dl.YoutubeDL(options)
        savepath = os.path.join(self.savedir, "%s--%s.mp3" % (title, artist))
        with ydl:
            print "Downloading: %s from %s..." % (title, link)

            # download location, check for progress

            try:
                os.stat(savepath)
                print "%s already downloaded, continuing..." % savepath
            except OSError:
                # download video
                try:
                    result = ydl.extract_info(row.Link, download=True)
                    os.rename(result['id'], savepath)
                    print "Downloaded and converted %s successfully!" % savepath

                except Exception as e:
                    print "Can't download audio! %s\n" % traceback.format_exc()
        return savepath

def create_skill():
    return MP3DemoSkill()
