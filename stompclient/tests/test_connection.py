import threading
from Queue import Queue
from unittest import TestCase

from stompclient.connection import ThreadLocalConnectionPool, ConnectionPool

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
        
    