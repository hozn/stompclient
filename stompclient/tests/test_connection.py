import threading
from Queue import Queue
from unittest import TestCase
import socket

import mock

import stompclient.connection
from stompclient.connection import ThreadLocalConnectionPool, ConnectionPool, Connection
from stompclient.exceptions import ConnectionError, ConnectionTimeoutError, NotConnectedError
from stompclient import frame

from stompclient.tests.mockutil import MockingSocketModule

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

class ConnectionPoolTest(TestCase):
    
    def test_nonthreadlocal(self):
        """ Test non-thread-localness of ConnectionPool. """
        pool = ConnectionPool()
        c1 = pool.get_connection('localhost', 1234)
        c2 = pool.get_connection('localhost', 1234)
        assert c1 is c2
        
        queue = Queue()
        
        def create():
            queue.put(pool.get_connection('localhost', 1234))
            
        t1 = threading.Thread(target=create)
        t1.start()
        
        c3 = queue.get()
        assert c3 is c2
        
    def test_threadlocal(self):
        """ Test thread-localness of ThreadLocalConnectionPool. """
        pool = ThreadLocalConnectionPool()
        c1 = pool.get_connection('localhost', 1234)
        c2 = pool.get_connection('localhost', 1234)
        assert c1 is c2
        
        queue = Queue()
        
        def create():
            queue.put(pool.get_connection('localhost', 1234))
            
        t1 = threading.Thread(target=create)
        t1.start()
        
        c3 = queue.get()
        assert c3 is not c2
        assert c3.host == c2.host
        assert c3.port == c2.port
        
        
class ConnectionTest(TestCase):
    
    def setUp(self):
        #self.conn._sock = mock.Mock(spec=socket._socketobject)
        mocksocketmodule = MockingSocketModule()
        stompclient.connection.socket = mocksocketmodule
        self.mocksocket = mocksocketmodule.mocksocket
    
    def test_connect(self):
        """ Test basic connection functionality. """
        conn = Connection('1.2.3.4', 61613)
        
        conn.connect()
        print self.mocksocket.method_calls
        
        self.assertTrue(self.mocksocket.connect.called)
        self.assertEquals((('1.2.3.4', 61613),), self.mocksocket.connect.call_args[0])
        
        self.mocksocket.reset_mock()
        conn.connect()
        self.assertFalse(self.mocksocket.connect.called)
    
    def test_connected(self):
        """ Test that 'connected' property reflects connection status. """
        conn = Connection('1.2.3.4', 61613)
        conn.connect()
        self.assertTrue(conn.connected)
        
        conn.disconnect()
        self.assertFalse(conn.connected)
        
        conn.connect()
        self.assertTrue(conn.connected)
        
    def test_connect_exc(self):
        """ Test to ensure socket.error exceptions get wrapped. """
        conn = Connection('1.2.3.4', 61613)
        
        self.mocksocket.connect.side_effect = socket.error
        
        self.assertRaises(ConnectionError, conn.connect)
        
        self.mocksocket.connect.side_effect = socket.timeout
        
        self.assertRaises(ConnectionTimeoutError, conn.connect)
    
    def test_auto_connect(self):
        """ Test the fact that send and read automatically attempt to connect. """
        conn = Connection('1.2.3.4', 61613)
        conn.send("MESSAGE")
        self.assertTrue(self.mocksocket.connect.called)
        conn.disconnect()
        
        f = frame.ConnectedFrame('my-session-id')
        self.mocksocket.reset_mock()
        self.mocksocket.recv.side_effect = lambda len: str(f)
        
        result = conn.read()
        self.assertEquals(str(f), str(result))
        self.assertTrue(self.mocksocket.connect.called)
        
    def test_disconnect_notconnected(self):
        """ Attempting to disconnect when not connected should raise exception. """
        conn = Connection('1.2.3.4', 61613)
        self.assertRaises(NotConnectedError, conn.disconnect)
        conn.connect()
        conn.disconnect()
        self.assertRaises(NotConnectedError, conn.disconnect)
        
    def test_disconnect_reconnect(self):
        """ Test disconnect and reconnect behavior. """
        conn = Connection('1.2.3.4', 61613)
        conn.connect()
        
        conn.disconnect()
        
        self.assertFalse(conn.connected)
            
        conn.send("MESSAGE")
        
        self.assertTrue(self.mocksocket.connect.called)
        self.assertTrue(self.mocksocket.sendall.called)
        