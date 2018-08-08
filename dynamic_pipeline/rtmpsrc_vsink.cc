/*
 */

#include <cstring>

#include <iostream>

#include <gstreamermm.h>
#include <glibmm/main.h>


static gint in_idle_probe = FALSE;

class Multiview
{
    Glib::RefPtr<Glib::MainLoop> main_loop;
    Glib::RefPtr<Gst::Pipeline> pipeline;
    Glib::RefPtr<Gst::Element> src;
    Glib::RefPtr<Gst::Element> demux;
    Glib::RefPtr<Gst::Element> demux_v_que;
    Glib::RefPtr<Gst::Element> h264parse;
    Glib::RefPtr<Gst::Element> vdec;
    Glib::RefPtr<Gst::Element> vconv;
    Glib::RefPtr<Gst::Element> caps;
    // Glib::RefPtr<Gst::Element> vque;
    Glib::RefPtr<Gst::Element> vsink;

    Glib::RefPtr<Gst::Element> demux_a_que;
    Glib::RefPtr<Gst::Element> asink;

    Glib::RefPtr<Gst::Pad> blockpad;

    bool on_bus_message(const Glib::RefPtr<Gst::Bus> &, const Glib::RefPtr<Gst::Message> &message)
    {
        switch (message->get_message_type())
        {
        case Gst::MESSAGE_EOS:
            std::cout << "\nEnd of stream" << '\n';
            main_loop->quit();
            return false;
        case Gst::MESSAGE_ERROR:
            std::cerr << "Error."
                      << Glib::RefPtr<Gst::MessageError>::cast_static(message)->parse_debug() << '\n';
            main_loop->quit();
            return false;
        default:
            break;
        }

        return true;
    }

    void on_parser_pad_added(const Glib::RefPtr<Gst::Pad> &newPad)
    {
        // We can now link this pad with the audio decoder
        std::cout << "Dynamic pad created. Linking parser/decoder." << std::endl;
        std::cout << newPad->get_name() << std::endl;

        Glib::RefPtr<Gst::Pad> sinkPad;

        if ("audio" == newPad->get_name())
        {
            sinkPad = demux_a_que->get_static_pad("sink");
        }
        else if ("video" == newPad->get_name())
        {
            sinkPad = demux_v_que->get_static_pad("sink");
        }
        else
        {
        }

        Gst::PadLinkReturn ret = newPad->link(sinkPad);
        if (ret != Gst::PAD_LINK_OK && ret != Gst::PAD_LINK_WAS_LINKED)
        {
            std::cerr << "Linking of pads " << newPad->get_name() << " and " << sinkPad->get_name() << " failed." << std::endl;
        }
    }

    void init()
    {
        src = Gst::ElementFactory::create_element("rtmpsrc");
        demux = Gst::ElementFactory::create_element("flvdemux");
        demux_v_que = Gst::ElementFactory::create_element("queue");
        h264parse = Gst::ElementFactory::create_element("h264parse");
        vdec = Gst::ElementFactory::create_element("avdec_h264");
        vconv = Gst::ElementFactory::create_element("videoscale");
        caps = Gst::ElementFactory::create_element("capsfilter");
        // vque = Gst::ElementFactory::create_element("queue");
        vsink = Gst::ElementFactory::create_element("glimagesink");

        demux_a_que = Gst::ElementFactory::create_element("queue");
        asink = Gst::ElementFactory::create_element("fakesink");

        if (!src
                || !demux
                || !demux_v_que
                || !h264parse
                || !vdec
                || !vconv
                // || !vque
                || !vsink
                || !caps

                || !demux_a_que
                || !asink)
        {
            throw std::runtime_error("One element could not be created.");
        }

        src->set_property<Glib::ustring>("location", "rtmp://192.168.0.11/live/s2");

        Glib::RefPtr<Gst::Caps> caps3 = Gst::Caps::create_from_string("video/x-raw, width=(int)500, height=(int)500");
        caps->set_property("caps", caps3);
        // XXX Gst::Caps::create_simple is maybe an invalid function
        // Reference: https://devtalk.nvidia.com/default/topic/934515/using-x-raw-memory-nvmm-in-gstreamer-program/
#if 0
        Glib::RefPtr<Gst::Caps> caps = Gst::Caps::create_simple("video/x-raw(memory:NVMM)",
                                       "width", 1920, "height", 1080, "framerate", Gst::Fraction(30, 1));
#else
        // Glib::RefPtr<Gst::Caps> caps = Gst::Caps::create_from_string("video/x-raw");
        // Glib::RefPtr<Gst::Caps> caps2 = Gst::Caps::create_from_string("video/x-raw, width=(int)1000, height=(int)1000");
        // Glib::RefPtr<Gst::Caps> caps3 = Gst::Caps::create_from_string("video/x-raw, width=(int)500, height=(int)500");
        // Glib::RefPtr<Gst::Caps> caps4 = Gst::Caps::create_from_string("video/x-raw(memory:NVMM), width=(int)480, height=(int)270");
#endif
        pipeline
            ->add(src)
            ->add(demux)
            ->add(demux_v_que)
            ->add(h264parse)
            ->add(vdec)
            ->add(vconv)
            ->add(caps)
            // ->add(vque)
            ->add(vsink)

            ->add(demux_a_que)
            ->add(asink);

        src->link(demux);

        // We cannot link the parser and decoder yet,
        // because the parser uses dynamic pads.
        // So we do it later in a pad-added signal handler:
        demux->signal_pad_added().connect(sigc::mem_fun(*this, &Multiview::on_parser_pad_added));

        demux_v_que
            ->link(h264parse)
            ->link(vdec)
            ->link(vconv)
            ->link(caps)
            // ->link(vque, caps4)
            ->link(vsink);

        demux_a_que
            ->link(asink);

        // block pad
        blockpad = src->get_static_pad("src");
        if (!blockpad) {
            std::cout << "blockpad is nullptr!\n";
            return;
        }
    }

