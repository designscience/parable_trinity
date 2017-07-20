import kivy
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.image import Image
# from kivy.properties import ListProperty, NumericProperty, ReferenceListProperty, ObjectProperty
# from kivy.config import Config
# from kivy.graphics import Canvas
# from kivy.uix.label import Label
from kivy.animation import Animation
# import logging
import time


class UserInterface(FloatLayout):
    pass


class HomeScreen(FloatLayout):
    def __init__(self, main_app):
        self.app = main_app
        self.test_me = False
        super(FloatLayout, self).__init__()

    def clear(self):
        self.ids.light_panel.clear_widgets()


class ChannelLight(RelativeLayout):
    def __init__(self, index):
        """Init uses an index starting at 0 to load the correct flame image file"""
        super(RelativeLayout, self).__init__()
        if index % 3 == 0:
            self.on_source = 'images/flame-northwest.png'
            self.off_source = 'images/pilot-northwest.png'
        elif index % 3 == 1:
            self.on_source = 'images/flame-north.png'
            self.off_source = 'images/pilot-north.png'
        else:
            self.on_source = 'images/flame-northeast.png'
            self.off_source = 'images/pilot-northeast.png'
        self.ids.flame.source = self.off_source

    def on(self):
        self.ids.flame.source = self.on_source

    def off(self):
        self.ids.flame.source = self.off_source

