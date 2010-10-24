"""
Clients that support both sending and receiving messages (produce & consume).
"""
import threading
from copy import copy
from Queue import Queue

from stompclient import frame
from stompclient.simplex import SimplexClient
from stompclient.util import FrameBuffer
from stompclient.connection import ConnectionError, NotConnectedError

__authors__ = ['"Hans Lellelid" <hans@xmpl.org>']
__copyright__ = "Copyright 2010 Hans Lellelid"
__license__ = """Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
 
  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

class QueueingDuplexClient(SimplexClient):
    """
    A STOMP client that supports both producer and consumer roles, depositing received
    frames onto thread-safe queues.
    
    This class can be used directly; however, it requires that the calling code
    pull frames from the queues and dispatch them.  More typically, this class can
    be used as a basis for a more convenient frame-dispatching client. 
    
    Because this class must be run in a multi-threaded context (thread for listening 
    loop), it IS NOT thread-safe.  Specifically is must be used with a non-threadsafe
    connecton pool, so that the same connection can be accessed from multipl threads.

    @ivar connected_queue: A queue to hold CONNECTED frames from the server.
    @type connected_queue: C{Queue.Queue}
    
    @ivar message_queue: A queue of all the MESSAGE frames from the server to a
                            destination that has been subscribed to.
    @type message_queue: C{Queue.Queue}
    
    @ivar receipt_queue: A queue of RECEPT frames from the server (these are replies 
                            to requests that included the 'receipt' header).
    @type receipt_queue: C{Queue.Queue} 
    
    @ivar error_queue: A queue of ERROR frames from the server.
    @type error_queue: C{Queue.Queue} 
    
    @ivar subscribed_destinations: A C{set} of subscribed destinations.
    @type subscribed_destinations: C{set} 
    """
    debug = False
    
    def __init__(self, host, port=61613, socket_timeout=None, connection_pool=None):
        super(QueueingDuplexClient, self).__init__(host, port=port, socket_timeout=socket_timeout, connection_pool=connection_pool)
        self.connected_queue = Queue()
        self.message_queue = Queue()
        self.receipt_queue = Queue()
        self.error_queue = Queue()
        self.buffer = FrameBuffer()
        self.shutdown_event = threading.Event()
        self.listening_event = threading.Event()
        self.subscribed_destinations = set()
        if isinstance(connection_pool, threading.local):
            raise Exception("Cannot use a thread-local pool for duplex clients.")
    
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
                    elif frame.command == 'CONNECTED':
                        self.connected_queue.put(frame)
                    else:
                        self.log.info("Ignoring frame from server: %s" % frame)
                        
        except Exception, e:
            self.log.exception("Error receiving data; aborting listening loop.")
            raise
        finally:
            self.listening_event.clear()
    
    def connect(self, login=None, passcode=None):
        """
        Get connection and send CONNECT frame to the STOMP server. 
        
        @return: The CONNECTED frame from the server.
        @rtype: L{stompclient.frame.Frame}
        """
        connect = frame.ConnectFrame(login, passcode)
        self.send_frame(connect)
        return self.connected_queue.get()
    
    def disconnect(self):
        """
        Disconnect from the server.
        """
        try:
            # Need a copy since unsubscribe() removes the destination from the set.
            subcpy = copy(self.subscribed_destinations)
            for destination in subcpy:
                self.unsubscribe(destination)
        except NotConnectedError:
            pass
        finally:
            self.shutdown_event.set()
        self.connection.disconnect()
        
        
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
        self.subscribed_destinations.remove(destination)
        return res

    def send_frame(self, frame):
        """
        Send a frame to the STOMP server.
        
        This implementation does support the 'receipt' header, blocking on the
        receipt queue until a receipt frame is received.
        
        @param frame: The frame instance to send.
        @type frame: L{stomp.frame.Frame}
        
        @raise NotImplementedError: If the frame includes a 'receipt' header, since this implementation
                does not support receiving data from the STOMP broker.
        """
        need_receipt = ('receipt' in frame.headers) 
        if need_receipt and not self.listening_event.is_set():
            raise Exception("Receipt requested, but cannot deliver; listening loop is not running.")
        
        try:
            self.connection.send(str(frame))
        except ConnectionError:
            self.connection.disconnect()
            self.connection.send(str(frame))
            
        if need_receipt:
            return self.receipt_queue.get()
    
        
    
