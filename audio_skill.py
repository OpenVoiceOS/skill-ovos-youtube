from mycroft.skills.core import MycroftSkill, FallbackSkill, get_handler_name
from mycroft.util.log import LOG
from mycroft.util import play_wav, play_mp3
from mycroft.skills.skill_data import to_letters
from mycroft.skills.audioservice import AudioService
from adapt.intent import IntentBuilder, Intent
from os.path import join, exists
import json


class AudioServiceB(AudioService):
    def __init__(self, emitter):
        AudioService.__init__(self, emitter)
        self.events = []
        self.backend = ""
        self.prefered = ""

    def set_prefered(self, backend):
        self.prefered = backend

    def register_backend_update(self, intent_name):
        self.emitter.on(intent_name, self.handle_backend_update)
        self.events.append((intent_name, self.handle_backend_update))

    def handle_backend_update(self, message):
        self.backend = message.data.get("AudioBackend", self.prefered)

    def play(self, tracks=None, utterance=''):
        utterance = utterance or self.backend
        AudioService.play(self, tracks, utterance)

    def shutdown(self):
        self.emitter.remove('mycroft.audio.service.track_info_reply',
                            self._track_info)
        for event, handler in self.events:
            self.emitter.remove(event, handler)


class AudioSkill(MycroftSkill):
    """ Skill that automatically initializes audio service and selects audio
    backend """

    def __init__(self, name=None, emitter=None):
        self.emitter = None
        self.backend_preference = ["chromecast", "mopidy", "mpv", "vlc",
                                   "mplayer"]
        super(AudioSkill, self).__init__(name, emitter)
        self.audio = None
        self.process = None
        self._modifiers = ["in", "on", "at", "from"]
        self._filters = []
        self.backends = []
        self.create_settings_meta()
        if "default_backend" not in self.settings:
            self.settings["default_backend"] = ""
        if "force_http" not in self.settings:
            self.settings["force_http"] = False
        if "use_audio_service" not in self.settings:
            self.settings["use_audio_service"] = True
        self.backend_preference = [""]
        if self.settings["default_backend"]:
            default = self.settings["default_backend"]
            if default in self.backend_preference:
                self.backend_preference.remove(default)
            self.backend_preference.insert(0, default)

    def load_data_files(self, root_directory):
        super(AudioSkill, self).load_data_files(root_directory)
        self.init_audio()

    def create_settings_meta(self):
        # auto generate default backend choice in home
        settings_path = join(self._dir, "settingsmeta.json")
        if not exists(settings_path):
            settings = {
                "name": self.name,
                "skillMetadata": {
                    "sections": [
                        {
                            "name": "Audio Configuration",
                            "fields": [
                                {
                                    "name": "default_backend",
                                    "type": "text",
                                    "label": "default_backend",
                                    "value": self.backend_preference[0]
                                },
                                {
                                    "type": "label",
                                    "label": "By default this skill does not convert https links to http, you may want this depending on your audio setup"
                                },
                                {
                                    "name": "force_http",
                                    "type": "checkbox",
                                    "label": "force_http",
                                    "value": "false"
                                },
                                {
                                    "type": "label",
                                    "label": "By default this skill uses audio service, you may not want this depending on your audio setup"
                                },
                                {
                                    "name": "use_audio_service",
                                    "type": "checkbox",
                                    "label": "use_audio_service",
                                    "value": "true"
                                }
                            ]
                        }
                    ]
                }
            }
            with open(settings_path, "w") as f:
                f.write(json.dumps(settings))

    def init_audio(self):
        self.audio = AudioServiceB(self.emitter)
        backends = self.config_core.get("Audio", {}).get("backends", {})
        self.backends = [bk for bk in backends.keys() if backends[bk].get(
            "active", False)]
        if self.vocab_dir is None:
            self.vocab_dir = join(self._dir, "vocab", self.lang)
        for backend in self.backends:
            for m in self._modifiers:
                self.register_vocabulary(m + " " + backend, "AudioBackend")
                self.add_filter(m + " " + backend)
            self.register_vocabulary(backend, "AudioBackend")
            self.add_filter(backend)

        with open(join(self.vocab_dir, "AudioBackend.entity"), "w") as f:
            for backend in self.backends:
                f.write(backend + "\n")
        self.register_entity_file("AudioBackend.entity")

        self.backend_preference = [backend for backend in
                                   self.backend_preference if backend in
                                   self.backends]
        if len(self.backend_preference):
            self.audio.set_prefered(self.backend_preference[0])

    def add_filter(self, f):
        if f not in self._filters:
            self._filters.append(f)

    def _clean_message(self, message):
        # adapt missed it
        if "AudioBackend" not in message.data:
            if "utterance" in message.data:
                for backend in self.backends:
                    if backend in message.data["utterance"]:
                        self.audio.backend = backend
            message.data["AudioBackend"] = self.audio.backend

        for f in self._filters:
            if f in message.data:
                if isinstance(message.data[f], basestring):
                    for backend in self.backends:
                        for m in self._modifiers:
                            message.data[f] = message.data[f] \
                                .replace(m + " " + backend, "")
                        message.data[f] = message.data[f] \
                            .replace(backend, "")
                elif isinstance(message.data[f], list):
                    for idx, t in enumerate(message.data[f]):
                        for m in self._modifiers:
                            message.data[f][idx] = t \
                                .replace(m + " " + backend, "")
                        message.data[f][idx] = t.replace(backend,
                                                         "")
        return message

    def play(self, tracks):
        self.stop()
        if self.settings["use_audio_service"]:
            self.audio.play(tracks)
        else:
            if not isinstance(tracks, list):
                tracks = [tracks]
            if ".wav" in tracks[0]:
                self.process = play_wav(tracks[0])
            else:
                self.process = play_mp3(tracks[0])

    def register_intent(self, intent_parser, handler, need_self=False):
        skill_id = to_letters(self.skill_id)
        if isinstance(intent_parser, Intent):
            intent_parser.optional += [(skill_id + "AudioBackend", None)]

        elif isinstance(intent_parser, IntentBuilder):
            intent_parser.optionally("AudioBackend")

        name = intent_parser.name or handler.__name__
        self.audio.register_backend_update(skill_id + name)

        def adapt_handler(message, dummy=None):
            message = self._clean_message(message)
            LOG.info(get_handler_name(handler))
            handler(message)

        super(AudioSkill, self).register_intent(intent_parser,
                                                adapt_handler)

    def register_intent_file(self, intent_file, handler, need_self=False):

        def padatious_handler(message, dummy=None):
            message = self._clean_message(message)
            LOG.info(get_handler_name(handler))
            handler(message)

        super(AudioSkill, self).register_intent_file(intent_file,
                                                     padatious_handler)

    def stop(self):
        if self.settings["use_audio_service"]:
            if self.audio.is_playing:
                self.audio.stop()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()

    def shutdown(self):
        super(AudioSkill, self).shutdown()
        self.stop()
        self.audio.shutdown()


class AudioFallback(AudioSkill, FallbackSkill):
    """
    FallbackSkill that automatically initializes audio service and
    selects audio backend
    """

    def __init__(self, name=None, emitter=None):
        super(AudioFallback, self).__init__(name, emitter)
