# import kivy
from kivy.uix.floatlayout import FloatLayout
# from kivy.uix.widget import Widget
# from kivy.uix.button import Button
# from kivy.properties import ListProperty, NumericProperty, ReferenceListProperty, ObjectProperty
# from kivy.config import Config
# from kivy.graphics import Canvas
# from kivy.uix.label import Label
# import logging
import time


class HomeScreen(FloatLayout):
    def __init__(self, main_app):
        self.app = main_app
        self.test_me = False
        super(FloatLayout, self).__init__()

    def test1(self):
        print('running test 1')
        # self.player.play()
        time.sleep(1)
        # self.player.kill()
        print('test 1 complete')

    def test2(self):
        print('running test 2')
        # self.player.play()
        time.sleep(1)
        # self.player.kill()
        print('test 2 complete')

