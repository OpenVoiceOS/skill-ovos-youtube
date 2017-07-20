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

import os
import urllib
import urllib2
from bs4 import BeautifulSoup
import subprocess

#mycroft
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from os.path import dirname
#from mycroft.skills.audioservice import AudioService

__author__ = 'jarbas'

LOGGER = getLogger(__name__)

import logging
logging.getLogger("chardet.charsetprober").setLevel(logging.WARNING)


class YoutubeSkill(MycroftSkill):
    def __init__(self):
        super(YoutubeSkill, self).__init__(name="YoutubeSkill")
        self.audio_service = None
        self.p = None
        ## TODO Storage
        try:
            self.savedir = self.config.get("save_path", os.path.dirname(__file__) + "/music")
        except:
            self.savedir = os.path.dirname(__file__) + "/music"

        #if not os.path.exists(self.savedir):
        #    os.makedirs(self.savedir)

        ## TODO Search Terns
        path = os.path.dirname(__file__) + '/searchterms.txt'
        with open(path) as f:
            self.search_terms = f.readlines()

    def initialize(self):
        self.load_data_files(dirname(__file__))
        # initialize audio service
        #self.audio_service = AudioService(self.emitter)

        play_song_intent = IntentBuilder("PlayYoutubeIntent").require("Title").build()
        self.register_intent(play_song_intent, self.handle_play_song_intent)

    def handle_play_song_intent(self, message):
        # Play the song requested
        title = message.data.get("Title")
        target = message.data.get("target", "all")
        utterance = message.data.get("utterance", "")
        self.speak("searching youtube for " + title)
        # TODO seperate artist and song
        videos = []
        url = "https://www.youtube.com/watch?v="
        self.log.info("Searching youtube for " + title)
        for v in self.search(title):
            if "channel" not in v and "list" not in v and "user" not in v:
                videos.append(url + v)
        self.log.info("Youtube Links:" + str(videos))
        if "fbchat_" in target:
            self.speak("Here is youtube link", metadata={"url":videos[0]})
        else:
            #self.audio_service.play(videos, utterance + " in vlc")
            command = ['cvlc']
            command.append('--no-video') # disables video output.
            command.append('--play-and-exit') # close cvlc after play
            command.append('--quiet') # deactivates all console messages.
            command.append(videos[0])
            self.p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = self.p.communicate()

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

    def stop(self):
        # TODO find better way
        #command = ["killall","cvlc"]
        #(out, err) = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        if self.p:
            self.p.terminate()

def create_skill():
    return YoutubeSkill()
