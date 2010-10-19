"""
Classes to support reading and writing STOMP frames.

This is a mixture of code from the stomper project and the stompy project codebases.
"""
import logging
import re

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


## --------------------------------------------------------------------------------------
## 
## Convenience Frame subclasses for CLIENT communication.
##
## --------------------------------------------------------------------------------------

class ConnectFrame(Frame):
    """ A CONNECT client frame. """
    
    def __init__(self, login=None, passcode=None):
        super(ConnectFrame, self).__init__('CONNECT')
        if login:
            self.headers['login'] = login
        if passcode:
            self.headers['passcode'] = passcode

class DisconnectFrame(Frame):
    """ A DISCONNECT client frame. """
    
    def __init__(self):
        super(DisconnectFrame, self).__init__('DISCONNECT')
        
class SendFrame(Frame):
    """ A SEND client frame. """
    
    def __init__(self, destination, body=None, transaction=None):
        """
        @param destination: The destination for message.
        @type destionaton: C{str}
        
        @param body: The message body bytes.
        @type body: C{str} 
        
        @param transaction: (optional) transaction identifier.
        @type transaction: C{str}
        """
        super(SendFrame, self).__init__('SEND', body=body)
        self.headers['content-length'] = HeaderValue(calculator=lambda: len(self.body))
        self.headers['destination'] = destination
        if transaction:
            self.headers['transaction'] = transaction

class SubscribeFrame(Frame):
    """ A SUBSCRIBE client frame. """
    
    def __init__(self, destination, ack=None, id=None, selector=None):
        """
        @param destination: The destination being subscribed to.
        @type destionaton: C{str}
        
        @param ack: Specific ack setting (if None, will not be added to headers)
        @type ack: C{str}
        
        @param id: An ID which can be referenced by UNSUBSCRIBE command later.
        @type id: C{str}
        
        @param selector: A SQL-92 selector for content-based routing (if supported by broker). 
        @type selector: C{str}
        """
        super(SubscribeFrame, self).__init__('SUBSCRIBE')
        self.headers['destination'] = destination
        if ack is not None:
            self.headers['ack'] = ack
        if id is not None:
            self.headers['id'] = id
        if selector is not None:
            self.headers['selector'] = selector

class UnsubscribeFrame(Frame):
    """ An UNSUBSCRIBE client frame. """
    
    def __init__(self, destination=None, id=None):
        """
        @param destination: The destination being unsubscribed from.
        @type destionaton: C{str}
        
        @param id: An ID used in SUBSCRIBE command (can be used instead of desination).
        @type id: C{str}
        
        @raise ValueError: If neither destination nor id are specified.
        """
        super(UnsubscribeFrame, self).__init__('UNSUBSCRIBE')
        if not destination and not id:
            raise ValueError("Must specify destination or id for unsubscribe request.")
        
        if destination:
            self.headers['destination'] = destination
        else: # implies that id was set
            self.headers['id'] = id
            
class BeginFrame(Frame):
    """ A BEGIN client frame. """
    
    def __init__(self, transaction):
        """
        @param transaction: The transaction identifier.
        @type transaction: C{str}
        """
        super(BeginFrame, self).__init__('BEGIN', headers={'transaction': transaction})

class CommitFrame(Frame):
    """ A COMMIT client frame. """
    
    def __init__(self, transaction):
        """
        @param transaction: The transaction identifier.
        @type transaction: C{str}
        """
        super(CommitFrame, self).__init__('COMMIT', headers={'transaction': transaction})

class AbortFrame(Frame):
    """ An ABORT client frame. """
    
    def __init__(self, transaction):
        """
        @param transaction: The transaction identifier.
        @type transaction: C{str}
        """
        super(AbortFrame, self).__init__('ABORT', headers={'transaction': transaction})
        
class AckFrame(Frame):
    """ An ACK client frame. """
    
    def __init__(self, message_id, transaction=None):
        """
        @param message_id: The message ID being acknowledged.
        @type message_id: C{str}
        
        @param transaction: The transaction identifier.
        @type transaction: C{str}
        """
        super(AckFrame, self).__init__('ACK')
        self.headers['message-id'] = message_id
        if transaction:

            self.headers['transaction'] = transaction


 
