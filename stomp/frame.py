#!/usr/bin/env python
import socket
import random

class Frame:
    """Build and manage a STOMP Frame.

    This is useful for connecting to and communicating with
    Apache ActiveMQ, an open source Java Message Service (JMS)
    message broker.

    For specifics on the protocol, see: http://stomp.codehaus.org/Protocol

    This library is basically a Python implementation of Perl's Net::Stomp
    See: http://search.cpan.org/dist/Net-Stomp/lib/Net/Stomp.pm

    To enable the ActiveMQ Broker for Stomp add the following to the activemq.xml configuration:

    <connector>
        <serverTransport uri="stomp://localhost:61613"/>
    </connector>

    """
    def __init__(self,sock=None):
        """Initialize Frame object
        Passing a socket object is optional
        >>> frameobj = Frame(socket)
        """
        self.command  = None
        self.headers  = {}
        self.body     = None
        self.session  = None
        self.my_name  = socket.gethostbyname(socket.gethostname())
        self.sock     = sock

    def connect(self,sock):
        """Connect to the STOMP server, get session id
        >>> frameobj.connect(sock)
        """
        self.sock = sock
        frame = self.build_frame({'command':'CONNECT','headers':{}})
        self.send_frame(frame.as_string())
        line = self._getline()
        if line == 'CONNECTED':
            self.session = (self.parse_headers(self._getline()))
            self._getline()

    def build_frame(self,args,want_receipt=False):
        """Build a frame based on arguments
        >>> frame = frameobj.build_frame(({'command':'CONNECT','headers':{}})
        Optional argument to get receipt of message.
        >>> frame = frameobj.build_frame(({'command':'SEND',
        ...                                'headers':headers,
        ...                                'body':body},want_receipt=True)
        """
        self.command = args['command']
        self.headers = args['headers']
        self.body = args.get('body')
        if want_receipt:
            receipt_stamp = str(random.randint(0,10000000))
            self.headers['receipt'] = self.session['session'] + "-" + receipt_stamp
        return self

    def as_string(self):
        """Make raw string from frame
        Suitable for passing over socket to STOMP server
        >>> stomp.send(frameobj.as_string())
        """
        command = self.command
        headers = self.headers
        body    = self.body
        frame   = "%s\n" % command
        
        headers['x-client'] = self.my_name

        bytes_message = False
        if 'bytes_message' in headers:
            bytes_message = True
            del headers['bytes_message']
            headers['content-length'] = len(body)

        if headers:
            for k,v in headers.iteritems():
                frame += "%s:%s\n" %(k,v)

        frame += "\n%s\x00" % body
        return frame

    def parse_frame(self):
        """Parse data from socket
        Accepts socket object as argument
        >>> frameobj.parse_frame(sock)
        """
        command = ''
        body    = ''
        headers = {}
        server_cmds = ['MESSAGE','RECEIPT','ERROR']

        while True:
            while True:
                line = self._getline()
                if line in server_cmds:
                    continue
                elif line == '\x00':
                    continue 
                if line == '':
                    break
                headers.update(self.parse_headers(line))
                continue
            
            if 'content-length' in headers:
                body = self._getline()
                headers['bytes_message'] = True
            if headers:
                while True:
                    byte = self.sock.recv(1)
                    if not byte:
                        exit(1)
                    if byte == "\x00":
                        break
                    body += byte
                break
            else:
                continue

        frame = Frame(self.sock)
        frame = frame.build_frame({'command':command,'headers':headers,'body':body})
        return frame

    def parse_headers(self,str):
        """Parse headers, return
        >>> frameobj.parse_headers(str)
        """
        headers = {}
        (key,value) = str.split(':',1)
        headers[key] = value
        return headers

    def send_frame(self,frame):
        """Send frame to server, get receipt if needed
        >>> frameobj.send_frame(frame)
        """
        self.sock.sendall(frame)
        if 'receipt' in self.headers:
            frame = self.parse_frame()
            return frame
        else:
            return None 

    def _getline(self):
        """Get a single line from socket
        >>> self._getline()
        """
        buffer = ''
        while not buffer.endswith('\n'):
            buffer += self.sock.recv(1)
        return buffer[:-1]
