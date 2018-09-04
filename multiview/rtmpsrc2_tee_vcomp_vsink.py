"""

a Dynamic Pipeline Example on Jetson.

rtmpsrc -> ... -> videosink.

"""

import sys

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
from gi.repository import GObject, Gst, GLib


class Source:
    def __init__(self, pipeline, endpoint):
        self.pipeline = pipeline

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
        self.tee = Gst.ElementFactory.make('tee')

        self.aque = Gst.ElementFactory.make('queue')
        self.asink = Gst.ElementFactory.make('fakesink')

        # Add elements
        self.pipeline.add(self.src)
        self.pipeline.add(self.demux)
        self.pipeline.add(self.vque)
        self.pipeline.add(self.h264parse)
        self.pipeline.add(self.vdec)
        self.pipeline.add(self.vconv)
        self.pipeline.add(self.caps)
        self.pipeline.add(self.tee)

        self.pipeline.add(self.aque)
        self.pipeline.add(self.asink)

        # Set elements
        if Gst.uri_is_valid(endpoint):
            self.uri = endpoint
        else:
            self.uri = Gst.filename_to_uri(endpoint)

        self.src.set_property('location', self.uri)

        capsprop = Gst.Caps.from_string('video/x-raw')
        self.caps.set_property('caps', capsprop)

        # Link elements
        self.src.link(self.demux)
        self.demux.connect('pad-added', self.pad_added_handler)

        self.vque.link(self.h264parse)
        self.h264parse.link(self.vdec)
        self.vdec.link(self.vconv)
        self.vconv.link(self.caps)
        self.caps.link(self.tee)

        self.aque.link(self.asink)

        self.tee_src_pads = []

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

        return

    def link_pad(self, pad):
        tee_src_pad_temp = self.tee.get_pad_template('src_%u')
        tee_src_pad = self.tee.request_pad(tee_src_pad_temp, None, None)
        tee_src_pad.link(pad)

        self.tee_src_pads.append(tee_src_pad)
        self.tee_src_pad = tee_src_pad


class VideoSink:
    def __init__(self, pipeline):
        self.pipeline = pipeline

        # For jetson only
        self.comp = Gst.ElementFactory.make('nvcompositor')
        self.sink = Gst.ElementFactory.make('nvoverlaysink')
        # self.sink.set_property('video-sink', 'nvoverlaysink')
        # self.sink.set_property('text-overlay', False)
        # self.sink.set_property('signal-fps-measurements', True)

        # For jetson and mac
        # self.comp = Gst.ElementFactory.make('glvideomixer')
        # self.sink = Gst.ElementFactory.make('glimagesink')

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


"""
Launcher.
"""


