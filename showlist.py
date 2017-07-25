from paraplayer import ParaPlayer
from multiprocessing import Queue
import xml.etree.ElementTree as ET  # XML support


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
        self.show_paused = False  # this means that a stop event was encountered

        self.player.set_start_callback(self.on_start)
        self.player.set_finish_callback(self.on_completion)

        if show_file_path is not None:
            self.load(show_file_path)

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

    def cancel(self):
        """Cancels playback of this show and resets event index"""
        self.stop()
        self.current_index = 0

    def stop(self):
        """Stops playback and resets player"""
        self.seq_queue.put('stop')
        self.player.stop()
        self.paused_at = 0.0
        self.start_time = 0.0

    def current_event(self):
        """Returns the current event (whether playing or queued)"""
        if 0 <= self.current_index < len(self.events):
            return self.events[self.current_index]
        else:
            return None

    def start(self):
        """Think of this as "play first"""
        # TODO: might need to reinstantiate the thread here
        # self.stop()
        if not self.locked:
            self.locked = True
            self.current_index = 0
            self.play()

    def play(self):
        """Starts playing the show"""
        ev = self.current_event()
        if ev is not None:
            if ev.type == 'stop':
                # no playback initiated so we'll wait until start() is called again
                self.show_paused = True
                self.current_index += 1
                print("Show playback intentionally stopped, press PLAY to resume")
            else:
                media_path = self.music_root + ev.source if ev.source != '' else None
                self.player.set_media(media_path, ev.duration)
                self.player.play()

    def resume(self):
        """An alias - easier to remember for external control after a show pause"""
        self.play_next()

    def play_next(self):
        """Plays the next event if one exists"""
        self.show_paused = False
        self.current_index += 1
        if self.current_index < len(self.events):
            self.play()
        else:
            # end of show
            self.locked = False

    def on_completion(self, media_path, time_sig):
        # TODO: need to determine if the sequence is longer than the music. Rare, but possible.
        if not self.show_paused:
            if media_path:
                print("On Completion called with time signature " + str(time_sig) + " for media " + media_path)
            else:
                print("On Completion called after pause at " + str(time_sig))
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
