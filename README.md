# MusicSkill

This skill illustrates a very simple general music player.  It works by downloading
music files from youtube (1st result, can be tunned) and playing with Cvlc

Its intended to be a cheap way to play anything without any account (eg. spotify) or having a music library on disk

## Current state

Working features:
    - Adjust save directory in conf file
          "MusicSkill": {
            "save": "/home/user/mycroft-core/mycroft/skills/musicskill/mp3"
            }
    - If file already downloaded doesnt download again
        - would it for some reason be best to have the skill build an intent for each already downloaded song?
    - blacklist results with terms "live" and "cover" in title

Phrases you can use with this:
   - Play "youtube search"
   - Youtube "youtube search"

Known issues:
 - Random erros downloading, when 1st search result is a playlist?
 - Random errors loading file, probably forbidden chars in youtube result name, unsure if fix worked
 - Stop isnt working, but i think its my mycroft instance that is broken (doesnt work in any skill)

TODO:
 - Maybe converting to mp3 and use playmp3 util function so cvlc is not needed (probably would need lame then)
 - Handle queuing up multiple songs
 - Refine video search

 - Fix know issues

Thanx:
 - tried forslunds media skills but they werent good for MY personal use case, so he is the indirect reason of this skill happening
 - mycroft et all
 - https://github.com/spidezad/Youtube-Videos-Search-and-Download  - i stole parts of your code for youtube search :P