class Launcher:
    def __init__(self, args):
        self.once = False
        self.once2 = False

        self.pipeline = Gst.Pipeline.new()

        self.sources = []
        self.sources.append(Source(self.pipeline, args[1]))
        self.sources.append(Source(self.pipeline, args[2]))
        self.vsink = VideoSink(self.pipeline)

        self.sources[0].link_pad(self.vsink.request_pad(0, 0, 960, 540))
        self.sources[1].link_pad(self.vsink.request_pad(960, 540, 960, 540))
        # self.sources[0].link_pad(self.vsink.request_pad(0, 540, 480, 270))
        # self.sources[1].link_pad(self.vsink.request_pad(480, 540, 480, 270))
        # self.sources[0].link_pad(self.vsink.request_pad(960, 540, 480, 270))
        # self.sources[1].link_pad(self.vsink.request_pad(0, 810, 480, 270))
        # self.sources[0].link_pad(self.vsink.request_pad(480, 810, 480, 270))
        # self.sources[1].link_pad(self.vsink.request_pad(960, 810, 480, 270))

        # self.pipeline.connect('deep-notify', self.notify)

        # create and event loop and feed gstreamer bus mesages to it
        self.loop = GLib.MainLoop()

        GLib.timeout_add_seconds(5, self.timeout_cb)

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

        # self.sources[0].tee.set_state(Gst.State.NULL)
        self.pipeline.set_state(Gst.State.NULL)

        self.sources[0].tee.release_request_pad(self.sources[0].tee_src_pad)

        tee_src_pad_temp = self.sources[0].tee.get_pad_template('src_%u')
        self.sources[0].tee_src_pad = self.sources[0].tee.request_pad(tee_src_pad_temp, None, None)

        srcpad2 = self.sources[1].src.get_static_pad('src')
        srcpad2.add_probe(Gst.PadProbeType.IDLE, self.probe_cb2)

        self.sources[0].tee.sync_state_with_parent()

        if self.once:
            self.sources[0].tee_src_pad.link(self.vsink.comp_sink_pads[0])
            self.once = False
        else:
            self.sources[0].tee_src_pad.link(self.vsink.comp_sink_pads[1])
            self.once = True

        # self.sources[0].tee.set_state(Gst.State.PLAYING)
        self.pipeline.set_state(Gst.State.PLAYING)
        print('called probe_cb END')
        return Gst.PadProbeReturn.REMOVE

    def probe_cb2(self, pad, info):
        print('called probe_cb2 BEGIN')

        # self.sources[1].tee.set_state(Gst.State.NULL)

        self.sources[1].tee.release_request_pad(self.sources[1].tee_src_pad)

        tee_src_pad_temp = self.sources[1].tee.get_pad_template('src_%u')
        self.sources[1].tee_src_pad = self.sources[1].tee.request_pad(tee_src_pad_temp, None, None)

        self.sources[1].tee.sync_state_with_parent()

        if self.once2:
            self.sources[1].tee_src_pad.link(self.vsink.comp_sink_pads[1])
            self.once2 = False
        else:
            self.sources[1].tee_src_pad.link(self.vsink.comp_sink_pads[0])
            self.once2 = True

        # self.sources[1].tee.set_state(Gst.State.PLAYING)

        print('called probe_cb2 END')
        return Gst.PadProbeReturn.REMOVE

    def event_cb(self, pad, info):
        print('called event_cb')

        event = info.get_event()
        print('event %s on pad %s', event.type, pad)
        if event.type != Gst.EventType.EOS:
            return Gst.PadProbeReturn.OK

        pad.remove_probe(info.id)

        self.sources[0].tee.set_state(Gst.State.NULL)

        self.pipeline.remove(self.sources[0].tee)
        self.sources[0].tee = Gst.ElementFactory.make('tee')
        self.pipeline.add(self.sources[0].tee)

        print('77')
        self.sources[0].caps.link(self.sources[0].tee)
        print('88')
        tee_src_pad_temp = self.sources[0].tee.get_pad_template('src_%u')
        print('99')
        self.sources[0].tee_src_pad = self.sources[0].tee.request_pad(tee_src_pad_temp, None, None)
        # self.sources[0].tee_src_pad.link(self.vsink.comp_sink_pads[0])



        # print('1Before: %r' % self.sources[0].tee_src_pad.is_linked())
        # self.sources[0].tee.release_request_pad(self.sources[0].tee_src_pad)
        # print('1After: %r' % self.sources[0].tee_src_pad.is_linked())

        # tee_src_pad_temp = self.sources[0].tee.get_pad_template('src_%u')
        # tee_src_pad = self.sources[0].tee.request_pad(tee_src_pad_temp, None, None)

        # print('2Before: %r' % tee_src_pad.is_linked())
        print('00')
        self.sources[0].tee.sync_state_with_parent()
        self.sources[0].tee_src_pad.link(self.vsink.comp_sink_pads[0])
        # print('2After: %r' % tee_src_pad.is_linked())
        print('AA')
        self.sources[0].tee.sync_state_with_parent()
        print('BB')

        self.sources[0].tee.set_state(Gst.State.PLAYING)

        return Gst.PadProbeReturn.DROP

    def probe_cb3(self, pad, info):
        print('called probe_cb3')

        pad.remove_probe(info.id)

        self.sources[0].tee_src_pad.add_probe(Gst.PadProbeType.BLOCK | Gst.PadProbeType.EVENT_DOWNSTREAM, self.event_cb)
        self.sources[0].tee.get_static_pad('sink').send_event(Gst.Event.new_eos())

        return Gst.PadProbeReturn.OK

    def timeout_cb(self):
        print('called timeout_cb BEGIN')

        srcpad = self.sources[0].src.get_static_pad('src')
        srcpad.add_probe(Gst.PadProbeType.IDLE, self.probe_cb)

        # srcpad = self.sources[0].src.get_static_pad('src')
        # srcpad.add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM, self.probe_cb3)

        print('called timeout_cb END')
        return True


def main(args):
    if len(args) != 3:
        sys.stderr.write('usage: %s <media file or uri>\n' % args[0])
        sys.exit(1)

    # GObject.threads_init()
    Gst.init(None)
    Launcher(args)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
