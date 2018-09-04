"""

a Dynamic Pipeline Example on Jetson.

videotestsrc x2 -> ... -> videosink.

"""

import sys

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
from gi.repository import GObject, Gst, GLib


"""
Launcher.
"""


class Launcher:
    def __init__(self, args):
        self.pipeline = Gst.Pipeline.new()

        # Make
        self.src1 = Gst.ElementFactory.make('videotestsrc')
        self.tee1 = Gst.ElementFactory.make('tee')
        self.que1 = Gst.ElementFactory.make('queue')
        self.src2 = Gst.ElementFactory.make('videotestsrc')
        self.tee2 = Gst.ElementFactory.make('tee')
        self.que2 = Gst.ElementFactory.make('queue')

        self.mix = Gst.ElementFactory.make('glvideomixer')
        self.vconv = Gst.ElementFactory.make('nvvidconv')
        # self.caps = Gst.ElementFactory.make('capsfilter')
        self.sink = Gst.ElementFactory.make('glimagesink')

        self.pipeline.add(self.src1)
        self.pipeline.add(self.tee1)
        self.pipeline.add(self.que1)
        self.pipeline.add(self.src2)
        self.pipeline.add(self.tee2)
        self.pipeline.add(self.que2)
        self.pipeline.add(self.mix)
        self.pipeline.add(self.vconv)
        # self.pipeline.add(self.caps)
        self.pipeline.add(self.sink)

        # Set
        self.src1.set_property('pattern', 0)
        self.src2.set_property('pattern', 24)

        self.capsprop = Gst.Caps.from_string('video/x-raw(memory:NVMM)')
        # self.caps.set_property('caps', capsprop)

        self.src_filter = Gst.Caps.from_string('video/x-raw, width=960, height=540')

        # Link
        self.src1.link_filtered(self.tee1, self.src_filter)
        self.tee1.link(self.que1)
        self.mix_sink_pad1 = self.mix.request_pad(self.mix.get_pad_template('sink_%u'), None, None)
        self.mix_sink_pad1.set_property('xpos', 0)
        self.mix_sink_pad1.set_property('ypos', 0)
        self.mix_sink_pad1.set_property('width', 960)
        self.mix_sink_pad1.set_property('height', 540)
        self.que1.get_static_pad('src').link(self.mix_sink_pad1)

        self.src2.link_filtered(self.tee2, self.src_filter)
        self.tee2.link(self.que2)
        self.mix_sink_pad2 = self.mix.request_pad(self.mix.get_pad_template('sink_%u'), None, None)
        self.mix_sink_pad2.set_property('xpos', 960)
        self.mix_sink_pad2.set_property('ypos', 540)
        self.mix_sink_pad2.set_property('width', 960)
        self.mix_sink_pad2.set_property('height', 540)
        self.que2.get_static_pad('src').link(self.mix_sink_pad2)

        self.mix.link(self.sink)
        self.vconv.link_filtered(self.sink, self.capsprop)
        # self.caps.link(self.sink)

        # self.pipeline.connect('deep-notify', self.notify)

        # create and event loop and feed gstreamer bus mesages to it
        self.loop = GLib.MainLoop()

        GLib.timeout_add_seconds(3, self.timeout_cb)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_message)

        # start play back and listed to events
        self.pipeline.set_state(Gst.State.PLAYING)

        try:
            self.loop.run()

        except:
            pass

        # cleanup
        self.pipeline.set_state(Gst.State.NULL)

    def notify(self, sender, obj, arg):
        prop = obj.get_property(arg.name)
        # print('notify', sender, arg.name, prop)
        print(prop)

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            sys.stdout.write('End-of-stream\n')
            self.loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            sys.stderr.write('Error: %s: %s\n' % (err, debug))
            self.loop.quit()
        return True

    def probe_cb2(self, pad, info):
        print('called probe_cb2 START')

        self.que2.set_state(Gst.State.NULL)

        self.pipeline.remove(self.que2)
        self.que2 = Gst.ElementFactory.make('queue')
        self.pipeline.add(self.que2)
        self.tee2.link(self.que2)

        self.que2.get_static_pad('src').link(self.mix_sink_pad1)
        self.que2.set_state(Gst.State.PLAYING)

        print('called probe_cb2 END')
        return Gst.PadProbeReturn.REMOVE

    def probe_cb(self, pad, info):
        print('called probe_cb START')

        self.que1.set_state(Gst.State.NULL)

        self.pipeline.remove(self.que1)
        self.que1 = Gst.ElementFactory.make('queue')
        self.pipeline.add(self.que1)
        self.tee1.link(self.que1)

        srcpad = self.src2.get_static_pad('src')
        srcpad.add_probe(Gst.PadProbeType.IDLE, self.probe_cb2)

        self.que1.get_static_pad('src').link(self.mix_sink_pad2)
        self.que1.set_state(Gst.State.PLAYING)

        print('called probe_cb END')
        return Gst.PadProbeReturn.REMOVE

    def timeout_cb(self):
        print('called timeout_cb START')

        srcpad = self.src1.get_static_pad('src')
        srcpad.add_probe(Gst.PadProbeType.IDLE, self.probe_cb)

        print('called timeout_cb END')
        return True


def main(args):
    Gst.init(None)
    Launcher(args)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
