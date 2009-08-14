import socket
import random
from errno import EAGAIN
from Queue import Queue
from Queue import Empty as QueueEmpty


class IntermediateMessageQueue(object):
    """Internal message queue that holds messages received by the server.

    This to make sure a message isn't received instead of a command response
    after issuing a receipt request.

    """

    def __init__(self):
        self._queue = Queue()

    def put(self, frame):
        """Put a new frame onto the message queue."""
        if "destination" not in frame.headers:
            return
        self._queue.put(frame)

    def get(self, frame, nb=False):
        """Get a new frame from the message queue.
        If no frame is available it try to get the next frame
        from the socket.

        :param frame: A :class:`Frame` instance.
        :keyword nb: Non-blocking.

        """
        try:
            return self._queue.get_nowait()
        except QueueEmpty:
            return frame.parse_frame(nb=nb)


class Frame(object):
    """Build and manage a STOMP Frame.

    :keyword sock: An open socket to the STOMP server.

    """

    def __init__(self, sock=None):
        self.command = None
        self.headers = {}
        self.body = None
        self.session = None
        self.my_name = socket.gethostbyname(socket.gethostname())
        self.sock = sock
        self.iqueue = IntermediateMessageQueue()
        self.rqueue = Queue()

    def connect(self, sock):
        """Connect to the STOMP server and get the session id."""
        self.sock = sock
        frame = self.build_frame({"command": "CONNECT", "headers": {}})
        self.send_frame(frame.as_string())

        # Get session from the next reply from the server.
        next_frame = self.get_reply()
        self.session = next_frame.headers

    def build_frame(self, args, want_receipt=False):
        """Build a frame based on a :class:`dict` of arguments.

        :param args: A :class:`dict` of arguments for the frame.

        :keyword want_receipt: Optional argument to get a receipt from
            the sever that the frame was received.

        Example

            >>> frame = frameobj.build_frame({"command": 'CONNECT',
                                              "headers": {},
                                              want_receipt=True)
        """
        self.command = args.get('command')
        self.headers = args.get('headers')
        self.body = args.get('body')
        if want_receipt:
            receipt_stamp = str(random.randint(0, 10000000))
            self.headers["receipt"] = "%s-%s" % (
                    self.session.get("session"), receipt_stamp)
        return self

    def as_string(self):
        """Raw string representation of this frame
        Suitable for passing over a socket to the STOMP server.

        Example

            >>> stomp.send(frameobj.as_string())

        """
        command = self.command
        headers = self.headers
        body = self.body
        frame = "%s\n" % command
        headers['x-client'] = self.my_name
        bytes_message = False
        if 'bytes_message' in headers:
            bytes_message = True
            del headers['bytes_message']
            headers['content-length'] = len(body)

        # Convert and append any existing headers to a string as the
        # protocol describes.
        headerparts = ("%s:%s\n" % (key, value)
                            for key, value in headers.iteritems())
        frame += "".join(headerparts)

        # Finally append the body with the EOF marker.
        frame += "\n%s\x00" % body

        return frame

    def get_message(self, nb=False):
        """Get next message frame."""
        while True:
            frame = self.iqueue.get(self, nb=nb)
            if not frame and nb:
                return None
            if frame.command == "MESSAGE":
                return frame
            else:
                self.rqueue.put(frame)

    def get_reply(self, nb=False):
        """Get command reply frame."""
        while True:
            try:
                return self.rqueue.get_nowait()
            except QueueEmpty:
                frame = self.parse_frame(nb=nb)
                if not frame and nb:
                    return None
                if frame.command == "MESSAGE":
                    self.iqueue.put(frame)
                else:
                    self.rqueue.put(frame)

    def parse_frame(self, nb=False):
        """Parse data from socket

        :keyword nb: Non-blocking: If this is set and there is no
            messages currently waiting, this functions returns ``None``
            instead of waiting for more data.

        Example

            >>> frameobj.parse_frame()

        """
        command = None
        body = None
        headers = {}

        while True:
            line = self._getline(nb=nb)
            if not line:
                return

            command = self.parse_command(line)
            line = line[len(command)+1:]
            headers_str, body = line.split('\n\n')
            headers = self.parse_headers(headers_str)

            if 'content-length' in headers:
                headers['bytes_message'] = True
            break

        frame = Frame(self.sock)
        frame = frame.build_frame({'command': command,
                                   'headers': headers,
                                   'body': body})
        return frame

    def parse_command(self, str):
        """Parse command received from the server."""
        command = str.split('\n', 1)[0]
        return command

    def parse_headers(self, str):
        """Parse headers received from the servers and convert
        to a :class:`dict`."""
        headers = {}
        for line in str.split('\n'):
            key, value = line.split(':', 1)
            headers[key] = value
        return headers

    def send_frame(self, frame):
        """Send frame to server, get receipt if needed."""
        self.sock.sendall(frame)

        if 'receipt' in self.headers:
            return self.get_reply()

    def _getline(self, nb=False):
        """Get a single line from socket

        :keyword nb: Non-blocking: If this is set, and there is no
            messages to receive, this function returns ``None``.

        """
        self.sock.setblocking(not nb)
        try:
            buffer = ''
            partial = ''
            while not buffer.endswith('\x00\n'):
                try:
                    partial = self.sock.recv(1)
                except socket.error, exc:
                    if exc.errno == EAGAIN:
                        if not buffer:
                            return None
                        continue
                buffer += partial
        finally:
            self.sock.setblocking(nb)
        return buffer[:-2]
