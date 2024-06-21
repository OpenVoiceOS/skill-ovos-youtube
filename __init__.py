from os.path import join, dirname

from ovos_utils import classproperty
from ovos_workshop.backwards_compat import MediaType, PlaybackType, Playlist, PluginStream
from ovos_utils.parse import fuzzy_match, MatchStrategy
from ovos_utils.process_utils import RuntimeRequirements
from ovos_workshop.decorators import ocp_search
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill
from tutubo import YoutubeSearch
from tutubo.models import Video, VideoPreview, Channel, ChannelPreview


class SimpleYoutubeSkill(OVOSCommonPlaybackSkill):
    def __init__(self, *args, **kwargs):
        super().__init__(supported_media=[MediaType.GENERIC, MediaType.VIDEO],
                         skill_icon=join(dirname(__file__), "res", "ytube.jpg"),
                         *args, **kwargs)

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
                yield PluginStream(
                    extractor_id="youtube",
                    stream=v.watch_url,
                    match_confidence=score,
                    playback=PlaybackType.VIDEO,
                    media_type=MediaType.VIDEO,
                    length=v.length * 1000 if v.length else 0,
                    image=v.thumbnail_url,
                    title=v.title,
                    skill_id=self.skill_id,
                    skill_icon=self.skill_icon
                )
                idx += 1
            elif isinstance(v, Channel) or isinstance(v, ChannelPreview):
                s = self.calc_channel_score(phrase, v, idx,
                                            base_score=base_score,
                                            explicit_request=explicit_request)
                ch = v.get()  # parse channel page
                # create playlist (list of track dicts)
                max_vids = 5
                pl = Playlist(
                    match_confidence=s,
                    playback=PlaybackType.VIDEO,
                    media_type=MediaType.VIDEO,
                    image=ch.thumbnail_url,
                    title=ch.title + " (Youtube Channel)",
                    skill_id=self.skill_id,
                    skill_icon=self.skill_icon
                )
                for vidx, v in enumerate(ch.videos):
                    if "patreon" in v.title.lower():  # TODO blacklist.voc
                        continue
                    pl.append(PluginStream(
                        extractor_id="youtube",
                        stream=v.watch_url,
                        match_confidence=self.calc_score(phrase, v, idx=vidx),
                        playback=PlaybackType.VIDEO,
                        media_type=MediaType.VIDEO,
                        length=v.length * 1000 if v.length else 0,
                        image=v.thumbnail_url,
                        title=v.title,
                        skill_id=self.skill_id,
                        skill_icon=self.skill_icon
                    ))
                    if vidx > max_vids:
                        break

                yield pl
            else:
                continue


