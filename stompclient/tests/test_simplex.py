"""
Tests for the simple (publish-only) client.
"""
from unittest import TestCase

from mock import sentinel

from stompclient.simplex import PublishClient
from stompclient import frame

from stompclient.tests.mockutil import MockingConnectionPool

__authors__ = ['"Hans Lellelid" <hans@xmpl.org>']
__copyright__ = "Copyright 2010 Hans Lellelid"
__license__ = """Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
 
  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

class SimplexClientTest(TestCase):
    
    def setUp(self):
        self.mockpool = MockingConnectionPool()
        self.mockconn = self.mockpool.connection
        self.client = PublishClient('127.0.0.1', 1234, connection_pool=self.mockpool)
        self.mockconn.connected = False
        
    def test_connect(self):
        """ Test connect. """
        self.client.connect()
        #self.assertTrue(self.mockconn.connect.called)
        
        print self.mockconn.send.call_args
        (sentframe,) = self.mockconn.send.call_args[0]
        
        expected = frame.Frame(command='CONNECT', headers={})
        
        self.assertEquals(expected, sentframe)
        
    def test_connect_auth(self):
        """ Test connect with authentication. """
        self.client.connect('foo', 'bar')
        #self.assertTrue(self.mockconn.connect.called)
        
        print self.mockconn.send.call_args
        (sentframe,) = self.mockconn.send.call_args[0]
        
        expected = frame.Frame(command='CONNECT', headers={'login': 'foo', 'passcode': 'bar'})
        
        self.assertEquals(expected, sentframe)
    
    def test_disconnect(self):
        """ Test disconnect. """
        self.client.connect()
        
        #self.mockconn.connected.side_effect = lambda: True
        print self.mockconn.send.call_args
        self.mockconn.connected = True
        
        self.client.disconnect()
        
        print self.mockconn.send.call_args
        
        (sentframe,) = self.mockconn.send.call_args[0]
        expected = frame.Frame('DISCONNECT')
        self.assertEquals(expected, sentframe)
        self.assertTrue(self.mockconn.disconnect.called)
        
    def test_disconnect_notconnected(self):
        """ Test disconnect when already disconnected """
        self.client.disconnect()
        self.assertFalse(self.mockconn.send.called)
        self.assertFalse(self.mockconn.disconnect.called)
     
    def test_send(self):
        """ Test send. """
        dest = '/foo/bar'
        body = "This is a test."
        self.client.send(dest, body)
        (sentframe,) = self.mockconn.send.call_args[0]
        
        expected = frame.Frame('SEND', headers={'destination': dest, 'content-length': len(body)}, body=body)
        
        self.assertEquals(str(expected), str(sentframe))
        
    def test_send_tx(self):
        """ Test send with transaction. """
        dest = '/foo/bar'
        body = "This is a test."
        self.client.send(dest, body, transaction='t-123')
        (sentframe,) = self.mockconn.send.call_args[0]
        
        expected = frame.Frame('SEND', headers={'destination': dest, 'content-length': len(body), 'transaction': 't-123'}, body=body)
        
        self.assertEquals(str(expected), str(sentframe))
        
    