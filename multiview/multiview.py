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

    def link(self, pad, name, width = 480, height = 270):
        mm = MediaMediator(self.pipeline, name, width, height)
        self.v_tee.link(mm.get_sink())
        mm.get_src().get_static_pad('src').link(pad)

    def unlink(self, name):
        self.pipeline.remove(self.pipeline.get_by_name(name))

    def relink(self, pad, old_name, new_name):
        self.unlink(old_name)
        self.link(pad, new_name)


class MediaMediator:
    def __init__(self, pipeline, name, width, height):
        self.pipeline = pipeline

        # Make elements
        self.v_que = Gst.ElementFactory.make('queue', name)
        self.v_to = Gst.ElementFactory.make('textoverlay')
        self.v_conv = Gst.ElementFactory.make('nvvidconv')
        self.v_caps = Gst.ElementFactory.make('capsfilter')

        self.pipeline.add(self.v_que)
        self.pipeline.add(self.v_to)
        self.pipeline.add(self.v_conv)
        self.pipeline.add(self.v_caps)

        self.v_to.set_property('text', name)
        self.v_to.set_property('valignment', 'top')
        self.v_to.set_property('halignment', 'left')
        self.v_to.set_property('font-desc', 'Sans, 20')

        if width != 0 and height != 0:
            caps_prop = Gst.Caps.from_string('video/x-raw, width=(int)%d, height=(int)%d' % (width, height))
        else:
            caps_prop = Gst.Caps.from_string('video/x-raw')

        self.v_caps.set_property('caps', caps_prop)

        self.v_que.link(self.v_to)
        self.v_to.link(self.v_conv)
        self.v_conv.link(self.v_caps)

    def get_sink(self):
        return self.v_que

    def get_src(self):
        return  self.v_caps


class MediaSink:
    def __init__(self, pipeline):
        self.pipeline = pipeline

        # Make elements
        self.v_comp = Gst.ElementFactory.make('nvcompositor')
        self.v_sink = Gst.ElementFactory.make('fpsdisplaysink')
        # self.v_sink.set_property('video-sink', 'nvoverlaysink')
        self.v_sink.set_property('text-overlay', False)
        self.v_sink.set_property('signal-fps-measurements', True)
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


class MediaRtmpSink:
    def __init__(self, pipeline):
        self.pipeline = pipeline

        # Make elements
        self.v_pgm_que = Gst.ElementFactory.make('queue')
        self.v_pre_que = Gst.ElementFactory.make('queue')
        self.v_comp = Gst.ElementFactory.make('glvideomixer')
        self.v_comp_que = Gst.ElementFactory.make('queue')
        self.v_enc = Gst.ElementFactory.make('omxh264enc')
        self.v_parse = Gst.ElementFactory.make('h264parse')
        self.mux = Gst.ElementFactory.make('flvmux')
        self.mux_tee = Gst.ElementFactory.make('tee')
        self.sink = Gst.ElementFactory.make('rtmpsink')

        # Add elements
        self.pipeline.add(self.v_pgm_que)
        self.pipeline.add(self.v_pre_que)
        self.pipeline.add(self.v_comp)
        self.pipeline.add(self.v_comp_que)
        self.pipeline.add(self.v_enc)
        self.pipeline.add(self.v_parse)
        self.pipeline.add(self.mux)
        self.pipeline.add(self.mux_tee)
        self.pipeline.add(self.sink)

        # Set elements
        self.mux.set_property('streamable', True)
        self.sink.set_property('location', 'rtmp://192.168.0.11/live/s0')

        # Link elements
        self.v_comp_sink_pads = {}

        comp_sink_pad_temp = self.v_comp.get_pad_template('sink_%u')
        self.v_comp_sink_pads['PGM'] = self.v_comp.request_pad(comp_sink_pad_temp, None, None)

        self.v_comp_sink_pads['PGM'].set_property('xpos', 0)
        self.v_comp_sink_pads['PGM'].set_property('ypos', 0)
        self.v_comp_sink_pads['PGM'].set_property('width', 1920)
        self.v_comp_sink_pads['PGM'].set_property('height', 1080)

        self.v_comp_sink_pads['PRE'] = self.v_comp.request_pad(comp_sink_pad_temp, None, None)

        self.v_comp_sink_pads['PRE'].set_property('xpos', 1220)
        self.v_comp_sink_pads['PRE'].set_property('ypos', 660)
        self.v_comp_sink_pads['PRE'].set_property('width', 640)
        self.v_comp_sink_pads['PRE'].set_property('height', 360)

        self.v_pgm_que.get_static_pad('src').link(self.v_comp_sink_pads['PGM'])
        self.v_pre_que.get_static_pad('src').link(self.v_comp_sink_pads['PRE'])
        self.v_comp.link(self.v_comp_que)
        self.v_comp_que.link(self.v_enc)
        self.v_enc.link(self.mux)
        self.mux.link(self.mux_tee)
        self.mux_tee.link(self.sink)

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
        self.media_sources.append(MediaSource(self.pipeline, args[3]))
        self.media_sources.append(MediaSource(self.pipeline, args[4]))
        self.media_sources.append(MediaSource(self.pipeline, args[5]))
        self.media_sources.append(MediaSource(self.pipeline, args[6]))
        self.media_sink = MediaSink(self.pipeline)

        self.media_rtmp_sink = MediaRtmpSink(self.pipeline)
        self.media_sources[0].v_tee.link(self.media_rtmp_sink.v_pgm_que)
        self.media_sources[1].v_tee.link(self.media_rtmp_sink.v_pre_que)

        self.media_sources[0].link(self.media_sink.request_pad(0, 0, 960, 540, 'PRE'), 'PRE', 960, 540)
        self.media_sources[1].link(self.media_sink.request_pad(960, 0, 960, 540, 'PGM'), 'PGM', 960, 540)
        self.media_sources[0].link(self.media_sink.request_pad(0, 540, 480, 270), '1', 0, 0)
        self.media_sources[1].link(self.media_sink.request_pad(480, 540, 480, 270), '2', 0, 0)
        self.media_sources[2].link(self.media_sink.request_pad(960, 540, 480, 270), '3')
        self.media_sources[3].link(self.media_sink.request_pad(0, 810, 480, 270), '4')
        self.media_sources[4].link(self.media_sink.request_pad(480, 810, 480, 270), '5')
        self.media_sources[5].link(self.media_sink.request_pad(960, 810, 480, 270), '6')

        self.loop = ''

        self.flag = False

    def execute(self):
        # self.pipeline.connect('deep-notify', self.notify)

        # create and event loop and feed gstreamer bus messages to it
        self.loop = GLib.MainLoop()

        # GLib.timeout_add_seconds(3, self.timeout_cb)

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
    if len(args) != 7:
        sys.stderr.write('usage: %s <media file or uri>\n' % args[0])
        sys.exit(1)

    Launcher(args).execute()


if __name__ == '__main__':
    sys.exit(main(sys.argv))