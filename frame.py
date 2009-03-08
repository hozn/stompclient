#!/usr/bin/env python
#
#   Copyright 2008-2009 Benjamin Smith
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

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
    def __init__(self):
        """Initialize Frame object
        >>> frameobj = Frame()
        """
        self.command = ''
        self.headers = {}
        self.body    = ''

    def build_frame(self,args):
        """Build a frame based on arguments
        >>> frame = frameobj.build_frame(({'command':'CONNECT','headers':{}})
        """
        self.command = args['command']
        self.headers = args['headers']
        if 'body' in args:
            self.body = args['body']
        return self

    def as_string(self):
        """Make raw string from frame
        Suitable for passing over socket to STOMP server
        >>> sock.send(frame.as_string())
        """
        command = self.command
        headers = self.headers
        body    = self.body
        frame   = "%s\n" % command
        
        bytes_message = False
        if 'bytes_message' in headers:
            bytes_message = True
            del headers['bytes_message']
            headers['content-length'] = body.len()

        if headers:
            for k,v in headers.iteritems():
                frame += "%s:%s\n" %(k,v)

        frame += "\n%s\x00" % body
        return frame

    def parse(self, sock):
        """Parse data from socket
        Accepts socket object as argument
        >>> frameobj.parse(sock)
        """
        command = ''
        body    = ''
        headers = {}

        while True:
            sock.recv(1)
            command = self._getline(sock)
            break

        while True:
            line = self._getline(sock)
            if line == '':
                break
            (key,value) = line.split(':',1)
            headers[key] = value
            continue

        if 'content-length' in headers:
            sock.recvfrom_into(body, headers['content-length'])
            headers['bytes_message'] = True
        else:
            while True:
                byte = sock.recv(1)
                if not byte:
                    print "Error reading body!"
                    exit(1)
                if byte == "\000":
                    break
                body += byte

        frame = Frame()
        frame = frame.build_frame({'command':command,'headers':headers,'body':body})
        return frame

    def _getline(self, sock):
        """Get a single line from socket"""
        buffer = ''
        while not buffer.endswith('\n'):
            buffer += sock.recv(1)
        return buffer[:-1]

