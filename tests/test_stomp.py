#!/usr/bin/env python
from dingus import Dingus, DingusTestCase, DontCare

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
        self.headers = {'destination':'/queue/nose_test',
                        'body':'test'}

    def should_build_frame_and_send(self):
        self.stomp.connect()
        print self.stomp.send(self.headers)
        call_build = self.frame.calls('build_frame',DontCare,want_receipt=True).one().args[0]
        assert call_build['command'] is 'SEND'
        assert self.frame.calls('send_frame',DontCare)
    
    def should_disconnect(self):
        self.stomp.disconnect()
        assert self.stomp.sock.calls('shutdown',0)

class WhenConsumingMessages(DingusTestCase(Stomp)):

    def setup(self):
        super(WhenConsumingMessages, self).setup()
        self.host    = 'localhost'
        self.port    = 61613
        self.stomp   = Stomp(self.host,self.port)
        self.frame   = self.stomp.frame
        self.headers = {'destination':'/queue/nose_test',
                        'ack':'client'}

    def should_subscribe(self):
        self.stomp.connect()
        self.stomp.subscribe(self.headers)
        call_build = self.frame.calls('build_frame',DontCare).one().args[0]
        assert call_build['command'] is 'SUBSCRIBE'
        assert self.frame.calls('send_frame',DontCare)

    def should_receive_and_ack(self):
        this_frame = self.stomp.receive_frame()
        assert self.stomp.frame.calls('parse_frame')
        self.stomp.ack(this_frame)
        call_build = self.frame.calls('build_frame',DontCare).one().args[0]
        assert call_build['command'] is 'ACK'
        assert self.frame.calls('send_frame',DontCare)

    def should_disconnect(self):
        self.stomp.disconnect()
        assert self.stomp.sock.calls('shutdown',0)
