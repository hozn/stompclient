import abc
import socket
import errno
import threading

from stompclient.util import FrameBuffer

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

class NotConnectedError(Exception):
    """No longer connected to the STOMP server."""


class ConnectionError(socket.error):
    """Couldn't connect to the STOMP server."""


class ConnectionTimeoutError(socket.timeout):
    """Timed-out while establishing connection to the STOMP server."""


class ConnectionPool(object):
    """
    A global pool of connections keyed by host:port.
    
    This pool does not provide any thread-localization for the connections that 
    it stores; use the ThreadLocalConnectionPool subclass if you want to ensure
    that connections cannot be shared between threads.   
    """
    
    def __init__(self):
        self.connections = {}

    def make_connection_key(self, host, port):
        """
        Create a unique key for the specified host and port.
        """
        return '%s:%s' % (host, port)

    def get_connection(self, host, port, socket_timeout=None):
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

class ThreadLocalConnectionPool(ConnectionPool, threading.local):
    """
    A connection pool that ensures that connections are not shared between threads.
    
    This is useful for publish-only clients when desiring a connection pool to be used in a 
    multi-threaded context (e.g. web servers).  This notably does NOT work for publish-
    subscribe clients, since the message messages are received by a separate thread. 
    """
    pass

class Connection(object):
    """
    Manages TCP connection to the STOMP server and provides an abstracted interface for sending
    and receiving STOMP frames.
    
    This class is notably not thread-safe.  You need to use external mechanisms to guard access
    to connections.  This is typically accomplished by using a thread-safe connection pool 
    implementation (e.g. L{stompclient.connection.ThreadLocalConnectionPool}).
    
    @ivar host: The hostname/address for this connection.
    @type host: C{str}
    
    @ivar port: The port for this connection.
    @type port: C{int}
    
    @ivar socket_timeout: Socket timeout (in seconds).
    @type socket_timeout: C{float}
    """
    def __init__(self, host, port=61613, socket_timeout=None):
        self.host = host
        self.port = port
        self.socket_timeout = socket_timeout
        self._sock = None
        self._buffer = FrameBuffer()

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
            raise ConnectionError(*exc.args)
        except socket.timeout, exc:
            raise ConnectionTimeoutError(*exc.args)
        
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(self.socket_timeout)
        self._sock = sock

    def disconnect(self, conf=None):
        """
        Disconnect from the server, if connected.
        """
        if self._sock is None:
            return
        try:
            self._sock.close()
        except socket.error:
            pass
        self._sock = None
        self._buffer.clear()
    
    def send(self, frame):
        """
        Sends the specified frame to STOMP server.
        
        @param frame: The frame to send to server.
        @type frame: L{stompclient.frame.Frame}
        """
        self.connect()
        try:
            self._sock.sendall(str(frame))
        except socket.error, e:
            if e.args[0] == errno.EPIPE:
                self.disconnect()
            raise ConnectionError("Error %s while writing to socket. %s." % e.args)

    def read(self):
        """
        Blocking call to read and return a frame from underlying socket.
        
        Frames are buffered using a L{stompclient.util.FrameBuffer} internally, so subsequent
        calls to this method may simply return an already-buffered frame.
        
        @return: A frame read from socket or buffered from previous socket read.
        @rtype: L{stompclient.frame.Frame}
        """
        self.connect()
        
        buffered_frame = self._buffer.extract_frame()
        
        if buffered_frame:
            return buffered_frame
        else:
            # Read bytes from socket until we have read a frame (or timeout out) and then return it.
            received_frame = None
            try:
                while True:
                    bytes = self._sock.recv(8192)
                    self._buffer.append(bytes)
                    received_frame = self._buffer.extract_frame()
                    if received_frame:
                        break
            except socket.timeout:
                pass
            except socket.error, e:
                if e.args[0] == errno.EPIPE:
                    self.disconnect()
                raise ConnectionError("Error %s while reading from socket. %s." % e.args)
            
            return received_frame