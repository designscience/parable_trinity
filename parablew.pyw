#!/usr/bin/python

"""
__version__ = "$Revision: 1.15a $"
__date__ = "$Date: 2012/07/27 $"
"""

""" ******************************************************************
This is the main file for the ParableW (Parable running on Windows)
program.  Parable is the sequencing program developed for the Shiva Vista
project but can be applied to other sequencing applications as well.

The parablew class encapsultates the ParableW program... its objects, its
GUI controls and the event handlers for them, the program initialization
and the

1.03 - corrected mapping inconsistencies between GUI display and electrical
channels.  Added updated BTIC class that ignores first few taps to reduce
human error.

1.04 - Moved lights to 2011 configuration. Included straight bank mapping.
Added joystick support for footswitch (needs testing).  

1.10 - Replaced BTIC class with Beatnik class

1.11 - Wrapped BeatRecorder() (tap handler) in exception block. Force loaded
sequences to stop().

1.12a - Adds improved accuracy of sequence playback. Ensures sequence are scaled
to whole number of beats. Also, tap time is sent with tap beat for better accuracy
when program is busy.  Still uses picle for saving sequence objects, but with greatly
improved ControlList.useCurrent() implementation that forces scale against ref_times
insteade of comprimising reference times.5/26/2012

1.14 - Sequences now saved as .seqx files (XML instead of pickle)

1.15 - Perpetual synch added.  Sequences re-synch with beat at the start of each
sequence loop.  

1.15a - bug in win2k requires str() to detect file path. 

***** Issue Notes  *****
* kill (abort button) checks main thread and restarts if dead.  A hack.
* consider sending time in Align, as is done with tap command
* still some small error in playback versus tap period, but better
* all sequences must be recreated due to use of pickle and changes in parclasses
* program hangs occassionally with doing graphic import of images
* auto pilot doesn't respect looping sequences (they keep looping)



****************************************************************** """ 


from PythonCard import model, timer, dialog
import parclasses
import parthreads
import sequenceimport
import random
import time
import pickle  # save objects to a binary file
import threading, Queue
import wx
import logging  # save to a log
#import pygame
#from pygame.locals import *

__version__ = "1.15a"

