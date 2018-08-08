#!/usr/bin/python

"""
dynamic pipeline target: capsfilter.

rtmpsrc -> flvdemux
        -> queue(v) -> h264parse -> omxh264dec
                -> nvvidconv -> capsfilter -> nvoverlaysink
        -> queue(a) -> fakesink
"""

# from subprocess import call
from sys import argv
from sys import exit
from os import system

if len(argv) < 2:
    print 'Input rtmpsrc location!'
    print 'ex> ' + argv[0] + ' rtmp://localhost/live/stream'
    exit(1)

cmd = 'gst-launch-1.0 -e -v'
cmd += ' rtmpsrc location=\'' + argv[1] + '\''
cmd += ' ! flvdemux name=dem'
cmd += ' dem.video ! queue ! h264parse ! omxh264dec'
cmd += ' ! nvvidconv ! capsfilter '
cmd += ' ! nvoverlaysink'
cmd += ' dem.audio ! queue ! fakesink'

print cmd
system(cmd)
