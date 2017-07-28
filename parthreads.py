""" ************************************************************
threading classes for Parable Sequencing Program
Author: Stu D'Alessandro

Contains classes used to run Parable sequences from within a threading
object.  Classes are callable so they can be used as the target parameter
of the threading object.

ControlBank is the main object contained here.  This is the heart of
the Parable 2 application as it receives commands from the main app's
events and loads, plays, and stops sequences (ControlLists).

These classes are listed in this separate file since they are not
Parable "primitives" but a higher-level application of those primitives.
Plus, the parclasses.py file was getting really long.

ver 1.7 - loads bank using seqx files
ver 3.0 - Python 3 & Trinity  7/2017

************************************************************ """

from __future__ import division
import os
import time
import parclasses
import beatnik
import threading
# import wx


# *********************** ControlGroup ****************************


class ControlBank(object):
    """ Maintains Parable sequences in thread.  Receives commands from
        in_q, sends responses in out_q, sends pending events in ev_q """
    def __init__(self, seq_dir, autoload=True):
        self.seq_dir = seq_dir  # default sequence directory path

        self.sequences = []  # stores ControlList events
        self.banks = []     # stores string descriptors of banks within the events

        self.autoload = autoload  # automatically load sequences from base folder
        self.die_pending = False  # if true do an orderly shutdown of the thread
        self.bank_clear_pending = False
        self.bank_load_pending = False
        self.next_bank = ""

        self.in_q = None
        self.out_q = None
        self.ev_q = None

        # self.btic = BTIC.BTIC()  # beat keeper object
        self.btic = beatnik.Beatnik()  # beat keeper object
        self.use_beat = False
        
    def __call__(self, event_queue, in_queue, out_queue):
        """ called as a target of a threaded.Thread object, this will
            run the sequencing functions, communicating through the queues """

        lock = threading.Lock()

        running = True
        self.in_q = in_queue  # command received from the main thread
        self.out_q = out_queue  # responses, commands to the main thread
        self.ev_q = event_queue  # return pending events to the main thread
        self.light_state = False  # current state of beat light

        # send first beat light message
        if self.btic.BeatLight() is True:
            self.out_q.put("beaton")
        else:
            self.out_q.put("beatoff")

        # run thread loop
        while running is True:
            if self.die_pending is False:
                lock.acquire()
                self.sendPendingEvents()
                lock.release()

                lock.acquire()
                self.processCommands()
                lock.release()

                # display beat light on UI
                light = self.btic.BeatLight()
                if light != self.light_state:
                    lock.acquire()
                    self.light_state = light
                    if light is True:
                        self.out_q.put("beatoff")
                    else:
                        self.out_q.put("beaton")
                    lock.release()

                if self.allClear() is True:
                    time.sleep(.01)
            else:
                # stop the loop/thread when all is cleaned up
                self.sendPendingEvents()
                if self.allClear() is True:
                    self.clearBank()                
                    self.die_pending = False
                    running = False
                else:
                    time.sleep(.01)

    def sendPendingEvents(self):
        """ Send any events due for playback to the main thread """
        for seq in self.sequences:
            ev_found = True
            while ev_found is True:
                ev = seq.getNextByTime()
                if isinstance(ev, parclasses.ControlEvent):
                    self.ev_q.put(ev)
                else:
                    if ev is True and self.out_q:
                        self.out_q.put("stopped|" + seq.name)
                    ev_found = False

    def processCommands(self):
        """ receive commands from the main thread and do them """
        if self.in_q.empty() is False and self.die_pending is False:
            cmdstr = self.in_q.get()
            cmd = cmdstr.split("|")
            # print("Thread received command " + cmd[0])

            # process the commands
            if cmd[0] == "die":
                self.die_pending = True
                self.stop()
                
            elif cmd[0] == "start":
                self.start(cmd[1])

            elif cmd[0] == "stop":
                if len(cmd) > 1:
                    if self.stop(cmd[1]) is True:
                        self.out_q.put("stopped|" + cmd[1])
                else:
                    self.stop()
                    self.out_q.put("stopall")

            elif cmd[0] == "toggle":  # toggle the run state of the sequence
                if len(cmd[1]) > 0:
                    # print("processing toggle")
                    if self.isRunning(cmd[1]) is True:
                        if self.stop(cmd[1]) is True:
                            self.out_q.put("stopped|" + cmd[1])
                    else:
                        self.start(cmd[1])            

            elif cmd[0] == "tap":
                try:
                    tap_time = float(cmd[1])
                    self.btic.BeatRecorder(tap_time)
                except Exception as e:
                    self.out_q.put("exception: {0}".format(e))

            elif cmd[0] == "align":
                self.btic.align(float(cmd[1]))

            elif cmd[0] == "loadbank":
                self.next_bank = cmd[1]
                self.bank_load_pending = True
                self.stop()

            elif cmd[0] == "clearbank":
                self.bank_clear_pending = True
                self.stop()

            elif cmd[0] == "usebeat":
                if cmd[1] == "yes":
                    self.use_beat = True
                    # print("Using Beat")
                else:
                    self.use_beat = False
                    for seq in self.sequences:
                        seq.stopSynching()
                    # print("Not Using Beat")

        # clear or load bank
        if self.bank_clear_pending is True and self.allClear() is True:
            self.bank_clear_pending = False
            self.clearBank()
        elif self.bank_load_pending is True and self.allClear() is True:
            self.bank_load_pending = False
            self.loadBank(self.next_bank)

    def stop(self, name=""):
        """ Stops one sequence if named or all sequences if not """
        if name == "":
            for seq in self.sequences:
                seq.stop()  # begin stopping the sequence
            return True
        else:
            result = False
            for seq in self.sequences:
                if seq.name == name:
                    seq.stop()  # begin stopping the sequence
                    result = True
            return result

    def start(self, name):
        """ Starts a sequence by name if it's loaded in the sequences list """
        result = False

        if len(name) > 0:
            for seq in self.sequences:
                if seq.name == name:
                    # synchronize with beat?
                    if self.use_beat is True and self.btic.isReady():
                        beattime = self.btic.nextBeatTime() + time.time()
                        seq.scaleToBeat(self.btic.fDL, self.btic)  # set second param to None to disable perpetual sync
                        seq.start(beattime)
                    else:
                        seq.start()
                        
                    # notify main thread
                    if self.out_q:
                        self.out_q.put("started|" + name)
                    result = True
        return result

    def isRunning(self, name):
        """ Returns True if sequence found and is running, else false """
        result = False
        if len(name) > 0:
            for seq in self.sequences:
                if seq.name == name:
                    result = not seq.atEnd()  # atEnd = finished running AND cleaning up
        return result

    def clearBank(self):
        """ if all activity is stopped deletes all sequences and
            reverts to an empty bank """
        result = True
        # delete all current sequences
        self.stop()  # for good measure
        if self.allClear() is True:
            self.bank_clear_pending = False
            while len(self.sequences) > 0:
                seq = self.sequences.pop()
                del seq
                
            # notify main thread
            if self.out_q:
                self.out_q.put("clearbank")
        else:
            result = False
        return result

    def loadBank(self, bank_name):
        """ Loads all sequences found in a folder.  Bank_name is a
            subfolder under the folder name """
        result = False

        if self.allClear() is True:
            self.bank_load_pending = False
            self.next_bank = ""

            # load default bank?
            if self.autoload is True:
                for filename in os.listdir(self.seq_dir):
                    parts = filename.rpartition('.')
                    if parts[2] == "seqx":
                        # path = self.seq_dir + "\\" + filename
                        path = str(self.seq_dir + filename)  # casting to str fixes win2k bug
                        print(filename)
                        # TODO: control list reports whether it is a show sequence and if it has a beat
                        seq = parclasses.ControlList(path)
                        seq.name = parts[0]
                        self.sequences.append(seq)
                        if self.out_q:
                            # TODO: return indicators for beat and show sequences, strip and use in main thread
                            self.out_q.put("newseq|" + str(parts[0]))
                        result = True

            # load the selected bank
            if len(bank_name) > 0:
                # folder = self.seq_dir + "\\" + bank_name
                folder = self.seq_dir + bank_name
                try:
                    for filename in os.listdir(folder):
                        parts = filename.rpartition('.')
                        if parts[2] == "seqx":
                            path = str(folder + "/" + filename)  # casting to str fixes win2k bug
                            print(filename)
                            seq = parclasses.ControlList(path)
                            seq.name = parts[0]
                            seq.stop()  # force a stop condition
                            self.sequences.append(seq)
                            if self.out_q:
                                self.out_q.put("newseq|" + str(parts[0]))
                            result = True
                except FileNotFoundError:
                    pass

            # Load show music sequence bank
            # NOTE: uses a-priori Show sequence folder
            if self.autoload is True:
                for filename in os.listdir(self.seq_dir + 'Show/'):
                    parts = filename.rpartition('.')
                    if parts[2] == "seqx":
                        # path = self.seq_dir + "\\" + filename
                        path = str(self.seq_dir + 'Show/' + filename)  # casting to str fixes win2k bug
                        print(filename)
                        # TODO: control list reports whether it is a show sequence and if it has a beat
                        seq = parclasses.ControlList(path)
                        seq.name = parts[0]
                        self.sequences.append(seq)
                        if self.out_q:
                            # TODO: return indicators for beat and show sequences, strip and use in main thread
                            self.out_q.put("newseq|" + str(parts[0]) + '.')
                        result = True
        else:
            self.stop()

        return result

    def allClear(self):
        """ all sequences are completely finished running and
            cleaned up """
        result = True
        for seq in self.sequences:
            if seq.atEnd() is False:
                result = False
                break

        return result
