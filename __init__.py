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

import urllib
import urllib2
from bs4 import BeautifulSoup
import subprocess

from mycroft.skills.core import MycroftSkill
__author__ = 'jarbas'

import logging
logging.getLogger("chardet.charsetprober").setLevel(logging.WARNING)


class YoutubeSkill(MycroftSkill):
    def __init__(self):
        super(YoutubeSkill, self).__init__(name="YoutubeSkill")
        self.audio_service = None
        self.p = None

    def initialize(self):

        self.register_intent_file("youtube.intent", self.handle_play_song_intent)
        #play_song_intent = IntentBuilder("PlayYoutubeIntent").require(
        # "Title").build()
        #self.register_intent(play_song_intent, self.handle_play_song_intent)

    def handle_play_song_intent(self, message):
        # Play the song requested
        title = message.data.get("music")
        self.speak("searching youtube for " + title)
        # TODO seperate artist and song
        videos = []
        url = "https://www.youtube.com/watch?v="
        self.log.info("Searching youtube for " + title)
        for v in self.search(title):
            if "channel" not in v and "list" not in v and "user" not in v:
                videos.append(url + v)
        self.log.info("Youtube Links:" + str(videos))

        #self.audio_service.play(videos, utterance + "vlc")
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
        #command = ["killall","cvlc"]
        #(out, err) = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        if self.p:
            self.p.terminate()


def create_skill():
    return YoutubeSkill()
