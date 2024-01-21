from os.path import join, dirname

from json_database import JsonStorageXDG
from ovos_bus_client.message import Message
from ovos_utils import classproperty, camel_case_split, timed_lru_cache
from ovos_utils.log import LOG
from ovos_utils.ocp import MediaType, PlaybackType
from ovos_utils.parse import fuzzy_match, MatchStrategy
from ovos_utils.process_utils import RuntimeRequirements
from ovos_workshop.decorators import ocp_search, ocp_featured_media
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill
from tutubo import YoutubeSearch
from tutubo.models import *


class SimpleYoutubeSkill(OVOSCommonPlaybackSkill):
    def __init__(self, *args, **kwargs):
        self.supported_media = [MediaType.VIDEO]
        self.skill_icon = join(dirname(__file__), "ui", "ytube.jpg")
        self.archive = JsonStorageXDG("YoutubeVideos", subfolder="OCP")
        self.playlists = JsonStorageXDG("YoutubeChannels", subfolder="OCP")
        super().__init__(*args, **kwargs)

    @classproperty
    def runtime_requirements(self):
        return RuntimeRequirements(internet_before_load=True,
                                   requires_internet=True)

    def initialize(self):
        if "fallback_mode" not in self.settings:
            self.settings["fallback_mode"] = False
        self.precache()
        self.add_event(f"{self.skill_id}.precache", self.precache)
        self.bus.emit(Message(f"{self.skill_id}.precache"))

    def precache(self, message: Message = None):
        """cache soundcloud searches and register some helper OCP keywords
        populates featured_media
        """

        def norm(t):
            return t.split("(")[0].split("[")[0].split("//")[0].replace(",", "-").replace(":", "-").strip()

        artist_names = [v["artist"] for v in self.archive.values()]
        playlist_names = [k for k in self.playlists.keys()]
        videos = []

        if message is not None:
            for query in self.settings.get("featured", ["8 bit guy", "PBS space time", "OpenVoiceOS",
                                                        "PBS Eons", "technology connections", "SmartGic"]):
                for r in self.search_youtube(query, MediaType.MUSIC):
                    if "playlist" in r:
                        playlist_names.append(norm(r["title"]))
                        for r in r["playlist"]:
                            if r["artist"]:
                                artist_names.append(norm(r["artist"]))
                                artist_names.append(camel_case_split(r["artist"]))
                            videos.append(r["title"])
                        continue

                    if r["artist"]:
                        artist_names.append(norm(r["artist"]))
                        videos.append(r["title"])

        artist_names = list(set([a for a in artist_names if a is not None and a.strip()]))
        playlist_names = list(set([a for a in playlist_names if a is not None and a.strip()]))
        if len(artist_names):
            self.register_ocp_keyword(MediaType.VIDEO, "channel_name", artist_names)
        if len(playlist_names):
            self.register_ocp_keyword(MediaType.VIDEO, "playlist_name", playlist_names)
        if len(videos):
            self.register_ocp_keyword(MediaType.VIDEO, "video_name", videos)
        self.register_ocp_keyword(MediaType.VIDEO, "video_streaming_provider", ["youtube"])
        self.register_ocp_keyword(MediaType.VIDEO, "video_genre",
                                  ["videos", "review", "unboxing", "educational", "science", "technology"])
        self.export_ocp_keywords_csv("youtube.csv")

    # score
    def calc_score(self, phrase, match, idx=0, explicit_request=False,
                   base_score=0):

        # shared logic
        score = self.calc_channel_score(phrase, match, idx,
                                        explicit_request, base_score)

        # the title says its official!
        if self.voc_match(match.title, "official"):
            score += 5

        return min(100, score)

    def calc_channel_score(self, phrase, match, idx=0, explicit_request=False,
                           base_score=0):
        # idx represents the order from youtube
        score = base_score - idx  # - 1% as we go down the results list

        score += 100 * fuzzy_match(phrase.lower(), match.title.lower(),
                                   strategy=MatchStrategy.TOKEN_SET_RATIO)

        # youtube gives pretty high scores in general, so we allow it
        # to run as fallback mode, which assigns lower scores and gives
        # preference to matches from other skills
        if self.settings["fallback_mode"]:
            if not explicit_request:
                score -= 25
        return min(100, score)

    @timed_lru_cache(seconds=3600 * 3)
    def search_yt(self, phrase):
        return list(YoutubeSearch(phrase).iterate_youtube(max_res=50))

    # common play
    @ocp_search()
    def search_youtube(self, phrase, media_type):
        # match the request media_type
        base_score = 0
        if media_type == MediaType.VIDEO:
            base_score += 25
        else:
            base_score -= 15

        explicit_request = False
        if self.voc_match(phrase, "youtube"):
            # explicitly requested youtube
            base_score += 50
            phrase = self.remove_voc(phrase, "youtube")
            explicit_request = True

        idx = 0
        for v in self.search_yt(phrase):
            if isinstance(v, Video) or isinstance(v, VideoPreview):
                score = self.calc_score(phrase, v, idx,
                                        base_score=base_score,
                                        explicit_request=explicit_request)
                # return as a video result (single track dict)
                entry = {
                    "match_confidence": score,
                    "media_type": MediaType.VIDEO,
                    "length": v.length * 1000,
                    "uri": "youtube//" + v.watch_url,
                    "playback": PlaybackType.VIDEO,
                    "image": v.thumbnail_url,
                    "bg_image": v.thumbnail_url,
                    "skill_icon": self.skill_icon,
                    "title": v.title,
                    "artist": v.author,
                    "skill_id": self.skill_id
                }
                # TODO - include date info, so we can use that to sort results
                self.archive[entry["uri"]] = entry
                yield entry
                idx += 1
            elif isinstance(v, Channel) or isinstance(v, ChannelPreview):
                s = self.calc_channel_score(phrase, v, idx,
                                            base_score=base_score,
                                            explicit_request=explicit_request)
                ch = v.get()  # parse channel page
                # create playlist (list of track dicts)
                max_vids = 5
                pl = []
                for vidx, v in enumerate(ch.videos):
                    if "patreon" in v.title.lower():  # TODO blacklist.voc
                        continue
                    pl.append({
                        "match_confidence": self.calc_score(phrase, v,
                                                            idx=vidx),
                        "media_type": MediaType.VIDEO,
                        "length": v.length * 1000,
                        "uri": "youtube//" + v.watch_url,
                        "playback": PlaybackType.VIDEO,
                        "image": v.thumbnail_url,
                        "bg_image": v.thumbnail_url,
                        "skill_icon": self.skill_icon,
                        "artist": ch.channel_name,
                        "title": v.title,
                        "skill_id": self.skill_id
                    })
                    if vidx > max_vids:
                        break

                entry = {
                    "match_confidence": s,
                    "media_type": MediaType.VIDEO,
                    "playback": PlaybackType.VIDEO,
                    "playlist": pl,  # return full playlist result
                    #                    "image": ch.thumbnail_url,
                    #                    "bg_image": ch.thumbnail_url,
                    "skill_icon": self.skill_icon,
                    "artist": ch.channel_name,
                    "title": ch.title + " (Youtube Channel)",
                    "skill_id": self.skill_id
                }
                self.playlists[entry["title"]] = entry
                yield entry
                for entry in pl:
                    self.archive[entry["uri"]] = entry
            else:
                continue

    @ocp_search()
    def search_db(self, phrase, media_type=MediaType.GENERIC):
        base_score = 30 if media_type == MediaType.VIDEO else 0
        entities = self.ocp_voc_match(phrase)

        base_score += 30 * len(entities)

        artist = entities.get("channel_name")
        playlist = entities.get("playlist_name")
        song = entities.get("video_name")
        skill = "video_streaming_provider" in entities  # skill matched

        results = []
        if skill:
            base_score += 30

        urls = []

        if song:
            LOG.debug("searching YoutubeMusic video cache")
            for video in self.archive.values():
                if song.lower() in video["title"].lower():
                    s = base_score + 30
                    if artist and (artist.lower() in video["title"].lower() or
                                   artist.lower() in video.get("artist", "").lower()):
                        s += 30
                    video["match_confidence"] = min(100, s)
                    if video["media_type"] != media_type and media_type != MediaType.GENERIC:
                        video["match_confidence"] -= 20
                    results.append(video)
                    urls.append(video["uri"])

        if artist:
            LOG.debug("searching Youtube channel cache")
            for video in self.archive.values():
                if video["uri"] in urls:
                    continue
                if artist.lower() in video["title"].lower() or \
                        camel_case_split(artist).lower() in camel_case_split(video["title"]).lower():
                    video["match_confidence"] = min(100, base_score + 40)
                    if video["media_type"] != media_type and media_type != MediaType.GENERIC:
                        video["match_confidence"] -= 20
                    results.append(video)
                    urls.append(video["uri"])

        if playlist:
            LOG.debug("searching Youtube playlist cache")
            for k, pl in self.playlists.items():
                if playlist.lower() in k.lower() and pl["playlist"]:
                    pl["match_confidence"] = min(100, base_score + 35)
                    results.append(pl)

        if not results:
            for video in self.archive.values():
                if phrase.lower() in video["title"].lower() or \
                        camel_case_split(phrase).lower() in camel_case_split(video["title"]).lower():
                    s = base_score + 35
                    video["match_confidence"] = min(100, s)
                    results.append(video)

        if skill and media_type == MediaType.VIDEO:
            results.append(self.get_playlist())

        return sorted(results, key=lambda k: k["match_confidence"], reverse=True)

    @ocp_featured_media()
    def featured_media(self):
        return [{
            "title": video["title"],
            "image": video["thumbnail"],
            "match_confidence": 80,
            "media_type": MediaType.VIDEO,
            "uri": uri,
            "playback": PlaybackType.VIDEO,
            "skill_icon": self.skill_icon,
            "bg_image": video["thumbnail"],
            "skill_id": self.skill_id
        } for uri, video in self.archive.items()]

    def get_playlist(self, score=50, num_entries=50):
        pl = self.featured_media()[:num_entries]
        return {
            "match_confidence": score,
            "media_type": MediaType.VIDEO,
            "playlist": pl,
            "playback": PlaybackType.VIDEO,
            "skill_icon": self.skill_icon,
            "image": self.skill_icon,
            "title": "YoutubeMusic Featured Media (Playlist)",
            "author": "YoutubeMusic"
        }


