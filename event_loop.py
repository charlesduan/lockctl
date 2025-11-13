"""
Manages an event loop.
"""


import selectors
import time
import heapq
import os

sel = selectors.DefaultSelector()
queue = []
fd_readers = {}


class TimedEvent:
    """
    A data structure of information relating to a timed event.
    """
    def __init__(self, callback, delay):
        self.callback = callback
        self.expiry = delay + time.monotonic()

        global queue
        queue.append(self)

    def upon_expiry(self):
        global queue
        self.callback(self)


class FDReader:
    """
    A data structure of information relating to a file descriptor.
    """
    def __init__(self, obj, callback, timeout = None):

        if type(obj) == int:
            self.fd = obj
            self.obj = None
        else:
            self.fd = obj.fileno()
            self.obj = obj

        self.callback = callback
        self.timeout = timeout
        self.expiry = None
        self.update_expiry()

        # Register the object
        global fd_readers, sel, queue
        fd_readers[self.fd] = self
        sel.register(self.fd, selectors.EVENT_READ, self)
        if self.expiry != None:
            queue.append(self)


    def update_expiry(self):
        if self.timeout == None:
            return
        else:
            self.expiry = time.monotonic() + self.timeout

    def invoke_read(self):
        self.callback(self)
        self.update_expiry()

    def terminate(self):
        sel.unregister(self.fd)
        del(fd_readers[self.fd])
        if self.obj:
            self.obj.close()
        else:
            os.close(self.fd)

    def upon_expiry(self):
        global queue
        self.terminate()



def read_to_delimiter(callback, delimiter = "\n"):
    """
    Constructs an event callback function that reads from a filehandle,
    separating text at the given delimiter, and then calls the given callback
    function with the delimited text.
    """
    buffer = ""
    def inner(fd_reader):
        nonlocal buffer
        fh = fd_reader.fd

        # Read the text and append it to the buffer
        text = os.read(fh, 1).decode("utf-8")
        buffer += text

        # Read off any delimited texts, passing them to the callback and
        # updating the buffer
        while (idx := buffer.find(delimiter)) >= 0:
            callback(buffer[:idx])
            buffer = buffer[(idx + len(delimiter)):]

        # Close the filehandle when done
        if len(text) == 0:
            fd_reader.terminate()

    return inner

def run_timed_events():
    queue.sort(key = lambda x: x.expiry, reverse = True)
    cur = time.monotonic()
    while len(queue) > 0 and queue[-1].expiry <= cur:
        queue.pop().upon_expiry()
        cur = time.monotonic()
    if len(queue) > 0:
        return queue[-1].expiry - cur
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

    # Run timed events
    timeout = run_timed_events()
    if len(queue) == 0 and len(fd_readers) == 0:
        raise StopIteration
    events = sel.select(timeout)
    for key, mask in events:
        key.data.invoke_read()

def run_loop():
    """
    Executes the event loop until all events are complete.
    """
    try:
        while True:
            run_iteration()
    except StopIteration:
        pass



