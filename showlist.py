from paraplayer import ParaPlayer
from multiprocessing import Queue
import xml.etree.ElementTree as ET  # XML support
import time


class ShowListEvent(object):
    def __init__(self, data: ET.Element):
        self.type = 'music'
        self.source = ''
        self.sequence = ''
        self.duration = 0.0

        """ loads this object from an ElementTree.Element object """
        self.duration = float(data.get("duration", "0.0"))
        self.source = str(data.get("source", ""))
        self.sequence = str(data.get("sequence", ""))
        self.type = data.get("type", "none")
        self.time = float(data.get("time", "0.0"))

        if self.source != '' and self.sequence == 'default':
            self.sequence = '{}.seqx'.format(self.source)


class ShowList(object):
    """This class reads in events from a .show file and manages playback of the show"""
    def __init__(self, player: ParaPlayer, seq_queue: Queue, show_file_path=None):
        self.music_root = ''
        self.seq_queue = seq_queue
        self.player = player
        self.events = []  # array of show events
        self.current_index = 0
        self.start_time = 0.0
        self.paused_at = 0.0
        self.locked = False  # Don't allow the show to be paused or stopped

        self.is_stopped = True  # prevent callbacks from playing the next track
        self.is_paused = False  # for display use only (callback)

        self.player.set_start_callback(self.on_start)
        self.player.set_finish_callback(self.on_completion)

        self.change_state_callback = None
        self.pause_state_callback = None
        self.change_track_callback = None

        if show_file_path is not None:
            self.load(show_file_path)

    def set_callbacks(self, change_state_callback=None, change_track_callback=None, pause_state_callback=None):
        """ Sets external callbacks to be run when the state changes or the track changes """
        self.change_state_callback = change_state_callback
        self.pause_state_callback = pause_state_callback
        self.change_track_callback = change_track_callback

    def load(self, show_file_path):
        # Load show file
        try:
            tree = ET.parse(show_file_path)
        except Exception as e:
            print("Error parsing show file {0}: {1}".format(show_file_path, e))
            return

        # set top-level attributes
        root = tree.getroot()
        self.music_root = str(root.get("music_root", ''))

        # Read event elements from the file and create element list
        del self.events[:]  # clear any exiting events
        self.events = []
        self.current_index = 0
        events = root.find("events")
        if events is not None:
            ev_list = events.findall("event")
            for ev in ev_list:
                self.events.append(ShowListEvent(ev))

    def get_event(self, item_index):
        """Returns the item at index of None"""
        if item_index < len(self.events):
            return self.events[item_index]
        else:
            return None

    def cancel(self):
        """Cancels playback of this show and resets event index"""
        self.is_stopped = True
        self.is_paused = False
        self.call_change_state()
        self.stop()
        self.current_index = 0
        self.call_track_change()

    def stop(self):
        """Stops playback and resets player"""
        self.is_stopped = True
        self.call_change_state()
        self.seq_queue.put('stop|')
        self.player.stop()
        self.paused_at = 0.0
        self.is_paused = False
        self.call_pause_state()
        self.start_time = 0.0

    def pause(self):
        """Stops playback and resets player"""
        if self.paused_at == 0.0:
            self.is_stopped = True
            self.call_change_state()
            self.seq_queue.put('stop|')
            self.player.pause()
            self.paused_at = time.time() - self.start_time
            self.is_paused = True
            self.call_pause_state()
        else:
            self.is_stopped = False
            self.call_change_state()
            self.seq_queue.put('resume|')
            self.player.play()
            self.start_time = time.time() - self.paused_at
            self.paused_at = 0.0
            self.is_paused = False
            self.call_pause_state()

    def current_event(self):
        """Returns the current event (whether playing or queued)"""
        if 0 <= self.current_index < len(self.events):
            return self.events[self.current_index]
        else:
            return None

    def start(self):
        """Think of this as "play first"""
        # CRITICAL: MUST reinstantiate the thread here
        # self.stop()
        if not self.locked:
            self.is_stopped = False
            self.locked = True
            self.current_index = 0
            self.call_track_change()
            self.play()
            self.call_change_state()
            self.is_paused = False
            self.call_pause_state()
            self.call_track_change()

    def play(self):
        """Starts playing the show"""
        ev = self.current_event()
        if ev is not None:
            if ev.type == 'stop':
                # no playback initiated so we'll wait until start() is called again
                self.paused_at = time.time() - self.start_time
                self.current_index += 1
                self.is_stopped = True
                self.call_track_change()
                self.call_pause_state()
                print("Show playback intentionally stopped, press PLAY to resume")
            else:
                media_path = self.music_root + ev.source if ev.source != '' else None
                self.player.set_media(media_path, ev.duration)
                self.player.play()
                self.is_stopped = False
                self.is_paused = False
                self.call_pause_state()
            self.call_change_state()
            self.call_track_change()

    def resume(self):
        """Plays the next event if one exists"""
        self.paused_at = 0.0  # un-pause TODO: add adjusting time entry here for paused "paused" entries
        self.is_stopped = False
        self.call_change_state()

        if self.current_index < len(self.events):
            self.call_track_change()
            self.play()
        else:
            # end of show
            self.locked = False
        self.is_paused = False
        self.call_pause_state()

    def play_next(self):
        """Plays the next event if one exists"""
        was_playing = not self.is_stopped
        self.paused_at = 0.0  # un-pause TODO: add adjusting time entry here for paused "paused" entries
        if not self.is_stopped:
            self.stop()
            self.call_change_state()

        self.current_index += 1
        if self.current_index < len(self.events):
            if was_playing:
                self.play()
                self.call_change_state()
        else:
            # end of show
            self.locked = False
            self.call_change_state()
        self.is_paused = False
        self.call_pause_state()
        self.call_track_change()

    def queue_next(self):
        """ Points to the next event if one exists"""
        self.paused_at = 0.0  # un-pause TODO: add adjusting time entry here for paused "paused" entries
        if not self.is_stopped:
            self.stop()

        self.current_index += 1
        if self.current_index >= len(self.events):
            self.current_index = len(self.events) - 1
            self.locked = False
        self.call_track_change()
        self.is_paused = False
        self.call_pause_state()

    def play_prev(self):
        """Plays the previous event if one exists"""
        was_playing = not self.is_stopped
        self.paused_at = 0.0  # un-pause TODO: add adjusting time entry here for paused "paused" entries
        if not self.is_stopped:
            self.stop()
            self.call_change_state()

        self.current_index -= 1
        if self.current_index >= 0:
            if was_playing:
                self.play()
                self.call_change_state()
        else:
            # start of show
            self.current_index = 0
            self.locked = False
            self.call_change_state()
        self.call_track_change()
        self.is_paused = False
        self.call_pause_state()

    def queue_prev(self):
        """ Points to the previous event if one exists"""
        self.paused_at = 0.0  # un-pause TODO: add adjusting time entry here for paused "paused" entries
        if not self.is_stopped:
            self.stop()
            self.call_change_state()

        self.current_index -= 1
        if self.current_index < 0:
            self.current_index = 0
            self.locked = False
        self.call_track_change()
        self.is_paused = False
        self.call_pause_state()

    def on_completion(self, media_path, time_sig):
        # TODO: need to determine if the sequence is longer than the music. Rare, but possible.
        if media_path:
            print("On Completion called with time signature " + str(time_sig) + " for media " + media_path)
        else:
            print("On Completion called after pause at " + str(time_sig))
        if not self.show_paused():
            self.play_next()

    def on_start(self, media_path, time_sig):
        """Used here to trigger the start of the sequence"""
        ev = self.current_event()
        if ev:
            if ev.sequence != '':
                self.seq_queue.put('start|{}'.format(ev.sequence))
        if media_path:
            print("On Start called with time signature " + str(time_sig) + " for media " + media_path)
        else:
            print("On Start called after pause at " + str(time_sig))

    def show_paused(self):
        return self.paused_at > 0.0 or self.is_stopped

    def call_change_state(self):
        """ Calls external callback if set """
        if self.change_state_callback is not None:
            self.change_state_callback(self.is_stopped)

    def call_track_change(self):
        """ Calls external callback if set """
        if self.change_track_callback is not None:
            self.change_track_callback(self.current_index)

    def call_pause_state(self):
        """ Calls external pause state change handler """
        if self.pause_state_callback is not None:
            self.pause_state_callback(self.is_paused)
