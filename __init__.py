# NO LICENSE
# These bits are free to do as they please, ones and zeros dont need licence or copyright

import urllib
import urllib2
from bs4 import BeautifulSoup
import subprocess
from os.path import join
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

    def handle_play_song_intent(self, message):
        # Play the song requested
        title = message.data.get("music")
        self.speak_dialog("searching.youtube", {"music": title})
        # TODO seperate artist and song
        videos = []
        url = "https://www.youtube.com/watch?v="
        self.log.info("Searching youtube for " + title)
        for v in self.search(title):
            if "channel" not in v and "list" not in v and "user" not in v:
                videos.append(url + v)
        self.log.info("Youtube Links:" + str(videos))
        # Display info on a screen
        self.enclosure.deactivate_mouth_events()
        # music code
        png = join(self.root_dir, "music.png")

        self.enclosure.mouth_display_png(png,
                                         threshold=70,
                                         invert=False, x=10, y=0,
                                         refresh=True)

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
        self.enclosure.activate_mouth_events()
        self.enclosure.mouth_reset()
        if self.p:
            self.p.terminate()


def create_skill():
    return YoutubeSkill()
