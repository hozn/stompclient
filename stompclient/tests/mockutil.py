"""
Utilities for working with mock objects.
"""
from mock import Mock

from stompclient.connection import Connection

class MockingConnectionPool(object):
    """
    A connection pool that returns a single Mock connection object instead of real ones.
    """
    
    def __init__(self):
        self.connection = Mock(spec=Connection)

    def get_connection(self, host, port, socket_timeout=None):
        """
        Return a specific connection for the specified host and port.
        """
        return self.connection

    def get_all_connections(self):
        "Return a list of all connection objects the manager knows about"
        return [self.connection]
