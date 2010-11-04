"""
Exception classes used by the stompclient library.
"""

import socket

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

class NotConnectedError(Exception):
    """No longer connected to the STOMP server."""

class ConnectionError(socket.error):
    """Couldn't connect to the STOMP server."""

class ConnectionTimeoutError(socket.timeout):
    """Timed-out while establishing connection to the STOMP server."""

class FrameError(Exception):
    """
    Raise for problem with frame generation or parsing.
    """
