"""

Dynamic Pipeline Example.

rtmpsrc -> ... -> videosink.

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

        self.src = Gst.ElementFactory.make("rtmpsrc")
        self.demux = Gst.ElementFactory.make("flvdemux")
        self.demux_v_que = Gst.ElementFactory.make("queue")
        self.h264parse = Gst.ElementFactory.make("h264parse")

        self.vdec = Gst.ElementFactory.make("omxh264dec")
        self.vconv = Gst.ElementFactory.make("nvvidconv")
        self.caps = Gst.ElementFactory.make("capsfilter")
        self.vsink = Gst.ElementFactory.make("nvoverlaysink")

        # self.vdec = Gst.ElementFactory.make("avdec_h264")
        # self.vconv = Gst.ElementFactory.make("videoscale")
        # self.caps = Gst.ElementFactory.make("capsfilter")
        # self.vsink = Gst.ElementFactory.make("glimagesink")

        self.demux_a_que = Gst.ElementFactory.make("queue")
        self.asink = Gst.ElementFactory.make("fakesink")

        self.pipeline.add(self.src)
        self.pipeline.add(self.demux)
        self.pipeline.add(self.demux_v_que)
        self.pipeline.add(self.h264parse)
        self.pipeline.add(self.vdec)
        self.pipeline.add(self.vconv)
        self.pipeline.add(self.caps)
        self.pipeline.add(self.vsink)
        self.pipeline.add(self.demux_a_que)
        self.pipeline.add(self.asink)

        # take the commandline argument and ensure that it is a uri
        if Gst.uri_is_valid(args[1]):
            uri = args[1]
        else:
            uri = Gst.filename_to_uri(args[1])

        self.src.set_property('location', uri)
        # self.vdec.set_property('disable-dpb', True)

        # capsprop = Gst.Caps.from_string("video/x-raw(memory:NVMM)")
        # self.caps.set_property("caps", capsprop)

        self.src.link(self.demux)
        self.demux.connect("pad-added", self.pad_added_handler)

        self.demux_v_que.link(self.h264parse)
        self.h264parse.link(self.vdec)
        self.vdec.link(self.vconv)
        self.vconv.link(self.caps)
        self.caps.link(self.vsink)

        self.demux_a_que.link(self.asink)

        # create and event loop and feed gstreamer bus mesages to it
        self.loop = GObject.MainLoop()

        GLib.timeout_add_seconds(5, self.timeout_cb)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        # start play back and listed to events
        self.pipeline.set_state(Gst.State.PLAYING)
        try:
            self.loop.run()

        except:
            pass

        # cleanup
        self.pipeline.set_state(Gst.State.NULL)

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
            new_pad.link(self.demux_a_que.get_static_pad("sink"))

        elif new_pad_type.startswith("video"):
            print("  It has type '%s' which is video." %
                  new_pad_type)
            new_pad.link(self.demux_v_que.get_static_pad("sink"))
        else:
            print("error!")

        return

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            sys.stdout.write("End-of-stream\n")
            self.loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            sys.stderr.write("Error: %s: %s\n" % (err, debug))
            self.loop.quit()
        return True

    def probe_cb(self, pad, info):
        print("called probe_cb")
        self.caps.set_state(Gst.State.NULL)
        self.pipeline.remove(self.caps)

        self.caps = Gst.ElementFactory.make('capsfilter')
        self.pipeline.add(self.caps)
        # capsprop = Gst.Caps.from_string(
        #     "video/x-raw(memory:NVMM), width=480, height=270")
        # self.caps.set_property("caps", capsprop)
        self.caps.sync_state_with_parent()

        self.vconv.link(self.caps)
        self.caps.link(self.vsink)
        self.caps.set_state(Gst.State.PLAYING)

        return Gst.PadProbeReturn.REMOVE

    def timeout_cb(self):
        print("called timeout_cb")
        srcpad = self.src.get_static_pad('src')
        srcpad.add_probe(Gst.PadProbeType.IDLE, self.probe_cb)
        return True


def main(args):
    if len(args) != 2:
        sys.stderr.write("usage: %s <media file or uri>\n" % args[0])
        sys.exit(1)

    GObject.threads_init()
    Gst.init(None)
    Launcher(args)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
