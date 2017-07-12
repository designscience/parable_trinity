import os
import kivy
import logging
import sys
import vlc
import time
import threading

import paraplayer
import parascreens

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout

os.environ['KIVY_IMAGE'] = 'pil,sdl2'
kivy.require('1.9.1')
__version__ = "1.0.0"

MRL = '/Users/Stu/Documents/Compression/Keith/Keith Emerson Tribute rev1.mp3'


class AppLayout(FloatLayout):
    @staticmethod
    def hello():
        return 'hi there'


class TrinityApp(App):
    def __init__(self):
        App.__init__(self)
        self.ui = AppLayout(size=(1280, 720))
        self.home_screen = None
        # self.player = paraplayer.ParaPlayer()
        print('VLC version: ' + str(vlc.libvlc_get_version()))

    def build(self):
        """ Instantiates UI widgets and returns the root widget """
        # self.player.set_media(MRL, 1.5)
        # self.player.set_finish_callback(self.on_completion)

        # self.player.loop(12.0, 14.0, False, self.on_loop)
        # self.player.play()
        # time.sleep(4)
        # self.player.kill()
        # self.player.join(5)
        # exit()

        # Render the home screen
        self.home_screen = parascreens.HomeScreen(self)
        self.ui.clear_widgets()
        self.ui.add_widget(self.home_screen)
        return self.ui

    def cleanup(self):
        """Clean up threads at program exit"""
        # self.player.kill()
        # self.player.join(5)
        sys.exit(0)

    def on_completion(self, media_path, time_sig):
        print("On Completion called with time signature " + str(time_sig) + " for media " + media_path)

    def on_loop(self, media_path, time_sig):
        print("On Loop called with time signature " + str(time_sig) + " for media " + media_path)


if __name__ == '__main__':
    TrinityApp().run()
