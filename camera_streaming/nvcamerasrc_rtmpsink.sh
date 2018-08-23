#!/usr/bin/python
# On TX1 and TX2
# audiotestsrc & nvcamerasrc -> rtmpsink

#from subprocess import call
from sys import argv
from sys import exit
from os import system

if len(argv) < 2:
    print 'Input rtmpsink location!'
    print 'ex> ' + argv[0] + ' rtmp://localhost/live/s0 rtmp://localhost/live/s1 ..'
    exit(1)

cmd = 'gst-launch-1.0 -e -v'
cmd += ' flvmux streamable=true name=mux'
cmd += ' ! tee name=t'
for idx, val in enumerate(argv):
    if idx == 0:
        continue
    cmd += ' t. ! queue'
    cmd += ' ! rtmpsink location=\'' + val + ' live=true\''
cmd += ' audiotestsrc is-live=true'
cmd += ' ! queue'
cmd += ' ! voaacenc'
cmd += ' ! mux.'
cmd += ' nvcamerasrc fpsRange=\"30.0 30.0\" '
cmd += ' ! \'video/x-raw(memory:NVMM), width=(int)1920, height=(int)1080, format=(string)I420, framerate=(fraction)30/1\''
cmd += ' ! queue'
cmd += ' ! omxh264enc iframeinterval=15 insert-sps-pps=true ! h264parse'
cmd += ' ! mux.'

print cmd
system(cmd)
