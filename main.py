import kivy
import logging
import sys
import vlc
import time
import threading

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout

kivy.require('1.9.1')
__version__ = "1.0.0"

MRL = '/Users/Stu/Documents/Compression/Keith/Keith Emerson Tribute rev1.mp3'


class AppLayout(FloatLayout):
    def hello(self, *args):
        return 'hi there'


class TrinityApp(App):
    def __init__(self):
        App.__init__(self)
        self.ui = AppLayout()
        self.Instance = vlc.Instance()
        self.player = self.Instance.media_player_new()
        print('VLC version: ' + str(vlc.libvlc_get_version()))

    def build(self):
        """ Instantiates UI widgets and returns the root widget """
        self.ui = AppLayout(size=(1280, 720))
        self.test_run()
        return self.ui

    def test_run(self):
        media = self.Instance.media_new(MRL)
        self.player.set_media(media)
        self.player.set_position(.2)
        self.player.play()
        time.sleep(3)
        print(str(self.player.get_time()))
        # self.player.stop()
        self.player.set_position(.6)
        # self.player.play()
        print(str(self.player.get_state()))
        time.sleep(1)
        print(str(self.player.get_time()))
        time.sleep(7)
        self.player.stop()
        print(str(self.player.is_seekable()))


class HomeScreen(FloatLayout):
    """ Idle state complete home screen widgets """
    def __init__(self):
        FloatLayout.__init__(self)


if __name__ == '__main__':
    TrinityApp().run()
