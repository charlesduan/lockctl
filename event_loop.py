"""
Manages an event loop.
"""


import selectors
import time
import heapq

sel = selectors.DefaultSelector()
queue = []
fh_count = 0

def add_read_fd(fd, callback):
    """
    Adds a file descriptor to watch in this event loop. Upon data being
    available for reading from the file descriptor, the callback is executed.
    """
    sel.register(fd, selectors.EVENT_READ, callback)
    fh_count += 1

def add_timed_event(delay, callback):
    """
    Adds an event to occur after the given delay.
    """
    heapq.heappush(queue, (time.monotonic() + delay, callback))

def run_timed_events():
    """
    Executes all timed events that ought to have occurred by now. Returns the
    amount of delay until the next timed event.
    """
    cur = time.monotonic()
    while len(queue) > 0 and queue[0][0] <= cur:
        heapq.heappop(queue)[1]()
        cur = time.monotonic()
    if len(queue) > 0:
        return queue[0][0] - cur
    else:
        return None

def run_iteration():
    """
    Executes one iteration of the event loop. An iteration consists of the
    following steps:

    - Execute any timed events that ought to occur now.
    - If no events remain and there are no filehandles to listen to, raise
      StopIteration.
    - Wait on filehandles with a select call, up to the timeout for the next
      timed event.
    - Execute events for any filehandles with pending data.

    Note that, even if there are timed events ready to be run after the select
    call, those events are not executed until the next iteration.
    """
    timeout = run_timed_events()
    if len(queue) == 0 and fh_count == 0:
        raise StopIteration
    events = sel.select(timeout)
    for key, mask in events:
        key.data(key.fileobj, mask)

def run_loop():
    """
    Executes the event loop until all events are complete.
    """
    try:
        while True:
            run_iteration()
    except StopIteration:
        pass

