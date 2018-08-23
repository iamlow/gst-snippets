#!/usr/bin/python
# On Mac and Ubuntu
# audiotestsrc & autovideosrc -> rtmpsink
#
# XXX 이 스크립트는 간헐적으로 gstreamer의 omxh264dec에서 디코딩을 못함.
# 이 증상이 발생하면 omxh264dec에세 재생이 가능할 때까지 반복해서 실행해야 함.
# x264enc로 인코딩한 데이터도 디코딩 가능하도록 추후 개선이 필요함.

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
cmd += ' autovideosrc'
cmd += ' ! video/x-raw,width=1280,height=720,framerate=30/1'
cmd += ' ! queue'
cmd += ' ! x264enc speed-preset=ultrafast tune=zerolatency'
# cmd += '   byte-stream=true threads=1 key-int-max=15 intra-refresh=true'
cmd += ' ! mux.'

print cmd
system(cmd)
