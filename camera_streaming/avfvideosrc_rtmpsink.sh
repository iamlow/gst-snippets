#!/usr/bin/python
# Capture a screen on Mac
# audiotestsrc & avfvideosrc -> rtmpsink

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
cmd += ' avfvideosrc capture-screen=true device-index=1'
cmd += ' ! videoscale ! video/x-raw, width=1920, height=1080, framerate=30/1'
cmd += ' ! queue'
cmd += ' ! x264enc speed-preset=ultrafast tune=zerolatency key-int-max=15'
# cmd += '   byte-stream=true threads=1 key-int-max=15 intra-refresh=true'
cmd += ' ! h264parse'
cmd += ' ! mux.'

print cmd
system(cmd)
