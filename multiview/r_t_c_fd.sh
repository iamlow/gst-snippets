#!/usr/bin/python
# rtmpsrc -> nvvidconv -> tee -> nvcompositor -> fpsdisplaysink:nvoverlaysink

#from subprocess import call
from sys import argv
from sys import exit
from os import system

cmd = 'gst-launch-1.0 -e -v'
cmd += ' nvcompositor name=mix'
cmd += ' sink_0::xpos=0     sink_0::ypos=0      sink_0::width=960   sink_0::height=540'
cmd += ' sink_1::xpos=960   sink_1::ypos=0      sink_1::width=960   sink_1::height=540'
cmd += ' sink_2::xpos=0     sink_2::ypos=540    sink_2::width=480   sink_2::height=270'
cmd += ' sink_3::xpos=480   sink_3::ypos=540    sink_3::width=480   sink_3::height=270'
cmd += ' sink_4::xpos=960   sink_4::ypos=540    sink_4::width=480   sink_4::height=270'
cmd += ' sink_5::xpos=1440  sink_5::ypos=540    sink_5::width=480   sink_5::height=270'
cmd += ' sink_6::xpos=0     sink_6::ypos=810    sink_6::width=480   sink_6::height=270'
cmd += ' sink_7::xpos=480   sink_7::ypos=810    sink_7::width=480   sink_7::height=270'
cmd += ' sink_8::xpos=960   sink_8::ypos=810    sink_8::width=480   sink_8::height=270'
cmd += ' sink_9::xpos=1440  sink_9::ypos=810    sink_9::width=480   sink_9::height=270'

# cmd += ' ! nvoverlaysink'
cmd += ' ! fpsdisplaysink video-sink=nvoverlaysink text-overlay=false signal-fps-measurements=true sync=false'

cmd += ' rtmpsrc location=\'' + argv[1] + '\''
cmd += ' ! flvdemux name=dex4'
cmd += ' dex4.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! nvvidconv ! \'video/x-raw\' ! tee name=t4'
cmd += ' dex4.audio ! queue ! fakesink'

cmd += ' rtmpsrc location=\'' + argv[2] + '\''
cmd += ' ! flvdemux name=dex5'
cmd += ' dex5.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! nvvidconv ! \'video/x-raw\' ! tee name=t5'
cmd += ' dex5.audio ! queue ! fakesink'

cmd += ' rtmpsrc location=\'' + argv[3] + '\''
cmd += ' ! flvdemux name=dex6'
cmd += ' dex6.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! nvvidconv ! \'video/x-raw\' ! tee name=t6'
cmd += ' dex6.audio ! queue ! fakesink'

cmd += ' rtmpsrc location=\'' + argv[4] + '\''
cmd += ' ! flvdemux name=dex7'
cmd += ' dex7.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! nvvidconv ! \'video/x-raw\' ! tee name=t7'
cmd += ' dex7.audio ! queue ! fakesink'

cmd += ' rtmpsrc location=\'' + argv[5] + '\''
cmd += ' ! flvdemux name=dex8'
cmd += ' dex8.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! nvvidconv ! \'video/x-raw\' ! tee name=t8'
cmd += ' dex8.audio ! queue ! fakesink'

cmd += ' t4. ! queue ! omxh264enc ! h264parse ! queue ! flvmux name=mux ! rtmpsink location=rtmp://a.rtmp.youtube.com/live2/ws8c-p19s-tc2g-3puj'
# cmd += ' audiotestsrc is-live=true'
# cmd += ' ! queue'
# cmd += ' ! voaacenc'
# cmd += ' ! mux.audio'

cmd += ' rtmpsrc location=\'' + argv[6] + '\''
cmd += ' ! flvdemux name=dex9'
cmd += ' dex9.video ! queue max-size-buffers=3 ! h264parse ! omxh264dec disable-dpb=true ! nvvidconv ! \'video/x-raw\' ! tee name=t9'
cmd += ' dex9.audio ! queue ! mux.audio'


cmd += ' t4. ! queue ! mix.sink_0'
cmd += ' t5. ! queue ! nvvidconv ! \'video/x-raw, width=(int)960, height=(int)540\' ! mix.sink_1'

cmd += ' t4. ! queue ! mix.sink_2'
cmd += ' t5. ! queue ! mix.sink_3'
cmd += ' t6. ! queue ! nvvidconv ! \'video/x-raw, width=(int)480, height=(int)270\' ! mix.sink_4'
# cmd += ' t7. ! queue ! nvvidconv ! \'video/x-raw, width=(int)480, height=(int)270\' ! textoverlay text=\'Room D NETWORK\' valignment=top halignment=left font-desc="Sans, 20" ! mix.sink_3'
cmd += ' t7. ! queue ! nvvidconv ! \'video/x-raw, width=(int)480, height=(int)270\' ! mix.sink_6'
cmd += ' t8. ! queue ! nvvidconv ! \'video/x-raw, width=(int)480, height=(int)270\' ! mix.sink_7'
cmd += ' t9. ! queue ! nvvidconv ! \'video/x-raw, width=(int)480, height=(int)270\' ! mix.sink_8'
# cmd += ' t5. ! queue ! nvvidconv ! \'video/x-raw, width=(int)480, height=(int)270\' ! textoverlay text=\'Room H NOHANGUL\' valignment=top halignment=left font-desc="Sans, 20" ! mix.sink_7'

print cmd
system(cmd)
