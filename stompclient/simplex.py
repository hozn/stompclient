"""
Support for basic, one-way (publish-only) communication with stomp server.
"""
import logging

from stompclient import frame
from stompclient.connection import ConnectionPool, ConnectionError 

__authors__ = ['"Hans Lellelid" <hans@xmpl.org>', 'Benjamin W. Smith (stompy)']
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

class SimplexClient(object):
    """
    A basic STOMP client that provides only the producer role (does not consume messages form server).
    
    The implication is that this client does not support subscribing to destinations or the 'receipt'
    header (which expects acknowledgement of message from server).
    
    This client may be used with a ThreadLocalConnection pool, since there is no need for a message-
    receiving thread.  (This means that it can be used in a context where a pool of connections
    needs to be maintained in a multi-threaded environment.)
    
    @ivar connection_pool: Object responsible for issuing STOMP connections.
    @type connection_pool: L{stomp.core.ConnectionPool}
    """

    def __init__(self, host, port=61613, socket_timeout=None, connection_pool=None):
        self.log = logging.getLogger('%s.%s' % (self.__class__.__module__, self.__class__.__name__))
        self.connection_pool = connection_pool if connection_pool else ConnectionPool()
        self.host = host
        self.port = port
        self.socket_timeout = socket_timeout
    
    @property
    def connection(self):
        """
        A connection object from the configured pool.
        @rtype: L{stompclient.connection.Connection} 
        """
        return self.connection_pool.get_connection(self.host, self.port, self.socket_timeout)
    
    def connect(self, login=None, passcode=None):
        """
        Get connection and send CONNECT frame to the STOMP server. 
        """
        connect = frame.ConnectFrame(login, passcode)
        return self.send_frame(connect)

    def disconnect(self, conf=None):
        """Disconnect from the server."""
        try:
            for destination in self._subscribed_to.keys():
                self.unsubscribe(destination)
            self._send_command("DISCONNECT", conf)
        except self.NotConnectedError:
            pass
        self.connection.disconnect()
        
    def send(self, destination, body=None, transaction=None):
        """
        Sends a message to STOMP server.
        
        @param destination: The destination "path" for message.
        @type destination: C{str}
        
        @param body: The body (bytes) of the message.
        @type body: C{str}
        
        @param transaction: (optional) The transaction ID associated with this ACK.
        @type transaction: C{str}
        """
        send = frame.SendFrame(destination, body, transaction)
        return self.send_frame(send)

    def subscribe(self, destination):
        """
        Subscribe to a given destination.
        
        @param destination: The destination "path" to subscribe to.
        @type destination: C{str}
        """
        raise NotImplementedError("%s client does not implement SUBSCRIBE" % (self.__class__,))

    def begin(self, transaction):
        """
        Begin transaction.
        
        @param transaction: The transaction ID.
        @type transaction: C{str}
        """
        begin = frame.BeginFrame(transaction)
        return self.send_frame(begin)

    def commit(self, transaction):
        """
        Commit transaction.

        @param transaction: The transaction ID.
        @type transaction: C{str}
        """
        commit = frame.CommitFrame(transaction)
        return self.send_frame(commit)

    def abort(self, transaction):
        """
        Abort (rollback) transaction.

        @param transaction: The transaction ID.
        @type transaction: C{str}
        """
        abort = frame.AbortFrame(transaction)
        return self.send_frame(abort)

    def unsubscribe(self, destination=None, id=None):
        """
        Unsubscribe from a given destination (or id).
        
        One of the 'destination' or 'id' parameters must be specified.
        
        @param destination: The destination to subscribe to.
        @type destination: C{str}
        
        @param id: The ID to unsubscribe from (may be used in place of destination).
        @type id: C{str}
        
        @raise ValueError: Underlying code will raise if neither destination nor id 
                            params are specified. 
        """
        raise NotImplementedError("%s client does not implement UNSUBSCRIBE" % (self.__class__,))
        
    def ack(self, message_id, transaction=None):
        """
        Acknowledge receipt of a message.
        
        @param transaction: (optional) The transaction ID associated with this ACK.
        @type transaction: C{str}
        """
        ack = frame.AckFrame(message_id, transaction)
        return self.send_frame(ack)

    def send_frame(self, frame):
        """
        Send a frame to the STOMP server.
        
        This implementation does not support the 'receipt' header; it can be overridden
        in subclasses to support reading responses from the server socket.
        
        @param frame: The frame instance to send.
        @type frame: L{stomp.frame.Frame}
        
        @raise NotImplementedError: If the frame includes a 'receipt' header, since this implementation
                does not support receiving data from the STOMP broker.
        """
        if 'receipt' in frame.headers:
            raise NotImplementedError('%s client implementation does not support message receipts.' % (self.__class__,))
        
        try:
            self.connection.send(str(frame))
        except ConnectionError:
            self.connection.disconnect()
            self.connection.send(str(frame))
    
        
    