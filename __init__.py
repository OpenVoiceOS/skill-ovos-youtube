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

import subprocess
import os
import requests
from lxml import html
import bs4
import re
import random

#youtube
import pafy
from pattern.web import URL, DOM, plaintext, extension

#mycroft
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'jarbas'

LOGGER = getLogger(__name__)


class MP3DemoSkill(MycroftSkill):

    def __init__(self):
        super(MP3DemoSkill, self).__init__(name="MusicSkill")
        self.process = None
        ## url construct string text
        self.prefix_of_search_url = "https://www.youtube.com/results?search_query="
        self.target_yt_search_url_str = ''
        self.filter_url_portion = '&filters=playlist'#can add in different filter url portion, default set to playlist filter
        self.page_url_portion = '' # now temp set for non playlist search

        ## Intermediate outputs
        self.playlist_url_list = []#list of playlist url obtained from the search results.
        self.video_link_title_dict = {} #
        self.video_link_title_keylist = []#will be the list of dict key for the self.video_link_title_dict, for sorting purpose

        ## Storage
        self.video_download_folder = self.config["save"]
        self.dbfolder = self.video_download_folder + "/metal"

        if not os.path.exists(self.video_download_folder):
            os.makedirs(self.video_download_folder)
        if not os.path.exists(self.dbfolder):
            os.makedirs(self.dbfolder)

        ## Search Terns
        path = os.path.dirname(__file__) + '/searchterms.txt'
        with open(path) as f:
            self.search = f.readlines()

    def initialize(self):
       # self.load_data_files(dirname(__file__))

        prefixes = [
            'youtube', 'play', 'play from youtube','youtube play','pm']
        self.__register_prefixed_regex(prefixes, "(?P<Title>.*)")

        play_song_intent = IntentBuilder("PlaySongIntent").require("Title").build()
        self.register_intent(play_song_intent, self.handle_play_song_intent)

        dl_metal_intent = IntentBuilder("DownloadMetalIntent").require("metaldbKeyword").build()
        self.register_intent(dl_metal_intent, self.handle_add_to_metal_db_intent)

        dl_music_intent = IntentBuilder("DownloadMusicIntent").require("musicdbKeyword").build()
        self.register_intent(dl_music_intent, self.handle_add_to_db_intent)

    def __register_prefixed_regex(self, prefixes, suffix_regex):
        for prefix in prefixes:
            self.register_regex(prefix + ' ' + suffix_regex)

    def handle_play_song_intent(self, message):
        # Play the song requested
        title = message.data.get("Title")
        # No need to speak the title...
        #self.speak_dialog("play.song", {'title': title})
        # download song from youtube
        #self.speak("please wait while mp3 is downloaded")
        self.video_download_folder = self.video_download_folder + "/play"

        path = self.dlsong(title)
        self.process = subprocess.Popen(["cvlc", str(path)])

        self.add_result("Requested_Song", title)
        self.add_result("Song_Download_Path", path)

        self.emit_results()
        # return to standard download folder
        self.video_download_folder = self.config["save"]

    def handle_add_to_metal_db_intent(self, message):

        try:
            num = message.data["dlnum"]
        except:
            num = 15
        name , style = self.get_band()
        txt = "Downloading "+style+" music from "+name
        self.speak(txt)
        # check if folders exist
        style_folder = self.dbfolder+"/"+style
        if not os.path.exists(style_folder):
            os.makedirs(style_folder)

        band_folder = style_folder + "/" + name
        if not os.path.exists(band_folder):
            os.makedirs(band_folder)
        #set new download path
        self.video_download_folder = band_folder

        searchstr=name+" "+style
        self.dlsong(searchstr, 15)
        #return to standard download folder
        self.video_download_folder = self.config["save"]

    def handle_add_to_db_intent(self, message):
        try:
            num = message.data["dlnum"]
        except:
            num = 15

        name = random.choice(self.search)

        txt = "Downloading "+name
        self.speak(txt)
        # check if folders exist
        style_folder = self.video_download_folder+"/"+name
        if not os.path.exists(style_folder):
            os.makedirs(style_folder)

        #set new download path
        self.video_download_folder = style_folder
        self.dlsong(name, num)
        #return to standard download folder
        self.video_download_folder = self.config["save"]

    def dlsong(self, search_key, num = 1):
        self.yt_search_key = search_key
        self.get_individual_video_link()
        song = self.download_all_videos(dl_limit=num)
        print song
        # for some randmness we can increase above dl limit and randomly get one of the results
        self.video_link_title_dict.clear()
        self.video_link_title_keylist [:] = []
        return  song # path to play

    def get_individual_video_link(self):
        """ Function for non playlist search.
            self.retreive_fr_playlist will be set to 0
            hae to handle mutliple page
            each page able to handle 20 results
        """
        self.filter_url_portion = ''  # ignore the filter option.

        target_search_results_obj = []
        # in case we want to search more pages just change this and make a loop
        self.page_url_portion = '&page=1'

        # start with forming the search
        self.form_search_url()

        # Get the dom object from the search page
        search_result_dom = self.get_dom_object(self.target_yt_search_url_str)

        # Get the search results
        target_search_results_obj.extend(self.tag_element_results(search_result_dom,
                                                                  'div[class="yt-lockup-content"] h3[class="yt-lockup-title"] a'))

        #print 'results len: ', len(target_search_results_obj)

        each_video_link_title_dict = {}
        for n in target_search_results_obj:
            video_link = n.attributes['href']
            ## modified video link
            # video_link = re.sub('watch\?v=',r'v/',video_link)

            video_title = n.attributes['title'] #"Mix" in video_title[:4]  or "mix" i(n video_title[:4] or
            ile = video_title.lower()
            if "cover" in ile or "live" in ile or "acustic" in ile or "acoustic" in ile or "lesson" in ile:
                print "found blacklisted term, bypassing song: " + ile
                pass #dont want these
            else:
                each_video_link_title_dict[video_title] = 'https://www.youtube.com' + video_link

        self.video_link_title_dict.update(each_video_link_title_dict)

    def download_all_videos(self, dl_limit=10):
        """ Download all video given in self.video_link_title_dict
            Will limit by dl_limit.
        """
        counter = dl_limit
        self.video_link_title_keylist = self.video_link_title_dict.keys()
        music = []
        for title in self.video_link_title_keylist:
            try:
                title = title.encode('ascii')
                # print 'downloading title with counter: ', counter
                if not counter:
                    return random.choice(music)  #some margin for randomness, first result isnt always accurate, (gets slower...)
                print 'downloading title: ', title

                self.add_result("Dowloaded_Song", title)

                path = self.download_video(self.video_link_title_dict[title], title)
                music.append(path)
                counter = counter - 1
            except:
                print "illegal characters in youtube name" + title + "\n trying next result"

    def get_band(self):
        while True:
            try:
                response = requests.get('http://www.metal-archives.com/band/random')
                tree = html.fromstring(response.content)
                soup = bs4.BeautifulSoup(response.text, "lxml")

                Name = soup.select('h1 a[href^=http://www.metal-archives.com]')[0].get_text()
                Style = tree.xpath(".//*[@id='band_stats']/dl[2]/dd[1]/text()")[0]
                return Name, Style
            except:
                pass

    def download_video(self, video_link, video_title):
        #reformat video title
        video_title = re.sub(" ", "_", video_title)
        video_title = re.sub("/", "_", video_title)
        video_title = video_title.lower()
        video_title = video_title.encode(encoding='UTF-8', errors='strict')   #remove some forbidden chars from youtueb names
            #this is supposed to fix an error that occurs randomly, cant reproduce it for a while now so im guessing the fix worked
        #download video
        try:
            video = pafy.new(video_link)
            # try to get best audio stream
            try:
                bestaudio = video.getbestaudio()
                # update video title and dl path with exytension
                video_title += "." + bestaudio.extension
                download_fullpath = os.path.join(self.video_download_folder, video_title)
                # check if file doesnt exist yet and save
                if not os.path.isfile(download_fullpath):
                    bestaudio.download(download_fullpath, quiet=False)
                return download_fullpath
            except:
             #try to get all audio streams
                audiostreams = video.audiostreams
                i = 0
                print"couldnt get best stream, trying all streams"
                for stream in audiostreams:
                    bestaudio = audiostreams[i]
                    # update video title and dl path with exytension
                    video_title += "." + bestaudio.extension
                    download_fullpath = os.path.join(self.video_download_folder, video_title)

                    #check if file doesnt exist yet and save
                    if not os.path.isfile(download_fullpath):
                        bestaudio.download(download_fullpath, quiet=False)
                    return download_fullpath
                    i += 1
        #try all streams, some videos randomly fail
        except:
            print 'Have problem downloading this file', video_title

    def reformat_search_for_spaces(self):
        """
            Method call immediately at the initialization stages
            get rid of the spaces and replace by the "+"
            Use in search term. Eg: "Cookie fast" to "Cookie+fast"

            steps:
            strip any lagging spaces if present
            replace the self.yt_search_key
        """
        self.yt_search_key = self.yt_search_key.rstrip().replace(' ', '+')

    def form_search_url(self):
        """ Form the url from one selected key phrase.
            Set to self.target_yt_search_url_str
        """
        self.reformat_search_for_spaces()
        self.target_yt_search_url_str = self.prefix_of_search_url + self.yt_search_key + self.filter_url_portion

    def get_dom_object(self, url_target):
        """ Get dom object based on element for scraping
            Take into consideration that there might be query problem.
            Args:
                url_target (str): url link to be searched.
            Returns:
                (DOM): dom object correspond to the url.

        """
        try:
            url = URL(url_target)
            dom_object = DOM(url.download(cached=True))
        except:
            print 'Problem retrieving data for this url: ', url_target
            self.url_query_timeout = 1

        return dom_object

    def tag_element_results(self, dom_obj, tag_expr):
        """ Take in expression for dom tag expression.
            Args:
                dom_obj (dom object): May be a subset of full object.
                tag_expr (str): expression that scrape the tag object. Similar to xpath.
                                Use pattern css selector for parsing.
            Returns:
                (list): list of tag_element_objects.

            TODO: May need to check for empty list.
        """
        return dom_obj(tag_expr)

    def stop(self):#not working on ANY skill ?
        print 'trying to stop'
        if self.process:# and self.process.poll() is None:
            # No reason to say "music stopped", that is obvious!
            # self.speak_dialog('music.stop')
            self.process.terminate()
            self.process.wait()
            print "stopped"


def create_skill():
    return MP3DemoSkill()
