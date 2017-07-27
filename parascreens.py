import kivy
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.button import Button
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
# from kivy.uix.widget import Widget
# from kivy.core.window import Window
# from kivy.uix.image import Image
# from kivy.properties import ListProperty, NumericProperty, ReferenceListProperty, ObjectProperty
# from kivy.config import Config
# from kivy.graphics import Canvas
# from kivy.uix.label import Label
# from kivy.animation import Animation
# import logging
# import time


class UserInterface(FloatLayout):
    pass


class HomeScreen(FloatLayout):
    def __init__(self, main_app):
        self.app = main_app
        self.test_me = False
        # self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        # self._keyboard.bind(on_key_down=self._on_keyboard_down)
        super(FloatLayout, self).__init__()
        self.hide_recorder_controls()

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        """Handle key presses"""
        try:
            val = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0].index(int(keycode[1])) + 1
            if val == 0:
                val = 10
            self.app.fire_channel(val)
            return True
        except:
            pass
        print('keycode ({}, {}) received'.format(keycode[0], keycode[1]))
        return True

    def _keyboard_closed(self):
        """Close keyboard object"""
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def clear(self):
        self.ids.light_panel.clear_widgets()

    def show_recorder_controls(self):
        self.ids.recorder_panel.disabled = False

    def hide_recorder_controls(self):
        self.ids.recorder_panel.disabled = True


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


class SequenceButton(Button):
    def __init__(self, sequence_name, app: App):
        """A button with which to control a sequence"""
        super(Button, self).__init__()
        self.trigger_time = 0.0
        self.sequence_name = sequence_name
        self.text = sequence_name
        self.app = app

    def show_running(self):
        self.background_color = [1, 1, 1, 1]
        self.color = [0, 0, 0, 1]

    def show_stopped(self):
        self.background_color = [0.3, 0.3, 0.3, 1]
        self.color = [1, 1, 1, 1]


class ShowListItem(BoxLayout):
    def __init__(self, app, item_index, item_type, media_file):
        super(BoxLayout, self).__init__()
        self.item_index = item_index
        self.ids.item_type.text = item_type
        self.ids.media_file.text = media_file
        self.app = app
        if item_type != 'music':
            self.ids.btn_record.opacity = 0.0

    def set_active(self):
        pass

    def clear_active(self):
        pass
