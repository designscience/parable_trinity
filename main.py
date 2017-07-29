import os
import kivy
# import logging
# import sys
# import vlc
import time
import threading
# import Queue
import multiprocessing

import paraplayer
import parascreens
import parclasses
import parthreads
import showlist

from kivy.clock import Clock, mainthread
from kivy.app import App
# from kivy.uix.floatlayout import FloatLayout
# from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton

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
        self.num_buttons = 64  # number of possible sequence buttons

        self.countdown = 0

        self.ui = parascreens.UserInterface()
        self.home_screen = None

        self.player = paraplayer.ParaPlayer()

        # Sequence maintenance
        self.sequences = [""] * self.num_buttons  # Sequence name
        self.trigger_times = [0.0] * self.num_buttons  # Sequence name
        # self.remote_addr = '192.168.1.115'
        self.remote_addr = '192.32.12.2'
        self.seq_directory = "/Users/Stu/Documents/Compression/Sequences/"
        # self.show_seq_directory = "/Users/Stu/Documents/Compression/Sequences/Show/"
        self.music_directory = "/Users/Stu/Documents/Compression/Music/"
        self.show_list_file = "/Users/Stu/Documents/Compression/compression.show.xml"

        # Threading queues
        self.out_queue = multiprocessing.Queue()  # send commands to main thread
        self.in_queue = multiprocessing.Queue()  # get responses from main thread
        self.ev_queue = multiprocessing.Queue()  # get event records from main thread
        self.temp_out_queue = multiprocessing.Queue()  # send commands to temp seq thread
        self.temp_ev_queue = multiprocessing.Queue()  # get event records from main thread

        # create a channel map for the actual cannons
        self.straight_map = parclasses.ChannelMap(24)  # for straight import mapping
        for i in range(0, 24):
            self.straight_map.addMapping(i + 1, i + 1)
        self.straight_map.addMapping(1, 1)
        self.straight_map.addMapping(23, 0)
        self.straight_map.addMapping(24, 0)

        self.effect_map = parclasses.ChannelMap(24)  # for effects channels
        self.effect_map.addMapping(1,  2)
        self.effect_map.addMapping(2,  5)
        self.effect_map.addMapping(3,  8)
        self.effect_map.addMapping(4, 11)
        self.effect_map.addMapping(5, 14)
        self.effect_map.addMapping(6, 17)
        self.effect_map.addMapping(7,  1)
        self.effect_map.addMapping(8,  4)
        self.effect_map.addMapping(9,  7)
        self.effect_map.addMapping(10, 10)
        self.effect_map.addMapping(11, 13)
        self.effect_map.addMapping(12, 16)
        self.effect_map.addMapping(13,  3)
        self.effect_map.addMapping(14,  6)
        self.effect_map.addMapping(15,  9)
        self.effect_map.addMapping(16, 12)
        self.effect_map.addMapping(17, 15)
        self.effect_map.addMapping(18, 18)
        self.effect_map.addMapping(19, 19)
        self.effect_map.addMapping(20, 20)
        self.effect_map.addMapping(21, 21)
        self.effect_map.addMapping(22, 22)
        self.effect_map.addMapping(23,  0)
        self.effect_map.addMapping(24,  0)

        self.graybox_map = parclasses.ChannelMap(24)  # for effects channels
        self.graybox_map.addMapping(1,  2)
        self.graybox_map.addMapping(2,  5)
        self.graybox_map.addMapping(3,  8)
        self.graybox_map.addMapping(4, 11)
        self.graybox_map.addMapping(5, 14)
        self.graybox_map.addMapping(6, 17)
        self.graybox_map.addMapping(7,  1)
        self.graybox_map.addMapping(8,  4)
        self.graybox_map.addMapping(9,  7)
        self.graybox_map.addMapping(10, 10)
        self.graybox_map.addMapping(11, 13)
        self.graybox_map.addMapping(12, 16)
        self.graybox_map.addMapping(13,  3)
        self.graybox_map.addMapping(14,  6)
        self.graybox_map.addMapping(15,  9)
        self.graybox_map.addMapping(16, 12)
        self.graybox_map.addMapping(17, 15)
        self.graybox_map.addMapping(18, 18)
        self.graybox_map.addMapping(19, 0)
        self.graybox_map.addMapping(20, 0)
        self.graybox_map.addMapping(21, 0)
        self.graybox_map.addMapping(22, 0)
        self.graybox_map.addMapping(23,  0)
        self.graybox_map.addMapping(24,  0)

        # temp sequence rate scaling factor (playback rate)
        self.scaleFactor = 1.10

        # create the temp sequence object - used to try out sequences
        self.seq = parclasses.ControlList()
        self.seq.name = "Temp Sequence"

        # Create the threaded sequence handler (ControlBank)
        self.cb = parthreads.ControlBank(self.seq_directory)

        # Uninitiated objects
        self.lights = []  # array of ChannelLight objects for GUI display
        self.ttemp = None  # Sequence thread
        self.tmain = None  # Sequence thread
        self.vp1 = None  # ValvePort output
        self.vp2 = None  # ValvePort output
        self.vp3 = None
        self.vpb = parclasses.ValvePortBank()
        self.auto_pilot = False  # in case we add auto-pilot at some point

        self.sequences = []  # list of SequenceButton objects (prev seq name)
        self.sequence_index = 0  # index of loaded sequences (buttons)
        # NOTE: trigger_times are stored in the SequenceButton object

        # Show list is used to play back music and sequences together
        self.showlist = showlist.ShowList(self.player, self.out_queue, self.show_list_file)
        self.show_events = []

        self.in_handler = False  # prevent too much recursion into loop handler

    def build(self):
        """ Instantiates UI widgets, loads machinery, and returns the root widget """
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
        self.vp1.setMap(self.effect_map)

        # Other output objects
        # TODO: address and port from command line arguments or from config file
        self.vp2 = parclasses.ValvePort_Ethernet(24, 6, self.remote_addr, 4444, False)
        self.vp2.setMap(self.graybox_map)

        # Recorder object
        self.vp3 = parclasses.ValvePort_Recorder(24, 6, self.music_directory, self.on_kill_press)
        self.vp3.setMap(self.straight_map)

        # add output objects to an output bank
        self.vpb.addPort(self.vp3)
        self.vpb.addPort(self.vp1)
        self.vpb.addPort(self.vp2)
        self.vpb.execute()   # show the lights

        # Create initial temp sequence
        li = parclasses.randy(140, 18, 1, 2)
        self.seq.append(li)
        self.seq.sortEvents()

        # Create thread objects
        self.ttemp = threading.Thread(target=self.seq, args=(self.temp_ev_queue, self.temp_out_queue))
        self.tmain = threading.Thread(target=self.cb, args=(self.ev_queue, self.out_queue, self.in_queue))

        # Animate lights then douse them
        self.bulb()

        # start and initialize main thread
        self.tmain.start()
        self.out_queue.put("loadbank|")

        # Load show file
        self.load_show(self.show_list_file)

        # Initiate thread handler
        print('Starting Kivy loop handler')
        Clock.schedule_once(self.loop_handler, 3)

        return self.ui

    def load_show(self, show_file_path=None):
        """Load a show file into the ShowList object"""
        lock = threading.Lock()
        lock.acquire()
        self.showlist.load(show_file_path)
        # display the show items
        for event in self.showlist.events:
            new_event = parascreens.ShowListItem(self, len(self.show_events), event.type, event.source)
            self.show_events.append(new_event)
            self.home_screen.ids.show_list.add_widget(new_event)
        lock.release()

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

    def loop_handler(self, dt=None):
        """Once this is called it will run each frame"""
        # lock = threading.Lock()
        if not self.in_handler:
            self.in_handler = True
            while self.ev_queue.empty() is False:
                # lock.acquire()
                ev = self.ev_queue.get()
                self.vpb.setEventExec(ev)
                # lock.release()

            while self.temp_ev_queue.empty() is False:
                # lock.acquire()
                ev = self.temp_ev_queue.get()
                self.vpb.setEventExec(ev)
                # lock.release()

            while self.in_queue.empty() is False:
                # lock.acquire()
                self.process_thread_command(self.in_queue.get())
                # lock.release()

            self.in_handler = False
        Clock.schedule_once(self.loop_handler, 0)  # call this on next frame

    def process_thread_command(self, cmdstr):
        """ process incoming commands from the main thread """
        # print(">>> " + cmdstr)
        cmd = cmdstr.split("|")

        # kill - kill the cannons
        if cmd[0] == "kill":
            self.vpb.reset()
            # running - color button to indicate running status
        elif cmd[0] == "started":
            for button in self.sequences:
                if button.sequence_name == cmd[1]:
                    button.show_running()
                    # self.components[btn].backgroundColor = (255, 0, 0, 255)
                    # self.components[btn].foregroundColor = (255, 255, 255, 255)
                    break
            # if (self.auto_pilot == True):
            #     self.auto_pilot_triggered = True;  # don't play another seq until done

        # stopped - color button to indicate stopped status
        elif cmd[0] == "stopped":
            for button in self.sequences:
                if button.sequence_name == cmd[1]:
                    button.show_stopped()
                    break
            # if self.auto_pilot is True:
            #     self.arm_auto_pilot();  # sequence done, start another one
        # clearbank - hide sequence buttons
        elif cmd[0] == "clearbank":
            for button in self.sequences:
                self.sequences.remove(button)
                del button
            self.home_screen.ids.sequence_panel.clear_widgets()
            self.sequences = []
            self.sequence_index = 0  # TODO: is sequence_index still needed
        # newseq - add a new sequence
        elif cmd[0] == "newseq":
            if self.sequence_index < self.num_buttons:
                new_button = parascreens.SequenceButton(cmd[1], self)
                self.sequences.append(new_button)
                self.home_screen.ids['sequence_panel'].add_widget(new_button)
                self.sequence_index += 1  # TODO: is sequence_index needed any more?
        # beat- toggle beat light
        elif cmd[0] == "beat":  # toggle the state of the beat light
            # TODO: create a beat light element and call toggle()
            # self.components.ImageButton1.visible = \
            #     not self.components.ImageButton1.visible and \
            #     self.components.chkUseBeat.checked
            pass
        # beaton - turn on beat light
        elif cmd[0] == "beaton":
            if self.home_screen.ids.use_beat.state == 'down':
                self.home_screen.ids.beat_light.opacity = 1.0
            else:
                self.home_screen.ids.beat_light.opacity = 0.0
        # beatoff - turn off beat light
        elif cmd[0] == "beatoff":
            self.home_screen.ids.beat_light.opacity = 0.0
        # exception - report exception
        elif cmd[0] == "exception":
            self.title = "Exception: " + cmd[1]
        elif cmd[0] == "message":
            self.title = str(cmd[1])

    def seq_btn_down(self, button: parascreens.SequenceButton):
        """ This is called on the down click of all sequence buttons.
            it toggles the sequence state (toggle handled in ControlBank) """
        if self.auto_pilot is False:
            # print("toggle|" + self.sequences[event.target.id])
            self.out_queue.put("toggle|" + button.sequence_name)
            button.trigger_time = time.time()

    def seq_btn_up(self, button: parascreens.SequenceButton):
        """ Depending on how long the button was pressed, either stop the sequence or does nothing """
        if self.auto_pilot is False:
            if time.time() - button.trigger_time > 0.2:
                # print("stop|" + self.sequences[event.target.id])
                self.out_queue.put("stop|" + button.sequence_name)

    def fire_channel(self, channel_number):
        """Takes a channel numnber and fires that channel. NO OFF! Must use Kill"""
        print('Firing channel {} manually'.format(channel_number))
        self.vp2.setChannelExec(int(channel_number), 1)

    def on_use_beat(self, toggle: ToggleButton):
        """Depending on the state of the button, use the tap beat or not"""
        if toggle.state == 'down':
            self.out_queue.put("usebeat|yes")
        else:
            self.out_queue.put("usebeat|no")

    def on_tap_press(self):
        """ process a tap beat to keep time with music """
        self.out_queue.put("tap|" + str(time.time()))
        if self.home_screen.ids.use_beat.state == 'normal':
            self.home_screen.ids.use_beat.state = 'down'
            self.out_queue.put("usebeat|yes")

    def on_kill_press(self):
        """terminate sequences with extreme prejudice"""
        self.out_queue.put("stop|")
        self.home_screen.ids.use_beat.state = 'normal'
        self.out_queue.put("usebeat|no")
        self.vpb.reset()
        self.auto_pilot = False
        if self.tmain.isAlive():
            self.title = "Thread is alive"
        else:
            self.title = "Threads dead - attempting restart"
            self.tmain = threading.Thread(target=self.cb, args=(self.ev_queue, self.out_queue, self.in_queue))
            self.tmain.start()
            self.out_queue.put("stop|")

    def on_align_press(self):
        """ realign the start_time for the tap beat"""
        self.out_queue.put("align|" + str(time.time()))


    def on_load_bank(self, bank_name):
        """Loads a bank at the path described by the sequence folder plus this bank name"""
        if bank_name != '':
            if self.seq.running() is False:
                self.out_queue.put("clearbank")
                self.out_queue.put("loadbank|" + bank_name)

                # Read the tempo from a file
                tempofn = "" + self.seq_directory + bank_name + "/tempo.txt"
                self.title = "{} not found".format(tempofn)
                try:
                    with open(tempofn, "r") as tempofile:
                        if tempofile is not None:
                            tempo = tempofile.readline()
                            self.title = tempo
                            self.out_queue.put("settempo|" + tempo)
                            self.out_queue.put("usebeat|yes")
                except FileNotFoundError:
                    self.title = 'tempo.txt not found'
            else:
                self.temp_out_queue.put("stop")
                print("Sequence was running. Please try again")

    def play_temp_seq(self):
        """Plays the temp sequence that is initialized with a randy sequence"""
        if self.ttemp.isAlive() is True:
            self.temp_out_queue.put("stop")
        else:
            # self.seq.scaleToBeat(parclasses.TimeCode(15))
            while self.temp_out_queue.empty() is False:
                self.temp_out_queue.get()

            # destroy the temp thread and recreate
            # "you can't stop a thread object and restart it. Don't try"
            del self.ttemp
            self.ttemp = threading.Thread(target=self.seq, args=(self.temp_ev_queue,self.temp_out_queue))
            self.ttemp.start()

    def stop_temp_seq(self):
        """Stop playback of the temp sequence"""
        if self.ttemp.isAlive() is True:
            self.temp_out_queue.put("stop")

    def start_the_show(self):
        if self.showlist:
            self.showlist.start()

    def stop_the_music(self):
        if self.player:
            print("playback stopped at {}".format(self.player.get_time()))
            self.player.stop()

    def on_stop(self):
        """Kivy function - stopping the application"""
        print("Exiting program")
        # Kill the media player
        self.player.kill()
        if self.player.is_alive():
            self.player.join(2)
        # command threads to stop then wait
        if self.tmain.isAlive():
            self.out_queue.put("die")
            self.tmain.join()  # wait for thread to finish
        if self.ttemp.isAlive():
            self.temp_out_queue.put("die")
            self.ttemp.join()  # wait for thread to finish

    def initiate_recording(self, show_index):
        """Sets up the recorder with a media file"""
        event = self.showlist.get_event(show_index)
        if event and event.type == 'music':
            self.vp3.set_media(event.source, event.duration)
        self.home_screen.show_recorder_controls()

    def on_show_control_button(self, button_text, button_state='normal'):
        """Handle show playback button clicks"""
        if button_text == 'prev':
            pass
        elif button_text == 'PLAY':
            if self.showlist:
                if button_state == 'down':
                    self.showlist.start()
                else:
                    self.showlist.stop()
        elif button_text == 'pause':
            if self.showlist:
                self.showlist.stop()
        elif button_text == 'next':
            if self.showlist:
                self.showlist.play_next()

    def on_recorder_button(self, button_text):
        """To avoid multiple button handlers, uses button label"""
        if button_text == 'record':
            self.vp3.record()
        elif button_text == 'accept':
            self.vp3.accept()
        elif button_text == 'discard':
            self.vp3.reject()
        elif button_text == 'commit':
            self.vp3.accept()
            self.vp3.commit()
            self.home_screen.hide_recorder_controls()


    # ~~~~~~~~~~~~~~~~~ these functions are written for the pyplayer class ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    def on_loop(self, media_path, time_sig):
        print("On Loop called with time signature " + str(time_sig) + " for media " + media_path)


if __name__ == '__main__':
    TrinityApp().run()