    // event
    Gst::PadProbeReturn event_probe_cb(const Glib::RefPtr<Gst::Pad>& pad,
                                       const Gst::PadProbeInfo& info) {

        if (!g_atomic_int_compare_and_exchange (&in_idle_probe, FALSE, TRUE))
            return Gst::PAD_PROBE_OK;

        std::cout << pad->get_parent_element()->get_name()
                  << " : event_probe_cb called : " << pad->get_name() << '\n';

        caps->set_state(Gst::STATE_NULL);
        pipeline->remove(caps);

        caps = Gst::ElementFactory::create_element("capsfilter");
        Glib::RefPtr<Gst::Caps> caps3 = Gst::Caps::create_from_string("video/x-raw, width=(int)1920, height=(int)1080");
        caps->set_property("caps", caps3);
        pipeline->add(caps);
        caps->sync_state_with_parent();

        vconv->link(caps)->link(vsink);

        vconv->set_state(Gst::STATE_PLAYING);
        std::cout << __LINE__ << '\n';
        // return Gst::PAD_PROBE_DROP;
        return Gst::PAD_PROBE_REMOVE;
        // return Gst::PAD_PROBE_PASS;
        // return Gst::PAD_PROBE_OK;
    }

    Gst::PadProbeReturn pad_probe_cb(const Glib::RefPtr<Gst::Pad>& pad,
                                    const Gst::PadProbeInfo& info)
    {
        std::cout << pad->get_parent_element()->get_name()
                  << " : pad_probe_cb called : " << pad->get_name() << '\n';

        pad->remove_probe(info.get_id());

        auto srcpad = caps->get_static_pad("src");
        srcpad->add_probe(Gst::PAD_PROBE_TYPE_IDLE
                          /*| Gst::PAD_PROBE_TYPE_EVENT_DOWNSTREAM*/,
                          sigc::mem_fun(*this, &Multiview::event_probe_cb));

        // auto sinkpad = vconv->get_static_pad("sink");
        // sinkpad->send_event(Gst::EventEos::create());

        return Gst::PAD_PROBE_OK;
    }

    bool on_timeout() {
        std::cout << __FUNCTION__ << std::endl;
        in_idle_probe = FALSE;
        blockpad->add_probe(Gst::PAD_PROBE_TYPE_IDLE,
                            sigc::mem_fun(*this, &Multiview::event_probe_cb));
        return true;
    }

  public:
    Multiview()
    {
        main_loop = Glib::MainLoop::create();
        pipeline = Gst::Pipeline::create();
        pipeline->get_bus()->add_watch(
            sigc::mem_fun(*this, &Multiview::on_bus_message));
    }

    void play_until_eos()
    {
        init();

        // vsrc->set_property("location", filename);
        pipeline->set_state(Gst::STATE_PLAYING);
        Glib::signal_timeout().connect(
            sigc::mem_fun(*this, &Multiview::on_timeout), 3000);        
        main_loop->run();
        pipeline->set_state(Gst::STATE_NULL);
    }
};

int main(int argc, char *argv[])
{
    Gst::init(argc, argv);
    Multiview mv;

    try
    {
        mv.play_until_eos();
    }
    catch (const std::runtime_error &err)
    {
        std::cerr << "runtime error: " << err.what() << '\n';
    }
    return 0;
}
