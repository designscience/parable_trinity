import threading
import vlc
import time

# A class intended for threaded operation, instantiates a VLC media player and operates it


class ParaPlayer(threading.Thread):

    def __init__(self):
        self.Instance = vlc.Instance()
        self.player = self.Instance.media_player_new()

        # Lines below are unused but may come in handy on a rainy day
        # self.vlc_events = self.player.event_manager()
        # self.vlc_events.event_attach(vlc.EventType.MediaPlayerEndReached, self., 1)

        self.media_path = None
        self.playback_length = 0  # length of playback before stopping or 0
        self.start_time = 0.0  # For silence playback tracking, time play started
        self.pause_time = 0.0  # For silence playback tracking, time paused

        self.is_active = False  # Thread is active. Set false to kill thread.
        self.is_playing = False  # Something is playing, possibly silence

        self.start_callback_armed = False  # arm start callback until player loads and starts
        self.start_callback = None
        self.finish_callback = None
        self.interval_callback = None
        self.interval_period = 0.0
        self.interval_last_checked = 0.0

        self.loop_start = 0.0
        self.loop_end = 0.0  # If looping this is set to a value higher than loop_start
        self.pause_on_loop = False
        self.loop_callback = None

        self._stop_thread = threading.Event()
        threading.Thread.__init__(self)

    def set_media(self, media_path=None, length=0):
        """Sets a media file for playback or None with length to play silence for a period of time
        in seconds (float)"""
        self._halt_playback()
        self.media_path = media_path
        self.playback_length = length
        if self.media_path is not None:
            media = self.Instance.media_new(self.media_path)
            self.player.set_media(media)
            self.player.set_position(0)

    def run(self):
        """Initializes the thread but does not actually play media"""
        # CRITICAL: call this repeatedly from the program loop, remove loop and sleep. I think, right?
        # CONSIDER: actually, maybe not, if the program loop halts it may result in less than perfect operation. TBD!!!
        print("Entering media thread")
        self.is_active = True
        # while self._stop_thread.is_set() is False:
        # CRITICAL: are there two competing conditions or are both needed?
        # CRITICAL: self.player.is_playing() returns 0/1, is never True of False!!! Not being checked
        while self._stop_thread.is_set() is False or self.player.is_playing() is True:
            while self.is_active is True or self.player.is_playing() is True:
                self._check_playback()
                self._check_interval()
                time.sleep(.3)
        print("Leaving ParaPlayer media thread")

    def kill(self):
        """kill this thread, orderly like"""
        print("Killing playback thread")
        self.is_active = False  # CRITICAL: does this conflict with is_active() on threading.thread?
        self._stop_thread.set()

    # Set callback functions for event mgt. All functions get media_path and current playback time
    def set_start_callback(self, callback_fn=None):
        self.start_callback = callback_fn

    def set_finish_callback(self, callback_fn=None):
        self.finish_callback = callback_fn

    def set_interval_callback(self, callback_fn=None):
        self.interval_callback = callback_fn

    def play(self):
        """Plays a media file or silence if no file is set"""
        if self.is_alive() is False:
            self.start()
        if self.is_playing is False:
            # Handle paused playback
            if self.pause_time > 0.0:
                self.start_time = time.time() - (self.pause_time - self.start_time)
                self.pause_time = 0.0
                if self.media_path is not None:
                    self.player.play()
            else:
                # Handle un-started playback
                if self.media_path is not None:
                    self.player.play()
                    if self._is_looping():
                        self.player.set_time(int(self.loop_start * 1000))
                self.start_time = time.time()
            self.is_playing = True
            # Call start callback
            if self.start_callback is not None:
                if self.media_path is not None:
                    self.start_callback_armed = True
                else:
                    self.start_callback(self.media_path, self.get_time())

    def pause(self):
        """Pause playback and keep track of time signatures"""
        if self.is_playing:
            self.is_playing = False
            self.pause_time = time.time()
            if self.player.is_playing() == 1:
                self.player.pause()

    def stop(self):
        """Stop playback and reset media, call finish callback"""
        self._halt_playback()
        self.loop_end = 0.0
        self.loop_start = 0.0
        self.start_time = 0.0
        self.pause_time = 0.0

    def rewind(self):
        """Set the player to the start of the media or to the start of the loop"""
        self.player.set_time(int(self.loop_start * 1000))  # loop start should be 0.0 if we're not looping
        self.player.stop()

    def get_time(self):
        """Returns the current time of playback"""
        if self.media_path is None:
            if self.start_time > 0.0:
                return time.time() - self.start_time
            else:
                return 0.0
        else:
            return float(self.player.get_time() / 1000)

    def report_time(self):
        rtime = self.get_time()
        print(rtime)
        return rtime

    def loop(self, start, end, pause=False, loop_callback_fn=None):
        """Plays the player in a loop, optionally pausing at the end of the loop, optionally calling a callback when
        the end is reaced."""
        self.stop()
        self.pause_on_loop = pause
        self.loop_callback = loop_callback_fn
        self.loop_start = float(start)
        self.loop_end = float(end)
        self.play()

    def _halt_playback(self):
        """If player is playing, stop it. Ring callback. Return playback timestamp."""
        if self.media_path is None:
            ptime = time.time() - self.start_time
        else:
            ptime = float(self.player.get_time() / 1000)
            if self.player.is_playing() == 1:
                self.player.stop()

        # Ring callback function
        if self.is_playing is True:
            self.is_playing = False
            if self.finish_callback is not None:
                self.finish_callback(self.media_path, ptime)
        return ptime

    def _check_playback(self):
        """(internal) check the status of playback and whether it's finished, ping callbacks, set flags"""
        # Check if active flag is cleared, stop playback
        if self.is_playing:
            # Check for thread halt
            if self.is_active is False:
                ptime = self._halt_playback()
            else:
                # Check the player time to fire armed callback
                if self.media_path is not None and self.start_callback_armed:
                    ptime = self.get_time()
                    if ptime > 0.0:
                        self.start_callback(self.media_path, ptime)
                        self.start_callback_armed = False

                # Check whether playback length is set and exceeded
                if float(self.playback_length) > 0.0:
                    if self.get_time() >= self.playback_length:
                        ptime = self._halt_playback()
                else:
                    # Check if looping, end reached?
                    if self._is_looping():
                        ptime = self.get_time()
                        if ptime >= self.loop_end:
                            if self.media_path is not None:
                                self.player.set_time(int(self.loop_start * 1000))
                            if self.pause_on_loop:
                                self.pause()
                            if self.loop_callback is not None:
                                self.loop_callback(self.media_path, self.get_time())
                    else:
                        # Check whether player reached the end (self.is_playing still set)
                        if self.media_path is not None:
                            if self.player.is_playing() == 0:
                                ptime = self._halt_playback()

            # Call the finish callback
            if self.is_playing is False:
                if self.finish_callback is not None:
                    self.finish_callback(self.media_path, ptime)

    def _check_interval(self):
        """Checks whether it's time for an interval callback and rings it if so"""
        if self.is_playing and self.interval_callback is not None:
            now = time.time()
            if (now - self.interval_period) > self.interval_last_checked:
                self.interval_callback(self.media_path, now)
                self.interval_last_checked = now

    def _is_looping(self):
        """Is this thing looping?"""
        return self.loop_end > 0.0 and self.loop_end > self.loop_start
