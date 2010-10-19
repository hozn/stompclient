"""
Stomp classes to support frames.

This is a mixture of code from the stomper project and the stompy project codebases.
"""

# The version of the protocol we implement.
STOMP_VERSION = '1.0'

# STOMP Spec v1.0 valid commands:
VALID_COMMANDS = [
    'ABORT', 'ACK', 'BEGIN', 'COMMIT', 
    'CONNECT', 'CONNECTED', 'DISCONNECT', 'MESSAGE',
    'SEND', 'SUBSCRIBE', 'UNSUBSCRIBE',
    'RECEIPT', 'ERROR',    
]

class FrameError(Exception):
    """
    Raise for problem with frame generation or parsing.
    """

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
                raise FrameError("The cmd '%s' is not valid! It must be one of '%s' (STOMP v%s)." % (
                    cmd, VALID_COMMANDS, STOMP_VERSION)
                )
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
        return '<%s cmd=%s len=%d>' % (self.__class__.__name__, self.cmd, len(self.body))
    
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

    