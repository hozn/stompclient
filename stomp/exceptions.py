import socket.error

class NotConnectedError(Exception):
    """No longer connected to the STOMP server."""


class ConnectionError(socket.error):
    """Couldn't connect to the STOMP server."""


class ConnectionTimeoutError(socket.timeout):
    """Timed-out while establishing connection to the STOMP server."""

