"""
Tests for the simple (publish-only) client.
"""
import time
import threading
from unittest import TestCase
from mockutil import MockingConnectionPool
from Queue import Queue, Empty

from stompclient.duplex import PublishSubscribeClient, QueueingDuplexClient
from stompclient import frame
    
class QueueingDuplexClientTest(TestCase):
    
    def setUp(self):
        self.mockpool = MockingConnectionPool()
        self.mockconn = self.mockpool.connection
        self.client = QueueingDuplexClient('127.0.0.1', 1234, connection_pool=self.mockpool)
        
        self.mock_frame_queue = Queue()
        
        def queue_response_frames(f):
            if f.command == 'CONNECT':
                self.mock_frame_queue.put(frame.Frame('CONNECTED', headers={'session-id': "bogus"}))
            else:
                if 'receipt' in f.headers:
                    receiptid = f.headers['receipt']
                    self.mock_frame_queue.put(frame.Frame('RECEIPT', headers={'receipt-id': receiptid}))
                    
        def queued_frame_returner():
            try:
                time.sleep(0.1)
                # print "Blocking on queue."
                return self.mock_frame_queue.get(block=True, timeout=1.0)
            except Empty:
                return None
        
        self.mockconn.send.side_effect = queue_response_frames
        self.mockconn.read.side_effect = queued_frame_returner
        
        # setup listener thread
        self.listener = threading.Thread(target=self.client.listen_forever, name="ListenerThread-%s" % time.time())
        self.listener.start()
        self.client.listening_event.wait(timeout=1.0) # MAKE SURE WE'RE LISTENING BEFORE WE RUN TEST!
        
    def tearDown(self):
        self.client.disconnect()
        # print "DISCONNECT --> shutdown status? %r" % self.client.shutdown_event.is_set()
        while self.listener.is_alive():
            # print "Waiting for listener thread to end ... shutdown = %r" % self.client.shutdown_event.is_set()
            self.listener.join(timeout=0.5)
        
    def test_connect(self):
        """ Test connect. """
        self.client.connect()
            
        print self.mockconn.send.call_args
        (sentframe,) = self.mockconn.send.call_args[0]
        
        expected = frame.Frame(command='CONNECT', headers={})
        
        self.assertEquals(expected, sentframe)
               
#    def test_disconnect(self):
#        """ Test disconnect. """
#        self.client.disconnect()
#        
#        (sentframe,) = self.mockconn.send.call_args[0]
#        expected = frame.Frame('DISCONNECT')
#        self.assertEquals(expected, sentframe)
#        
#        self.assertTrue(self.mockconn.disconnect.called)
#        

    def test_send(self):
        """ Test send. """
        dest = '/foo/bar'
        body = "This is a test."
        
        self.client.send(dest, body)
        
        messageframe = frame.Frame('MESSAGE', headers={'destination': dest, 'content-length': len(body)}, body=body)
        self.mock_frame_queue.put(messageframe)
        
        (sentframe,) = self.mockconn.send.call_args[0]
        
        expected = frame.Frame('SEND', headers={'destination': dest, 'content-length': len(body)}, body=body)
        
        self.assertEquals(str(expected), str(sentframe))
        

    def test_send_receipt(self):
        """ Test send with receipt requested. """
        dest = '/foo/bar'
        body = "This is a test."
        
        self.client.send(dest, body)
        
        messageframe = frame.Frame('MESSAGE', headers={'destination': dest, 'content-length': len(body)}, body=body)
        self.mock_frame_queue.put(messageframe)
        
        (sentframe,) = self.mockconn.send.call_args[0]
        
        expected = frame.Frame('SEND', headers={'destination': dest, 'content-length': len(body)}, body=body)
        
        self.assertEquals(str(expected), str(sentframe))
        
        # self.client.message_queue.get(timeout=1.0)
        
    def test_subscribe(self):
        """ Test send. """
        dest = '/foo/bar'
        body = "This is a test."
        
        self.client.subscribe(dest)
        self.client.send(dest, body)
        
        messageframe = frame.Frame('MESSAGE', headers={'destination': dest, 'content-length': len(body)}, body=body)
        self.mock_frame_queue.put(messageframe)
        
        (sentframe,) = self.mockconn.send.call_args[0]
        
        expected = frame.Frame('SEND', headers={'destination': dest, 'content-length': len(body)}, body=body)
        
        self.assertEquals(str(expected), str(sentframe))
        
        pushed = self.client.message_queue.get(timeout=1.0)
        self.assertEquals(messageframe, pushed)
        
#    def test_send_tx(self):
#        """ Test send with transaction. """
#        dest = '/foo/bar'
#        body = "This is a test."
#        self.client.send(dest, body, transaction='t-123')
#        (sentframe,) = self.mockconn.send.call_args[0]
#        
#        expected = frame.Frame('SEND', headers={'destination': dest, 'content-length': len(body), 'transaction': 't-123'}, body=body)
#        
#        self.assertEquals(str(expected), str(sentframe))
#        
    