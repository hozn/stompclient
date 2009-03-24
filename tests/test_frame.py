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
