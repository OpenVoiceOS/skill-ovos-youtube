from os.path import join, dirname

from ovos_utils import classproperty
from ovos_utils.ocp import MediaType, PlaybackType, Playlist, MediaEntry
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
                         skill_voc_filename="youtube_skill",
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
            base_score -= 50

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
                yield MediaEntry(
                    uri=v.watch_url,
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
                    pl.append(MediaEntry(
                        uri=v.watch_url,
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
        # MediaEntry(uri='https://www.youtube.com/watch?v=Ae829mFAGGE', title="ZZ Top - Gimme All Your Lovin' (Official Music Video) [HD Remaster]", artist='', match_confidence=50.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=280000, image='https://img.youtube.com/vi/Ae829mFAGGE/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=Gg9cNGHl-bg', title='ZZ Top - La Grange (Live From Gruene Hall) | Stages', artist='', match_confidence=49.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=278000, image='https://img.youtube.com/vi/Gg9cNGHl-bg/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=7wRHBLwpASw', title='ZZ Top - Sharp Dressed Man (Official Music Video) [HD Remaster]', artist='', match_confidence=48.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=254000, image='https://img.youtube.com/vi/7wRHBLwpASw/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=PCtcRfvcOqs', title='The Very Best of ZZTOP - ZZTOP Greatest Hits Full Album', artist='', match_confidence=-34.81818181818181, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=5997000, image='https://img.youtube.com/vi/PCtcRfvcOqs/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=eUDcTLaWJuo', title='ZZ Top - Legs (Official Music Video) [HD Remaster]', artist='', match_confidence=46.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=296000, image='https://img.youtube.com/vi/eUDcTLaWJuo/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=Z_4ULKpkLNc', title='ZZ Top - Rough Boy (Official Music Video)', artist='', match_confidence=45.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=228000, image='https://img.youtube.com/vi/Z_4ULKpkLNc/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=kaIZWjItReI', title='ZZ Top - I Gotsta Get Paid', artist='', match_confidence=44.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=219000, image='https://img.youtube.com/vi/kaIZWjItReI/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=kxOOC2Wf1rQ', title='ZZ Top   La grange, Tush Live In Montreux 2013', artist='', match_confidence=43.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=552000, image='https://img.youtube.com/vi/kxOOC2Wf1rQ/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # Playlist(title='ZZ Top (Youtube Channel)', artist='', position=0, image='https://yt3.googleusercontent.com/Y2jeeBQuUyBRb10nxTkWrNwGyO90fz7RRGpJ-jovV0P0apKG1XQErkktScQ5h953ww90LAtQGUY=s900-c-k-c0x00ffffff-no-rj', match_confidence=42.0, skill_id='t.fake', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', playback=<PlaybackType.VIDEO: 1>, media_type=<MediaType.VIDEO: 3>)
        # MediaEntry(uri='https://www.youtube.com/watch?v=gre65UqotpQ', title="ZZ Top - She's Got Legs - BeachLife Festival 2024", artist='', match_confidence=42.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=297000, image='https://img.youtube.com/vi/gre65UqotpQ/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=TG2JtdUEMJU', title="ZZ Top - Gimme All Your Lovin' (Live)", artist='', match_confidence=41.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=258000, image='https://img.youtube.com/vi/TG2JtdUEMJU/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=fnwZeLdLPdQ', title='ZZ Top- La Grange (lyrics)', artist='', match_confidence=-10.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=221000, image='https://img.youtube.com/vi/fnwZeLdLPdQ/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=7FGHq4eo9HQ', title='ZZ TOP - FULL SHOW@Musikfest Bethlehem, PA 8/11/24', artist='', match_confidence=39.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=5066000, image='https://img.youtube.com/vi/7FGHq4eo9HQ/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=1VmVK2s3aTc', title='ZZ Top - Thunderbird [Official Music Video]', artist='', match_confidence=38.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=245000, image='https://img.youtube.com/vi/1VmVK2s3aTc/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=UYriLYygHyA', title='ZZ Top - Blue Jean Blues [Official Audio]', artist='', match_confidence=37.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=235000, image='https://img.youtube.com/vi/UYriLYygHyA/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=sUEMVC_-Lag', title='ZZ Top - Brown Sugar [Official Audio]', artist='', match_confidence=36.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=258000, image='https://img.youtube.com/vi/sUEMVC_-Lag/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=jnJSJ4UcJWs', title='ZZ Top - Heard It On The X [Official Audio]', artist='', match_confidence=35.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=171000, image='https://img.youtube.com/vi/jnJSJ4UcJWs/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=6OPO_S6qtNo', title='ZZ Top - Just Got Paid [Official Audio]', artist='', match_confidence=34.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=230000, image='https://img.youtube.com/vi/6OPO_S6qtNo/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=FIuPiX6rzZM', title='ZZ Top - La Grange [Official Audio]', artist='', match_confidence=33.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=282000, image='https://img.youtube.com/vi/FIuPiX6rzZM/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=orJvQMWQ3Hs', title='ZZ Top - Legs [Official Audio]', artist='', match_confidence=32.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=262000, image='https://img.youtube.com/vi/orJvQMWQ3Hs/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=qeFm6vCaPOk', title='ZZ Top - Thunderbird [Official Audio]', artist='', match_confidence=31.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=245000, image='https://img.youtube.com/vi/qeFm6vCaPOk/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=2dK3UQLlXM8', title='ZZ Top - Tush [Official Audio]', artist='', match_confidence=30.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=151000, image='https://img.youtube.com/vi/2dK3UQLlXM8/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=yX-7kIbYBhU', title='ZZ Top - Certified Blues [Official Audio]', artist='', match_confidence=29.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=235000, image='https://img.youtube.com/vi/yX-7kIbYBhU/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=Vppbdf-qtGU', title='ZZ Top - La Grange', artist='', match_confidence=28.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=229000, image='https://img.youtube.com/vi/Vppbdf-qtGU/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=sn1kjlIdIl8', title='Got Me Under Pressure (2008 Remaster)', artist='', match_confidence=-59.04651162790698, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=244000, image='https://img.youtube.com/vi/sn1kjlIdIl8/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=euzlaYW7Qho', title='I Need You Tonight (2008 Remaster)', artist='', match_confidence=-59.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=379000, image='https://img.youtube.com/vi/euzlaYW7Qho/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=OorZcOzNcgE', title='Deep Purple - Child In Time - Live (1970)', artist='', match_confidence=-66.11111111111111, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=576000, image='https://img.youtube.com/vi/OorZcOzNcgE/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=yqzUsATxom4', title='Billy F Gibbons: "Missin\' Yo\' Kissin\'" from "The Big Bad Blues"', artist='', match_confidence=-67.30434782608695, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=200000, image='https://img.youtube.com/vi/yqzUsATxom4/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=Mqfwbf3X8SA', title='Lynyrd Skynyrd - Simple Man - Live At The Florida Theatre / 2015 (Official Video)', artist='', match_confidence=-67.58823529411765, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=434000, image='https://img.youtube.com/vi/Mqfwbf3X8SA/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=gOoKzw3JSCM', title='ZZ Top - Viva Las Vegas (Official Music Video)', artist='', match_confidence=22.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=273000, image='https://img.youtube.com/vi/gOoKzw3JSCM/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=fjNm4Axtol8', title='ZZ Top Make Their First Appearance on Live Television | Carson Tonight Show', artist='', match_confidence=21.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=444000, image='https://img.youtube.com/vi/fjNm4Axtol8/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=bSt4myecN_c', title='La Grange (2005 Remaster)', artist='', match_confidence=-73.54838709677419, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=231000, image='https://img.youtube.com/vi/bSt4myecN_c/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=Pn2-b_opVTo', title='ZZ Top Sharp Dressed Man', artist='', match_confidence=19.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=253000, image='https://img.youtube.com/vi/Pn2-b_opVTo/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=6c7d8BYJy8I', title='ZZ Top - Just Got Paid (From "Double Down Live - 1980")', artist='', match_confidence=18.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=236000, image='https://img.youtube.com/vi/6c7d8BYJy8I/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=WzU3iR3Wrog', title='Tush (2006 Remaster)', artist='', match_confidence=-67.61538461538461, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=134000, image='https://img.youtube.com/vi/WzU3iR3Wrog/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=eCUCSqcSnac', title='ZZ Top - Tube Snake Boogie (Official Music Video)', artist='', match_confidence=16.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=173000, image='https://img.youtube.com/vi/eCUCSqcSnac/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=gf7ze6vcS_8', title="ZZ Top - I'm Bad I'm Nationwide (Official Music Video)", artist='', match_confidence=15.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=272000, image='https://img.youtube.com/vi/gf7ze6vcS_8/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=mB3SOEsk3zw', title='ZZ Top - Sharp Dressed Man (Live)', artist='', match_confidence=14.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=265000, image='https://img.youtube.com/vi/mB3SOEsk3zw/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=WUnp0xPF6zw', title='Sharp Dressed Man (2019 Remaster)', artist='', match_confidence=-76.74358974358974, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=253000, image='https://img.youtube.com/vi/WUnp0xPF6zw/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=-Ifs9nZRSSw', title="I'm Bad, I'm Nationwide", artist='', match_confidence=-72.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=287000, image='https://img.youtube.com/vi/-Ifs9nZRSSw/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=JIrhcOIYfA8', title="ZZ Top- I'm Bad, I'm Nationwide (lyrics)", artist='', match_confidence=-39.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=284000, image='https://img.youtube.com/vi/JIrhcOIYfA8/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=UvoyWlnvVxw', title='LIVE!!! ZZ Top   "Waitin\' for the Bus"/Jesus Just Left Chicago " 2010', artist='', match_confidence=10.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=459000, image='https://img.youtube.com/vi/UvoyWlnvVxw/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=SE1xO44FlME', title='ZZ Top La Grange live 1982', artist='', match_confidence=9.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=277000, image='https://img.youtube.com/vi/SE1xO44FlME/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=TKJymx2KDWo', title='ZZ Top - Sleeping Bag (Official Music Video)', artist='', match_confidence=8.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=268000, image='https://img.youtube.com/vi/TKJymx2KDWo/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=sYDo9zuvaOY', title='Beer Drinkers & Hell Raisers (2006 Remaster)', artist='', match_confidence=-89.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=206000, image='https://img.youtube.com/vi/sYDo9zuvaOY/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=yWMnxyIhCDw', title='ZZ Top “La Grange” on the Howard Stern Show', artist='', match_confidence=6.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=477000, image='https://img.youtube.com/vi/yWMnxyIhCDw/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=ISveIzgq_kQ', title='ZZ Top - Got Me Under Pressure (Live)', artist='', match_confidence=5.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=242000, image='https://img.youtube.com/vi/ISveIzgq_kQ/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')
        # MediaEntry(uri='https://www.youtube.com/watch?v=euZm1TfO9xY', title='ZZ Top - La Grange - Tush  [Live] "Crossroads Guitar Festival 2004"', artist='', match_confidence=4.0, skill_id='t.fake', playback=<PlaybackType.VIDEO: 1>, status=<TrackState.DISAMBIGUATION: 1>, media_type=<MediaType.VIDEO: 3>, length=554000, image='https://img.youtube.com/vi/euZm1TfO9xY/default.jpg', skill_icon='/home/miro/PycharmProjects/skill-ovos-youtube/res/ytube.jpg', javascript='')