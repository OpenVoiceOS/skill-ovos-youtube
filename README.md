# <img src='./ui/ytube.jpg' width='50' height='50' style='vertical-align:bottom'/> Simple Youtube Skill

simple youtube skill for better-cps

## About

search youtube by voice!

this skill can be configured as a fallback matcher for play queries, you can set `self.settings["fallback_mode"] = True`
and returned results will have lower confidence, other skills should take precedence most of the time

built on top of [youtube_searcher](https://github.com/HelloChatterbox/youtube_searcher)

![](./gui.png)
![](./gui2.png)

## Examples

* "play rob zombie"
* "play freezing moon with dead on vocals"
* "play programming music mix"
* "play center of all infinity album"

# Platform support

- :heavy_check_mark: - tested and confirmed working
- :x: - incompatible/non-functional
- :question: - untested
- :construction: - partial support

|     platform    |   status   |  tag  | version | last tested | 
|:---------------:|:----------:|:-----:|:-------:|:-----------:|
|    [Chatterbox](https://hellochatterbox.com)   | :question: |  dev  |         |    never    | 
|     [HolmesV](https://github.com/HelloChatterbox/HolmesV)     | :question: |  dev  |         |    never    | 
|    [LocalHive](https://github.com/JarbasHiveMind/LocalHive)    | :question: |  dev  |         |    never    |  
|  [Mycroft Mark1](https://github.com/MycroftAI/enclosure-mark1)    | :question: |  dev  |         |    never    | 
|  [Mycroft Mark2](https://github.com/MycroftAI/hardware-mycroft-mark-II)    | :question: |  dev  |         |    never    |  
|    [NeonGecko](https://neon.ai)      | :question: |  dev  |         |    never    |   
|       [OVOS](https://github.com/OpenVoiceOS)        | :question: |  dev  |         |    never    |    
|     [Picroft](https://github.com/MycroftAI/enclosure-picroft)       | :question: |  dev  |         |    never    |  
| [Plasma Bigscreen](https://plasma-bigscreen.org/)  | :question: |  dev  |         |    never    |  

- `tag` - link to github release / branch / commit
- `version` - link to release/commit of platform repo where this was tested

## Credits

JarbasAl

## Category

**Entertainment**

## Tags

- video
- youtube
- common play
- music
