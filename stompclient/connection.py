import abc
import socket
import errno
import threading

from stompclient.util import FrameBuffer
from stompclient.exceptions import ConnectionError, ConnectionTimeoutError, NotConnectedError

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
    subscribe clients, since a listener thread needs to be able to share the *same* socket 
    with other publisher thread(s). 
    """
    pass

class Connection(object):
    """
    Manages TCP connection to the STOMP server and provides an abstracted interface for sending
    and receiving STOMP frames.
    
    This class provides some basic synchronization to avoid threads stepping on eachother. 
    Specifically the following activities are each protected by [their own] C{threading.RLock}
    instances:
    - connect() and disconnect() methods (share a lock).
    - read()
    - send()
    
    It is assumed that send() and recv() should be allowed to happen concurrently, so these do 
    not *share* a lock.  If you need more thread-isolation, consider using a thread-safe 
    connection pool implementation (e.g. L{stompclient.connection.ThreadLocalConnectionPool}).
    
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
        self._connected = threading.Event()
        self._connect_lock = threading.RLock()
        self._send_lock = threading.RLock()
        self._read_lock = threading.RLock()
        
    @property
    def connected(self):
        """
        Whether this connection thinks it is currently connected.
        """
        return self._connected.is_set()
    
    def connect(self):
        """
        Connects to the STOMP server if not already connected.
        """
        with self._connect_lock:
            if self._sock:
                return
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, self.port))
            except socket.timeout as exc:
                raise ConnectionTimeoutError(*exc.args)
            except socket.error as exc:
                raise ConnectionError(*exc.args)
            
            sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(self.socket_timeout)
            self._sock = sock
            self._connected.set()
        
    def disconnect(self, conf=None):
        """
        Disconnect from the server, if connected.
        
        @raise NotConnectedError: If the connection is not currently connected. 
        """
        with self._connect_lock:
            if self._sock is None:
                raise NotConnectedError()
            try:
                self._sock.close()
            except socket.error:
                pass
            self._sock = None
            self._buffer.clear()
            self._connected.clear()
    
    def send(self, frame):
        """
        Sends the specified frame to STOMP server.
        
        @param frame: The frame to send to server.
        @type frame: L{stompclient.frame.Frame}
        """
        with self._send_lock:
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
        with self._read_lock:
            self.connect()
            
            buffered_frame = self._buffer.extract_frame()
            
            if buffered_frame:
                return buffered_frame
            else:
                # Read bytes from socket until we have read a frame (or timeout out) and then return it.
                received_frame = None
                try:
                    while self._connected.is_set():
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