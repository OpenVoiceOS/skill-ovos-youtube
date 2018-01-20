# NO LICENSE
# These bits are free to do as they please, ones and zeros dont need licence or copyright

import urllib
import urllib2
from bs4 import BeautifulSoup
from os.path import join
from mycroft.skills.core import MycroftSkill
try:
    from mycroft.skills.audioservice import AudioService
except ImportError:
    AudioService = None
    import subprocess


__author__ = 'jarbas'


# disable webscrapping logs
import logging
logging.getLogger("chardet.charsetprober").setLevel(logging.WARNING)


class YoutubeSkill(MycroftSkill):
    def __init__(self):
        super(YoutubeSkill, self).__init__(name="YoutubeSkill")
        self.audio_service = None
        self.p = None

    def initialize(self):
        if AudioService:
            self.audio_service = AudioService(self.emitter)

        self.register_intent_file("youtube.intent", self.handle_play_song_intent)

    def handle_play_song_intent(self, message):
        # Play the song requested
        title = message.data.get("music")
        self.speak_dialog("searching.youtube", {"music": title})

        videos = []
        url = "https://www.youtube.com/watch?v="
        self.log.info("Searching youtube for " + title)
        for v in self.search(title):
            if "channel" not in v and "list" not in v and "user" not in v:
                videos.append(url + v)
        self.log.info("Youtube Links:" + str(videos))

        # Display icon on faceplate
        self.enclosure.deactivate_mouth_events()
        # music code
        self.enclosure.mouth_display("IIAEAOOHGAGEGOOHAA", x=10, y=0,
                                         refresh=True)

        if AudioService:
            self.audio_service.stop()
            self.audio_service.play(videos, "vlc")
        else:
            command = ['cvlc']
            command.append('--no-video') # disables video output.
            command.append('--play-and-exit') # close cvlc after play
            command.append('--quiet') # deactivates all console messages.
            command.append(videos[0])
            self.p = subprocess.Popen(command, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
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
        self.enclosure.activate_mouth_events()
        self.enclosure.mouth_reset()
        if self.p:
            self.p.terminate()


def create_skill():
    return YoutubeSkill()
