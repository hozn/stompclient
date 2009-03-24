#!/usr/bin/env python
from dingus import Dingus, DingusTestCase, DontCare
from unittest import TestCase
import sys
import socket
import stomp
import stomp
import frame
from stomp import Stomp
from frame import Frame

class WhenConnecting(DingusTestCase(Stomp)):

    def setup(self):
        super(WhenConnecting, self).setup()
        self.host  = 'localhost'
        self.port  = 61613
        self.stomp = Stomp(self.host,self.port)
        self.sock  = self.stomp.sock
        self.frame = self.stomp.frame

    def should_set_socket_opts(self):
        assert stomp.socket.calls('socket',DontCare,DontCare)

    def should_connect(self):
        self.stomp.connect()
        assert self.frame.calls('connect',self.sock)
        assert self.sock.calls('connect',(self.host,self.port))

class WhenProducingMessages(DingusTestCase(Stomp)):

    def setup(self):
        super(WhenProducingMessages, self).setup()
        self.host    = 'localhost'
        self.port    = 61613
        self.stomp   = Stomp(self.host,self.port)
        self.frame   = self.stomp.frame
        self.sock    = self.stomp.sock
        self.headers = {'destination':'/queue/nose_test',
                        'body':'test'}

    def should_connect(self):
        self.stomp.connect()
        assert self.frame.calls('connect',self.sock)
        assert self.sock.calls('connect',(self.host,self.port))

    def should_build_frame_and_send(self):
        self.stomp.send(self.headers)
        built_frame = self.frame.calls('build_frame',DontCare).one()
        built_frame_args = built_frame.args[0]
        send_args = built_frame[3]

        assert built_frame_args['command'] is 'SEND'
        assert self.frame.calls('send_frame',send_args.as_string())

    def should_disconnect(self):
        self.stomp.disconnect()
        built_frame = self.frame.calls('build_frame',DontCare).one()
        built_frame_args = built_frame.args[0]
        send_args = built_frame[3]

        assert built_frame_args['command'] is 'DISCONNECT'
        assert self.frame.calls('send_frame',send_args.as_string())
        assert self.stomp.sock.calls('shutdown',0)

class WhenConsumingMessages(DingusTestCase(Stomp)):

    def setup(self):
        super(WhenConsumingMessages, self).setup()
        self.host    = 'localhost'
        self.port    = 61613
        self.stomp   = Stomp(self.host,self.port)
        self.frame   = self.stomp.frame
        self.sock    = self.stomp.sock
        self.headers = {'destination':'/queue/nose_test',
                        'ack':'client'}

    def should_connect(self):
        self.stomp.connect()
        assert self.frame.calls('connect',self.sock)
        assert self.sock.calls('connect',(self.host,self.port))

    def should_subscribe(self):
        self.stomp.subscribe(self.headers)
        built_frame = self.frame.calls('build_frame',DontCare).one()
        built_frame_args = built_frame.args[0]
        send_args = built_frame[3]

        assert built_frame_args['command'] is 'SUBSCRIBE'
        assert self.frame.calls('send_frame',send_args.as_string())

    def should_receive_and_ack(self):
        this_frame = self.stomp.receive_frame()
        assert self.stomp.frame.calls('parse_frame')

        self.stomp.ack(this_frame)
        built_frame = self.frame.calls('build_frame',DontCare).one()
        built_frame_args = built_frame.args[0]
        send_args = built_frame[3]

        assert built_frame_args['command'] is 'ACK'
        assert self.frame.calls('send_frame',send_args.as_string())

    def should_disconnect(self):
        self.stomp.disconnect()
        built_frame = self.frame.calls('build_frame',DontCare).one()
        built_frame_args = built_frame.args[0]
        send_args = built_frame[3]

        assert built_frame_args['command'] is 'DISCONNECT'
        assert self.frame.calls('send_frame',send_args.as_string())
        assert self.stomp.sock.calls('shutdown',0)

    def should_unsubscribe(self):
        self.stomp.unsubscribe()
        built_frame = self.frame.calls('build_frame',DontCare).one()
        built_frame_args = built_frame.args[0]
        send_args = built_frame[3]

        assert built_frame_args['command'] is 'UNSUBSCRIBE'
        assert self.frame.calls('send_frame',send_args.as_string())

class WhenSocketCantConnect(TestCase):
        def should_fail_connect(self):
            self.stomp = Stomp('localhost',99999)
            self.failUnlessRaises(SystemExit,self.stomp.connect)
