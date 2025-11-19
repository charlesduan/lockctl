"""
Event Manager, for dispatching events in an event-driven system.
"""

import selectors
import time
import os
import socket
from collections import deque

queue = deque()
time_queue = {}
handlers = set()

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

class MainHandler(Handler):
    def __init__(self):
        self.selector = selectors.DefaultSelector()

    def handle_run(self, payload):
        self.handle_timed(payload)
        self.handle_select(payload)
        queue.append((self, 'run', None))

    def handle_select(self, payload):
        if queue:
            timeout = 0
        else:
            timeout = self.queue_min()
        events = self.select(timeout)
        for key, mask in events:
            # Find the relevant callback
            queue.append((key.data, 'read', key.fileobj))

    def handle_timed(self, payload):
        now = time.monotonic()
        now_events = []
        future_events = []
        for timed_event in time_queue:
            pass


def send(obj: Handler, message, payload = None):
    """Send a message to the given Handler object."""
    queue.append((obj, message, payload))

def schedule(obj: Handler, delay, message, payload = None):
    time_queue.append(
            (time.monotonic() + delay, obj, message, payload)

def run():
    main_handler = MainHandler()
    queue.append((main_handler, 'run', None))
    try:
        while queue:
            obj, msg, payload = queue.popleft()
            try:
                obj.handle(msg, payload)
            except Exception as e:
                print(repr(e))
    finally:
        pass # Should clean up all remaining handlers

