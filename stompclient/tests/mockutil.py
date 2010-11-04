"""
Utilities for working with mock objects.
"""
import socket

from mock import Mock

from stompclient.connection import Connection

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

class MockingConnectionPool(object):
    """
    A connection pool that returns a single Mock connection object instead of real ones.
    """
    
    def __init__(self):
        self.connection = Mock(spec=Connection)

    def get_connection(self, host, port, socket_timeout=None):
        """
        Return a specific connection for the specified host and port.
        """
        return self.connection

    def get_all_connections(self):
        "Return a list of all connection objects the manager knows about"
        return [self.connection]
    
class MockingSocketModule(object):
    """
    A class that replaces the C{socket} module to return C{mock.Mock} instances in response to 
    C{socket.socket()} invocation.
    """
    def __init__(self):
        self.mocksocket = Mock(spec=socket._socketobject)
        
    def socket(self, *args, **kwargs):
        return self.mocksocket
    
    def __getattr__(self, name):
        return getattr(socket, name)