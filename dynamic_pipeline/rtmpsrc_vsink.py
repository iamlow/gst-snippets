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

data = dict()


class ProbeData:
    def __init__(self, pipe, data):
        self.pipe = pipe
        self.data = data


def pad_added_handler(src, new_pad, data):
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
        new_pad.link(data["demux_a_que"].get_static_pad("sink"))

    elif new_pad_type.startswith("video"):
        print("  It has type '%s' which is video." %
              new_pad_type)
        new_pad.link(data["demux_v_que"].get_static_pad("sink"))
    else:
        print("error!")

    return


def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        sys.stdout.write("End-of-stream\n")
        loop.quit()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write("Error: %s: %s\n" % (err, debug))
        loop.quit()
    return True


def dispose_src_cb(src):
    src.set_state(Gst.State.NULL)


def probe_cb(pad, info, pdata):
    print("called probe_cb")
    # peer = pad.get_peer()
    # pad.unlink(peer)
    pdata.data["caps"].set_state(Gst.State.NULL)
    pdata.pipe.remove(pdata.data["caps"])
    # Can't set the state of the src to NULL from its streaming thread
    # GLib.idle_add(dispose_src_cb, pdata.data["caps"])

    pdata.data["caps"] = Gst.ElementFactory.make('capsfilter')
    # pdata.src.props.pattern = random.randint(0, 24)
    pdata.pipe.add(pdata.data["caps"])
    # srcpad = pdata.src.get_static_pad ("src")
    pdata.data["caps"].sync_state_with_parent()
    pdata.data["vconv"].link(pdata.data["caps"])
    pdata.data["caps"].link(pdata.data["vsink"])
    # srcpad.link(peer)
    pdata.data["caps"].set_state(Gst.State.PLAYING)

    # GLib.timeout_add_seconds(1, timeout_cb, pdata)

    return Gst.PadProbeReturn.REMOVE


def timeout_cb(pdata):
    print("called timeout_cb")
    srcpad = pdata.data["src"].get_static_pad('src')
    srcpad.add_probe(Gst.PadProbeType.IDLE, probe_cb, pdata)
    return True

def main(args):
    if len(args) != 2:
        sys.stderr.write("usage: %s <media file or uri>\n" % args[0])
        sys.exit(1)

    GObject.threads_init()
    Gst.init(None)

    pipeline = Gst.Pipeline.new()

    data["src"] = Gst.ElementFactory.make("rtmpsrc")
    data["demux"] = Gst.ElementFactory.make("flvdemux")
    data["demux_v_que"] = Gst.ElementFactory.make("queue")
    data["h264parse"] = Gst.ElementFactory.make("h264parse")
    data["vdec"] = Gst.ElementFactory.make("avdec_h264")
    data["vconv"] = Gst.ElementFactory.make("videoscale")
    data["caps"] = Gst.ElementFactory.make("capsfilter")
    data["vsink"] = Gst.ElementFactory.make("glimagesink")
    data["demux_a_que"] = Gst.ElementFactory.make("queue")
    data["asink"] = Gst.ElementFactory.make("fakesink")

    pipeline.add(data["src"])
    pipeline.add(data["demux"])
    pipeline.add(data["demux_v_que"])
    pipeline.add(data["h264parse"])
    pipeline.add(data["vdec"])
    pipeline.add(data["vconv"])
    pipeline.add(data["caps"])
    pipeline.add(data["vsink"])
    pipeline.add(data["demux_a_que"])
    pipeline.add(data["asink"])

    # take the commandline argument and ensure that it is a uri
    if Gst.uri_is_valid(args[1]):
        uri = args[1]
    else:
        uri = Gst.filename_to_uri(args[1])
    data["src"].set_property('location', uri)

    data["src"].link(data["demux"])
    data["demux"].connect("pad-added", pad_added_handler, data)

    data["demux_v_que"].link(data["h264parse"])
    data["h264parse"].link(data["vdec"])
    data["vdec"].link(data["vconv"])
    data["vconv"].link(data["caps"])
    data["caps"].link(data["vsink"])

    data["demux_a_que"].link(data["asink"])

    pdata = ProbeData(pipeline, data)

    # create and event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()

    GLib.timeout_add_seconds(5, timeout_cb, pdata)

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # start play back and listed to events
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()

    except:
        pass

    # cleanup
    pipeline.set_state(Gst.State.NULL)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