class FrameBuffer(object):
    """
    A customized version of the StompBuffer class from Stomper project that returns frame objects
    and supports iteration.
    
    This version of the parser also assumes that stomp messages with no content-lengh
    end in a simple \\x00 char, not \\x00\\n as is assumed by
    C{stomper.stompbuffer.StompBuffer}. Additionally, this class differs from Stomper version 
    by conforming to PEP-8 coding style.
    
    This class can be used to smooth over a transport that may provide partial frames (or
    may provide multiple frames in one data buffer).
    
    This class does not extend C{stomper.stompbuffer.StompBuffer}, since essentially it 
    overrides every method in order to conform to spec in frame parsing. For example, the 
    original doesn't work with frames generated by stomp.py project.
    
    @ivar buffer: The internal byte buffer.
    @type buffer: C{str}
    
    @ivar debug: Log extra parsing debug (logs will be DEBUG level). 
    @type debug: C{bool} 
    """
        
    # regexp to check that the buffer starts with a command.
    command_re = re.compile('^(.+?)\n')
    
    # regexp to remove everything up to and including the first
    # instance of '\x00' (used in resynching the buffer).
    sync_re = re.compile('^.*?\x00')
    
    # regexp to determine the content length. The buffer should always start
    # with a command followed by the headers, so the content-length header will
    # always be preceded by a newline.  It may not always proceeded by a newline, though!
    content_length_re = re.compile('\ncontent-length\s*:\s*(\d+)\s*(\n|$)')
    
    def __init__(self):
        self.buffer = ''
        self.debug = False
        self.log = logging.getLogger('%s.%s' % (self.__module__, self.__class__.__name__))
        
    def buffer_len(self):
        """
        @return: Number of bytes in the internal buffer.
        @rtype: C{int}
        """
        return len(self.buffer)
    
    def buffer_empty(self):
        """
        @return: C{True} if buffer is empty, C{False} otherwise. 
        @rtype: C{bool}
        """
        return not bool(self.buffer)
        
    def append(self, data):
        """
        Appends bytes to the internal buffer (may or may not contain full stomp frames).
        
        @param data: The bytes to append.
        @type data: C{str}
        """
        self.buffer += data

    def extract_message(self):
        """
        Pulls one complete frame off the buffer and returns it. 
        
        If there is no complete message in the buffer, returns None.

        Note that the buffer can contain more than once message. You
        should therefore call this method in a loop (or use iterator
        functionality exposed by class) until None returned.
        
        @return: The next complete frame in the buffer.
        @rtype: L{stomp.frame.Frame}
        """
        (mbytes, hbytes) = self._find_message_bytes(self.buffer)
        if not mbytes:
            return None
        
        msgdata = self.buffer[:mbytes]
        self.buffer = self.buffer[mbytes:]
        hdata = msgdata[:hbytes]
        # Strip off any leading whitespace from headers; this is necessary, because
        # we do not (any longer) expect a trailing \n after the \x00 byte (which means
        # it will become a leading \n to the next frame).
        hdata = hdata.lstrip() 
        elems = hdata.split('\n')
        cmd = elems.pop(0)
        headers = {}
        
        for e in elems:
            try:
                (k,v) = e.split(':', 1) # header values may contain ':' so specify maxsplit
            except ValueError:
                continue
            headers[k.strip()] = v.strip()

        # hbytes points to the start of the '\n\n' at the end of the header,
        # so 2 bytes beyond this is the start of the body. The body EXCLUDES
        # the final byte, which is  '\x00'.
        body = msgdata[hbytes + 2:-1]
        return Frame(cmd, headers=headers, body=body)


    def _find_message_bytes(self, data):
        """
        Examines passed-in data and returns a tuple of message and header lengths.
        
        Return data is a C{tuple} in the form (message_length, header_length) where 
        message_length is the length in bytes of the first complete message, if it 
        contains at least one message, or 0 if it contains no message.
        
        If message_length is non-zero, header_length contains the length in
        bytes of the header. If message_length is zero, header_length should
        be ignored.
        
        @return: A tuple in the form (message_length, header_length)
        @rtype: C{tuple}
        """

        # Sanity check. See the docstring for the method to see what it
        # does an why we need it.
        self.sync_buffer()
        
        # If the string '\n\n' does not exist, we don't even have the complete
        # header yet and we MUST exit.
        try:
            i = data.index('\n\n')
        except ValueError:
            if self.debug:
                self.log.debug("No complete frames in buffer.")
            return (0, 0)
        # If the string '\n\n' exists, then we have the entire header and can
        # check for the content-length header. If it exists, we can check
        # the length of the buffer for the number of bytes, else we check for
        # the existence of a null byte.

        # Pull out the header before we perform the regexp search. This
        # prevents us from matching (possibly malicious) strings in the
        # body.
        _hdr = self.buffer[:i]
        match = self.content_length_re.search(_hdr)
        if match:
            # There was a content-length header, so read out the value.
            content_length = int(match.groups()[0])
            
            if self.debug:
                self.log.debug("Message contains a content-length header; reading %d bytes" % content_length)
            
            # This is the content length of the body up until the null
            # byte, not the entire message. Note that this INCLUDES the 2
            # '\n\n' bytes inserted by the STOMP encoder after the body
            # (see the calculation of content_length in
            # StompEngine.callRemote()), so we only need to add 2 final bytes
            # for the footer.
            #
            #The message looks like:
            #
            #   <header>\n\n<body>\n\n\x00
            #           ^         ^^^^
            #          (i)         included in content_length!
            #
            # We have the location of the end of the header (i), so we
            # need to ensure that the message contains at least:
            #
            #     i + len ( '\n\n' ) + content_length + len ( '\x00' )
            #
            # Note that i is also the count of bytes in the header, because
            # of the fact that str.index() returns a 0-indexed value.
            req_len = i + len('\n\n') + content_length + len('\x00')
            
            if self.debug:
                self.log.debug("We have [%s] bytes and need [%s] bytes" % (len(data), req_len)) 
                
            if len(data) < req_len:
                # We don't have enough bytes in the buffer.
                if self.debug:
                    self.log.debug("Not enough bytes in buffer to construct a frame.")
                return (0, 0)
            else:
                # We have enough bytes in the buffer
                return (req_len, i)
        else:
            if self.debug:
                self.log.debug("No content-length header present; reading until first null byte.")
            # There was no content-length header, so just look for the
            # message terminator ('\x00' ).
            try:
                j = data.index('\x00')
            except ValueError:
                # We don't have enough bytes in the buffer.
                if self.debug:
                    self.log.debug("Could not find NULL termination byte.")
                return (0, 0)
            
            # j points to the 0-indexed location of the null byte. However,
            # we need to add 1 (to turn it into a byte count)
            return (j + 1, i)


    def sync_buffer(self):
        """
        Method to detect and correct corruption in the buffer.
        
        Corruption in the buffer is defined as the following conditions
        both being true:
        
            1. The buffer contains at least one newline;
            2. The text until the first newline is not a STOMP command.
        
        In this case, we heuristically try to flush bits of the buffer until
        one of the following conditions becomes true:
        
            1. the buffer starts with a STOMP command;
            2. the buffer does not contain a newline.
            3. the buffer is empty;

        If the buffer is deemed corrupt, the first step is to flush the buffer
        up to and including the first occurrence of the string '\x00', which
        is likely to be a frame boundary.

        Note that this is not guaranteed to be a frame boundary, as a binary
        payload could contain the string '\x00'. That condition would get
        handled on the next loop iteration.
        
        If the string '\x00' does not occur, the entire buffer is cleared.
        An earlier version progressively removed strings until the next newline,
        but this gets complicated because the body could contain strings that
        look like STOMP commands.
        
        Note that we do not check "partial" strings to see if they *could*
        match a command; that would be too resource-intensive. In other words,
        a buffer containing the string 'BUNK' with no newline is clearly
        corrupt, but we sit and wait until the buffer contains a newline before
        attempting to see if it's a STOMP command.
        """
        while True:
            if not self.buffer:
                # Buffer is empty; no need to do anything.
                break
            m = self.command_re.match(self.buffer)
            if m is None:
                # Buffer doesn't even contain a single newline, so we can't
                # determine whether it's corrupt or not. Assume it's OK.
                break
            cmd = m.groups()[0]
            if cmd in VALID_COMMANDS:
                # Good: the buffer starts with a command.
                break
            else:
                # Bad: the buffer starts with bunk, so strip it out. We first
                # try to strip to the first occurrence of '\x00', which
                # is likely to be a frame boundary, but if this fails, we
                # strip until the first newline.
                (self.buffer, nsubs) = self.sync_re.subn('', self.buffer)

                if nsubs:
                    # Good: we managed to strip something out, so restart the
                    # loop to see if things look better.
                    continue
                else:
                    # Bad: we failed to strip anything out, so kill the
                    # entire buffer. Since this resets the buffer to a
                    # known good state, we can break out of the loop.
                    self.buffer = ''
                    break

    def __iter__(self):
        """
        Returns an iterator object.
        """
        return self
    
    def next(self):
        """
        Return the next STOMP message in the buffer (supporting iteration).
        
        @rtype: L{stomp.frame.Frame}
        """
        msg = self.extract_message()
        if not msg:
            raise StopIteration()
        return msg
