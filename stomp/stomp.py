#!/usr/bin/env python

import socket
from frame import Frame
from errno import EAGAIN

class NotConnectedError(Exception):
    """Raise if not connected"""
    def __init__(self, value):
        self.value = value
    
    def __str__(self):
        return repr(self.value)

class Stomp(object):
    """Dead simple Python STOMP client library

    This is useful for connecting to and communicating with
    Apache ActiveMQ, an open source Java Message Service (JMS)
    message broker.

    The majority of the methods available take a single argument; a dictionary.
    This dictionary should contain the necessary bits you need
    to pass to the STOMP server.  It is outlined in each method
    exactly what it needs to work.

    For specifics on the protocol, see: http://stomp.codehaus.org/Protocol

    This library is basically a Python implementation of Perl's Net::Stomp
    See: http://search.cpan.org/dist/Net-Stomp/lib/Net/Stomp.pm

    To enable the ActiveMQ Broker for Stomp add the following to the activemq.xml configuration:

    <connector>
        <serverTransport uri="stomp://localhost:61613"/>
    </connector>
    """
    def __init__(self,hostname,port):
        """Initialize Stomp object
        Also accepts arguments needed to build the TCP connection.
        
        >>> from stomp import Stomp
        >>> stomp = Stomp('hostname', 61613)
        """
        self.host        = hostname
        self.port        = port
        self.sock        = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._subscribed = None
        self._connected  = None
        self.frame       = Frame()

    def _get_subscribed(self):
        return self._subscribed

    def _set_subscribed(self,sub):
        self._subscribed = sub

    subscribed = property(_get_subscribed, _set_subscribed, 
                          'The queue or topic we are subscribed to')

    def _get_connected(self):
        return self._connected
    
    def _set_connected(self,conn):
        self._connected = conn

    connected = property(_get_connected, _set_connected,
                         'Are we connected to STOMP Server')

    def _is_connected(self):
        if not self.connected:
            raise NotConnectedError, 'Not connected to STOMP server.'

    def connect(self, conf=None):
        """Connect to STOMP server
        This method does not require any arguments.

        >>> stomp.connect()
        """
        try:
            self.sock.connect((self.host,self.port))
            self.frame.connect(self.sock)
            self.connected = True
        except (socket.error,socket.timeout), err:
            print "Cannot connect to %s on port %d" %(self.host,self.port)
            print "Caught error: %s" % err
            raise SystemExit

    def disconnect(self, conf=None):
        """Disconnect from STOMP server
        This method does not require any arguments.
        
        >>> stomp.disconnect()
        """
        if self.subscribed:
            self.unsubscribe({'destination':self.subscribed})
        if conf is None:
            conf = {}
        frame = self.frame.build_frame({'command':'DISCONNECT','headers':conf})
        self.send_frame(frame)
        self.sock.shutdown(0)

    def send(self,conf=None):
        """Send message to STOMP server

        You'll need to pass the body and any other headers your STOMP server likes.

        destination is *required*

        In the case of ActiveMQ with persistence, you could do this:
        >>> for i in xrange(1,1000):
        ...     stomp.send({'destination':'/queue/foo',
        ...                 'body':'Testing',
        ...                 'persistent':'true'})
        """
        self._is_connected()
        body = conf['body']
        del conf['body']
        frame = self.frame.build_frame({'command':'SEND',
                                        'headers':conf,
                                        'body':body}, want_receipt=True)
        frame = self.send_frame(frame)
        return frame

    def subscribe(self,conf=None):
        """Subscribe to a given destination

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        In the case of ActiveMQ, you could do this:
        >>> stomp.subscribe({'destination':'/queue/foo',
        ...                  'ack':'client'})
        """
        self._is_connected()
        frame = self.frame.build_frame({'command':'SUBSCRIBE','headers':conf})
        self.send_frame(frame)
        self.subscribed = conf.get('destination')

    def begin(self,conf=None):
        """Subscribe to a given destination

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        In the case of ActiveMQ, you could do this:
        >>> stomp.begin({'transaction':'<randomish_hash_like_thing>'})
        """
        self._is_connected()
        frame = self.frame.build_frame({'command':'BEGIN','headers':conf})
        self.send_frame(frame)

    def commit(self,conf=None):
        """Subscribe to a given destination

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        In the case of ActiveMQ, you could do this:
        >>> stomp.commit({'transaction':'<randomish_hash_like_thing>'})
        """
        self._is_connected()
        frame = self.frame.build_frame({'command':'COMMIT','headers':conf})
        self.send_frame(frame)

    def abort(self,conf=None):
        """Subscribe to a given destination

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        In the case of ActiveMQ, you could do this:
        >>> stomp.abort({'transaction':'<randomish_hash_like_thing>'})
        """
        self._is_connected()
        frame = self.frame.build_frame({'command':'ABORT','headers':conf})
        self.send_frame(frame)

    def unsubscribe(self,conf=None):
        """Unsubscribe from a given destination

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        >>> stomp.unsubscribe({'destination':'/queue/foo'})
        """
        self._is_connected()
        if conf is None:
            conf = {}
        frame = self.frame.build_frame({'command':'UNSUBSCRIBE','headers':conf})
        self.send_frame(frame)
        self.subscribed = None

    def ack(self,frame):
        """Acknowledge receipt of a message
        
        Accepts a frame as an argument and it is *required*.

        Given that you are already subscribed to a destination
        and that the destination has messages for consumption

        >>> while True:
        ...     frame = stomp.receive_frame()
        ...     stomp.ack(frame)
        """
        self._is_connected()
        msgid = frame.headers.get('message-id')
        thisframe = self.frame.build_frame({'command':'ACK','headers':{'message-id':msgid}})
        self.send_frame(thisframe)

    def receive_frame(self, nonblocking=False):
        """Get a frame from the STOMP server
        
        :keyword nonblocking: By default this function waits forever
            until there is a message to be received, however, in non-blocking
            mode it returns ``None`` if there is no messages available.

        Given that you are already subscribed to a destination
        and that the destination has messages for consumption

        >>> while True:
        ...     frame = stomp.receive_frame()
        ...     print frame.headers['message-id']
        ...     stomp.ack(frame)
        """
        self._is_connected()
        frame = self.frame.get_message(nb=nonblocking)
        return frame

    def poll(self):
        """See if there is a message to be fetched on the server, if there is
        returns the frame."""
        return self.receive_frame(nonblocking=True)

    def send_frame(self, frame):
        """Send frame to the STOMP server

        Takes a frame object as argument

        You could build your own frame and bypass all that 
        this library provides, if you wish
       
        >>> from stomp import Stomp, Frame
        >>> stomp = Stomp('localhost',61613)
        >>> frameobj = Frame()
        >>> frame = frameobj.build_frame({'command':'DISCONNECT','headers':{}})
        >>> stomp.send_frame(frame)
        """
        self._is_connected()
        frame = self.frame.send_frame(frame.as_string())
        return frame
