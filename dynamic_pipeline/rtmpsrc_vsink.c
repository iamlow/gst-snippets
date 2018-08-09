#include <stdio.h>
#include <string.h>
#include <gst/gst.h>

static GMainLoop *loop;
static GstElement *pipeline;

static GstElement *src;
static GstElement *demux;

// for video
static GstElement *demux_v_que;
static GstElement *h264parse;
static GstElement *vdec;
static GstElement *vconv;
static GstElement *caps;
static GstElement *vsink;

// for audio
static GstElement *demux_a_que;
static GstElement *asink;

static GstPadProbeReturn
pad_probe_cb (GstPad * pad, GstPadProbeInfo * info, gpointer user_data) {
    printf("called pad_probe_cb\n");
    gst_element_set_state (caps, GST_STATE_NULL);
    gst_bin_remove (GST_BIN (pipeline), caps);
    caps = gst_element_factory_make ("capsfilter", NULL);
    gst_object_ref (caps);
    gst_bin_add_many (GST_BIN (pipeline), caps, NULL);
    gst_element_sync_state_with_parent (caps);
    gst_element_link_many (vconv, caps, vsink, NULL);
    gst_element_set_state (caps, GST_STATE_PLAYING);

    return GST_PAD_PROBE_REMOVE;
}

static gboolean
timeout_cb (gpointer user_data) {
    printf("called timeout_cb\n");
    GstPad *pad = gst_element_get_static_pad (src, "src");
    gst_pad_add_probe (pad, GST_PAD_PROBE_TYPE_IDLE, pad_probe_cb, NULL, NULL);

    return TRUE;
}

static void
pad_added_cb (GstElement * element, GstPad * pad, gpointer user_data) {
    GstCaps *caps;
    GstStructure *s;
    const gchar *name;

    caps = gst_pad_get_current_caps (pad);
    s = gst_caps_get_structure (caps, 0);
    name = gst_structure_get_name (s);

    printf("name = %s\n", name);

    if (strcmp (name, "audio/mpeg") == 0) {
        GstPad *sinkpad;

        sinkpad = gst_element_get_static_pad (demux_a_que, "sink");
        if (gst_pad_link (pad, sinkpad) != GST_PAD_LINK_OK) {
            g_printerr ("Failed to link demux with demux_a_que\n");
            g_main_loop_quit (loop);
        }
        gst_object_unref (sinkpad);
    }

    if (strcmp (name, "video/x-h264") == 0) {
        GstPad *sinkpad;

        sinkpad = gst_element_get_static_pad (demux_v_que, "sink");
        if (gst_pad_link (pad, sinkpad) != GST_PAD_LINK_OK) {
            g_printerr ("Failed to link demux with demux_v_que\n");
            g_main_loop_quit (loop);
        }
        gst_object_unref (sinkpad);
    }

    gst_caps_unref (caps);
}

static gboolean
message_cb (GstBus *bus, GstMessage *message, gpointer user_data) {
    switch (GST_MESSAGE_TYPE (message)) {
        case GST_MESSAGE_ERROR:{
            GError *err = NULL;
            gchar *name, *debug = NULL;

            name = gst_object_get_path_string (message->src);
            gst_message_parse_error (message, &err, &debug);

            g_printerr ("ERROR: from element %s: %s\n", name, err->message);
            if (debug != NULL)
                g_printerr ("Additional debug info:\n%s\n", debug);

            g_error_free (err);
            g_free (debug);
            g_free (name);

            g_main_loop_quit (loop);
            break;
        }

        case GST_MESSAGE_WARNING:{
            GError *err = NULL;
            gchar *name, *debug = NULL;

            name = gst_object_get_path_string (message->src);
            gst_message_parse_warning (message, &err, &debug);

            g_printerr ("ERROR: from element %s: %s\n", name, err->message);
            if (debug != NULL)
                g_printerr ("Additional debug info:\n%s\n", debug);

            g_error_free (err);
            g_free (debug);
            g_free (name);
            break;
        }

        case GST_MESSAGE_EOS:
            g_print ("Got EOS\n");
            g_main_loop_quit (loop);
            break;

        default:
            break;
    }

    return TRUE;
}

int main(int argc, char *argv[]) {
    GstBus *bus;

    gst_init (&argc, &argv);

    if (argc != 2) {
        g_error ("Usage: %s filename", argv[0]);
        return -1;
    }

    pipeline = gst_pipeline_new (NULL);

    src = gst_element_factory_make ("rtmpsrc", NULL);
    demux = gst_element_factory_make ("flvdemux", NULL);

    demux_v_que = gst_element_factory_make ("queue", NULL);
    h264parse = gst_element_factory_make ("h264parse", NULL);
    vdec = gst_element_factory_make ("avdec_h264", NULL);
    vconv = gst_element_factory_make ("videoscale", NULL);
    caps = gst_element_factory_make ("capsfilter", NULL);
    vsink = gst_element_factory_make ("glimagesink", NULL);

    demux_a_que = gst_element_factory_make ("queue", NULL);
    asink = gst_element_factory_make ("fakesink", NULL);

    if (!pipeline 
            || !src 
            || !demux 
            || !demux_v_que 
            || !h264parse 
            || !vdec 
            || !vconv
            || !caps 
            || !vsink 
            || !demux_a_que 
            || !asink) {
        g_error ("Failed to create elements");
        return -2;
    }

    g_object_set (src, "location", argv[1], NULL);

    gst_bin_add_many (GST_BIN (pipeline), 
            src, demux, 
            demux_v_que, h264parse, vdec, vconv, caps, vsink, 
            demux_a_que, asink, NULL);
    if (!gst_element_link_many (src, demux, NULL)
            || !gst_element_link_many (demux_v_que, h264parse, 
            vdec, vconv, caps, vsink, NULL)
            || !gst_element_link_many (demux_a_que, asink, NULL)) {
        g_error ("Failed to link elements");
        return -3;
    }

    g_signal_connect (demux, "pad-added", G_CALLBACK (pad_added_cb), NULL);

    loop = g_main_loop_new (NULL, FALSE);

    bus = gst_pipeline_get_bus (GST_PIPELINE (pipeline));
    gst_bus_add_signal_watch (bus);
    g_signal_connect (G_OBJECT (bus), "message", G_CALLBACK (message_cb), NULL);
    gst_object_unref (GST_OBJECT (bus));

    if (gst_element_set_state (pipeline,
            GST_STATE_PLAYING) == GST_STATE_CHANGE_FAILURE) {
        g_error ("Failed to go into PLAYING state");
        return -4;
    }

    g_timeout_add_seconds (5, timeout_cb, NULL);

    g_main_loop_run (loop);

    gst_element_set_state (pipeline, GST_STATE_NULL);

    g_main_loop_unref (loop);

    gst_object_unref (pipeline);

    return 0;
}