#!/usr/bin/env python
from dingus import Dingus, DingusTestCase, DontCare
from unittest import TestCase
import sys
import socket
import frame
from frame import Frame

class WhenSettingUp(DingusTestCase(Frame)):

    def setup(self):
        super(WhenSettingUp, self).setup()
        self.frame = Frame()
        self.sockobj = frame.socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def should_set_name(self):
        assert frame.socket.calls('gethostbyname',frame.socket.gethostname())

    def should_connect(self):
        self.frame.connect(self.sockobj.connect('localhost',99999))
        sendall = self.frame.sock.calls('sendall',DontCare).one().args[0]

        assert 'CONNECT' in sendall

    def should_send_frame_and_return_none(self):
        self.frame.connect(self.sockobj.connect('localhost',99999))
        self.frame.session = {'session':'ID:nose-session123'}
        this_frame = self.frame.build_frame({'command':'CONNECT','headers':{}})
        send_frame = self.frame.send_frame(this_frame.as_string())

        assert send_frame is None

#    def should_send_frame_and_return_frame(self):
#        my_frame = Frame()
#        headers = {'destination':'/queue/nose_test',
#                   'persistent':'true'}
#        body    = {'body':'Testing'}
#        my_frame.connect(self.sockobj.connect('localhost',99999))
#        my_frame.session = {'session':'ID:nose-session123'}
#        this_frame = my_frame.build_frame({'command':'SEND',
#                                             'headers':headers,
#                                             'body':body},want_receipt=True)
#        send_frame = my_frame.send_frame(this_frame.as_string())
#
#        assert isinstance(send_frame,Frame) 

    def should_build_frame(self):
        this_frame = self.frame.build_frame({'command':'CONNECT','headers':{}})

        assert self.frame.command is not None
        assert self.frame.headers is not None
        assert '\x00' in this_frame.as_string(),this_frame

    def should_build_frame_with_body(self):
        headers = {'destination':'/queue/nose_test',
                   'persistent':'true'}
        body    = 'Testing'
        this_frame = self.frame.build_frame({'command':'SEND',
                                             'headers':headers,
                                             'body':body})

        assert self.frame.body is not None

    def should_build_frame_with_receipt(self):
        headers = {'destination':'/queue/nose_test',
                   'persistent':'true'}
        body    = 'Testing'
        self.frame.session = {'session':'ID:nose-session123'}
        this_frame = self.frame.build_frame({'command':'SEND',
                                             'headers':headers,
                                             'body':body},want_receipt=True)

        assert 'receipt' in self.frame.headers
        
    def should_build_frame_bytes_message(self):
        headers = {'destination':'/queue/nose_test',
                   'persistent':'true',
                   'bytes_message':'true'}
        body    = 'Testing'
        this_frame = self.frame.build_frame({'command':'SEND',
                                             'headers':headers,
                                             'body':body})

        assert 'content-length:%i' % len(body) in this_frame.as_string()