if __name__ == "__main__":
    from ovos_utils.messagebus import FakeBus

    s = SimpleYoutubeSkill(bus=FakeBus(), skill_id="t.fake")

    for r in s.search_youtube("zz top", MediaType.MUSIC):
        print(r)
        # PluginStream(stream='https://www.youtube.com/watch?v=Ae829mFAGGE', extractor_id='youtube', title="ZZ Top - Gimme All Your Lovin' (Official Music Video) [HD Remaster]", artist='', match_confidence=-6.044776119402982, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=280000, image='https://img.youtube.com/vi/Ae829mFAGGE/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=Gg9cNGHl-bg', extractor_id='youtube', title='ZZ Top - La Grange (Live From Gruene Hall) | Stages', artist='', match_confidence=-4.235294117647056, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=278000, image='https://img.youtube.com/vi/Gg9cNGHl-bg/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=PCtcRfvcOqs', extractor_id='youtube', title='The Very Best of ZZTOP - ZZTOP Greatest Hits Full Album', artist='', match_confidence=-6.090909090909086, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=5997000, image='https://img.youtube.com/vi/PCtcRfvcOqs/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=7wRHBLwpASw', extractor_id='youtube', title='ZZ Top - Sharp Dressed Man (Official Music Video) [HD Remaster]', artist='', match_confidence=-8.476190476190476, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=254000, image='https://img.youtube.com/vi/7wRHBLwpASw/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=fnwZeLdLPdQ', extractor_id='youtube', title='ZZ Top- La Grange (lyrics)', artist='', match_confidence=4.076923076923073, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=221000, image='https://img.youtube.com/vi/fnwZeLdLPdQ/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=4IDz-XyFZCc', extractor_id='youtube', title='ZZTOP BEST SONGS EVER #bluesrock #zztop #music #classicrock #classicrockgreatesthits 💚💛❤️🙏✊✌️♥️🌟🦁📀', artist='', match_confidence=-13.877551020408168, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=38535000, image='https://img.youtube.com/vi/4IDz-XyFZCc/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # Playlist(title='ZZ Top (Youtube Channel)', artist='', position=0, image='', match_confidence=79.0, skill_id='t.fake', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg', playback=<PlaybackType.VIDEO: 1>, media_type=<MediaType.VIDEO: 3>)
        # PluginStream(stream='https://www.youtube.com/watch?v=Vppbdf-qtGU', extractor_id='youtube', title='ZZ Top - La Grange', artist='', match_confidence=12.333333333333336, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=229000, image='https://img.youtube.com/vi/Vppbdf-qtGU/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=eUDcTLaWJuo', extractor_id='youtube', title='ZZ Top - Legs (Official Music Video) [HD Remaster]', artist='', match_confidence=-10.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=296000, image='https://img.youtube.com/vi/eUDcTLaWJuo/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=kaIZWjItReI', extractor_id='youtube', title='ZZ Top - I Gotsta Get Paid', artist='', match_confidence=0.0769230769230731, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=219000, image='https://img.youtube.com/vi/kaIZWjItReI/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=Z_4ULKpkLNc', extractor_id='youtube', title='ZZ Top - Rough Boy (Official Music Video)', artist='', match_confidence=-9.365853658536583, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=228000, image='https://img.youtube.com/vi/Z_4ULKpkLNc/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=1VmVK2s3aTc', extractor_id='youtube', title='ZZ Top - Thunderbird [Official Music Video]', artist='', match_confidence=-11.046511627906973, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=245000, image='https://img.youtube.com/vi/1VmVK2s3aTc/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=UYriLYygHyA', extractor_id='youtube', title='ZZ Top - Blue Jean Blues [Official Audio]', artist='', match_confidence=-11.365853658536583, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=235000, image='https://img.youtube.com/vi/UYriLYygHyA/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=sUEMVC_-Lag', extractor_id='youtube', title='ZZ Top - Brown Sugar [Official Audio]', artist='', match_confidence=-10.783783783783782, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=258000, image='https://img.youtube.com/vi/sUEMVC_-Lag/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=jnJSJ4UcJWs', extractor_id='youtube', title='ZZ Top - Heard It On The X [Official Audio]', artist='', match_confidence=-14.046511627906973, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=171000, image='https://img.youtube.com/vi/jnJSJ4UcJWs/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=6OPO_S6qtNo', extractor_id='youtube', title='ZZ Top - Just Got Paid [Official Audio]', artist='', match_confidence=-13.615384615384615, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=230000, image='https://img.youtube.com/vi/6OPO_S6qtNo/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=FIuPiX6rzZM', extractor_id='youtube', title='ZZ Top - La Grange [Official Audio]', artist='', match_confidence=-12.857142857142861, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=282000, image='https://img.youtube.com/vi/FIuPiX6rzZM/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=orJvQMWQ3Hs', extractor_id='youtube', title='ZZ Top - Legs [Official Audio]', artist='', match_confidence=-11.000000000000004, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=262000, image='https://img.youtube.com/vi/orJvQMWQ3Hs/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=qeFm6vCaPOk', extractor_id='youtube', title='ZZ Top - Thunderbird [Official Audio]', artist='', match_confidence=-15.783783783783782, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=245000, image='https://img.youtube.com/vi/qeFm6vCaPOk/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=2dK3UQLlXM8', extractor_id='youtube', title='ZZ Top - Tush [Official Audio]', artist='', match_confidence=-13.000000000000004, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=151000, image='https://img.youtube.com/vi/2dK3UQLlXM8/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=yX-7kIbYBhU', extractor_id='youtube', title='ZZ Top - Certified Blues [Official Audio]', artist='', match_confidence=-19.365853658536583, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=235000, image='https://img.youtube.com/vi/yX-7kIbYBhU/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=TG2JtdUEMJU', extractor_id='youtube', title="ZZ Top - Gimme All Your Lovin' (Live)", artist='', match_confidence=-18.783783783783782, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=258000, image='https://img.youtube.com/vi/TG2JtdUEMJU/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=sn1kjlIdIl8', extractor_id='youtube', title='Got Me Under Pressure (2008 Remaster)', artist='', match_confidence=-30.594594594594597, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=244000, image='https://img.youtube.com/vi/sn1kjlIdIl8/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=Pn2-b_opVTo', extractor_id='youtube', title='ZZ Top Sharp Dressed Man', artist='', match_confidence=-12.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=253000, image='https://img.youtube.com/vi/Pn2-b_opVTo/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=Mqfwbf3X8SA', extractor_id='youtube', title='Lynyrd Skynyrd - Simple Man - Live At The Florida Theatre / 2015 (Official Video)', artist='', match_confidence=-34.29629629629629, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=434000, image='https://img.youtube.com/vi/Mqfwbf3X8SA/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=v2AC41dglnM', extractor_id='youtube', title='AC/DC - Thunderstruck (Official Video)', artist='', match_confidence=-31.105263157894733, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=293000, image='https://img.youtube.com/vi/v2AC41dglnM/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=3ZoKmdbERzA', extractor_id='youtube', title='Black Stone Cherry - Me and Mary Jane [OFFICIAL VIDEO]', artist='', match_confidence=-34.44444444444444, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=251000, image='https://img.youtube.com/vi/3ZoKmdbERzA/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=GPVsAJ2kgo8', extractor_id='youtube', title='Cheap Sunglasses (2019 Remaster)', artist='', match_confidence=-34.75, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=287000, image='https://img.youtube.com/vi/GPVsAJ2kgo8/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=gf7ze6vcS_8', extractor_id='youtube', title="ZZ Top - I'm Bad I'm Nationwide (Official Music Video)", artist='', match_confidence=-30.888888888888886, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=272000, image='https://img.youtube.com/vi/gf7ze6vcS_8/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=SE1xO44FlME', extractor_id='youtube', title='ZZ Top La Grange live 1982', artist='', match_confidence=-19.923076923076927, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=277000, image='https://img.youtube.com/vi/SE1xO44FlME/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=LOoPWnnl4CE', extractor_id='youtube', title='Jesus Just Left Chicago (2006 Remaster)', artist='', match_confidence=-36.307692307692314, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=211000, image='https://img.youtube.com/vi/LOoPWnnl4CE/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=3-dxpinUORo', extractor_id='youtube', title="ZZ Top - Waitin' For The Bus / Jesus Just Left Chicago", artist='', match_confidence=-33.888888888888886, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=384000, image='https://img.youtube.com/vi/3-dxpinUORo/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=rM_nGN_du84', extractor_id='youtube', title='Legs (2008 Remaster)', artist='', match_confidence=-36.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=274000, image='https://img.youtube.com/vi/rM_nGN_du84/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=TKJymx2KDWo', extractor_id='youtube', title='ZZ Top - Sleeping Bag (Official Music Video)', artist='', match_confidence=-33.36363636363637, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=268000, image='https://img.youtube.com/vi/TKJymx2KDWo/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=eCUCSqcSnac', extractor_id='youtube', title='ZZ Top - Tube Snake Boogie (Official Music Video)', artist='', match_confidence=-35.755102040816325, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=173000, image='https://img.youtube.com/vi/eCUCSqcSnac/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=KCLXy-vSu3o', extractor_id='youtube', title='Zz top - Tush', artist='', match_confidence=-2.8461538461538467, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=134000, image='https://img.youtube.com/vi/KCLXy-vSu3o/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=PmAadq5M4M4', extractor_id='youtube', title='ZZ Top - Live in Las Vegas 2022, Raw Whisky Tour (4K) - Venetian Theater 2022-12-09 *FULL SHOW*', artist='', match_confidence=-43.684210526315795, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=5047000, image='https://img.youtube.com/vi/PmAadq5M4M4/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=JIrhcOIYfA8', extractor_id='youtube', title="ZZ Top- I'm Bad, I'm Nationwide (lyrics)", artist='', match_confidence=-36.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=284000, image='https://img.youtube.com/vi/JIrhcOIYfA8/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=toStlVtrvN4', extractor_id='youtube', title='ZZ TOP - Full HD Concert @ Hard Rock Live, Hollywood, FL, USA 10 MAR 2024', artist='', match_confidence=-43.78082191780822, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=4560000, image='https://img.youtube.com/vi/toStlVtrvN4/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=tir5zIhAETY', extractor_id='youtube', title='Blue Jean Blues (2005 Remaster)', artist='', match_confidence=-46.54838709677419, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=280000, image='https://img.youtube.com/vi/tir5zIhAETY/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=b76kjd5nvMg', extractor_id='youtube', title='ZZ TOP - Blue Jean Blues', artist='', match_confidence=-29.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=420000, image='https://img.youtube.com/vi/b76kjd5nvMg/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=Keux3G2Gb_M', extractor_id='youtube', title='I Got the Six (2008 Remaster)', artist='', match_confidence=-48.103448275862064, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=175000, image='https://img.youtube.com/vi/Keux3G2Gb_M/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=JwM1MnG5UVo', extractor_id='youtube', title='Slash, Le Grange', artist='', match_confidence=-49.75, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=443000, image='https://img.youtube.com/vi/JwM1MnG5UVo/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=kxOOC2Wf1rQ', extractor_id='youtube', title='ZZ Top   La grange, Tush Live In Montreux 2013', artist='', match_confidence=-43.95652173913043, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=552000, image='https://img.youtube.com/vi/kxOOC2Wf1rQ/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=ISveIzgq_kQ', extractor_id='youtube', title='ZZ Top - Got Me Under Pressure (Live)', artist='', match_confidence=-41.78378378378378, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=242000, image='https://img.youtube.com/vi/ISveIzgq_kQ/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=0968f0VWvd8', extractor_id='youtube', title="ZZ Top - My Head's In Mississippi (Official Music Video)", artist='', match_confidence=-48.28571428571429, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=246000, image='https://img.youtube.com/vi/0968f0VWvd8/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=wShLjF_YE2A', extractor_id='youtube', title="My Head's in Mississippi (2019 Remaster)", artist='', match_confidence=-54.99999999999999, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=260000, image='https://img.youtube.com/vi/wShLjF_YE2A/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=I_2D8Eo15wE', extractor_id='youtube', title='Ram Jam - Black Betty', artist='', match_confidence=-51.476190476190474, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=145000, image='https://img.youtube.com/vi/I_2D8Eo15wE/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')
        # PluginStream(stream='https://www.youtube.com/watch?v=yWMnxyIhCDw', extractor_id='youtube', title='ZZ Top “La Grange” on the Howard Stern Show', artist='', match_confidence=-48.04651162790697, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=477000, image='https://img.youtube.com/vi/yWMnxyIhCDw/default.jpg', skill_icon='/home/miro/PycharmProjects/OCPSkills/skill-ovos-youtube/res/ytube.jpg')