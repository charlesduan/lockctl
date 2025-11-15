"""
Event Manager, for dispatching events in an event-driven system.
"""

import selectors
import time
import os
import socket
from collections import deque

queue = deque()

class Handler:
    """
    An object that can handle events. This class should be subclassed for event
    handlers.

    To handle events, define methods named "handle_{message}" that each take one
    argument, the message payload.
    """
    def handle(self, message, payload):
        method = getattr(self, f"handle_{message}")
        method(payload)

def send(obj: Handler, message, payload = None):
    """Send a message to the given Handler object."""
    queue.append((obj, message, payload))

def run():
    queue.append([ (MainHandler, 'run', None) ])
    try:
        while queue:
            obj, msg, payload = queue.popleft()
            try:
                obj.handle(msg, payload)
            except Exception as e:
                print(repr(e))
    finally:
        pass # Should clean up all remaining handlers

