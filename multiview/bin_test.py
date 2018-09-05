"""

Input Bin

"""

import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
from gi.repository import GObject, Gst, GLib


class InputBin:
    def __init__(self, endpoint):
        self.bin = Gst.Bin.new(None)

        # Make elements
        self.src = Gst.ElementFactory.make('rtmpsrc')
        self.demux = Gst.ElementFactory.make('flvdemux')

        self.vque = Gst.ElementFactory.make('queue')
        self.h264parse = Gst.ElementFactory.make('h264parse')

        # For jetson and mac
        # self.vdec = Gst.ElementFactory.make('avdec_h264')
        # self.vconv = Gst.ElementFactory.make('videoscale')

        # For jetson only
        self.vdec = Gst.ElementFactory.make('omxh264dec')
        self.vconv = Gst.ElementFactory.make('nvvidconv')

        self.caps = Gst.ElementFactory.make('capsfilter')
        # self.vtee = Gst.ElementFactory.make('tee')

        self.aque = Gst.ElementFactory.make('queue')
        self.asink = Gst.ElementFactory.make('fakesink')

        # Add elements
        self.bin.add(self.src)
        self.bin.add(self.demux)
        self.bin.add(self.vque)
        self.bin.add(self.h264parse)
        self.bin.add(self.vdec)
        self.bin.add(self.vconv)
        self.bin.add(self.caps)
        # self.bin.add(self.vtee)

        self.bin.add(self.aque)
        self.bin.add(self.asink)

        # Set elements
        if Gst.uri_is_valid(endpoint):
            self.uri = endpoint
        else:
            self.uri = Gst.filename_to_uri(endpoint)

        self.src.set_property('location', self.uri)

        # capsprop = Gst.Caps.from_string('video/x-raw')
        # self.caps.set_property('caps', capsprop)

        # Link elements
        self.src.link(self.demux)
        self.demux.connect('pad-added', self.pad_added_handler)

        self.vque.link(self.h264parse)
        self.h264parse.link(self.vdec)
        self.vdec.link(self.vconv)
        self.vconv.link(self.caps)
        # self.caps.link(self.vtee)

        self.aque.link(self.asink)

        caps_pad = self.caps.get_static_pad('src')
        ghost_pad = Gst.GhostPad.new('src', caps_pad)
        ghost_pad.set_active(True)
        self.bin.add_pad(ghost_pad)

    def pad_added_handler(self, src, new_pad):
        print("Received new pad '%s' from '%s':" % (new_pad.get_name(),
              src.get_name()))

        # If our converter is already linked, we have nothing to do here
        if new_pad.is_linked():
            print("We are already linked. Ignoring.")
            return

        # Check the new pad's type
        new_pad_type = new_pad.query_caps(None).to_string()

        if new_pad_type.startswith("audio"):
            print("  It has type '%s' which is audio." %
                  new_pad_type)
            new_pad.link(self.aque.get_static_pad("sink"))

        elif new_pad_type.startswith("video"):
            print("  It has type '%s' which is video." %
                  new_pad_type)
            new_pad.link(self.vque.get_static_pad("sink"))
        else:
            print("error!")

    def get_bin(self):
        return self.bin

    # def link(self, elem):
    #     return self.vtee.link(elem)


class OutputBin:
    def __init__(self):
        self.bin = Gst.Bin.new(None)

        # self.comp = Gst.ElementFactory.make('glvideomixer')
        # self.sink = Gst.ElementFactory.make('glimagesink')
        self.comp = Gst.ElementFactory.make('nvcompositor')
        self.sink = Gst.ElementFactory.make('nvoverlaysink')

        self.bin.add(self.comp)
        self.bin.add(self.sink)

        self.comp.link(self.sink)

    def request_pad(self, xpos, ypos, width, height):
        comp_sink_pad_temp = self.comp.get_pad_template('sink_%u')
        comp_sink_pad = self.comp.request_pad(comp_sink_pad_temp)

        comp_sink_pad.set_property('xpos', xpos)
        comp_sink_pad.set_property('ypos', ypos)
        comp_sink_pad.set_property('width', width)
        comp_sink_pad.set_property('height', height)

        return comp_sink_pad

    def get_bin(self):
        return self.bin


class VideoSink:
    def __init__(self, pipeline):
        self.pipeline = pipeline

        # For jetson only
        # self.comp = Gst.ElementFactory.make('nvcompositor')
        # self.sink = Gst.ElementFactory.make('nvoverlaysink')
        # self.sink.set_property('video-sink', 'nvoverlaysink')
        # self.sink.set_property('text-overlay', False)
        # self.sink.set_property('signal-fps-measurements', True)

        # For jetson and mac
        self.comp = Gst.ElementFactory.make('glvideomixer')
        self.sink = Gst.ElementFactory.make('glimagesink')

        self.pipeline.add(self.comp)
        self.pipeline.add(self.sink)

        self.comp.link(self.sink)

        self.comp_sink_pads = []

    def request_pad(self, xpos, ypos, width, height):
        comp_sink_pad_temp = self.comp.get_pad_template('sink_%u')
        comp_sink_pad = self.comp.request_pad(comp_sink_pad_temp, None, None)

        comp_sink_pad.set_property('xpos', xpos)
        comp_sink_pad.set_property('ypos', ypos)
        comp_sink_pad.set_property('width', width)
        comp_sink_pad.set_property('height', height)

        self.comp_sink_pads.append(comp_sink_pad)

        return comp_sink_pad


class Launcher:
    def __init__(self, args):
        self.pipeline = Gst.Pipeline.new()
        self.ib = InputBin(args[1])

        self.tee1 = Gst.ElementFactory.make('tee')
        self.que1 = Gst.ElementFactory.make('queue')
        self.que2 = Gst.ElementFactory.make('queue')

        self.pipeline.add(self.ib.get_bin())
        self.pipeline.add(self.tee1)
        self.pipeline.add(self.que1)
        self.pipeline.add(self.que2)
        self.vsink = VideoSink(self.pipeline)

        self.ib.get_bin().link(self.tee1)
        self.tee1.link(self.que1)
        self.tee1.link(self.que2)

        self.que1.get_static_pad('src').link(self.vsink.request_pad(0, 0, 960, 540))
        self.que2.get_static_pad('src').link(self.vsink.request_pad(960, 540, 960, 540))

        # create and event loop and feed gstreamer bus messages to it
        self.loop = GLib.MainLoop()

        # self.pipeline.connect('deep-notify', self.notify)

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

    def probe_cb(self, pad, info):
        print('called probe_cb BEGIN')

        self.ib.get_bin().set_state(Gst.State.NULL)
        # self.pipeline.set_state(Gst.State.NULL)

        self.ib.get_bin().set_state(Gst.State.PLAYING)
        # self.pipeline.set_state(Gst.State.PLAYING)

        print('called probe_cb END')
        return Gst.PadProbeReturn.REMOVE

    def timeout_cb(self):
        print('called timeout_cb BEGIN')

        srcpad = self.ib.get_bin().get_static_pad('src')
        srcpad.add_probe(Gst.PadProbeType.IDLE, self.probe_cb)

        print('called timeout_cb END')
        return True


def main(args):
    if len(args) != 2:
        sys.stderr.write('usage: %s <media file or uri>\n' % args[0])
        sys.exit(1)

    Gst.init(None)
    Launcher(args)


if __name__ == '__main__':
    sys.exit(main(sys.argv))