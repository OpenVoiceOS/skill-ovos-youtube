# <img src='./ui/ytube.jpg' width='50' height='50' style='vertical-align:bottom'/> Simple Youtube Skill

simple youtube skill for OCP

## About

search youtube by voice!

this skill can be configured as a fallback matcher for play queries, you can set `self.settings["fallback_mode"] = True`
and returned results will have lower confidence, other skills should take precedence most of the time


![](./gui.png)
![](./gui2.png)

## Examples

* "play open voice os videos"
* "play programming music mix"
* "play hivemind video"
* "play freezing moon with dead on vocals"

## Settings

you can add queries to skill settings that will then be pre-fetched on skill load

this populates the featured_media entries + provides fast matching against cached entries

```javascript
{    
"featured":  ["zz top", "ai covers", "frank sinatra"]
}
```

## Credits

JarbasAl

## Category

**Entertainment**

## Tags

- video
- youtube
- common play
- music
