#!/usr/bin/python

from PythonCard import model, timer, dialog
import parclasses
import parthreads
import sequenceimport
import random
import time
import threading
import Queue
import wx
from os import path
import winsound
import pygame
import vlc
# import logging  # save to a log

"""
__version__ = "$Revision: 1.3 $"
__date__ = "$Date: 2016/06/22 $"
"""

""" ******************************************************************
This is the main file for the ParableW (Parable running on Windows)
program.  Parable is the sequencing program developed for the Shiva Vista
project but can be applied to other sequencing applications as well.

The parablew class encapsulates the ParableW program... its objects, its
GUI controls and the event handlers for them, the program initialization
and the

1.03 - corrected mapping inconsistencies between GUI display and electrical
channels.  Added updated BTIC class that ignores first few taps to reduce
human error.

1.04 - Moved lights to 2011 configuration. Included straight bank mapping.
Added joystick support for foot switch (needs testing).

1.10 - Replaced BTIC class with Beatnik class

1.11 - Wrapped BeatRecorder() (tap handler) in exception block. Force loaded
sequences to stop().

1.12a - Adds improved accuracy of sequence playback. Ensures sequence are scaled
to whole number of beats. Also, tap time is sent with tap beat for better accuracy
when program is busy.  Still uses picle for saving sequence objects, but with greatly
improved ControlList.useCurrent() implementation that forces scale against ref_times
insteade of comprimising reference times.5/26/2012

1.14 - Sequences now saved as .seqx files (XML instead of pickle)

1.15 - Perpetual sync added.  Sequences re-sync with beat at the start of each
sequence loop.  

1.15a - bug in win2k requires str() to detect file path. 

1.16 - adding tempo preload

1.2 - adding ethernet control for Raspberry Pi switch box, randomizing feature, channel bank features

1.3 - adding back ValvePort_Object (fom 2010 Ein Hammer code) to record for later playback

***** Issue Notes  *****
* kill (abort button) checks main thread and restarts if dead.  A hack.
* consider sending time in Align, as is done with tap command
* still some small error in playback versus tap period, but better
* all sequences must be recreated due to use of pickle and changes in parclasses
* program hangs occasionally with doing graphic import of images
* auto pilot doesn't respect looping sequences (they keep looping)

****************************************************************** """ 

__version__ = "1.16"

