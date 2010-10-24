import socket
import errno
import threading

from stomp.exception import ConnectionError, ConnectionTimeoutError

__authors__ = ['"Hans Lellelid" <hans@xmpl.org>', 'Andy McCurdy (redis)']
__copyright__ = "Copyright 2010 Hans Lellelid, Copyright 2010 Andy McCurdy"
__license__ = """Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
 
  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""


class ConnectionPool(threading.local):
    """
    A thread-local pool of connections keyed by host:port.
    """
    
    def __init__(self):
        self.connections = {}

    def make_connection_key(self, host, port):
        """
        Create a unique key for the specified host and port.
        """
        return '%s:%s' % (host, port)

    def get_connection(self, host, port, socket_timeout):
        """
        Return a specific connection for the specified host and port.
        """
        key = self.make_connection_key(host, port)
        if key not in self.connections:
            self.connections[key] = Connection(host, port, socket_timeout)
        return self.connections[key]

    def get_all_connections(self):
        "Return a list of all connection objects the manager knows about"
        return self.connections.values()
    
class Connection(object):
    """
    Handles TCP connections to the STOMP server.
    """
    def __init__(self, hostname, port=61613, socket_timeout=None):
        self.host = hostname
        self.port = port
        self.socket_timeout = socket_timeout
        self._sock = None
        self._fp = None

        
    def connect(self):
        """
        Connects to the STOMP server if not already connected.
        """
        if self._sock:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
        except socket.error, exc:
            raise self.ConnectionError(*exc.args)
        except socket.timeout, exc:
            raise self.ConnectionTimeoutError(*exc.args)
        
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(self.socket_timeout)
        self._sock = sock
        self._fp = sock.makefile('r')

    def disconnect(self, conf=None):
        """
        Disconnect from the server, if connected.
        
        Sends a DISCONNECT command to the server.
        """
        if self._sock is None:
            return
        try:
            self._sock.close()
        except socket.error:
            pass
        self._sock = None
        self._fp = None
    
    def send(self, command):
        """
        Send ``command`` to the STOMP server. Return the result.
        
        :param command: The serialized command string.
        """
        self.connect()
        try:
            self._sock.sendall(command)
        except socket.error, e:
            if e.args[0] == errno.EPIPE:
                self.disconnect()
            raise ConnectionError("Error %s while writing to socket. %s." % e.args)

    def read(self, length, timeout=None):
        """
        Blocking call to read length bytes from underlying socket.
        
        This can be used in conjunction with the L{stomp.util.FrameBuffer} to parse into 
        discrete frames.
        
        @param length: Number of bytes to read.
        @type length: C{int}
        
        @param timeout: Timeout to wait for bytes.
        @type timeout: C{float}
        """
        save_timeout = self._sock.gettimeout()
        if timeout is not None:
            self._sock.settimeout(timeout)
        try:
            return self._sock.recv(length)
        except socket.timeout:
            pass
        finally:
            self._sock.settimeout(save_timeout)