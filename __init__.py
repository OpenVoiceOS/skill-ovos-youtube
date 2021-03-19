from os.path import join, dirname

from ovos_utils.skills.templates.common_play import BetterCommonPlaySkill
from ovos_utils.playback import CPSMatchType, CPSPlayback
from ovos_utils.parse import fuzzy_match, MatchStrategy

from youtube_searcher import search_youtube


class SimpleYoutubeSkill(BetterCommonPlaySkill):
    def __init__(self):
        super(SimpleYoutubeSkill, self).__init__("Simple Youtube")
        self.supported_media = [CPSMatchType.GENERIC,
                                CPSMatchType.MUSIC,
                                CPSMatchType.AUDIO,
                                CPSMatchType.PODCAST,
                                CPSMatchType.DOCUMENTARY,
                                CPSMatchType.VIDEO]
        self._search_cache = {}
        self.skill_icon = join(dirname(__file__), "ui", "ytube.jpg")
        if "fallback_mode" not in self.settings:
            self.settings["fallback_mode"] = False

    # common play
    def CPS_search(self, phrase, media_type=CPSMatchType.GENERIC):
        """Analyze phrase to see if it is a play-able phrase with this skill.

        Arguments:
            phrase (str): User phrase uttered after "Play", e.g. "some music"
            media_type (CPSMatchType): requested CPSMatchType to search for

        Returns:
            search_results (list): list of dictionaries with result entries
            {
                "match_confidence": CPSMatchConfidence.HIGH,
                "media_type":  CPSMatchType.MUSIC,
                "uri": "https://audioservice.or.gui.will.play.this",
                "playback": CPSPlayback.GUI,
                "image": "http://optional.audioservice.jpg",
                "bg_image": "http://optional.audioservice.background.jpg"
            }
        """
        # match the request media_type
        base_score = 0
        if media_type == CPSMatchType.MUSIC:
            base_score += 15
        elif media_type == CPSMatchType.VIDEO:
            base_score += 25

        explicit_request = False
        if self.voc_match(phrase, "youtube"):
            # explicitly requested youtube
            base_score += 50
            phrase = self.remove_voc(phrase, "youtube")
            explicit_request = True

        # playback_type defines if results should be GUI / AUDIO / AUDIO + GUI
        # this could be done at individual match level instead if needed
        if media_type == CPSMatchType.AUDIO:  # TODO or not self.gui.connected
            playback = [CPSPlayback.AUDIO]
        elif media_type != CPSMatchType.VIDEO:
            playback = [CPSPlayback.GUI, CPSPlayback.AUDIO]
        else:
            playback = [CPSPlayback.GUI]

        # search youtube, cache results for speed in repeat queries
        if phrase in self._search_cache:
            results = self._search_cache[phrase]
        else:
            try:
                results = search_youtube(phrase)["videos"]
            except Exception as e:
                # youtube can break at any time... they also love AB testing
                # often only some queries will break...
                return []
            self._search_cache[phrase] = results

        # filter results
        def parse_duration(video):
            # parse duration into (int) seconds
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
            # better-cps expects milliseconds
            return length * 1000

        def is_music(match):
            return self.voc_match(match["title"], "music")

        def is_podcast(match):
            # lets require duration above 30min to exclude trailers and such
            dur = parse_duration(match) / 1000  # convert ms to seconds
            if dur < 30 * 60:
                return False
            return self.voc_match(match["title"], "podcast")

        def is_documentary(match):
            # lets require duration above 20min to exclude trailers and such
            dur = parse_duration(match) / 1000  # convert ms to seconds
            if dur < 20 * 60:
                return False
            return self.voc_match(match["title"], "documentary")

        if media_type == CPSMatchType.MUSIC:
            # only return videos assumed to be music
            # music.voc contains things like "full album" and "music"
            # if any of these is present in the title, the video is valid
            results = [r for r in results if is_music(r)]

        if media_type == CPSMatchType.PODCAST:
            # only return videos assumed to be podcasts
            # podcast.voc contains things like "podcast"
            results = [r for r in results if is_podcast(r)]

        if media_type == CPSMatchType.DOCUMENTARY:
            # only return videos assumed to be documentaries
            # podcast.voc contains things like "documentary"
            results = [r for r in results if is_documentary(r)]

        # score
        def calc_score(match):
            score = base_score
            # this will give score of 100 if query is included in video title
            score += 100 * fuzzy_match(
                phrase.lower(), match["title"].lower(),
                strategy=MatchStrategy.TOKEN_SET_RATIO)

            # small penalty to not return 100 and allow better disambiguation
            if media_type == CPSMatchType.GENERIC:
                score -= 10
            if score >= 100:
                if media_type == CPSMatchType.AUDIO:
                    score -= 20  # likely don't want to answer most of these
                elif media_type != CPSMatchType.VIDEO:
                    score -= 10
                elif media_type == CPSMatchType.MUSIC and not is_music(match):
                    score -= 5

            # youtube gives pretty high scores in general, so we allow it
            # to run as fallback mode, which assigns lower scores and gives
            # preference to matches from other skills
            if self.settings["fallback_mode"]:
                if not explicit_request:
                    score -= 25
            return min(100, score)

        matches = []
        if CPSPlayback.GUI in playback:
            matches += [{
                "match_confidence": calc_score(r),
                "media_type": CPSMatchType.VIDEO,
                "length": parse_duration(r),
                "uri": r["url"],
                "playback": CPSPlayback.GUI,
                "image": r["thumbnails"][-1]["url"].split("?")[0],
                "bg_image": r["thumbnails"][-1]["url"].split("?")[0],
                "skill_icon": self.skill_icon,
                "skill_logo": self.skill_icon,  # backwards compat
                "title": r["title"],
                "skill_id": self.skill_id
            } for r in results]
        if CPSPlayback.AUDIO in playback:
            matches += [{
                "match_confidence": calc_score(r) - 15,  # penalty
                "media_type": CPSMatchType.VIDEO,
                "length": parse_duration(r),
                "uri": r["url"],
                "playback": CPSPlayback.AUDIO,
                "image": r["thumbnails"][-1]["url"].split("?")[0],
                "bg_image": r["thumbnails"][-1]["url"].split("?")[0],
                "skill_icon": self.skill_icon,
                "skill_logo": self.skill_icon,  # backwards compat
                "title": r["title"] + " (audio only)",
                "skill_id": self.skill_id
            } for r in results]

        return matches


def create_skill():
    return SimpleYoutubeSkill()
