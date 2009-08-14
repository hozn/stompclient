import socket
from four.frame import Frame
from functools import wraps


class NotConnectedError(Exception):
    """No longer connected to the STOMP server."""


class ConnectionError(socket.error):
    """Couldn't connect to the STOMP server."""


class ConnectionTimeoutError(socket.timeout):
    """Timed-out while establishing connection to the STOMP server."""


class Stomp(object):
    """STOMP Client.

    :param hostname: Hostname of the STOMP server to connect to.
    :param port: The port to use. (default ``61613``)

    """
    ConnectionError = ConnectionError
    ConnectionTimeoutError = ConnectionTimeoutError
    NotConnectedError = NotConnectedError

    def __init__(self, hostname, port=61613):
        self.host = hostname
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._subscribed_to = {}
        self._subscribed = None
        self._connected = None
        self.frame = Frame()

    def connect(self):
        """Connect to STOMP server."""
        try:
            self.sock.connect((self.host, self.port))
            self.frame.connect(self.sock)
            self.connected = True
        except socket.error, exc:
            raise self.ConnectionError(*exc.args)
        except socket.timeout, exc:
            raise self.ConnectionTimeoutError(*exc.args)

    def disconnect(self, conf=None):
        """Disconnect from the server."""
        conf = conf or {}
        for destination in self._subscribed_to.keys():
            self.unsubscribe({'destination': destination})
        frame = self.frame.build_frame({'command': 'DISCONNECT',
                                        'headers': conf})
        self.send_frame(frame)
        self.sock.shutdown(0)

    def send(self, conf=None):
        """Send message to STOMP server

        You'll need to pass the body and any other headers your
        STOMP server likes.

        destination is *required*

        In the case of ActiveMQ with persistence, you could do this:

            >>> for i in xrange(1,1000):
            ...     stomp.send({'destination': '/queue/foo',
            ...                 'body': 'Testing',
            ...                 'persistent': 'true'})

        """
        self._connected_or_raise()
        body = conf['body']
        del conf['body']
        frame = self.frame.build_frame({'command': 'SEND',
                                        'headers': conf,
                                        'body': body},
                                        want_receipt=True)
        frame = self.send_frame(frame)
        return frame

    def subscribe(self, conf=None):
        """Subscribe to a given destination

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        In the case of ActiveMQ, you could do this:

            >>> stomp.subscribe({'destination':'/queue/foo',
        ...                      'ack':'client'})
        """
        self._connected_or_raise()
        frame = self.frame.build_frame({'command': 'SUBSCRIBE',
                                        'headers': conf})
        self.send_frame(frame)
        destination = conf["destination"]
        self._subscribed_to[destination] = True

    def begin(self, conf=None):
        """Begin transaction.

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        In the case of ActiveMQ, you could do this:

            >>> stomp.begin({'transaction':'<randomish_hash_like_thing>'})
        """
        self._connected_or_raise()
        frame = self.frame.build_frame({'command': 'BEGIN',
                                        'headers': conf})
        self.send_frame(frame)

    def commit(self, conf=None):
        """Commit transaction.

        You will need to pass any headers your STOMP server likes.

        destination is **required**

        In the case of ActiveMQ, you could do this:

            >>> stomp.commit({'transaction':'<randomish_hash_like_thing>'})

        """
        self._connected_or_raise()
        frame = self.frame.build_frame({'command': 'COMMIT',
                                        'headers': conf})
        self.send_frame(frame)

    def abort(self, conf=None):
        """Abort transaction.

        In the case of ActiveMQ, you could do this:

            >>> stomp.abort({'transaction':'<randomish_hash_like_thing>'})

        """
        self._connected_or_raise()
        frame = self.frame.build_frame({'command': 'ABORT',
                                        'headers': conf})
        self.send_frame(frame)

    def unsubscribe(self, conf=None):
        """Unsubscribe from a given destination

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        >>> stomp.unsubscribe({'destination':'/queue/foo'})
        """
        self._connected_or_raise()
        if conf is None:
            conf = {}
        frame = self.frame.build_frame({'command': 'UNSUBSCRIBE',
                                        'headers': conf})
        self.send_frame(frame)
        destination = conf["destination"]
        self._subscribed_to.pop(destination, None)

    def ack(self, frame):
        """Acknowledge receipt of a message

        :param: A :class:`four.frame.Frame` instance.

        Example

            >>> while True:
            ...     frame = stomp.receive_frame()
            ...     stomp.ack(frame)

        """
        self._connected_or_raise()
        message_id = frame.headers.get('message-id')
        self.send_action("ACK", message_id=message_id)

    def send_action(self, command, **headers):
        headers = dict((key.replace("_", "-"), value)
                            for key, value in headers.items())
        frame = self.frame.build_frame({"command": command,
                                        "headers": headers or {}})
        self.send_frame(frame)

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

        :param frame: A :class:`four.frame.Frame` instance.

        Example

            >>> from four import Frame
            >>> frame = Frame().build_frame({
            ...    "command": "DISCONNECT",
            ...    "headers": {},
            ... })
            >>> stomp.send_frame(frame)

        """
        self._connected_or_raise()
        frame = self.frame.send_frame(frame.as_string())
        return frame

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


    def _get_connected(self):
        return self._connected

    def _set_connected(self, conn):
        self._connected = conn

    connected = property(_get_connected, _set_connected,
                         "Connection status.")
