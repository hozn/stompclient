#!/usr/bin/env python
from dingus import Dingus, DingusTestCase, DontCare
from unittest import TestCase
import sys
import socket
from stomp import frame
from stomp.frame import Frame

class WhenSettingUp(DingusTestCase(Frame)):

    def setup(self):
        super(WhenSettingUp, self).setup()
        self.frame = Frame()
        self.sockobj = frame.socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def should_set_name(self):
        assert frame.socket.calls('gethostbyname',frame.socket.gethostname())

    def should_connect(self):
        self.frame._getline = Dingus()
        self.frame._getline.return_value = 'CONNECTED\nsession:ID:nose-session123\n\n\x00\n' 
        self.frame.connect(self.sockobj.connect('localhost',99999))
        sendall = self.frame.sock.calls('sendall',DontCare).one().args[0]

        assert self.frame.session is not None
        assert 'CONNECT' in sendall

class WhenSendingFrames(DingusTestCase(Frame)):

    def setup(self):
        super(WhenSendingFrames, self).setup()
        self.frame = Frame()
        self.sockobj = frame.socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def should_send_frame_and_return_none(self):
        self.frame._getline = Dingus()
        self.frame._getline.return_value = 'CONNECTED\nsession:ID:nose-session123\n\n\x00\n' 
        self.frame.connect(self.sockobj.connect('localhost',99999))
        this_frame = self.frame.build_frame({'command':'CONNECT','headers':{}})
        send_frame = self.frame.send_frame(this_frame.as_string())

        assert send_frame is None

    def should_send_frame_and_return_frame(self):
        my_frame = Frame()
        my_frame._getline = Dingus()
        headers = {'destination':'/queue/nose_test',
                   'persistent':'true'}
        body    = {'body':'Testing'}
        my_frame._getline.return_value = 'CONNECTED\nsession:ID:nose-session123\n\n\x00\n' 
        my_frame.connect(self.sockobj.connect('localhost',99999))
        this_frame = my_frame.build_frame({'command':'SEND',
                                           'headers':headers,
                                           'body':body},want_receipt=True)
        my_frame._getline.return_value = 'RECEIPT\nreceipt-id:ID:nose-receipt123\n\n\x00\n'
        send_frame = my_frame.send_frame(this_frame.as_string())

        assert isinstance(my_frame,Frame) 

class WhenBuildingFrames(DingusTestCase(Frame)):

    def setup(self):
        super(WhenBuildingFrames, self).setup()
        self.frame = Frame()
        self.sockobj = frame.socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def should_build_frame(self):
        this_frame = self.frame.build_frame({'command':'CONNECT','headers':{}})

        assert self.frame.command is not None
        assert self.frame.headers is not None
        assert '\x00' in this_frame.as_string()

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

class WhenParsingFrames(DingusTestCase(Frame)):

    def setup(self):
        super(WhenParsingFrames, self).setup()
        self.frame = Frame()
        self.sockobj = frame.socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def should_parse_headers(self):
        header = 'destination:/queue/nose_test'
        parsed = self.frame.parse_headers(header)

        assert isinstance(parsed,type({}))

    def should_parse_command(self):
        command_str = 'CONNECT\nsession:ID:nose-session123'
        command     = self.frame.parse_command(command_str)
    
        assert isinstance(command,type(''))

    def should_set_bytes_message(self):
        my_frame = Frame()
        my_frame._getline = Dingus()
        body = 'Test 1'
        my_frame._getline.return_value = ('MESSAGE\nsession:ID:nose-session123'
                                          '\ncontent-length:%d\n\n%s\x00\n'%(len(body),body))
        this_frame = my_frame.parse_frame()

        assert 'bytes_message' in this_frame.headers
    
    def should_get_line(self):
        command = 'CONNECTED'
        headers = {'session':'ID:nose-session123'}
        body    = '\x00\n'
        my_frame = Frame()
        self.frame.parse_frame = Dingus()
        this_frame = my_frame.build_frame({'command':command,
                                           'headers':headers,
                                           'body':body})
        self.frame.parse_frame.return_value = this_frame
        self.frame.connect(self.sockobj.connect(('localhost',99999)))
        header = "session:%(session)s\n" % headers
        ret = '\n'.join([command,header,body])
        self.frame.sock.recv.return_value = ret
        self.frame._getline()

        assert self.frame.sock.calls('recv',1)
