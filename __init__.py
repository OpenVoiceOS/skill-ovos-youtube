import sys
from bs4 import BeautifulSoup
from mycroft.audio import wait_while_speaking
if sys.version_info[0] < 3:
    from urllib import quote
    from urllib2 import urlopen
else:
    from urllib.request import urlopen
    from urllib.parse import quote

# disable webscrapping logs
import logging
logging.getLogger("chardet.charsetprober").setLevel(logging.WARNING)

from mycroft.skills.core import intent_handler, IntentBuilder, \
    intent_file_handler
try:
    from mycroft_jarbas_utils.skills.audio import AudioSkill
except ImportError:
    from os.path import dirname

    sys.path.append(dirname(__file__))
    from audio_skill import AudioSkill

__author__ = 'jarbas'


class YoutubeSkill(AudioSkill):
    def __init__(self):
        self.backend_preference = ["chromecast", "mopidy", "mpv", "vlc",
                                   "mplayer"]
        super(YoutubeSkill, self).__init__()
        self.add_filter("music")

    @intent_handler(IntentBuilder("YoutubePlay").require(
        "youtube").require("play"))
    def handle_play_song_intent(self, message):
        # use adapt if youtube is included in the utterance
        # use the utterance remainder as query
        title = message.utterance_remainder()
        self.youtube_play(title)

    @intent_file_handler("youtube.intent")
    def handle_play_song_padatious_intent(self, message):
        # handle a more generic play command and extract name with padatious
        title = message.data.get("music")
        self.youtube_play(title)

    def youtube_search(self, title):
        videos = []
        url = "https://www.youtube.com/watch?v="
        self.log.info("Searching youtube for " + title)
        for v in self.search(title):
            if "channel" not in v and "list" not in v and "user" not in v:
                videos.append(url + v)
        self.log.info("Youtube Links:" + str(videos))
        return videos

    def youtube_play(self, title):
        # Play the song requested
        if self.audio.is_playing:
            self.audio.stop()
        self.speak_dialog("searching.youtube", {"music": title})
        wait_while_speaking()
        videos = self.youtube_search(title)

        # deactivate mouth animation
        self.enclosure.deactivate_mouth_events()
        # music code
        self.enclosure.mouth_display("IIAEAOOHGAGEGOOHAA", x=10, y=0,
                                         refresh=True)

        self.audio.play(videos)

    def search(self, text):
        query = quote(text)
        url = "https://www.youtube.com/results?search_query=" + query
        response = urlopen(url)
        html = response.read()
        soup = BeautifulSoup(html)
        vid = soup.findAll(attrs={'class': 'yt-uix-tile-link'})
        if vid:
            for video in vid:
                yield video['href'].replace("/watch?v=", "")

    def stop(self):
        self.enclosure.activate_mouth_events()
        self.enclosure.mouth_reset()
        if self.audio.is_playing:
            self.audio.stop()


def create_skill():
    return YoutubeSkill()
