"""
Support for basic, one-way (publish-only) communication with stomp server.
"""
import abc
import logging

from stompclient import frame
from stompclient.connection import ThreadLocalConnectionPool, ConnectionError, NotConnectedError

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

class BaseClient(object):
    """
    A STOMP client base class with shared functionality.
    
    @ivar connection_pool: Object responsible for issuing STOMP connections.
    @type connection_pool: L{stomp.core.ConnectionPool}
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, host, port=61613, socket_timeout=None, connection_pool=None):
        self.log = logging.getLogger('%s.%s' % (self.__class__.__module__, self.__class__.__name__))
        self.connection_pool = connection_pool if connection_pool else ThreadLocalConnectionPool()
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
            disconnect = frame.DisconnectFrame()
            result = self.send_frame(disconnect)
            self.connection.disconnect()
            return result
        except NotConnectedError:
            pass
        
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

    def subscribe(self, destination):
        """
        Subscribe to a given destination.
        
        @param destination: The destination "path" to subscribe to.
        @type destination: C{str}
        """
        raise NotImplementedError("%s client does not implement SUBSCRIBE" % (self.__class__,))
    
    @abc.abstractmethod
    def unsubscribe(self, destination=None):
        """
        Unsubscribe from a given destination.
        
        @param destination: The destination "path" to unsubscribe from.
        @type destination: C{str}
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
    
    @abc.abstractmethod
    def send_frame(self, frame):
        """
        Send a frame to the STOMP server and return result (if applicable).
        
        @param frame: The frame instance to send.
        @type frame: L{stomp.frame.Frame}
        
        @return: The "response" frame from stomp server (if applicable).
        @rtype: L{stompclient.frame.Frame}
        """

class PublishClient(BaseClient):
    """
    A basic STOMP client that provides a publish-only interaction with server.
    
    This client does not support subscribing to destinations, the 'receipt' header 
    (which expects acknowledgement of message from server), and does not process
    CONNECTED frames to keep track of session id (which is not actually used by 
    the protocol anyway).
    
    This client is ideally suited for use in a multi-threaded server environment, 
    since it can be used with a ThreadLocalConnection pool (since there is no need for a message-
    receiving thread).
    
    @ivar connection_pool: Object responsible for issuing STOMP connections (defaults to using
                            L{stompclient.connection.ThreadLocalConnectionPool} for this client impl).
    @type connection_pool: L{stompclient.connection.ConnectionPool}
    """

    def __init__(self, host, port=61613, socket_timeout=None, connection_pool=None):
        connection_pool = connection_pool if connection_pool else ThreadLocalConnectionPool()
        super(PublishClient, self).__init__(host=host,
                                            port=port,
                                            socket_timeout=socket_timeout,
                                            connection_pool=connection_pool)

    def subscribe(self, destination):
        """
        Subscribe to a given destination.
        
        @param destination: The destination "path" to subscribe to.
        @type destination: C{str}
        """
        raise NotImplementedError("%s client does not implement SUBSCRIBE" % (self.__class__,))

    def unsubscribe(self, destination):
        """
        Unsubscribe from a given destination.
        
        @param destination: The destination to subscribe to.
        @type destination: C{str}
        """
        raise NotImplementedError("%s client does not implement UNSUBSCRIBE" % (self.__class__,))

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
            self.connection.send(frame)
        except ConnectionError:
            self.connection.disconnect()
            self.connection.send(str(frame))        
    
