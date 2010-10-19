import socket
import errno
import threading

from stompy.frame import Frame
from functools import wraps


class NotConnectedError(Exception):
    """No longer connected to the STOMP server."""


class ConnectionError(socket.error):
    """Couldn't connect to the STOMP server."""


class ConnectionTimeoutError(socket.timeout):
    """Timed-out while establishing connection to the STOMP server."""


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
            self.connections[key] = Stomp(host, port, socket_timeout)
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

    def read(self, length=None):
        """
        Reads a full frame from socket if length is none, else reads length bytes.
        """
        if length is not None:
            return self._fp.read(length)
        else:
            buffer = ''
            partial = ''
            while not buffer.endswith('\x00\n'):
                try:
                    partial = self._fp.read(1)
                except socket.error, exc:
                    if exc.errno == errno.EAGAIN:
                        if not buffer:
                            return None
                        continue
                buffer += partial
            return buffer[:-2]
    
class Stomp(object):
    """STOMP Client.

    :param hostname: Hostname of the STOMP server to connect to.
    :param port: The port to use. (default ``61613``)

    """
    ConnectionError = ConnectionError
    ConnectionTimeoutError = ConnectionTimeoutError
    NotConnectedError = NotConnectedError

    def __init__(self, hostname, port=61613, socket_timeout=None, connection_pool=None):
        self.host = hostname
        self.port = port
        self.socket_timeout = socket_timeout
        self._subscribed_to = {}
        self._subscribed = None
        self.connected = None
        self.frame = Frame()
        self.connection_pool = connection_pool if connection_pool else ConnectionPool()
        self.connection = self.get_connection(host, port, socket_timeout)
    
    def get_connection(self, host, port, socket_timeout):
        "Returns a connection object"
        conn = self.connection_pool.get_connection(host, port, socket_timeout)
        return conn
    
    def disconnect(self, conf=None):
        """Disconnect from the server."""
        try:
            for destination in self._subscribed_to.keys():
                self.unsubscribe({"destination": destination})
            self._send_command("DISCONNECT", conf)
        except self.NotConnectedError:
            pass
        self.connection.disconnect()

    def send(self, conf=None):
        """Send message to STOMP server

        You'll need to pass the body and any other headers your
        STOMP server likes.

        destination is **required**

        In the case of ActiveMQ with persistence, you could do this:

            >>> for i in xrange(1,1000):
            ...     stomp.send({'destination': '/queue/foo',
            ...                 'body': 'Testing',
            ...                 'persistent': 'true'})

        """
        headers = dict(conf)
        body = headers.pop("body", "")
        return self._send_command("SEND", headers, extra={"body": body}, want_receipt=True)

    def _build_frame(self, *args, **kwargs):
        self._connected_or_raise()
        return self.frame.build_frame(*args, **kwargs)

    def subscribe(self, conf=None):
        """Subscribe to a given destination

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        In the case of ActiveMQ, you could do this:

            >>> stomp.subscribe({'destination':'/queue/foo',
        ...                      'ack':'client'})
        """
        destination = conf["destination"]
        self._send_command("SUBSCRIBE", conf)
        self._subscribed_to[destination] = True

    def begin(self, conf=None):
        """Begin transaction.

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        In the case of ActiveMQ, you could do this:

            >>> stomp.begin({'transaction':'<randomish_hash_like_thing>'})
        """
        self._send_command("BEGIN", conf)

    def commit(self, conf=None):
        """Commit transaction.

        You will need to pass any headers your STOMP server likes.

        destination is **required**

        In the case of ActiveMQ, you could do this:

            >>> stomp.commit({'transaction':'<randomish_hash_like_thing>'})

        """
        self._send_command("COMMIT", conf)

    def abort(self, conf=None):
        """Abort transaction.

        In the case of ActiveMQ, you could do this:

            >>> stomp.abort({'transaction':'<randomish_hash_like_thing>'})

        """
        self._send_command("ABORT", conf)

    def unsubscribe(self, conf=None):
        """Unsubscribe from a given destination

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        >>> stomp.unsubscribe({'destination':'/queue/foo'})
        """
        destination = conf["destination"]
        self._send_command("UNSUBSCRIBE", conf)
        self._subscribed_to.pop(destination, None)

    def ack(self, frame):
        """Acknowledge receipt of a message

        :param: A :class:`stompy.frame.Frame` instance.

        Example

            >>> while True:
            ...     frame = stomp.receive_frame()
            ...     stomp.ack(frame)

        """
        message_id = frame.headers.get('message-id')
        self._send_command("ACK", {"message-id": message_id})

    def receive_frame(self, nonblocking=False):
        """Get a frame from the STOMP server

        :keyword nonblocking: By default this function waits forever
            until there is a message to be received, however, in non-blocking
            mode it returns ``None`` if there is currently no message
            available.

        Note that you must be subscribed to one or more destinations.
        Use :meth:`subscribe` to subscribe to a topic/queue.

        Example: Blocking

            >>> while True:
            ...     frame = stomp.receive_frame()
            ...     print(frame.headers['message-id'])
            ...     stomp.ack(frame)

        Example: Non-blocking

            >>> frame = stomp.recieve_frame(nonblocking=True)
            >>> if frame:
            ...     process_message(frame)
            ... else:
            ...     # no messages yet.

        """
        self._connected_or_raise()
        return self.frame.get_message(nb=nonblocking)

    def poll(self):
        """Alias to :meth:`receive_frame` with ``nonblocking=True``."""
        return self.receive_frame(nonblocking=True)

    def send_frame(self, frame):
        """Send a custom frame to the STOMP server

        :param frame: A :class:`stompy.frame.Frame` instance.

        Example

            >>> from stompy import Frame
            >>> frame = Frame().build_frame({
            ...    "command": "DISCONNECT",
            ...    "headers": {},
            ... })
            >>> stomp.send_frame(frame)

        """
        try:
            replyframe = self.connection.send(str(frame))
            return self.parse_response(command_name, **options)
        except ConnectionError:
            self.connection.disconnect()
            self.connection.send(command, self)
            return self.parse_response(command_name, **options)
        
        self._connected_or_raise()
        frame = self.frame.send_frame(frame.as_string())
        return frame
    
    def parse_response(self, response):
        pass
    
    def _send_command(self, command, conf=None, extra=None, **kwargs):
        conf = conf or {}
        extra = extra or {}
        frame_conf = {"command": command, "headers": conf}
        frame_conf.update(extra)
        frame = self._build_frame(frame_conf, **kwargs)
        reply = self.send_frame(frame)
        if kwargs.get("want_receipt", False):
            return reply
        return frame
    
        
    
    
    #### COMMAND EXECUTION AND PROTOCOL PARSING ####
    def _execute_command(self, command_name, command, **options):
        subscription_command = command_name in self.SUBSCRIPTION_COMMANDS
        if self.subscribed and not subscription_command:
            raise RedisError("Cannot issue commands other than SUBSCRIBE and "
                "UNSUBSCRIBE while channels are open")
        try:
            self.connection.send(command, self)
            if subscription_command:
                return None
            return self.parse_response(command_name, **options)
        except ConnectionError:
            self.connection.disconnect()
            self.connection.send(command, self)
            if subscription_command:
                return None
            return self.parse_response(command_name, **options)
        
    def _connected_or_raise(self):
        if not self.connected:
            raise self.NotConnectedError("Not connected to STOMP server.")

    @property
    def subscribed(self):
        """**DEPRECATED** The queue or topic currently subscribed to."""
        as_list = self._subscribed_to.keys()
        if not as_list:
            return
        return as_list[0]