class parablew(model.Background):
    def __init__(self, aParent, aBgRsrc):
        model.Background.__init__(self, aParent, aBgRsrc)

        # This doesn't seem to bind the event
        # panel = wx.Panel(self)
        # panel.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.title = "Parable 2016 - v" + __version__

        # self.components.chkBeeps.visible = True

        # Initialize the sound mixer
        pygame.mixer.init()

        # foot switch current state
        self.foot = False       # set to True when switch is closed

        # button maintenance
        self.num_buttons = 35  # number of possibel sequence buttons
        self.top_button = 0    # 0-based button (name) index  "SEQ0"

        self.auto_pilot = False     # run in auto pilot mode
        self.auto_pilot_rate = 50   # how frequently to play sequences 1-100
        self.auto_pilot_triggered = False   # currently playing a sequence
        self.auto_pilot_next = time.time()  # next time to trigger

        # sequence maintenance
        self.sequences = [""] * self.num_buttons  # Sequence name
        self.trigger_times = [0.0] * self.num_buttons  # Sequence name
        self.seq_directory = "C:\\sequences\\"
        self.compose_file = 'Compose\\WORKING.seqx'
        self.music_directory = "C:\\Users\\Stu\\Documents\\Burning Man\\Shiva Vista\\2016\\"
        self.featured_music = "Keith_Emerson_Tribute_rev1.ogg"

        # Media object for music playback, depends on VLC player
        self.media = vlc.MediaPlayer(self.music_directory + self.featured_music)
        self.media_time = 0

        # Threading queues
        self.out_queue = Queue.Queue() # send commands to main thread
        self.in_queue = Queue.Queue()  # get responses from main thread
        self.ev_queue = Queue.Queue()  # get event records from main thread
        self.temp_out_queue = Queue.Queue() # send commands to temp seq thread
        self.temp_ev_queue = Queue.Queue()  # get event records from main thread

        # create a channel map for the actual cannons
        self.effect_map = parclasses.ChannelMap(24)  # for effects channels
        self.gui_map = parclasses.ChannelMap(24)  # for GUI 'lights'
        self.straight_map = parclasses.ChannelMap(24)  # for straight import mapping
        self.import_map = parclasses.ChannelMap(24)  # for alternative graphic import mapping (else use straight map)
        self.controlbox_map = parclasses.ChannelMap(18)  # modified effects map

        self.effect_map.addMapping(1,  2)
        self.effect_map.addMapping(2,  5)
        self.effect_map.addMapping(3,  8)
        self.effect_map.addMapping(4, 14) # was 11
        self.effect_map.addMapping(5, 17) # was 14
        self.effect_map.addMapping(6, 20) # was 17
        self.effect_map.addMapping(7,  1)
        self.effect_map.addMapping(8,  4)
        self.effect_map.addMapping(9,  7)
        self.effect_map.addMapping(10, 13) # was 10
        self.effect_map.addMapping(11, 16) # was 13
        self.effect_map.addMapping(12, 19) # was 16
        self.effect_map.addMapping(13,  3)
        self.effect_map.addMapping(14,  6)
        self.effect_map.addMapping(15,  9)
        self.effect_map.addMapping(16, 15) # was 12
        self.effect_map.addMapping(17, 18) # was 15
        self.effect_map.addMapping(18, 21) # was 18
        self.effect_map.addMapping(19, 10) # was 19
        self.effect_map.addMapping(20, 11) # was 20
        self.effect_map.addMapping(21, 23) # was 21
        self.effect_map.addMapping(22, 22) # was 22
        self.effect_map.addMapping(23,  0)
        self.effect_map.addMapping(24,  0)

        # map that works for GUI display "lights"
        self.gui_map.addMapping(1,  2)
        self.gui_map.addMapping(2,  5)
        self.gui_map.addMapping(3,  8)
        self.gui_map.addMapping(4, 11) 
        self.gui_map.addMapping(5, 14) 
        self.gui_map.addMapping(6, 17) 
        self.gui_map.addMapping(7,  1)
        self.gui_map.addMapping(8,  4)
        self.gui_map.addMapping(9,  7)
        self.gui_map.addMapping(10, 10)
        self.gui_map.addMapping(11, 13)
        self.gui_map.addMapping(12, 16)
        self.gui_map.addMapping(13,  3)
        self.gui_map.addMapping(14,  6)
        self.gui_map.addMapping(15,  9)
        self.gui_map.addMapping(16, 12) 
        self.gui_map.addMapping(17, 15) 
        self.gui_map.addMapping(18, 18) 
        self.gui_map.addMapping(19, 19) 
        self.gui_map.addMapping(20, 20) 
        self.gui_map.addMapping(21, 21) 
        self.gui_map.addMapping(22, 22) 
        self.gui_map.addMapping(23,  0)
        self.gui_map.addMapping(24,  0)
                
        # map for importing direct to channels
        self.straight_map.addMapping(1, 1)
        self.straight_map.addMapping(2,  2)
        self.straight_map.addMapping(3,  3)
        self.straight_map.addMapping(4, 4) 
        self.straight_map.addMapping(5, 5) 
        self.straight_map.addMapping(6, 6) 
        self.straight_map.addMapping(7,  7)
        self.straight_map.addMapping(8,  8)
        self.straight_map.addMapping(9,  9)
        self.straight_map.addMapping(10, 10)
        self.straight_map.addMapping(11, 11)
        self.straight_map.addMapping(12, 12)
        self.straight_map.addMapping(13,  13)
        self.straight_map.addMapping(14,  14)
        self.straight_map.addMapping(15,  15)
        self.straight_map.addMapping(16, 16) 
        self.straight_map.addMapping(17, 17) 
        self.straight_map.addMapping(18, 18) 
        self.straight_map.addMapping(19, 19) 
        self.straight_map.addMapping(20, 20) 
        self.straight_map.addMapping(21, 21) 
        self.straight_map.addMapping(22, 22) 
        self.straight_map.addMapping(23,  0)
        self.straight_map.addMapping(24,  0)

        # map for importing direct to channels
        self.controlbox_map.addMapping(1, 1)
        self.controlbox_map.addMapping(2, 2)
        self.controlbox_map.addMapping(3, 5)
        self.controlbox_map.addMapping(4, 8)
        self.controlbox_map.addMapping(5, 1)
        self.controlbox_map.addMapping(6, 14)
        self.controlbox_map.addMapping(7, 17)
        self.controlbox_map.addMapping(8, 11)
        self.controlbox_map.addMapping(9, 7)
        self.controlbox_map.addMapping(10, 4)
        self.controlbox_map.addMapping(11, 10)
        self.controlbox_map.addMapping(12, 13)
        self.controlbox_map.addMapping(13, 16)
        self.controlbox_map.addMapping(14, 3)
        self.controlbox_map.addMapping(15, 6)
        self.controlbox_map.addMapping(16, 9)
        self.controlbox_map.addMapping(17, 12)
        self.controlbox_map.addMapping(18, 15)
        self.controlbox_map.addMapping(19, 19)
        self.controlbox_map.addMapping(20, 20)
        self.controlbox_map.addMapping(21, 21)
        self.controlbox_map.addMapping(22, 22)
        self.controlbox_map.addMapping(23,  0)
        self.controlbox_map.addMapping(24,  0)

        # map for alternative import mapping
        # ironically, this provides straight column-to-channel mapping
        # using straight_map (or no map) you get 6 centers, 6 lefts, 6 rights, 4 talons
        # interesting note: this is the inverse of gui_map
        self.import_map.addMapping(2,  1)
        self.import_map.addMapping(5,  2)
        self.import_map.addMapping(8,  3)
        self.import_map.addMapping(11, 4) 
        self.import_map.addMapping(14, 5) 
        self.import_map.addMapping(17, 6) 
        self.import_map.addMapping(1,  7)
        self.import_map.addMapping(4,  8)
        self.import_map.addMapping(7,  9)
        self.import_map.addMapping(10, 10)
        self.import_map.addMapping(13, 11)
        self.import_map.addMapping(16, 12)
        self.import_map.addMapping(3,  13)
        self.import_map.addMapping(6,  14)
        self.import_map.addMapping(9,  15)
        self.import_map.addMapping(12, 16) 
        self.import_map.addMapping(15, 17) 
        self.import_map.addMapping(18, 18) 
        self.import_map.addMapping(19, 19) 
        self.import_map.addMapping(20, 20) 
        self.import_map.addMapping(21, 21) 
        self.import_map.addMapping(22, 22) 
        self.import_map.addMapping(23,  0)
        self.import_map.addMapping(24,  0)

        # create the temp sequence object - used to try out sequences
        self.seq = parclasses.ControlList()
        self.seq.name = "Temp Sequence"

        # create valveport (output) objects
        self.vp1 = parclasses.ValvePort_GUI(22, 6, self.components.OutputCanvas1)
        self.vp1.setMap(self.gui_map)

        # position sequencing "lights" on the screen
        for i in range(0, 6):
            ch = (i*3)  # 0-based channel index
            """            
            self.vp1.set_light(ch+1, (100 * i + 50, 20))
            self.vp1.set_light(ch+2, (100 * i + 25, 20))
            self.vp1.set_light(ch+3, (100 * i , 20))
            
            self.vp1.set_light(ch+1, (100 * i + 25, 50))
            self.vp1.set_light(ch+2, (100 * i + 25, 25))
            self.vp1.set_light(ch+3, (100 * i + 25, 0))
            """
            self.vp1.set_light(ch+1, ((100 * i), 25))
            self.vp1.set_light(ch+2, ((100 * i) + 20, 50))
            self.vp1.set_light(ch+3, ((100 * i) + 40, 25))
        
        self.vp1.set_light(19, (630, 35))
        self.vp1.set_light(20, (630, 8))
        self.vp1.set_light(21, (665, 8))
        self.vp1.set_light(22, (665, 35))

        # create screen buttons
        for i in range(self.num_buttons):
            self.components['SEQ' + str(i)] = {'type':'Button', 'name':'SEQ' + str(i), 'id':i, 'position':(20 +(152 * (i%5)), 150 + (40 * int(i/5))), 'size':(120, 30), 'label':'Sequence ' + str(i+1), 'command':'seqBtn' + str(i+1), 'visible':False}
            
        # Other output objects
        self.vp2 = parclasses.ValvePort_Parallel(24, 6)
        self.vp2.setMap(self.effect_map)

        # self.vp2 = parclasses.ValvePort_Ethernet(18, 6)
        # self.vp2.setMap(self.straight_map)
        # self.vp2.setMap(self.controlbox_map)

        # TODO: testing only!
        # for j in range(1,5):
        #     for i in range(1, 18):
        #         self.vp2.oneChannelExec(i)
        #         sleep(0.2)

        self.vp3 = parclasses.ValvePort_Beep() # not very good
        self.vp3.setMap(self.effect_map)
        self.vp3.mute = True

        # ValvePort_Object records performance to a file
        self.vp4 = parclasses.ValvePort_Object(24, 6, self.seq) # capture to file
        self.vp4.setMap(self.straight_map)

        # temp sequence rate scaling factor
        # self.scaleFactor = 1.0
        self.scaleFactor = 1.10

        # add output objects to an output bank
        self.vpb = parclasses.ValvePortBank()
        self.vpb.addPort(self.vp1)
        self.vpb.addPort(self.vp2)
        self.vpb.addPort(self.vp3)
        self.vpb.addPort(self.vp4)
        self.vpb.execute()   # show the lights

        # Create initial temp sequence
        for i in range(12):
            ch = i + 1
            # li = parclasses.spiral(10, 22, 3, 12, 3)
            # li = parclasses.beep(ch, 2, 2, 0, 0)
            li = parclasses.randy(64, 22, 1, 2)
            self.seq.append(li)
            
        self.seq.sortEvents()

        # Create the threaded sequence handler (ControlBank)
        self.cb = parthreads.ControlBank("C:\\sequences\\")

        # Create thread objects
        self.ttemp = threading.Thread(target=self.seq, args=(self.temp_ev_queue,self.temp_out_queue))
        self.tmain = threading.Thread(target=self.cb, args=(self.ev_queue,self.out_queue,self.in_queue))

        # Load bank folder list
        self.bank_index = 0
        self.banks = None
        if path.exists('banks.txt'):
            # Load bank paths from the file
            self.banks = []
            with open('banks.txt', 'r') as f:
                for eachLine in f:
                    if len(eachLine) > 2:
                        self.banks.append(eachLine.splitlines()[0])

            # check banks paths
            # TODO: check this above so partial banks can be loaded
            for bank in self.banks:
                if path.exists(path.join(self.seq_directory, bank)) is False:
                    print "Bank at path {0} not found. Banks not loaded.".format(path.join(self.seq_directory, bank))
                    self.banks = None

            if self.banks:
                print "{0} banks loaded from file".format(len(self.banks))
        else:
            print "banks.txt not found"

        """
        # create joystick object
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self.stick = pygame.joystick.Joystick(0)
            self.stick.init()
            print "Joystick detected with " + str(self.stick.get_numbuttons()) + " buttons"
        else:
            self.stick = None
            print "No joystick"
        """

    # When exiting the program, do some cleanup
    def __exit__(self, exc_type, exc_value, traceback):
        self.media.stop()
        pygame.mixer.quit()

    # key press handler (for when I figure out how to bind it
    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        print "Key pressed " + str(keycode)
        if keycode == wx.WXK_F1:
            self.on_pbTap_mouseDown(event)
        event.Skip()

    def on_initialize(self, event):
        """ initialize the UI components """
        self.components.slSeqRate.setRange(1, 100)
        self.components.slSeqRate.value = 50
        self.components.chkLoop.checked = False

        self.myTimer = timer.Timer(self.components.OutputCanvas1, -1) # create a timer
        self.myTimer.Start(5)

        self.components.btnHello.start_time = time.time()  # to establish the variable

        # bind key down event to handler DOES NOT WORK!!
        # self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        # start and initialize main thread
        self.tmain.start()
        # self.out_queue.put("loadbank|drumming up the heat")
        self.out_queue.put("loadbank|")

        """
        complist = self.findAllComponents()
        for comp in complist:
          print comp
          print " "
        self.components.__setitem__("parable01", "wxCheckBox")
        """

    def on_idle(self, event):
        while self.ev_queue.empty() is False:
            ev = self.ev_queue.get()
            self.vpb.setEventExec(ev)

        while self.temp_ev_queue.empty() is False:
            ev = self.temp_ev_queue.get()
            self.vpb.setEventExec(ev)

        while self.in_queue.empty() is False:
            self.processCommand(self.in_queue.get())


    def processCommand(self, cmdstr):
        """ process incoming commands from the main thread """
        # print ">>> " + cmdstr
        cmd = cmdstr.split("|")

        # kill - kill the cannons
        if cmd[0] == "kill":
            self.vpb.reset()
        # running - color button to indicate running status
        elif cmd[0] == "started":
            for i in range(self.num_buttons):
                if self.sequences[i] == cmd[1]:
                    btn = "SEQ" + str(i)
                    self.components[btn].backgroundColor = (255,0,0,255)
                    self.components[btn].foregroundColor = (255,255,255,255)
                    break
            if (self.auto_pilot == True):
                self.auto_pilot_triggered = True  # don't play another seq until done
            
        # stopped - color button to indicate stopped status
        elif cmd[0] == "stopped":
            for i in range(self.num_buttons):
                if self.sequences[i] == cmd[1]:
                    btn = "SEQ" + str(i)
                    self.components[btn].backgroundColor = (236, 233, 216, 255)
                    self.components[btn].foregroundColor = (0, 0, 0, 0)
                    break
            if (self.auto_pilot is True):
                self.arm_auto_pilot();  # sequence done, start another one
        # learbank - hide sequence buttons
        elif cmd[0] == "clearbank":
            for i in range(self.num_buttons):
                btn = "SEQ" + str(i)
                self.components[btn].visible = False
                self.top_button = 0
        # newseq - add a new sequence
        elif cmd[0] == "newseq":
            if self.top_button < self.num_buttons:
                btn = "SEQ" + str(self.top_button)
                self.sequences[self.top_button] = cmd[1]
                self.components[btn].label = cmd[1]
                self.components[btn].visible = True        
                self.top_button += 1
        # beat- toggle beat light
        elif cmd[0] == "beat":  # toggle the state of the beat light
            self.components.ImageButton1.visible = \
                not self.components.ImageButton1.visible and \
                self.components.chkUseBeat.checked
        # beaton - turn on beat light
        elif cmd[0] == "beaton":
            if self.components.chkUseBeat.checked:
                self.components.ImageButton1.visible = True
            else:
                self.components.ImageButton1.visible = False  # always off                    
        # beatoff - turn off beat light
        elif cmd[0] == "beatoff":
            self.components.ImageButton1.visible = False
        # exception - report exception
        elif cmd[0] == "exception":
            self.title = "Exception: " + cmd[1]
        # message - display message
        elif cmd[0] == "message":
            self.title = str(cmd[1])            

    def on_pbTap_mouseDown(self, event):
        """ process a tap beat to keep time with music """
        self.out_queue.put("tap|" + str(time.time()))  # new 7/2012 - sending tap time
        if self.components.chkUseBeat.checked is False:
            self.components.chkUseBeat.checked = True
            self.out_queue.put("usebeat|yes")
                    
    def on_align_mouseDown(self, event):
        """ realign the start_time for the tap beat """
        self.out_queue.put("align|" + str(time.time()))  

    def on_OutputCanvas1_timer(self, event):
        if self.auto_pilot == True and self.auto_pilot_triggered == False:
            if time.time() > self.auto_pilot_next:
                self.auto_pilot_trigger()  # start another sequence

    def on_chkLoop_mouseClick(self, event):
        self.seq.looping = self.components.chkLoop.checked

    # def on_chkBeeps_mouseClick(self, event):
    #     self.vp3.mute = not self.components.chkBeeps.checked
            
    def on_chkUseBeat_mouseClick(self, event):
        if self.components.chkUseBeat.checked is True:
            self.out_queue.put("usebeat|yes")
        else:
            self.out_queue.put("usebeat|no")

    # def on_btnAutoPilot_mouseClick(self, event):
    #     # self.components.AutoPilotBox.visible = self.components.btnAutoPilot.checked
    #     self.auto_pilot = self.components.btnAutoPilot.checked
    #     self.out_queue.put("stop|")    # stop all current activity
    #     if (self.auto_pilot is True):
    #         self.components.btnAutoPilot.backgroundColor = (255,0,0,255)
    #         self.components.btnAutoPilot.foregroundColor = (255,255,255,255)
    #         self.arm_auto_pilot()  # set the next auto pilot fire time
    #     else:
    #         self.components.btnAutoPilot.backgroundColor = (255,255,255,255)
    #         self.components.btnAutoPilot.foregroundColor = (0,0,0,255)

    def on_btnKill_mouseClick(self, event):
        """ attempt to kill all cannons """
        self.out_queue.put("stop|")
        self.components.chkUseBeat.checked = False
        self.out_queue.put("usebeat|no")
        self.vpb.reset()
        self.auto_pilot = False
        # self.components.btnAutoPilot.checked = False
        # self.components.btnAutoPilot.backgroundColor = (255,255,255,255)
        # self.components.btnAutoPilot.foregroundColor = (0,0,0,255)
        if self.tmain.isAlive():
            self.title = "Thread is alive"
        else:
            self.title = "Threads dead - attempting restart"
            self.tmain = threading.Thread(target=self.cb, args=(self.ev_queue,self.out_queue,self.in_queue))
            self.tmain.start()
            self.out_queue.put("stop|")
            
    """
    def on_btnHello_mouseClick(self, event):
    #def on_btnHello_mouseDown(self, event):
        #print self.cl
        if (self.seq.running() == True):
        #if self.t1.isAlive() == True:
            self.out_queue.put("stop")
            self.seq.stop()
        else:   # sequence is not yet running
            self.seq.scaleToBeat(parclasses.TimeCode(15))
            self.seq.start()
            # test threaded operation
            #while self.out_queue.empty() == False:
            #    self.out_queue.get()
            #self.components.btnHello.start_time = time.time()
            #self.t1.start()
    """

    def on_btnHello_mouseClick(self, event):
        """ start a thread to playback this sequence """
        if self.ttemp.isAlive() is True:
            self.temp_out_queue.put("stop")
        else:   
            # self.seq.scaleToBeat(parclasses.TimeCode(15))
            while self.temp_out_queue.empty() is False:
                self.temp_out_queue.get()
            self.components.btnHello.start_time = time.time()

            # destroy the temp thread and recreate
            # "you can't stop a thread object and restart it. Don't try"
            del self.ttemp
            self.ttemp = threading.Thread(target=self.seq, args=(self.temp_ev_queue, self.temp_out_queue))
            self.ttemp.start()

    """
    def on_btnHello_mouseUp(self, event):
        if (time.time() - self.components.btnHello.start_time) > 0.2:
            if (self.seq.running() == True):
                self.out_queue.put("stop")
                #self.seq.stop()
        event.skip()
    """         

    # ugly but functional - redirect sequence button mouse events to 
    # single handler functions.  Future: find a better way to bind the
    # events to the handler
    def on_SEQ0_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ0_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ1_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ1_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ2_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ2_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ3_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ3_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ4_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ4_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ5_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ5_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ6_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ6_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ7_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ7_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ8_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ8_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ9_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ9_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ10_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ10_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ11_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ11_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ12_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ12_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ13_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ13_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ14_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ14_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ15_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ15_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ16_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ16_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ17_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ17_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ18_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ18_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ19_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ19_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ20_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ20_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ21_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ21_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ22_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ22_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ23_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ23_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ24_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ24_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ25_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ25_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ26_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ26_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ27_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ27_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ28_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ28_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ29_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ29_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ30_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ30_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ31_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ31_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ32_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ32_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ33_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ33_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ34_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ34_mouseUp(self, event): self.seqCmdUp(event)
    def on_SEQ35_mouseDown(self, event): self.seqCmdDown(event)
    def on_SEQ35_mouseUp(self, event): self.seqCmdUp(event)

    def seqCmdDown(self, event):
        """ This is called on the down click of all sequence buttons.
            it toggles the sequence state (toggle handled in ControlBank) """
        if (self.auto_pilot is False):
            # print"toggle|" + self.sequences[event.target.id]
            self.out_queue.put("toggle|" + self.sequences[event.target.id])
            self.trigger_times[event.target.id] = time.time()
        event.Skip()

    def seqCmdUp(self, event):
        """ Depending on how long the button was pressed, either stop
            the sequence or does nothing """
        if (self.auto_pilot is False):
            if time.time() - self.trigger_times[event.target.id] > 0.2:
                # print "stop|" + self.sequences[event.target.id]
                self.out_queue.put("stop|" + self.sequences[event.target.id])
        event.Skip()
              
    def on_fileImport_command(self, event):
        if (self.seq.running() is False):
            # self.components.slSeqRate.value = 50
            self.components.slSeqRate.value = 92
            # self.scaleFactor = 1.0
            self.scaleFactor = 0.25 # goo typical rate
            aStyle = wx.OPEN | wx.FD_CHANGE_DIR
            result = dialog.fileDialog(self, 'Import', self.seq_directory, '', "*.jpg", aStyle)
            if result.accepted is True:
                del self.seq
                gi = sequenceimport.GraphicImport()
                self.seq = gi.import_sequence(result.paths[0], 22, 10, 250, self.import_map)
                # self.seq = gi.import_sequence(result.paths[0], 22, 10, 250, self.straight_map) # import from old gfx
                self.seq.scaleOnNext(self.scaleFactor)  # @@@ this is a hack to save time - pre-scale when loading in
        else:
            self.temp_out_queue.put("stop")
            # self.seq.stop()
            print "Sequence was running. lease try again"

    def on_fileSave_command(self, event):
        """ Saves sequence as XML .seqx file """
        aStyle = wx.SAVE | wx.HIDE_READONLY | wx.OVERWRITE_PROMPT
        result = dialog.fileDialog(self, 'Save Sequence', self.seq_directory, self.seq.name, "*.seqx", aStyle )
        if result.accepted is True:
            self.seq.saveXML(result.paths[0])

    def on_fileOpen_command(self, event):
        """ Opens XML .seqx file  """
        if self.seq.running() is False:
            self.components.slSeqRate.value = 50
            dialog_style = wx.OPEN | wx.FD_CHANGE_DIR
            result = dialog.fileDialog(self, 'Open Sequence', self.seq_directory, '', "*.seqx", dialog_style)
            if result.accepted is True:
                del self.seq
                self.seq = parclasses.ControlList(result.paths[0])
        else:
            self.temp_out_queue.put("stop")
            # self.seq.stop()
            print "Sequence was running.  Please try again"

    def on_fileOpenBank_command(self, event):
        if self.seq.running() is False:
            self.components.slSeqRate.value = 50
            # self.scaleFactor = 1.0
            aStyle = wx.DD_DIR_MUST_EXIST | wx.RESIZE_BORDER # | wx.DD_CHANGE_DIR
            result = dialog.directoryDialog(self, 'Open Bank', self.seq_directory, aStyle)

            if result.accepted is True:
                self.out_queue.put("clearbank")
                self.out_queue.put("loadbank|" + result.path[len(self.seq_directory):])

                # read the tempo from a file
                tempofn = "" + result.path + "\\tempo.txt"
                self.title = tempofn.replace("\\", "\\\\") + " not found"
                with open(tempofn.replace("\\", "\\\\"), "r") as tempofile:
                    if tempofile is not None:
                        tempo = tempofile.readline()
                        self.title = tempo
                        self.out_queue.put("settempo|" + tempo)
        else:
            self.temp_out_queue.put("stop")
            print "Sequence was running.  Please try again"

    def on_btnNextBank_mouseClick(self, event):
        if self.banks:
            if self.bank_index < len(self.banks) - 1:
                self.bank_index += 1
            self.open_bank(self.bank_index)

    def on_btnPrevBank_mouseClick(self, event):
        if self.banks:
            if self.bank_index > 0:
                self.bank_index -= 1
            self.open_bank(self.bank_index)

    def open_bank(self, bank_index):
        self.title = ""
        if self.banks is not None and 0 <= bank_index < self.banks.count:
            if self.seq.running():
                self.temp_out_queue.put("stop")
            else:
                self.components.slSeqRate.value = 50
                self.out_queue.put("clearbank")
                self.out_queue.put("loadbank|" + self.banks[bank_index])
                self.title = "Bank \"{0}\" loaded ".format(self.banks[bank_index])

                # read the tempo from a file
                tempofn = path.join(self.seq_directory, self.banks[bank_index], "tempo.txt")
                with open(tempofn, "r") as tempofile:
                    if tempofile is not None:
                        tempo = tempofile.readline()
                        self.title += tempo
                        self.out_queue.put("settempo|" + tempo)

    def on_slSeqRate_mouseUp(self, event):
        self.scaleFactor = 0.05 * (101 - self.components.slSeqRate.value)
        self.seq.scaleOnNext(self.scaleFactor)
        event.skip()

    def on_close(self, event):
        # command threads to stop then wait
        if self.tmain.isAlive():
            self.out_queue.put("die")
            self.tmain.join()  # wait for thread to finish
        if self.ttemp.isAlive():
            self.temp_out_queue.put("die")
            self.ttemp.join()  # wait for thread to finish
        print "Exiting program"
        event.Skip()

    def arm_auto_pilot(self):
        # get auto pilot ready to arm
        self.auto_pilot_triggered = False
        nexttime = .05 * (101 - self.auto_pilot_rate) * random.randint(1, 10)
        print "Next sequence in " + str(nexttime)
        self.auto_pilot_next = time.time() + nexttime
        # self.auto_pilot_next = time.time() + 1 # testing only

    def auto_pilot_trigger(self):
        """ run a random sequence now """
        self.auto_pilot_triggered = True
        nextseq = random.randint(0, self.top_button - 1)
        btn = "SEQ" + str(nextseq)
        print "Next " + btn + " " + self.components[btn].label 
        self.out_queue.put("loop|" + self.components[btn].label + "|off")
        self.out_queue.put("start|" + self.components[btn].label)


    def on_btnStart_mouseClick(self, event):
        """ open a sequence file if exists, start ValvePort_Object capture """
        # give a heads-up beep sequence
        # i = 4
        # while i > 0:
        #     winsound.Beep(440, 4)
        #     time.sleep(1)
        #     i -= 1
        # winsound.Beep(880, 4)

        # self.seq = parclasses.ControlList()
        # self.vp4.cl = self.seq
        # load previous sequence from external file

        # try:
        #     self.vp4.cl.loadXML(self.seq_directory + self.compose_file)
        #     self.seq.loadXML(self.seq_directory + self.compose_file)
        # except IOError:
        #     print 'Unable to read working sequence file'
        self.media.play()
        self.vp4.start()

    def on_btnStop_mouseClick(self, event):
        """ open a sequence file if exists, start ValvePort_Object capture """
        self.vp4.stop()
        self.media_time = self.media.get_time()
        self.media.stop()
        print "Music stopped at: " + str(self.media_time)

        del self.seq
        self.seq = parclasses.ControlList(self.vp4.cl)  # ??? doesn't seem to work

    def on_btnSave_mouseClick(self, event):
        """ adds the new sequence to the master project file """
        self.vp4.stop()
        self.media_time = self.media.get_time()
        print "Music stopped at: " + str(self.media_time)
        self.media.stop()

        self.vp4.cl.reconcile()  # TODO: use reconcile instead?
        self.vp4.cl.saveXML(self.seq_directory + self.compose_file)
        self.vp4.cl.saveXML(self.seq_directory + 'Compose/SESSION.' + str(time.time()) + '.seqx')  # session file

        # load previous sequence from external file
        try:
            self.seq.loadXML(self.seq_directory + self.compose_file)
        except IOError:
            print 'Unable to read working sequence file'

    def on_btnLoad_mouseClick(self, event):
        """ Loads the working compose sequence to the ValvePort_Object recorder """
        # TODO: this is messed up. Revisit this. Do we need to del self.seq? Just reload it? start from scratch
        self.seq = parclasses.ControlList()
        self.vp4.cl = self.seq  # TODO: override eq operator to make the same, not to point to the same object
        # load previous sequence from external file
        self.seq.loadXML(self.seq_directory + self.compose_file)
        self.seq.sortEvents()
        print self.seq

    def on_btnNew_mouseClick(self, event):
        """ Overwrites the compose file with a new, blank file """
        self.vp4.cl.clear()
        self.vp4.cl.saveXML(self.seq_directory + self.compose_file)
        self.seq.clear()

if __name__ == '__main__':
    app = model.Application(parablew)
    app.MainLoop()
