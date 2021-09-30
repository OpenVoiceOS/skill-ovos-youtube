from os.path import join, dirname

from json_database import JsonStorageXDG
from ovos_utils.parse import fuzzy_match, MatchStrategy
from ovos_plugin_common_play.ocp import MediaType, PlaybackType
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill, \
    common_play_search
from youtube_searcher import search_youtube


class SimpleYoutubeSkill(OVOSCommonPlaybackSkill):
    def __init__(self):
        super(SimpleYoutubeSkill, self).__init__("Simple Youtube")
        self.supported_media = [MediaType.GENERIC,
                                MediaType.MUSIC,
                                MediaType.PODCAST,
                                MediaType.DOCUMENTARY,
                                MediaType.VIDEO]
        self._search_cache = JsonStorageXDG("simple_youtube.search.history",
                                            subfolder="common_play")
        self.skill_icon = join(dirname(__file__), "ui", "ytube.jpg")
        if "fallback_mode" not in self.settings:
            self.settings["fallback_mode"] = False

        if "audio_mode" not in self.settings:
            # audio mode favors the audio_player whenever it makes sense,
            # it will cast more video types to audio (music videos,
            # full concert, lyrics videos...)
            self.settings["audio_mode"] = False

    def search_youtube(self, phrase):
        # media youtube, cache results for speed in repeat queries
        if phrase in self._search_cache:
            results = self._search_cache[phrase]
        else:
            try:
                results = search_youtube(phrase)["videos"]
            except Exception as e:
                # youtube can break at any time... they also love AB testing
                # often only some queries will break...
                self.log.error("youtube media failed!")
                self.log.exception(e)
                return []
            self._search_cache[phrase] = results
            self._search_cache.store()
        return results

    # matching helpers
    @staticmethod
    def parse_duration(video):
        # extract_streams duration into (int) seconds
        # {'length': '3:49'
        if not video.get("length"):
            return 0
        length = 0
        nums = video["length"].split(":")
        if len(nums) == 1 and nums[0].isdigit():
            # seconds
            length = int(nums[0])
        elif len(nums) == 2:
            # minutes : seconds
            length = int(nums[0]) * 60 + \
                     int(nums[0])
        elif len(nums) == 3:
            # hours : minutes : seconds
            length = int(nums[0]) * 60 * 60 + \
                     int(nums[0]) * 60 + \
                     int(nums[0])
        # better-_player expects milliseconds
        return length * 1000

    def is_music(self, match):
        if self.settings["audio_mode"]:
            return (self.voc_match(match["title"], "music") or
                    self.voc_match(match["title"], "music_video") or
                    self.voc_match(match["title"], "live")) and \
                   not self.voc_match(match["title"], "video_filter")
        return self.voc_match(match["title"], "music") and \
               not self.voc_match(match["title"], "video_filter")

    def is_podcast(self, match):
        # lets require duration above 30min to exclude trailers and such
        dur = self.parse_duration(match) / 1000  # convert ms to seconds
        if dur < 30 * 60:
            return False
        return self.voc_match(match["title"], "podcast")

    def is_documentary(self, match):
        # lets require duration above 20min to exclude trailers and such
        dur = self.parse_duration(match) / 1000  # convert ms to seconds
        if dur < 20 * 60:
            return False
        return self.voc_match(match["title"], "documentary")

    # common play
    @common_play_search()
    def search_youtube_music(self, phrase,
                             media_type=MediaType.GENERIC):
        # media only for media we are 100% sure is music
        if media_type not in [MediaType.GENERIC,
                              MediaType.MUSIC]:
            return []

        # match the request media_type
        base_score = 0
        if media_type == MediaType.MUSIC:
            base_score += 20

        if self.voc_match(phrase, "youtube"):
            # explicitly requested youtube
            base_score += 30
            phrase = self.remove_voc(phrase, "youtube")

        results = self.search_youtube(phrase)

        # only return videos assumed to be music
        # music.voc contains things like "full album" and "music"
        # if any of these is present in the title, the video is valid
        results = [r for r in results if self.is_music(r)]

        # score
        def calc_score(match, idx=0):
            # idx represents the order from youtube
            score = base_score - idx * 5  # - 5% as we go down the results list

            # this will give score of 100 if query is included in video title
            score += 100 * fuzzy_match(
                phrase.lower(), match["title"].lower(),
                strategy=MatchStrategy.TOKEN_SET_RATIO)

            # small penalty to not return 100 and allow better disambiguation
            if media_type == MediaType.GENERIC:
                score -= 10

            # the title says its official!
            if self.voc_match(match["title"], "official"):
                score += 5

            return min(100, score)

        matches = [{
            "match_confidence": calc_score(r, idx),
            "media_type": MediaType.MUSIC,
            "length": self.parse_duration(r),
            "uri": "youtube//" + r["url"],
            "playback": PlaybackType.AUDIO,
            "image": r["thumbnails"][-1]["url"].split("?")[0],
            "bg_image": r["thumbnails"][-1]["url"].split("?")[0],
            "skill_icon": self.skill_icon,
            "skill_logo": self.skill_icon,  # backwards compat
            "title": r["title"],
            "skill_id": self.skill_id
        } for idx, r in enumerate(results)]

        return matches

    @common_play_search()
    def search_youtube_videos(self, phrase,
                              media_type=MediaType.GENERIC):
        # match the request media_type
        base_score = 0
        if media_type == MediaType.MUSIC:
            base_score += 15
        elif media_type == MediaType.VIDEO:
            base_score += 25

        explicit_request = False
        if self.voc_match(phrase, "youtube"):
            # explicitly requested youtube
            base_score += 50
            phrase = self.remove_voc(phrase, "youtube")
            explicit_request = True

        # video vs audio playback
        pb = PlaybackType.VIDEO

        results = self.search_youtube(phrase)

        # primitive results filtering
        # music handled by the other media method
        results = [r for r in results if not self.is_music(r)]

        if self.settings["audio_mode"]:
            results = [r for r in results
                       if not self.voc_match(r["title"], "video_filter")]
            pb = PlaybackType.AUDIO

        if media_type == MediaType.PODCAST:
            # only return videos assumed to be podcasts
            # podcast.voc contains things like "podcast"
            results = [r for r in results if self.is_podcast(r)]

        if media_type == MediaType.DOCUMENTARY:
            # only return videos assumed to be documentaries
            # podcast.voc contains things like "documentary"
            results = [r for r in results if self.is_documentary(r)]

        # score
        def calc_score(match, idx=0):
            # idx represents the order from youtube
            score = base_score - idx * 5  # - 5% as we go down the results list

            # this will give score of 100 if query is included in video title
            score += 100 * fuzzy_match(
                phrase.lower(), match["title"].lower(),
                strategy=MatchStrategy.TOKEN_SET_RATIO)

            # small penalty to not return 100 and allow better disambiguation
            if media_type == MediaType.GENERIC:
                score -= 10

            # the title says its official!
            if self.voc_match(match["title"], "official"):
                score += 5

            if score >= 100:
                if media_type == MediaType.AUDIO:
                    score -= 20  # likely don't want to answer most of these
                elif media_type != MediaType.VIDEO:
                    score -= 10
                elif media_type == MediaType.MUSIC and not \
                        self.is_music(match):
                    score -= 5

            # youtube gives pretty high scores in general, so we allow it
            # to run as fallback mode, which assigns lower scores and gives
            # preference to matches from other skills
            if self.settings["fallback_mode"]:
                if not explicit_request:
                    score -= 25
            return min(100, score)

        matches = [{
            "match_confidence": calc_score(r, idx),
            "media_type": MediaType.VIDEO,
            "length": self.parse_duration(r),
            "uri": "youtube//" + r["url"],
            "playback": pb,
            "image": r["thumbnails"][-1]["url"].split("?")[0],
            "bg_image": r["thumbnails"][-1]["url"].split("?")[0],
            "skill_icon": self.skill_icon,
            "skill_logo": self.skill_icon,  # backwards compat
            "title": r["title"],
            "skill_id": self.skill_id
        } for idx, r in enumerate(results)]

        return matches


def create_skill():
    return SimpleYoutubeSkill()