class parablew(model.Background):
    def __init__(self, aParent, aBgRsrc):
        model.Background.__init__(self, aParent, aBgRsrc)



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
        #self.seq_directory = "C:\\Documents and Settings\\Stu D'Alessandro\\My Documents\\Burning Man\\Shiva Vista\\2009\\Parable\\sequences\\"
        #self.seq_directory = "..\\..\\sequences\\"

        # Threading queues
        self.out_queue = Queue.Queue() # send commands to main thread
        self.in_queue = Queue.Queue()  # get responses from main thread
        self.ev_queue = Queue.Queue()  # get event records from main thread
        self.temp_out_queue = Queue.Queue() # send commands to temp seq thread
        self.temp_ev_queue = Queue.Queue()  # get event records from main thread

        # create a channel map for the actual cannons
        self.effect_map = parclasses.ChannelMap(24) # for effects channels
        self.gui_map = parclasses.ChannelMap(24) # for GUI 'lights'
        self.straight_map = parclasses.ChannelMap(24) # for straight import mapping
        self.import_map = parclasses.ChannelMap(24) # for alternative graphic import mapping (else use straight map)

        # Set up straight map
        for i in range(1, 22):
            self.straight_map.addMapping(i,  i)
        self.straight_map.addMapping(23,  0)
        self.straight_map.addMapping(24,  0)
        
        # create valveport (output) objects
        self.vp1 = parclasses.ValvePort_GUI(22, 6, self.components.OutputCanvas1)
        self.vp1.setMap(self.straight_map)

        # position sequencing "lights" on the screen
        for i in range(0, 6):
            ch = (i*3)  # 0-based channel index

            self.vp1.set_light(ch+1, ((100 * i)     , 25))
            self.vp1.set_light(ch+2, ((100 * i) + 20, 50))
            self.vp1.set_light(ch+3, ((100 * i) + 40, 25))
        
        self.vp1.set_light(19, (630, 35))
        self.vp1.set_light(20, (630, 8))
        self.vp1.set_light(21, (665, 8))
        self.vp1.set_light(22, (665, 35))

        #create screen buttons
        for i in range(self.num_buttons):
            self.components['SEQ' + str(i)] = {'type':'Button', 'name':'SEQ' + str(i), 'id':i, 'position':(20 +(152 * (i%5)), 150 + (40 * int(i/5))), 'size':(120, 30), 'label':'Sequence ' + str(i+1), 'command':'seqBtn' + str(i+1), 'visible':False}
            
        # Other output objects
        self.vp2 = parclasses.ValvePort_Parallel(24, 6)
        self.vp2.setMap(self.effect_map)

        self.vp3 = parclasses.ValvePort_Beep() # not very good
        self.vp3.setMap(self.effect_map)
        self.vp3.mute = True

        # temp sequence rate scaling factor
        #self.scaleFactor = 1.0
        self.scaleFactor = 1.10

        # add output objects to an output bank
        self.vpb = parclasses.ValvePortBank()
        self.vpb.addPort(self.vp1)
        self.vpb.addPort(self.vp2)
        self.vpb.addPort(self.vp3)
        self.vpb.execute()   # show the lights

        #create the temp sequence object - used to try out sequences
        self.seq = parclasses.ControlList()
        self.seq.name = "Temp Sequence"

        # Create initial temp sequence
        for i in range(12):
            ch = i + 1
            #li = parclasses.spiral(10, 22, 3, 12, 3)
            #li = parclasses.beep(ch, 2, 2, 0, 0)
            li = parclasses.randy(64, 22, 1, 2)
            self.seq.append(li)
            
        self.seq.sortEvents()

        # Create the threaded sequence handler (ControlBank)
        self.cb = parthreads.ControlBank("C:\\sequences\\")

        # Create thread objects
        self.ttemp = threading.Thread(target=self.seq, args=(self.temp_ev_queue,self.temp_out_queue))
        self.tmain = threading.Thread(target=self.cb, args=(self.ev_queue,self.out_queue,self.in_queue))


    # key press handler (for when I figure out how to bind it
    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        print "Key pressed " + str(keycode)
        if keycode == wx.WXK_F1:
           on_pbTap_mouseDown(self, event) 
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
        #self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        #start and initialize main thread
        self.tmain.start()
        #self.out_queue.put("loadbank|drumming up the heat")
        self.out_queue.put("loadbank|")

        

    def on_idle(self, event):
        while self.ev_queue.empty() == False:
            ev = self.ev_queue.get()
            self.vpb.setEventExec(ev)

        while self.temp_ev_queue.empty() == False:
            ev = self.temp_ev_queue.get()
            self.vpb.setEventExec(ev)

        while self.in_queue.empty() == False:
            self.processCommand(self.in_queue.get())


    def processCommand(self, cmdstr):
        """ process incoming commands from the main thread """
        #print ">>> " + cmdstr
        cmd = cmdstr.split("|")

        #kill - kill the cannons
        if cmd[0] == "kill":
            vpb.reset()    
        #running - color button to indicate running status
        elif cmd[0] == "started":
            for i in range(self.num_buttons):
                if self.sequences[i] == cmd[1]:
                    btn = "SEQ" + str(i)
                    self.components[btn].backgroundColor = (255,0,0,255)
                    self.components[btn].foregroundColor = (255,255,255,255)
                    break
            if (self.auto_pilot == True):
                self.auto_pilot_triggered = True;  # don't play another seq until done
            
        #stopped - color button to indicate stopped status
        elif cmd[0] == "stopped":
            for i in range(self.num_buttons):
                if self.sequences[i] == cmd[1]:
                    btn = "SEQ" + str(i)
                    self.components[btn].backgroundColor = (236,233,216,255)
                    self.components[btn].foregroundColor = (0,0,0,0)
                    break
            if (self.auto_pilot == True):
                self.arm_auto_pilot();  # sequence done, start another one
        #clearbank - hide sequence buttons
        elif cmd[0] == "clearbank":
            for i in range(self.num_buttons):
                btn = "SEQ" + str(i)
                self.components[btn].visible = False
                self.top_button = 0
        #newseq - add a new sequence
        elif cmd[0] == "newseq":
            if self.top_button < self.num_buttons:
                btn = "SEQ" + str(self.top_button)
                self.sequences[self.top_button] = cmd[1]
                self.components[btn].label = cmd[1]
                self.components[btn].visible = True        
                self.top_button += 1
        #beat- toggle beat light
        elif cmd[0] == "beat":  # toggle the state of the beat light
            self.components.ImageButton1.visible = \
                not self.components.ImageButton1.visible and \
                self.components.chkUseBeat.checked
        #beaton - turn on beat light
        elif cmd[0] == "beaton":
            if self.components.chkUseBeat.checked:
                self.components.ImageButton1.visible = True
            else:
                self.components.ImageButton1.visible = False  # always off                    
        #beatoff - turn off beat light
        elif cmd[0] == "beatoff":
            self.components.ImageButton1.visible = False
        #exception - report exception
        elif cmd[0] == "exception":
            self.title = "Exception: " + cmd[1]
            

    def on_pbTap_mouseDown(self, event):
        """ process a tap beat to keep time with music """
        self.out_queue.put("tap|" + str(time.time()))  # new 7/2012 - sending tap time
        if self.components.chkUseBeat.checked == False:
            self.components.chkUseBeat.checked = True
            self.out_queue.put("usebeat|yes")
                    

    def on_align_mouseDown(self, event):
        """ realign the start_time for the tap beat """
        self.out_queue.put("align|" + str(time.time()))  


    def on_OutputCanvas1_timer(self, event):
        if (self.auto_pilot == True and self.auto_pilot_triggered == False):
            if (time.time() > self.auto_pilot_next):
                self.auto_pilot_trigger()  # start another sequence

    def on_chkLoop_mouseClick(self, event):
        self.seq.looping = self.components.chkLoop.checked


    def on_chkBeeps_mouseClick(self, event):
        self.vp3.mute = not self.components.chkBeeps.checked
            
    def on_chkUseBeat_mouseClick(self, event):
        if self.components.chkUseBeat.checked == True:
            self.out_queue.put("usebeat|yes")
        else:
            self.out_queue.put("usebeat|no")

    def on_btnAutoPilot_mouseClick(self, event):
        #self.components.AutoPilotBox.visible = self.components.btnAutoPilot.checked
        self.auto_pilot = self.components.btnAutoPilot.checked
        self.out_queue.put("stop|")    # stop all current activity
        if (self.auto_pilot == True):
            self.components.btnAutoPilot.backgroundColor = (255,0,0,255)
            self.components.btnAutoPilot.foregroundColor = (255,255,255,255)            
            self.arm_auto_pilot()  # set the next auto pilot fire time
        else:
            self.components.btnAutoPilot.backgroundColor = (255,255,255,255)
            self.components.btnAutoPilot.foregroundColor = (0,0,0,255)            

    def on_btnKill_mouseClick(self, event):
        """ attempt to kill all cannons """
        self.out_queue.put("stop|")
        self.components.chkUseBeat.checked = False
        self.out_queue.put("usebeat|no")
        self.vpb.reset()
        self.auto_pilot = False
        self.components.    btnAutoPilot.checked = False
        self.components.btnAutoPilot.backgroundColor = (255,255,255,255)
        self.components.btnAutoPilot.foregroundColor = (0,0,0,255)
        if self.tmain.isAlive():
            self.title = "Thread is alive"
        else:
            self.title = "Threads dead - attempting restart"
            self.tmain = threading.Thread(target=self.cb, args=(self.ev_queue,self.out_queue,self.in_queue))
            self.tmain.start()
            self.out_queue.put("stop|")

    
    def on_btnHello_mouseClick(self, event):
    #def on_btnHello_mouseDown(self, event):
        """ start a thread to playback this sequence """
        if self.ttemp.isAlive() == True:
            self.temp_out_queue.put("stop")
        else:   
            #self.seq.scaleToBeat(parclasses.TimeCode(15))
            while self.temp_out_queue.empty() == False:
                self.temp_out_queue.get()
            self.components.btnHello.start_time = time.time()

            # destroy the temp thread and recreate
            # "you can't stop a thread object and restart it. Don't try"
            del self.ttemp
            self.ttemp = threading.Thread(target=self.seq, args=(self.temp_ev_queue,self.temp_out_queue))
            self.ttemp.start()


    def seqCmdDown(self, event):
        """ This is called on the down click of all sequence buttons.
            it toggles the sequence state (toggle handled in ControlBank) """
        if (self.auto_pilot == False):
            #print"toggle|" + self.sequences[event.target.id]
            self.out_queue.put("toggle|" + self.sequences[event.target.id])
            self.trigger_times[event.target.id] = time.time()
        event.Skip()

    def seqCmdUp(self, event):
        """ Depending on how long the button was pressed, either stop
            the sequence or does nothing """
        if (self.auto_pilot == False):
            if time.time() - self.trigger_times[event.target.id] > 0.2:
                #print "stop|" + self.sequences[event.target.id]
                self.out_queue.put("stop|" + self.sequences[event.target.id])
        event.Skip()
              
    def on_fileImport_command(self, event):
        if (self.seq.running() == False):
            #self.components.slSeqRate.value = 50
            self.components.slSeqRate.value = 92
            #self.scaleFactor = 1.0
            self.scaleFactor = 0.25 # goo typical rate
            aStyle = wx.OPEN | wx.FD_CHANGE_DIR
            result = dialog.fileDialog(self, 'Import', self.seq_directory, '', "*.jpg", aStyle)
            if result.accepted == True:
                del self.seq
                gi = sequenceimport.GraphicImport()
                self.seq = gi.import_sequence(result.paths[0], 22, 10, 250, self.import_map)
                #self.seq = gi.import_sequence(result.paths[0], 22, 10, 250, self.straight_map)  # for importing from old graphics
                self.seq.scaleOnNext(self.scaleFactor)  #  @@@ this is a hack to save time - pre-scale when loading in
        else:
            self.temp_out_queue.put("stop")
            #self.seq.stop()
            print "Sequence was running. lease try again"


    def on_fileSave_command(self, event):
        """ Saves sequence as XML .seqx file """
        aStyle = wx.SAVE | wx.HIDE_READONLY | wx.OVERWRITE_PROMPT
        result = dialog.fileDialog(self, 'Save Sequence', self.seq_directory, self.seq.name, "*.seqx", aStyle )
        if result.accepted == True:
            self.seq.saveXML(result.paths[0])


    def on_fileOpen_command(self, event):
        """ Opens XML .seqx file  """
        if (self.seq.running() == False):
            self.components.slSeqRate.value = 50
            aStyle = wx.OPEN | wx.FD_CHANGE_DIR
            result = dialog.fileDialog(self, 'Open Sequence', self.seq_directory, '', "*.seqx", aStyle)
            if result.accepted == True:
                del self.seq
                self.seq = parclasses.ControlList(result.paths[0])
        else:
            self.temp_out_queue.put("stop")
            #self.seq.stop()
            print "Sequence was running.  Please try again"


    def on_fileOpenBank_command(self, event):
        if (self.seq.running() == False):
            self.components.slSeqRate.value = 50
            #self.scaleFactor = 1.0
            aStyle = wx.DD_DIR_MUST_EXIST | wx.RESIZE_BORDER # | wx.DD_CHANGE_DIR
            result = dialog.directoryDialog(self, 'Open Bank', self.seq_directory, aStyle)

            if result.accepted == True:
                self.out_queue.put("clearbank")
                self.out_queue.put("loadbank|" + result.path[len(self.seq_directory):])
                
        else:
            self.temp_out_queue.put("stop")
            print "Sequence was running.  Please try again"


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
        #self.auto_pilot_next = time.time() + 1 # testting only

    def auto_pilot_trigger(self):
        """ run a random sequence now """
        self.auto_pilot_triggered = True
        nextseq = random.randint(0, self.top_button - 1)
        btn = "SEQ" + str(nextseq)
        print "Next " + btn + " " + self.components[btn].label 
        self.out_queue.put("loop|" + self.components[btn].label + "|off")
        self.out_queue.put("start|" + self.components[btn].label)


        
if __name__ == '__main__':
    app = model.Application(parablew)
    app.MainLoop()
