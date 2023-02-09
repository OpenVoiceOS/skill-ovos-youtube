from os.path import join, dirname

from ovos_plugin_common_play.ocp import MediaType, PlaybackType
from ovos_utils.parse import fuzzy_match, MatchStrategy
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill, \
    ocp_search
from tutubo import YoutubeSearch
from tutubo.models import *
from ovos_utils.process_utils import RuntimeRequirements
from ovos_utils import classproperty


class SimpleYoutubeSkill(OVOSCommonPlaybackSkill):
    def __init__(self):
        super(SimpleYoutubeSkill, self).__init__("Simple Youtube")
        self.supported_media = [MediaType.GENERIC, MediaType.VIDEO]
        self.skill_icon = join(dirname(__file__), "ui", "ytube.jpg")

    @classproperty
    def runtime_requirements(self):
        return RuntimeRequirements(internet_before_load=True,
                                   network_before_load=True,
                                   gui_before_load=True,
                                   requires_internet=True,
                                   requires_network=True,
                                   requires_gui=True,
                                   no_internet_fallback=False,
                                   no_network_fallback=False,
                                   no_gui_fallback=False)

    def initialize(self):
        if "fallback_mode" not in self.settings:
            self.settings["fallback_mode"] = False

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
        for v in YoutubeSearch(phrase).iterate_youtube(max_res=50):
            if isinstance(v, Video) or isinstance(v, VideoPreview):
                score = self.calc_score(phrase, v, idx,
                                        base_score=base_score,
                                        explicit_request=explicit_request)
                # return as a video result (single track dict)
                yield {
                    "match_confidence": score,
                    "media_type": MediaType.VIDEO,
                    "length": v.length * 1000,
                    "uri": "youtube//" + v.watch_url,
                    "playback": PlaybackType.VIDEO,
                    "image": v.thumbnail_url,
                    "bg_image": v.thumbnail_url,
                    "skill_icon": self.skill_icon,
                    "title": v.title,
                    "skill_id": self.skill_id
                }
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
                        "title": v.title,
                        "skill_id": self.skill_id
                    })
                    if vidx > max_vids:
                        break

                yield {
                    "match_confidence": s,
                    "media_type": MediaType.VIDEO,
                    "playback": PlaybackType.VIDEO,
                    "playlist": pl,  # return full playlist result
                    "image": ch.thumbnail_url,
                    "bg_image": ch.thumbnail_url,
                    "skill_icon": self.skill_icon,
                    "title": ch.title + " (Youtube Channel)",
                    "skill_id": self.skill_id
                }
            else:
                continue


def create_skill():
    return SimpleYoutubeSkill()
