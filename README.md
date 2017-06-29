# MusicSkill

This skill illustrates a very simple general music player.  Search youtube and play with cvlc

Its intended to be a cheap way to play anything without any account (eg. spotify) or having a music library on disk

# usage

youtube play "whatever you want"

# install

run requirements.sh

# logs

2017-06-29 23:54:50,468 - Skills - DEBUG - {"type": "8:PlayYoutubeIntent", "data": {"confidence": 0.25, "target": "cli", "Title": "metallica", "intent_type": "8:PlayYoutubeIntent", "mute": false, "utterance": "youtube play metallica"}, "context": {"target": "cli"}}
2017-06-29 23:54:50,469 - YoutubeSkill - INFO - Searching youtube for metallica
2017-06-29 23:54:50,477 - Skills - DEBUG - {"type": "speak", "data": {"target": "cli", "mute": false, "expect_response": false, "more": false, "utterance": "searching youtube for metallica", "metadata": {"source_skill": "YoutubeSkill"}}, "context": null}
2017-06-29 23:54:53,392 - YoutubeSkill - INFO - Youtube Links:['https://www.youtube.com/watch?v=4tdKl-gTpZg', 'https://www.youtube.com/watch?v=Ckom3gf57Yw', 'https://www.youtube.com/watch?v=DqDeH3hwxfw', 'https://www.youtube.com/watch?v=HyrWd_gfQNQ', 'https://www.youtube.com/watch?v=iT6vqeL-ysI', 'https://www.youtube.com/watch?v=UKuJAMz3Vzc', 'https://www.youtube.com/watch?v=zMpKsRcGyTI', 'https://www.youtube.com/watch?v=G-Bn_kD6QN4', 'https://www.youtube.com/watch?v=wsrvmNtWU4E', 'https://www.youtube.com/watch?v=dkNfNR1WYMY', 'https://www.youtube.com/watch?v=CD-E-LDc384', 'https://www.youtube.com/watch?v=kV-2Q8QtCY4', 'https://www.youtube.com/watch?v=uhBHL3v4d3I', 'https://www.youtube.com/watch?v=3rFoGVkZ29w', 'https://www.youtube.com/watch?v=S5TnPjOd_To', 'https://www.youtube.com/watch?v=NJzoBmVPeYw', 'https://www.youtube.com/watch?v=zc3cE4pYw5I']
* plays in cvlc