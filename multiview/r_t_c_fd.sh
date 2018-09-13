#!/usr/bin/python
# rtmpsrc -> nvvidconv -> tee -> nvcompositor -> fpsdisplaysink:nvoverlaysink

#from subprocess import call
from sys import argv
from sys import exit
from os import system

cmd = 'gst-launch-1.0 -e -v'

##############################################################################
# sinks
#

# multiview
cmd += ' nvcompositor name=mix'
cmd += ' sink_0::xpos=0    sink_0::ypos=0   sink_0::width=960 sink_0::height=540'
cmd += ' sink_1::xpos=960  sink_1::ypos=0   sink_1::width=960 sink_1::height=540'
cmd += ' sink_2::xpos=0    sink_2::ypos=540 sink_2::width=480 sink_2::height=270'
cmd += ' sink_3::xpos=480  sink_3::ypos=540 sink_3::width=480 sink_3::height=270'
cmd += ' sink_4::xpos=960  sink_4::ypos=540 sink_4::width=480 sink_4::height=270'
cmd += ' sink_5::xpos=1440 sink_5::ypos=540 sink_5::width=480 sink_5::height=270'
cmd += ' sink_6::xpos=0    sink_6::ypos=810 sink_6::width=480 sink_6::height=270'
cmd += ' sink_7::xpos=480  sink_7::ypos=810 sink_7::width=480 sink_7::height=270'
cmd += ' sink_8::xpos=960  sink_8::ypos=810 sink_8::width=480 sink_8::height=270'
cmd += ' sink_9::xpos=1440 sink_9::ypos=810 sink_9::width=480 sink_9::height=270'
# cmd += ' ! nvoverlaysink'
cmd += ' ! fpsdisplaysink video-sink=nvoverlaysink text-overlay=false signal-fps-measurements=true sync=true'

# pip and transfer
cmd += ' glvideomixer name=glvm'
cmd += ' sink_0::xpos=0 sink_0::ypos=0'
# cmd += ' sink_1::xpos=1220 sink_1::ypos=660 sink_1::width=640 sink_1::height=360'
cmd += ' sink_1::xpos=1220 sink_1::ypos=660'
cmd += ' ! queue ! omxh264enc ! h264parse ! flvmux name=mux ! tee name=pip'
cmd += ' pip. ! queue ! rtmpsink location=rtmp://a.rtmp.youtube.com/live2/ws8c-p19s-tc2g-3puj'
cmd += ' pip. ! queue ! rtmpsink location=rtmp://192.168.0.11/live/s0 sync=true'

# cmd += ' audiotestsrc is-live=true'
# cmd += ' ! queue'
# cmd += ' ! voaacenc'
# cmd += ' ! mux.audio'


##############################################################################
# sources
#

# input 1
cmd += ' rtmpsrc location=\"' + argv[1] + '\"'
cmd += ' ! flvdemux name=dem1'
cmd += ' dem1.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! tee name=t1'
cmd += ' dem1.audio ! queue ! fakesink'

# input 2
cmd += ' rtmpsrc location=\"' + argv[2] + '\"'
cmd += ' ! flvdemux name=dem2'
cmd += ' dem2.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! tee name=t2'
cmd += ' dem2.audio ! queue ! fakesink'

# input 3
cmd += ' rtmpsrc location=\"' + argv[3] + '\"'
cmd += ' ! flvdemux name=dem3'
cmd += ' dem3.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! tee name=t3'
cmd += ' dem3.audio ! queue ! fakesink'

# input 4
cmd += ' rtmpsrc location=\"' + argv[4] + '\"'
cmd += ' ! flvdemux name=dem4'
cmd += ' dem4.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! tee name=t4'
cmd += ' dem4.audio ! queue ! fakesink'

# input 5
cmd += ' rtmpsrc location=\"' + argv[5] + '\"'
cmd += ' ! flvdemux name=dem5'
cmd += ' dem5.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! tee name=t5'
cmd += ' dem5.audio ! queue ! fakesink'

# input 6
cmd += ' rtmpsrc location=\"' + argv[6] + '\"'
cmd += ' ! flvdemux name=dem6'
cmd += ' dem6.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! tee name=t6'
cmd += ' dem6.audio ! queue ! fakesink'


##############################################################################
# mediators
#

# pip & transfer
cmd += ' t1. ! queue'
cmd += ' ! nvvidconv ! "video/x-raw"'
cmd += ' ! textoverlay text=\"Main\" valignment=top halignment=left font-desc=\"Sans, 20\"'
cmd += ' ! tee ! glvm.sink_0'

cmd += ' t2. ! queue'
cmd += ' ! nvvidconv ! "video/x-raw, width=(int)640, height=(int)360"'
cmd += ' ! textoverlay text=\"Sub\" valignment=top halignment=left font-desc=\"Sans, 20\"'
cmd += ' ! tee ! glvm.sink_1'

# multiview
cmd += ' t1. ! queue'
cmd += ' ! nvvidconv ! \"video/x-raw, width=(int)960, height=(int)540\"'
cmd += ' ! textoverlay text=\"PRE\" valignment=top halignment=left font-desc=\"Sans, 20\"'
cmd += ' ! tee ! mix.sink_0'

cmd += ' t2. ! queue'
cmd += ' ! nvvidconv ! \"video/x-raw, width=(int)960, height=(int)540\"'
cmd += ' ! textoverlay text=\"PGM\" valignment=top halignment=left font-desc=\"Sans, 20\"'
cmd += ' ! mix.sink_1'

cmd += ' t1. ! queue'
cmd += ' ! nvvidconv ! \"video/x-raw, width=(int)480, height=(int)270\"'
cmd += ' ! textoverlay text=\"CH1\" valignment=top halignment=left font-desc=\"Sans, 20\"'
cmd += ' ! mix.sink_2'

cmd += ' t2. ! queue'
cmd += ' ! nvvidconv ! \"video/x-raw, width=(int)480, height=(int)270\"'
cmd += ' ! textoverlay text=\"CH2\" valignment=top halignment=left font-desc=\"Sans, 20\"'
cmd += ' ! mix.sink_3'

cmd += ' t3. ! queue'
cmd += ' ! nvvidconv ! \"video/x-raw, width=(int)480, height=(int)270\"'
cmd += ' ! textoverlay text=\"CH3\" valignment=top halignment=left font-desc=\"Sans, 20\"'
cmd += ' ! mix.sink_4'

cmd += ' t4. ! queue'
cmd += ' ! nvvidconv ! \"video/x-raw, width=(int)480, height=(int)270\"'
cmd += ' ! textoverlay text=\"CH4\" valignment=top halignment=left font-desc=\"Sans, 20\"'
cmd += ' ! mix.sink_6'

cmd += ' t5. ! queue'
cmd += ' ! nvvidconv ! \"video/x-raw, width=(int)480, height=(int)270\"'
cmd += ' ! textoverlay text=\"CH5\" valignment=top halignment=left font-desc=\"Sans, 20\"'
cmd += ' ! mix.sink_7'

cmd += ' t6. ! queue'
cmd += ' ! nvvidconv ! \"video/x-raw, width=(int)480, height=(int)270\"'
cmd += ' ! textoverlay text=\"CH6\" valignment=top halignment=left font-desc=\"Sans, 20\"'
cmd += ' ! mix.sink_8'


##############################################################################
# launcher
#
print cmd
system(cmd)
