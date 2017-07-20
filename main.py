import os
import kivy
# import logging
import sys
import vlc
import time
import threading
# import Queue
import multiprocessing

# import paraplayer
import parascreens
import parclasses
import parthreads


from kivy.app import App
# from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.clock import Clock

os.environ['KIVY_IMAGE'] = 'pil,sdl2'
kivy.require('1.10.0')
__version__ = "1.0.0"

MRL = '/Users/Stu/Documents/Compression/Keith/Keith Emerson Tribute rev1.mp3'

class TrinityApp(App):
    def __init__(self):
        App.__init__(self)
        self.title = 'Parable Trinity'
        self.icon = 'images/svlogo_sm.ico'

        # Settings
        self.num_channels = 18  # number of output channels
        self.num_buttons = 35  # number of possible sequence buttons

        self.countdown = 0

        self.ui = parascreens.UserInterface()
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

        # temp sequence rate scaling factor (playback rate)
        self.scaleFactor = 1.10

        # create the temp sequence object - used to try out sequences
        self.seq = parclasses.ControlList()
        self.seq.name = "Temp Sequence"

        # Create the threaded sequence handler (ControlBank)
        self.cb = parthreads.ControlBank("/Users/Stu/Sequences")

        # Uninitiated objects
        self.lights = []  # array of ChannelLight objects for GUI display
        self.ttemp = None  # Sequence thread
        self.tmain = None  # Sequence thread
        self.vp1 = None  # ValvePort output
        self.vp2 = None  # ValvePort output
        self.vpb = parclasses.ValvePortBank()

    def build(self):
        """ Instantiates UI widgets, loads machinery, and returns the root widget """
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

        # Render lights
        self.home_screen.clear()
        for i in range(0, self.num_channels):
            light = parascreens.ChannelLight(i)
            self.home_screen.ids['light_panel'].add_widget(light)
            self.lights.append(light)

        # create ValvePort (output) objects
        self.vp1 = parclasses.ValvePort_Kivy(22, 6, self.lights)
        self.vp1.setMap(self.straight_map)

        # Other output objects
        self.vp2 = parclasses.ValvePort_Parallel(24, 6)
        self.vp2.setMap(self.straight_map)

        # add output objects to an output bank
        self.vpb.addPort(self.vp1)
        self.vpb.addPort(self.vp2)
        self.vpb.execute()   # show the lights

        # Create initial temp sequence
        li = parclasses.randy(64, 22, 1, 2)
        self.seq.append(li)
        self.seq.sortEvents()

        # Create thread objects
        self.ttemp = threading.Thread(target=self.seq, args=(self.temp_ev_queue, self.temp_out_queue))
        self.tmain = threading.Thread(target=self.cb, args=(self.ev_queue, self.out_queue, self.in_queue))

        # TODO: add a Kivy Clock schedule
        # self.myTimer = timer.Timer(self.components.OutputCanvas1, -1) # create a timer
        # self.myTimer.Start(5)

        # Animate lights then douse them
        self.bulb()
        return self.ui

    def bulb(self):
        """Purely for testing and panache... shows alll lights then extinguishes them"""
        for i in range(0, self.num_channels):
            self.lights[i].on()
        self.countdown = 0
        Clock.schedule_interval(self.startup, 0.03)

    def startup(self, dt):
        """Initiates actions once after the main program loop has been entered"""
        # Douse the lights
        if self.countdown < self.num_channels:
            self.lights[self.countdown].off()
            self.countdown += 1
        return self.countdown < self.num_channels

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
