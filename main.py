import os
import kivy
# import logging
import sys
import vlc
# import time
# import threading
# import Queue
import multiprocessing

# import paraplayer
import parascreens
import parclasses


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

        # Settings
        self.num_channels = 18  # number of output channels
        self.num_buttons = 35  # number of possible sequence buttons

        self.ui = AppLayout(size=(1280, 720))
        self.home_screen = None
        # self.player = paraplayer.ParaPlayer()

        # Sequence maintenance
        self.sequences = [""] * self.num_buttons  # Sequence name
        self.trigger_times = [0.0] * self.num_buttons  # Sequence name
        self.seq_directory = "C:\\sequences\\"

        # Threading queues
        self.out_queue = multiprocessing.Queue()  # send commands to main thread
        self.in_queue = multiprocessing.Queue()  # get responses from main thread
        self.ev_queue = multiprocessing.Queue()  # get event records from main thread
        self.temp_out_queue = multiprocessing.Queue()  # send commands to temp seq thread
        self.temp_ev_queue = multiprocessing.Queue()  # get event records from main thread

        # create a channel map for the actual cannons
        self.straight_map = parclasses.ChannelMap(24)  # for straight import mapping
        for i in range(1, 22):
            self.straight_map.addMapping(i, i)
        self.straight_map.addMapping(23, 0)
        self.straight_map.addMapping(24, 0)

        # create ValvePort (output) objects
        # self.vp1 = parclasses.ValvePort_GUI(22, 6, self.components.OutputCanvas1)
        # self.vp1.setMap(self.straight_map)

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
        # self.ui.add_widget(self.home_screen)

        # Render lights
        for i in range(0, self.num_channels):
            light = parascreens.ChannelLight('light{0}'.format(i), i * 100, 100)
            self.ui.add_widget(light)

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
