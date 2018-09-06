"""

Multiply viewer.

"""

import sys

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
from gi.repository import GObject, Gst, GLib


class MediaSource:
    def __init__(self, pipeline, endpoint):
        self.pipeline = pipeline

        # Make elements
        self.src = Gst.ElementFactory.make('rtmpsrc')
        self.demux = Gst.ElementFactory.make('flvdemux')

        self.v_que = Gst.ElementFactory.make('queue')
        self.v_parse = Gst.ElementFactory.make('h264parse')

        self.v_dec = Gst.ElementFactory.make('omxh264dec')
        self.v_conv = Gst.ElementFactory.make('nvvidconv')

        self.v_caps = Gst.ElementFactory.make('capsfilter')
        self.v_tee = Gst.ElementFactory.make('tee')

        self.a_que = Gst.ElementFactory.make('queue')
        self.a_sink = Gst.ElementFactory.make('fakesink')

        # Add elements
        self.pipeline.add(self.src)
        self.pipeline.add(self.demux)
        self.pipeline.add(self.v_que)
        self.pipeline.add(self.v_parse)
        self.pipeline.add(self.v_dec)
        self.pipeline.add(self.v_conv)
        self.pipeline.add(self.v_caps)
        self.pipeline.add(self.v_tee)

        self.pipeline.add(self.a_que)
        self.pipeline.add(self.a_sink)

        # Set elements
        if Gst.uri_is_valid(endpoint):
            self.uri = endpoint
        else:
            self.uri = Gst.filename_to_uri(endpoint)

        self.src.set_property('location', self.uri)

        caps_prop = Gst.Caps.from_string('video/x-raw')
        self.v_caps.set_property('caps', caps_prop)

        # Link elements
        self.src.link(self.demux)
        self.demux.connect('pad-added', self.pad_added_handler)

        self.v_que.link(self.v_parse)
        self.v_parse.link(self.v_dec)
        self.v_dec.link(self.v_conv)
        self.v_conv.link(self.v_caps)
        self.v_caps.link(self.v_tee)

        self.a_que.link(self.a_sink)

        self.v_tee_ques = []

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
            new_pad.link(self.a_que.get_static_pad("sink"))

        elif new_pad_type.startswith("video"):
            print("  It has type '%s' which is video." %
                  new_pad_type)
            new_pad.link(self.v_que.get_static_pad("sink"))
        else:
            print("error!")

    def link(self, pad, name):
        tee_que = Gst.ElementFactory.make('queue', name)
        self.pipeline.add(tee_que)
        self.v_tee.link(tee_que)
        tee_que.get_static_pad('src').link(pad)

    def unlink(self, name):
        self.pipeline.remove(self.pipeline.get_by_name(name))

    def relink(self, pad, old_name, new_name):
        self.unlink(old_name)
        self.link(pad, new_name)


class MediaSink:
    def __init__(self, pipeline):
        self.pipeline = pipeline

        # Make elements
        self.v_comp = Gst.ElementFactory.make('nvcompositor')
        self.v_sink = Gst.ElementFactory.make('nvoverlaysink')

        self.v_sink.set_property('sync', 'true')

        # Add elements
        self.pipeline.add(self.v_comp)
        self.pipeline.add(self.v_sink)

        self.v_comp.link(self.v_sink)

        self.v_comp_sink_pads = {}

    def request_pad(self, xpos, ypos, width, height, name=None):
        comp_sink_pad_temp = self.v_comp.get_pad_template('sink_%u')
        comp_sink_pad = self.v_comp.request_pad(comp_sink_pad_temp, None, None)

        comp_sink_pad.set_property('xpos', xpos)
        comp_sink_pad.set_property('ypos', ypos)
        comp_sink_pad.set_property('width', width)
        comp_sink_pad.set_property('height', height)

        self.v_comp_sink_pads[name] = comp_sink_pad

        return comp_sink_pad

    def get_pad(self, name):
        return self.v_comp_sink_pads[name]


class Launcher:
    def __init__(self, args):
        Gst.init(None)

        self.pipeline = Gst.Pipeline.new()
        self.media_sources = []
        self.media_sources.append(MediaSource(self.pipeline, args[1]))
        self.media_sources.append(MediaSource(self.pipeline, args[2]))
        self.media_sink = MediaSink(self.pipeline)

        self.media_sources[0].link(self.media_sink.request_pad(0, 0, 960, 540, 'PRE'), 'PRE')
        self.media_sources[1].link(self.media_sink.request_pad(960, 0, 960, 540, 'PGM'), 'PGM')
        self.media_sources[0].link(self.media_sink.request_pad(0, 540, 480, 270), '1')
        self.media_sources[0].link(self.media_sink.request_pad(480, 540, 480, 270), '2')
        self.media_sources[0].link(self.media_sink.request_pad(960, 540, 480, 270), '3')
        self.media_sources[1].link(self.media_sink.request_pad(0, 810, 480, 270), '4')
        self.media_sources[1].link(self.media_sink.request_pad(480, 810, 480, 270), '5')
        self.media_sources[1].link(self.media_sink.request_pad(960, 810, 480, 270), '6')

        self.loop = ''

        self.flag = False

    def execute(self):
        # create and event loop and feed gstreamer bus messages to it
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

    def timeout_cb(self):
        print('called timeout_cb BEGIN')

        srcpad = self.media_sources[0].src.get_static_pad('src')
        srcpad.add_probe(Gst.PadProbeType.IDLE, self.probe_cb)

        # srcpad = self.sources[0].src.get_static_pad('src')
        # srcpad.add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM, self.probe_cb3)

        print('called timeout_cb END')
        return True

    def probe_cb(self, pad, info):
        print('called probe_cb BEGIN')

        # self.sources[0].tee.set_state(Gst.State.NULL)
        self.pipeline.set_state(Gst.State.NULL)

        if self.flag:
            ids = [0, 1]
            self.flag = False
        else:
            ids = [1, 0]
            self.flag = True

        self.media_sources[ids[0]].unlink('PRE')
        self.media_sources[ids[1]].relink(self.media_sink.get_pad('PRE'), 'PGM', 'PRE')
        self.media_sources[ids[0]].link(self.media_sink.get_pad('PGM'), 'PGM')

        # self.sources[0].tee.set_state(Gst.State.PLAYING)
        self.pipeline.set_state(Gst.State.PLAYING)
        print('called probe_cb END')

        return Gst.PadProbeReturn.REMOVE


def main(args):
    if len(args) != 3:
        sys.stderr.write('usage: %s <media file or uri>\n' % args[0])
        sys.exit(1)

    Launcher(args).execute()


if __name__ == '__main__':
    sys.exit(main(sys.argv))