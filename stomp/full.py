"""
Clients that support both sending and receiving messages (produce & consume).
"""
import threading
from Queue import Queue

from stomp import frame
from stomp.basic import SimplexClient
from stomp.util import FrameBuffer
from stomp.exception import ConnectionError

class BlockingDuplexClient(SimplexClient):
    """
    A STOMP client that supports both producer and consumer roles using threading.
    
    @ivar message_queue: A queue of all the MESSAGE frames from the server to a
                            destination that has been subscribed to.
    @type message_queue: C{Queue.Queue}
    
    @type receipt_queue: A queue of RECEPT frames from the server (these are replies to requests 
                            that included the 'receipt' header).
    @type receipt_queue: C{Queue.Queue} 
    
    @ivar subscribed_destinations: A C{set} of subscribed destinations. 
    """
    debug = False
    
    def __init__(self, host, port=61613, socket_timeout=None, connection_pool=None):
        super(BlockingDuplexClient, self).__init__(host, port=port, socket_timeout=socket_timeout, connection_pool=connection_pool)
        self.message_queue = Queue()
        self.receipt_queue = Queue()
        self.error_queue = Queue()
        self.buffer = FrameBuffer()
        self.shutdown_event = threading.Event()
        self.listening_event = threading.Event()
        self.subscribed_destinations = set()
    
    def listener_forever(self):
        """
        Blocking method that reads from connection socket.
        
        This would typically be started within its own thread, since it will
        block until error.
        """
        self.listening_event.set()
        self.shutdown_event.clear()
        try:
            while not self.shutdown_event.is_set():
                data = self.connection.read(8192)
                if not data:
                    break
                if self.debug:
                    self.log.debug("RECV: %r" % data)
                self.buffer.append(data)
                
                for frame in self.buffer:
                    self.log.debug("Processing frame: %s" % frame)
                    if frame.command == 'RECEIPT':
                        self.receipt_queue.put(frame)
                    elif frame.command == 'MESSAGE':
                        if frame.destination in self.subscribed_destinations:
                            self.message_queue.put(frame)
                        else:
                            if self.debug:
                                self.log.debug("Ignoring frame for unsubscribed destination: %s" % frame)
                    elif frame.command == 'ERROR':
                        self.error_queue.put(frame)
                    else:
                        self.log.info("Ignoring frame from server: %s" % frame)
                        
        except Exception, e:
            self.log.exception("Error receiving data; aborting listening loop.")
            raise
        finally:
            self.listening_event.clear()
    
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
        subscribe = frame.SubscribeFrame(destination)
        res = self.send_frame(subscribe)
        self.subscribed_destinations.add(destination)
        return res
        
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
        res = self.send_frame(unsubscribe)
        self.subscribed_destinations.pop(destination)
        return res

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
        wait_for_reply = ('receipt' in frame.headers) 
        if wait_for_reply and not self.listening_event.is_set():
            raise Exception("Receipt requested, but cannot deliver; listening loop is not running.")
        
        try:
            self.connection.send(str(frame))
        except ConnectionError:
            self.connection.disconnect()
            self.connection.send(str(frame))
            
        if wait_for_reply:
            return self.receipt_queue.get()
    
        
    
