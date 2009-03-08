#!/usr/bin/env python

import socket
from frame import Frame

class Stomp:
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
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((hostname,port))
        self.frame = Frame()

    def connect(self, conf={}):
        """Connect to STOMP server
        This method does not require any arguments.

        >>> stomp.connect()
        """
        frame = self.frame.build_frame({'command':'CONNECT','headers':conf})
        self.send_frame(frame)
        frame = self.receive_frame()

    def disconnect(self, conf={}):
        """Disconnect from STOMP server
        This method does not require any arguments.
        
        >>> stomp.disconnect()
        """
        frame = self.frame.build_frame({'command':'DISCONNECT','headers':conf})
        self.send_frame(frame)
        self.sock.close()

    def send(self,conf={}):
        """Send message to STOMP server

        You'll need to pass the body and any other headers your STOMP server likes.

        destination is *required*

        In the case of ActiveMQ with persistence, you could do this:
        >>> for i in xrange(1,1000):
        ...     stomp.send({'destination':'/queue/foo',
        ...                 'body':'Testing',
        ...                 'persistent':'true'})
        """
        body = conf['body']
        del conf['body']
        frame = self.frame.build_frame({'command':'SEND','headers':conf,'body':body})
        self.send_frame(frame)

    def subscribe(self,conf={}):
        """Subscribe to a given destination

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        In the case of ActiveMQ, you could do this:
        >>> stomp.subscribe({'destination':'/queue/foo',
        ...                  'ack':'client'})
        """
        frame = self.frame.build_frame({'command':'SUBSCRIBE','headers':conf})
        self.send_frame(frame)

    def unsubscribe(self,conf={}):
        """Unsubscribe from a given destination

        You will need to pass any headers your STOMP server likes.

        destination is *required*

        >>> stomp.unsubscribe({'destination':'/queue/foo'})
        """
        frame = self.frame.build_frame({'command':'UNSUBSCRIBE','headers':conf})
        self.send_frame(frame)

    def ack(self,frame):
        """Acknowledge receipt of a message
        
        Accepts a frame as an argument and it is *required*.

        Given that you are already subscribed to a destination
        and that the destination has messages for consumption

        >>> while True:
        ...     frame = stomp.receive_frame()
        ...     stomp.ack(frame)
        """
        msgid = frame.headers['message-id']
        thisframe = self.frame.build_frame({'command':'ACK','headers':{'message-id':msgid}})
        self.send_frame(thisframe)

    def receive_frame(self):
        """Get a frame from the STOMP server
        
        Takes no arguments

        Given that you are already subscribed to a destination
        and that the destination has messages for consumption

        >>> while True:
        ...     frame = stomp.receive_frame()
        ...     print fram.headers['message-id']
        ...     stomp.ack(frame)
        """
        frame = self.frame.parse(self.sock)
        return frame

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
        self.sock.send(frame.as_string())
