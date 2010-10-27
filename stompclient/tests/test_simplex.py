"""
Tests for the simple (publish-only) client.
"""
from unittest import TestCase
from mockutil import MockingConnectionPool

from stompclient.simplex import PublishClient
from stompclient import frame

class SimplexClientTest(TestCase):
    
    def setUp(self):
        self.mockpool = MockingConnectionPool()
        self.mockconn = self.mockpool.connection
        self.client = PublishClient('127.0.0.1', 1234, connection_pool=self.mockpool)
        
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
        self.client.disconnect()
        
        (sentframe,) = self.mockconn.send.call_args[0]
        expected = frame.Frame('DISCONNECT')
        self.assertEquals(expected, sentframe)
        
        self.assertTrue(self.mockconn.disconnect.called)
        
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
        
    