if __name__ == "__main__":
    from ovos_utils.messagebus import FakeBus

    s = SimpleYoutubeSkill(bus=FakeBus(), skill_id="t.fake")

    for r in s.search_db("Open Voice OS", MediaType.VIDEO):
        print(r)
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 56000, 'uri': 'youtube//https://www.youtube.com/watch?v=5oBp98Z6fNo', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/5oBp98Z6fNo/default.jpg', 'bg_image': 'https://img.youtube.com/vi/5oBp98Z6fNo/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS current buildroot firmware code base running on the Mark2 with Raspberry Pi 4 2GB model.', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 23000, 'uri': 'youtube//https://www.youtube.com/watch?v=QlbS72tS9Zg', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/QlbS72tS9Zg/default.jpg', 'bg_image': 'https://img.youtube.com/vi/QlbS72tS9Zg/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS - Mark1 Support', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 138000, 'uri': 'youtube//https://www.youtube.com/watch?v=x5UCjL-D_5A', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/x5UCjL-D_5A/default.jpg', 'bg_image': 'https://img.youtube.com/vi/x5UCjL-D_5A/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS - Side by side comparison with Google HUB', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 49000, 'uri': 'youtube//https://www.youtube.com/watch?v=Aor6CFkcWzU', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/Aor6CFkcWzU/default.jpg', 'bg_image': 'https://img.youtube.com/vi/Aor6CFkcWzU/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Fully local STT using the Whisper model and TensorflowLite.', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 39000, 'uri': 'youtube//https://www.youtube.com/watch?v=2D1IZaj2Uws', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/2D1IZaj2Uws/default.jpg', 'bg_image': 'https://img.youtube.com/vi/2D1IZaj2Uws/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Instant listening feature', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 86000, 'uri': 'youtube//https://www.youtube.com/watch?v=0zkX_ov2cmM', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/0zkX_ov2cmM/default.jpg', 'bg_image': 'https://img.youtube.com/vi/0zkX_ov2cmM/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS - Operation System Update', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 71000, 'uri': 'youtube//https://www.youtube.com/watch?v=jKpBW3Xvmxg', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/jKpBW3Xvmxg/default.jpg', 'bg_image': 'https://img.youtube.com/vi/jKpBW3Xvmxg/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS - Running on macos x86 ventura', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 1528000, 'uri': 'youtube//https://www.youtube.com/watch?v=hCwdtZu7WqA', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/hCwdtZu7WqA/default.jpg', 'bg_image': 'https://img.youtube.com/vi/hCwdtZu7WqA/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS Voice Assistant Platform Showcase', 'artist': 'The KDE Community', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 228000, 'uri': 'youtube//https://www.youtube.com/watch?v=KLD2RSRKI-M', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/KLD2RSRKI-M/default.jpg', 'bg_image': 'https://img.youtube.com/vi/KLD2RSRKI-M/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - First run wizard', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 29000, 'uri': 'youtube//https://www.youtube.com/watch?v=hQetwizHnU0', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/hQetwizHnU0/default.jpg', 'bg_image': 'https://img.youtube.com/vi/hQetwizHnU0/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Our animated weather skill', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 314000, 'uri': 'youtube//https://www.youtube.com/watch?v=Bjx0RAZ3VY0', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/Bjx0RAZ3VY0/default.jpg', 'bg_image': 'https://img.youtube.com/vi/Bjx0RAZ3VY0/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - First boot wizard (The Mycroft way)', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 104000, 'uri': 'youtube//https://www.youtube.com/watch?v=G37SvJQQAsc', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/G37SvJQQAsc/default.jpg', 'bg_image': 'https://img.youtube.com/vi/G37SvJQQAsc/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Quick performance check', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 109000, 'uri': 'youtube//https://www.youtube.com/watch?v=nmZem5jBShI', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/nmZem5jBShI/default.jpg', 'bg_image': 'https://img.youtube.com/vi/nmZem5jBShI/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS - Open Virtual Appliance', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 96000, 'uri': 'youtube//https://www.youtube.com/watch?v=BXk_chYJaIQ', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/BXk_chYJaIQ/default.jpg', 'bg_image': 'https://img.youtube.com/vi/BXk_chYJaIQ/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Bigscreen Demo', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 62000, 'uri': 'youtube//https://www.youtube.com/watch?v=QYgx6EFTqoo', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/QYgx6EFTqoo/default.jpg', 'bg_image': 'https://img.youtube.com/vi/QYgx6EFTqoo/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Upcoming audio GUI', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 43000, 'uri': 'youtube//https://www.youtube.com/watch?v=YzC7oFYCcRE', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/YzC7oFYCcRE/default.jpg', 'bg_image': 'https://img.youtube.com/vi/YzC7oFYCcRE/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Audio player MPRIS support', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 30000, 'uri': 'youtube//https://www.youtube.com/watch?v=cepLKDtvkPI', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/cepLKDtvkPI/default.jpg', 'bg_image': 'https://img.youtube.com/vi/cepLKDtvkPI/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Bigscreen demo3', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 83000, 'uri': 'youtube//https://www.youtube.com/watch?v=1KMFV0UVYEM', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/1KMFV0UVYEM/default.jpg', 'bg_image': 'https://img.youtube.com/vi/1KMFV0UVYEM/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Audio Service Teaser', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 35000, 'uri': 'youtube//https://www.youtube.com/watch?v=OcnmLZi1gkU', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/OcnmLZi1gkU/default.jpg', 'bg_image': 'https://img.youtube.com/vi/OcnmLZi1gkU/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - XMOS VocalFusion Driver.', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 69000, 'uri': 'youtube//https://www.youtube.com/watch?v=4luBeUP06VA', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/4luBeUP06VA/default.jpg', 'bg_image': 'https://img.youtube.com/vi/4luBeUP06VA/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Bigscreen demo2', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 199000, 'uri': 'youtube//https://www.youtube.com/watch?v=gcVAkhvvmg4', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/gcVAkhvvmg4/default.jpg', 'bg_image': 'https://img.youtube.com/vi/gcVAkhvvmg4/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Quick & Dirty pre-alpha demo', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 85000, 'uri': 'youtube//https://www.youtube.com/watch?v=_I2MCET2Y2E', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/_I2MCET2Y2E/default.jpg', 'bg_image': 'https://img.youtube.com/vi/_I2MCET2Y2E/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Audio Service Teaser', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 41000, 'uri': 'youtube//https://www.youtube.com/watch?v=rHMTOKqBh1c', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/rHMTOKqBh1c/default.jpg', 'bg_image': 'https://img.youtube.com/vi/rHMTOKqBh1c/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'Featured Ai: Openvoiceos.com', 'artist': 'AI News & Tools Artificial Intelligence News&Tools', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 44000, 'uri': 'youtube//https://www.youtube.com/watch?v=jYTzdQXdvrU', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/jYTzdQXdvrU/default.jpg', 'bg_image': 'https://img.youtube.com/vi/jYTzdQXdvrU/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - XMOS VocalFusion Driver 2', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 49000, 'uri': 'youtube//https://www.youtube.com/watch?v=e0nhC06-2lQ', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/e0nhC06-2lQ/default.jpg', 'bg_image': 'https://img.youtube.com/vi/e0nhC06-2lQ/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS - Smart speaker functions', 'artist': 'Peter Steenbergen', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 86000, 'uri': 'youtube//https://www.youtube.com/watch?v=hY9E3-eE1WI', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/hY9E3-eE1WI/default.jpg', 'bg_image': 'https://img.youtube.com/vi/hY9E3-eE1WI/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS - Mycroft A.I. Edition, idle/listening performance', 'artist': 'Peter Steenbergen', 'skill_id': 't.fake'}
        # {'match_confidence': 100, 'media_type': <MediaType.VIDEO: 3>, 'length': 372000, 'uri': 'youtube//https://www.youtube.com/watch?v=DEeba_mywTs', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/DEeba_mywTs/default.jpg', 'bg_image': 'https://img.youtube.com/vi/DEeba_mywTs/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'Showcase: OpenVoiceOS current development status', 'artist': 'Peter Steenbergen', 'skill_id': 't.fake'}

    for r in s.search_db("hivemind", MediaType.VIDEO):
        print(r)
        # {'match_confidence': 65, 'media_type': <MediaType.VIDEO: 3>, 'length': 35000, 'uri': 'youtube//https://www.youtube.com/watch?v=TGsFldouzRo', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/TGsFldouzRo/default.jpg', 'bg_image': 'https://img.youtube.com/vi/TGsFldouzRo/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS - Hivemind satelite', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 65, 'media_type': <MediaType.VIDEO: 3>, 'length': 75000, 'uri': 'youtube//https://www.youtube.com/watch?v=u3cftkais9s', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/u3cftkais9s/default.jpg', 'bg_image': 'https://img.youtube.com/vi/u3cftkais9s/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'HiveMind Satellite running on a Google AIY Voice Kit (V1) with ChatGPT integration as a fallback.', 'artist': "Smart'Gic", 'skill_id': 't.fake'}

    for r in s.search_db("bigscreen", MediaType.VIDEO):
        print(r)
        # {'match_confidence': 65, 'media_type': <MediaType.VIDEO: 3>, 'length': 96000, 'uri': 'youtube//https://www.youtube.com/watch?v=BXk_chYJaIQ', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/BXk_chYJaIQ/default.jpg', 'bg_image': 'https://img.youtube.com/vi/BXk_chYJaIQ/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Bigscreen Demo', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 65, 'media_type': <MediaType.VIDEO: 3>, 'length': 30000, 'uri': 'youtube//https://www.youtube.com/watch?v=cepLKDtvkPI', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/cepLKDtvkPI/default.jpg', 'bg_image': 'https://img.youtube.com/vi/cepLKDtvkPI/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Bigscreen demo3', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 65, 'media_type': <MediaType.VIDEO: 3>, 'length': 69000, 'uri': 'youtube//https://www.youtube.com/watch?v=4luBeUP06VA', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/4luBeUP06VA/default.jpg', 'bg_image': 'https://img.youtube.com/vi/4luBeUP06VA/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OpenVoiceOS (Mycroft A.I. Edition) - Bigscreen demo2', 'artist': 'OpenVoiceOS', 'skill_id': 't.fake'}
        # {'match_confidence': 65, 'media_type': <MediaType.VIDEO: 3>, 'length': 55000, 'uri': 'youtube//https://www.youtube.com/watch?v=35dK-x1T1jQ', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/35dK-x1T1jQ/default.jpg', 'bg_image': 'https://img.youtube.com/vi/35dK-x1T1jQ/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'OCP analog inputs - cassette player in plasma bigscreen', 'artist': 'jxcxgxfx', 'skill_id': 't.fake'}

    for r in s.search_db("black hole", MediaType.VIDEO):
        print(r)
        # {'match_confidence': 65, 'media_type': <MediaType.VIDEO: 3>, 'length': 1105000, 'uri': 'youtube//https://www.youtube.com/watch?v=Q6kJaMf3Lgo', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/Q6kJaMf3Lgo/default.jpg', 'bg_image': 'https://img.youtube.com/vi/Q6kJaMf3Lgo/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': "What If There's A Black Hole Inside The Sun? | Hawking Stars", 'artist': 'PBS Space Time', 'skill_id': 't.fake'}
        # {'match_confidence': 65, 'media_type': <MediaType.VIDEO: 3>, 'length': 929000, 'uri': 'youtube//https://www.youtube.com/watch?v=KePNhUJ2reI', 'playback': <PlaybackType.VIDEO: 1>, 'image': 'https://img.youtube.com/vi/KePNhUJ2reI/default.jpg', 'bg_image': 'https://img.youtube.com/vi/KePNhUJ2reI/default.jpg', 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'title': 'How Time Becomes Space Inside a Black Hole | Space Time', 'artist': 'PBS Space Time', 'skill_id': 't.fake'}
