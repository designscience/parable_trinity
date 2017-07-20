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
            self.ids.flame.source = 'images/flame-northwest.png'
        elif index % 3 == 1:
            self.ids.flame.source = 'images/flame-north.png'
        else:
            self.ids.flame.source = 'images/flame-northeast.png'

    def on(self):
        self.opacity = 1.0
        self.ids.flame.canvas.ask_update()

    def off(self):
        self.opacity = 0.0
        self.ids.flame.canvas.ask_update()

