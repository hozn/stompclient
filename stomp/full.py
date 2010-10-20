"""
Clients that support both sending and receiving messages (produce & consume).
"""
import threading
from Queue import Queue

from stomp import frame
from stomp.basic import SimplexClient
from stomp.exception import ConnectionError

class BlockingDuplexClient(SimplexClient):
    """
    A STOMP client that supports both producer and consumer roles using threading.
    """
    
    def __init__(self, host, port=61613, socket_timeout=None, connection_pool=None):
        super(BlockingDuplexClient, self).__init__(host, port=port, socket_timeout=socket_timeout, connection_pool=connection_pool)
        self.message_queue = Queue()
        self.reply_queue = Queue()
        self.shutdown_event = threading.Event()
    
    def listener_forever(self):
        """
        Blocking method that reads from connection socket.
        
        This would typically be started within its own thread.
        """
#        self.shutdown_event.clear()
#        try:
#            while not self.shutdown_event.is_set():
#                data = self.request.recv(8192)
#                if not data:
#                    break
#                if self.debug:
#                    self.log.debug("RECV: %r" % data)
#                self.buffer.append(data)
#                
#                for frame in self.buffer:
#                    self.log.debug("Processing frame: %s" % frame)
#                    self.engine.process_frame(frame)
#        except Exception, e:
#            self.log.error("Error receiving data (unbinding): %s" % e)
#            self.engine.unbind()
#            raise
            
    
    def disconnect(self, conf=None):
        """Disconnect from the server."""
        try:
            for destination in self._subscribed_to.keys():
                self.unsubscribe({"destination": destination})
            self._send_command("DISCONNECT", conf)
        except self.NotConnectedError:
            pass
        self.connection.disconnect()
        # XXX: Signal shut down of blocking loop?
        
    def subscribe(self, destination):
        """
        Subscribe to a given destination.
        
        @param destination: The destination "path" to subscribe to.
        @type destination: C{str}
        """
        
        raise NotImplementedError("%s client does not implement SUBSCRIBE" % (self.__class__,))

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
        unsubscribe = frame.UnsubscribeFrame(destination=destination, id=id)
        return self.send_frame(unsubscribe)

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
            pass
            # XXX: We need to block and fetch a response
        
        try:
            self.connection.send(str(frame))
        except ConnectionError:
            self.connection.disconnect()
            self.connection.send(str(frame))
    
        
    
