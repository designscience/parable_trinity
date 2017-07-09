import threading
import vlc

# A class intended for threaded operation, instantiates a VLC media player and operates it


class ParaPlayer(threading.Thread):

    def __init__(self, timeout = 0):
        threading.Thread.__init__(self)
        self.timeout = timeout
        self.vlc

    def start(self):
        print("Starting media thread")
