"""
Classes to support reading and writing STOMP frames.

This is a mixture of code from the stomper project and the stompy project codebases.
"""
import uuid

from stompclient.exceptions import FrameError
 
__authors__ = ['"Hans Lellelid" <hans@xmpl.org>', 'Ricky Iacovou (stomper)', 'Benjamin W. Smith (stompy)']
__copyright__ = "Copyright 2010 Hans Lellelid, Copyright 2008 Ricky Iacovou, Copyright 2009 Benjamin W. Smith"
__license__ = """Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
 
  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

# STOMP Spec v1.0 valid commands:
VALID_COMMANDS = [
    'ABORT', 'ACK', 'BEGIN', 'COMMIT', 
    'CONNECT', 'CONNECTED', 'DISCONNECT', 'MESSAGE',
    'SEND', 'SUBSCRIBE', 'UNSUBSCRIBE',
    'RECEIPT', 'ERROR',    
]

class Frame(object):
    """
    Class to hold a STOMP message frame. 
    
    This class is based on code from the Stomper project, with a few modifications.
    
    @ivar command: The STOMP command.  When assigned it is validated
                against the VALID_COMMANDS module-level list.
    @type command: C{str}
    
    @ivar headers: A dictionary of headers for this frame.
    @type headers: C{dict}
    
    @ivar body: The body of the message (bytes).
    @type body: C{str}
    """    
    def __init__(self, command=None, headers=None, body=None):
        """
        Initialize new frame with command, headers, and body.
        """
        if body is None:
            body = ''
        if headers is None:
            headers = {}
        self.command = command
        self.body = body
        self.headers = headers
    
    def _get_cmd(self):
        """
        Returns the command for this frame.
        """
        return self._cmd
    
    def _set_cmd(self, cmd):
        """
        Sets the command, after ensuring that it is a valid command (or None).
        """
        if cmd is not None:
            cmd = cmd.upper()
            if cmd not in VALID_COMMANDS:
                raise FrameError("The command '%s' is not valid; it must be one of %r" % (cmd, VALID_COMMANDS))
        self._cmd = cmd
    
    command = property(_get_cmd, _set_cmd)

    def unpack(self, framebytes):
        """
        Parse data from received bytes into this frame object.
        """
        command = self.parse_command(framebytes)
        line = framebytes[len(command)+1:]
        headers_str, _, body = framebytes.partition("\n\n")
        if not headers_str:
            raise FrameError("No headers in frame line; received: (%s)" % line)
        headers = self.parse_headers(headers_str)
        
        self.command = command
        self.headers = headers
        self.body = body

    def parse_command(self, framebytes):
        """
        Parse command received from the server.
        
        @return: The command.
        @rtype: C{str}
        """
        command = framebytes.split('\n', 1)[0]
        return command

    def parse_headers(self, headers_str):
        """
        Parse headers received from the servers and convert to a :class:`dict`.
        
        @return: The headers dict.
        @rtype: C{dict}
        """
        # george:constanza\nelaine:benes
        # -> {"george": "constanza", "elaine": "benes"}
        return dict(line.split(":", 1) for line in headers_str.split("\n"))
    
    def pack(self):
        """
        Create a string representation from object state.
        
        @return: The string (bytes) for this stomp frame.
        @rtype: C{str} 
        """
        command = self.command
        headers = self.headers
        body = self.body
        
        headers['content-length'] = len(body)

        # Convert and append any existing headers to a string as the
        # protocol describes.
        headerparts = ("%s:%s\n" % (key, value) for key, value in headers.iteritems())

        # Frame is Command + Header + EOF marker.
        framebytes = "%s\n%s\n%s\x00" % (command, "".join(headerparts), body)
        
        return framebytes
    
    def __getattr__(self, name):
        """ Convenience way to return header values as if they're object attributes. 
        
        We replace '-' chars with '_' to make the headers python-friendly.  For example:
            
        frame.headers['message-id'] == frame.message_id
        
        >>> f = StompFrame(cmd='MESSAGE', headers={'message-id': 'id-here', 'other_header': 'value'}, body='')
        >>> f.message_id
        'id-here'
        >>> f.other_header
        'value'
        """
        if name.startswith('_'):
            raise AttributeError()
        
        try:
            return self.headers[name]
        except KeyError:
            # Try converting _ to -
            return self.headers.get(name.replace('_', '-'))
    
    def __eq__(self, other):
        """ Override equality checking to test for matching command, headers, and body. """
        return (isinstance(other, Frame) and 
                self.cmd == other.cmd and 
                self.headers == other.headers and 
                self.body == other.body)
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __str__(self):
        return self.pack()
    
    def __repr__(self):
        return '<%s cmd=%s len=%d>' % (self.__class__.__name__, self.command, len(self.body))
    
class HeaderValue(object):
    """
    An descriptor class that can be used when a calculated header value is needed.
    
    This class is a descriptor, implementing  __get__ to return the calculated value.
    While according to  U{http://docs.codehaus.org/display/STOMP/Character+Encoding} there 
    seems to some general idea about having UTF-8 as the character encoding for headers;
    however the C{stomper} lib does not support this currently.
    
    For example, to use this class to generate the content-length header:
    
        >>> body = 'asdf'
        >>> headers = {}
        >>> headers['content-length'] = HeaderValue(calculator=lambda: len(body))
        >>> str(headers['content-length'])
        '4' 
        
    @ivar calc: The calculator function.
    @type calc: C{callable}
    """
    def __init__(self, calculator):
        """
        @param calculator: The calculator callable that will yield the desired value.
        @type calculator: C{callable}
        """
        if not callable(calculator):
            raise ValueError("Non-callable param: %s" % calculator)
        self.calc = calculator
    
    def __get__(self, obj, objtype):
        return self.calc()
    
    def __str__(self):
        return str(self.calc())
    
    def __set__(self, obj, value):
        self.calc = value
        
    def __repr__(self):
        return '<%s calculator=%s>' % (self.__class__.__name__, self.calc)


## --------------------------------------------------------------------------------------
## 
## Convenience Frame subclasses for CLIENT communication.
##
## --------------------------------------------------------------------------------------

class ConnectFrame(Frame):
    """ A CONNECT client frame. """
    
    def __init__(self, login=None, passcode=None, extra_headers=None):
        super(ConnectFrame, self).__init__('CONNECT', headers=extra_headers)
        if login:
            self.headers['login'] = login
        if passcode:
            self.headers['passcode'] = passcode

class DisconnectFrame(Frame):
    """ A DISCONNECT client frame. """
    
    def __init__(self, extra_headers=None):
        super(DisconnectFrame, self).__init__('DISCONNECT', headers=extra_headers)
        
class SendFrame(Frame):
    """ A SEND client frame. """
    
    def __init__(self, destination, body=None, transaction=None, extra_headers=None):
        """
        @param destination: The destination for message.
        @type destination: C{str}
        
        @param body: The message body bytes.
        @type body: C{str} 
        
        @param transaction: (optional) transaction identifier.
        @type transaction: C{str}
        """
        super(SendFrame, self).__init__('SEND', headers=extra_headers, body=body)
        self.headers['content-length'] = HeaderValue(calculator=lambda: len(self.body))
        self.headers['destination'] = destination
        if transaction:
            self.headers['transaction'] = transaction

class SubscribeFrame(Frame):
    """ A SUBSCRIBE client frame. """
    
    def __init__(self, destination, ack=None, id=None, selector=None, extra_headers=None):
        """
        @param destination: The destination being subscribed to.
        @type destination: C{str}
        
        @param ack: Specific ack setting (if None, will not be added to headers)
        @type ack: C{str}
        
        @param id: An ID which can be referenced by UNSUBSCRIBE command later.
        @type id: C{str}
        
        @param selector: A SQL-92 selector for content-based routing (if supported by broker). 
        @type selector: C{str}
        """
        super(SubscribeFrame, self).__init__('SUBSCRIBE', headers=extra_headers)
        self.headers['destination'] = destination
        if ack is not None:
            self.headers['ack'] = ack
        if id is not None:
            self.headers['id'] = id
        if selector is not None:
            self.headers['selector'] = selector

class UnsubscribeFrame(Frame):
    """ An UNSUBSCRIBE client frame. """
    
    def __init__(self, destination=None, id=None, extra_headers=None):
        """
        @param destination: The destination being unsubscribed from.
        @type destination: C{str}
        
        @param id: An ID used in SUBSCRIBE command (can be used instead of desination).
        @type id: C{str}
        
        @raise ValueError: If neither destination nor id are specified.
        """
        super(UnsubscribeFrame, self).__init__('UNSUBSCRIBE', headers=extra_headers)
        if not destination and not id:
            raise ValueError("Must specify destination or id for unsubscribe request.")
        
        if destination:
            self.headers['destination'] = destination
        else: # implies that id was set
            self.headers['id'] = id
            
class BeginFrame(Frame):
    """ A BEGIN client frame. """
    
    def __init__(self, transaction, extra_headers=None):
        """
        @param transaction: The transaction identifier.
        @type transaction: C{str}
        """
        super(BeginFrame, self).__init__('BEGIN', headers=extra_headers)
        self.headers['transaction'] = transaction

class CommitFrame(Frame):
    """ A COMMIT client frame. """
    
    def __init__(self, transaction, extra_headers=None):
        """
        @param transaction: The transaction identifier.
        @type transaction: C{str}
        """
        super(CommitFrame, self).__init__('COMMIT', headers=extra_headers)
        self.headers['transaction'] = transaction

class AbortFrame(Frame):
    """ An ABORT client frame. """
    
    def __init__(self, transaction, extra_headers=None):
        """
        @param transaction: The transaction identifier.
        @type transaction: C{str}
        """
        super(AbortFrame, self).__init__('ABORT', headers=extra_headers)
        self.headers['transaction'] = transaction
        
class AckFrame(Frame):
    """ An ACK client frame. """
    
    def __init__(self, message_id, transaction=None, extra_headers=None):
        """
        @param message_id: The message ID being acknowledged.
        @type message_id: C{str}
        
        @param transaction: The transaction identifier.
        @type transaction: C{str}
        """
        super(AckFrame, self).__init__('ACK', headers=extra_headers)
        self.headers['message-id'] = message_id
        if transaction:
            self.headers['transaction'] = transaction

# ---------------------------------------------------------------------------------
# Server Frames
# ---------------------------------------------------------------------------------

class ConnectedFrame(Frame):
    """ A CONNECTED server frame (response to CONNECT).
    
    @ivar session: The (throw-away) session ID to include in response.
    @type session: C{str} 
    """
    def __init__(self, session, extra_headers=None):
        """
        @param session: The (throw-away) session ID to include in response.
        @type session: C{str}
        """
        super(ConnectedFrame,self).__init__('CONNECTED', headers=extra_headers)
        self.headers['session'] = session

class MessageFrame(Frame):
    """ A MESSAGE server frame. """
    
    def __init__(self, destination, body=None, message_id=None, extra_headers=None):
        """
        @param body: The message body bytes.
        @type body: C{str} 
        """
        super(MessageFrame, self).__init__('MESSAGE', headers=extra_headers, body=body)
        if message_id is None:
            message_id = uuid.uuid4()
        self.headers['message-id'] = message_id
        self.headers['destination'] = destination
        self.headers['content-length'] = HeaderValue(calculator=lambda: len(self.body))
        
# TODO: Figure out what we need from ErrorFrame (exception wrapping?)
class ErrorFrame(Frame):
    """ An ERROR server frame. """
    
    def __init__(self, message, body=None, extra_headers=None):
        """
        @param body: The message body bytes.
        @type body: C{str} 
        """
        super(ErrorFrame, self).__init__('ERROR', headers=extra_headers, body=body)
        self.headers['message'] = message
        self.headers['content-length'] = HeaderValue(calculator=lambda: len(self.body))
    
    def __repr__(self):
        return '<%s message=%r>' % (self.__class__.__name__, self.headers['message']) 
    
class ReceiptFrame(Frame):
    """ A RECEIPT server frame. """
    
    def __init__(self, receipt, extra_headers=None):
        """
        @param receipt: The receipt message ID.
        @type receipt: C{str}
        """
        super(ReceiptFrame, self).__init__('RECEIPT', headers=extra_headers)
        self.headers['receipt-id'] = receipt