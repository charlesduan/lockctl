"""
Event Manager, for dispatching events in an event-driven system.
"""

import selectors
import time
import os
import socket
from collections import deque
import math
from collections import namedtuple
import traceback

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

class FDHandler(Handler):
    """
    An event handler associated with a file descriptor. Only this type of
    handler can be added to wait on a file descriptor.
    """
    def __init__(self, fileobj, timeout = None):
        self.fileobj = fileobj
        self.timeout = timeout
        if type(fileobj) is int: self.fd = fileobj
        else: self.fd = fileobj.fileno()

    def _register(self, h):
        """
        Registers the MainHandler that is listening to this object. This method
        should not be called directly; it is invoked upon passing this object to
        a MainHandler's register_reader method.
        """
        self.main_handler = h

    def handle_timeout(self, payload):
        """
        Event handler if the timeout is reached. By default, this just calls
        terminate().
        """
        self.terminate()

    def terminate(self):
        """
        Terminates this event handler. It attempts to close self.fileobj, either
        by calling its close() method or by calling os.close(). It also
        instructs the MainHandler to unregister this filehandle.

        Subclasses may override this method, but they must call
        self.main_handler.unregister(self).
        """
        self.main_handler.unregister(self)
        try:
            if self.fileobj.has_attr("close"): self.fileobj.close()
            elif type(self.fileobj) is int:    os.close(self.fileobj)
        except:
            pass


class LineReader(FDHandler):
    """
    Event handler that reads a filehandle by line. A subclass of this should
    respond to the message "line" where the line text is the payload.
    """

    def __init__(self, fileobj, delimiter = "\n", encoding = "utf-8", timeout =
                 None):
        super().__init__(fileobj, timeout)
        self.delimiter = delimiter.encode(encoding)
        self.encoding = encoding
        self.buffer = bytearray()


    def handle_read(self, payload):
        buf = os.read(self.fd, 4096)
        if not buf:
            self.terminate()
            return

        self.buffer += buf
        while (idx := self.buffer.find(self.delimiter)) >= 0:
            self.handle_line(self.buffer[0:idx].decode(self.encoding))
            del self.buffer[0:(idx + len(self.delimiter))]


    def terminate(self):
        if self.buffer: self.handle_line(self.buffer.decode(self.encoding))
        super().terminate()



class SocketListener(FDHandler):
    """
    An event handler that listens on a socket.
    """

    def __init__(self, host, port, conn_handler):
        """
        Constructs the socket listener. The conn_handler should be a lambda
        function that takes an io object (a socket) and returns an FDHandler
        object that will handle reads from the socket.
        """
        s = socket.create_server((host, port))
        s.setblocking(False)
        super().__init__(s)
        self.conn_handler = conn_handler


    def handle_read(self, payload):
        """
        Accepts a connection from the socket, constructs a socket reader
        handler, and registers it for reading from the main handler.
        """
        conn, address = self.fileobj.accept()
        conn.setblocking(False)
        handler = self.conn_handler(conn)
        main_handler.register_reader(handler)


Message = namedtuple('Message', 'handler event payload')
ScheduledMessage = namedtuple('ScheduledMessage', 'time message')

class MainHandler(Handler):
    """
    The event handler that dispatches the timed and file descriptor events.
    There generally should be only one of these, stored as the main_handler
    variable of the module.
    """

    def __init__(self):
        self.selector = selectors.DefaultSelector()
        self.queue = []
        self.timed_queue = {}
        self.fd_handlers = set()


    def handle_run(self, payload = None):
        """
        Runs the two main functions of the event system: queuing timed events
        and reading filehandles. These are delegated to the "run_select" and
        "run_timed" methods respectively.

        Upon completion of these two tasks, this method generally adds itself
        back to the event queue so that further timers and filehandles can be
        processed. However, if there are no more possible events (because there
        are no file descriptors to be read and no remaining timed events), then
        this method does not add itself back to the queue, thereby terminating
        the event loop.

        """
        timeout = self.run_timed()
        self.run_select(timeout)

        if self.queue or self.timed_queue:
            self.send(self, 'run')



    def run_select(self, timeout):
        """
        Queries for readable filehandles, blocking only if there is nothing else
        to do. Upon finding any readable filehandles, dispatch a "read" event to
        the corresponding handler, with the given filehandle object as the
        payload.

        If there are no file descriptors to be read from and there is no
        timeout, returns without doing anything.
        """

        if timeout is None and not self.fd_handlers: return
        events = self.selector.select(timeout)
        for key, mask in events:
            # Find the relevant callback
            handler = key.data
            self.send(handler, 'read', key.fileobj)
            # If the handler has a timeout, update the timeout
            if handler.timeout is not None:
                self.schedule(handler, handler.timeout, "timeout")



    def run_timed(self):
        """
        Reviews the queue of timed events to see if any of them are ready for
        dispatching. If so, removes them from the timed queue and adds them to
        the main queue. The method returns an amount of time to wait for the
        next timed event, or zero if there are events on the queue.
        """
        now = time.monotonic()
        future_events = {}
        next_time = math.inf
        for key, scheduled_message in self.timed_queue.items():
            this_time = scheduled_message.time
            if next_time > this_time: next_time = this_time

            if this_time <= now:
                self.queue.append(scheduled_message.message)
            else:
                future_events[key] = scheduled_message

        self.timed_queue = future_events

        if self.queue:              return 0
        elif next_time == math.inf: return None
        else:                       return next_time - now


    def send(self, handler, message, payload = None):
        """
        Sends a message to the given Handler object, by adding the message to
        the processing queue.
        """
        if not isinstance(handler, Handler): raise TypeError()
        self.queue.append(Message(handler, message, payload))


    def register_reader(self, handler: FDHandler):
        """
        Registers a file descriptor reader. The event handler must respond to
        the "read" message, with the file object as the payload. If the handler
        has a timeout, then an event is scheduled to call the "timeout" message
        appropriately.
        """
        if not isinstance(handler, FDHandler): raise TypeError()
        self.fd_handlers.add(handler)
        handler._register(self)
        if handler.timeout is not None:
            self.schedule(handler, handler.timeout, "timeout")
        self.selector.register(handler.fileobj, selectors.EVENT_READ, handler)

    def unregister(self, handler: FDHandler):
        """
        Removes a file descriptor handler (when it is closed). This method
        removes any remaining events for the handler from the queue. Generally
        this method should be called in the course of the FDHandler.terminate()
        method.
        """
        if not isinstance(handler, FDHandler): raise TypeError()
        self.queue = [ x for x in self.queue if x[0] is not handler ]
        self.deschedule(handler)
        self.selector.unregister(handler.fileobj)
        self.fd_handlers.remove(handler)


    def schedule(self, obj, delay, message, payload = None):
        """
        Schedules a timed event to be associated with a given Handler object.
        Only one timed event may be associated with a Handler; calling this
        method twice overwrites the existing scheduled event.
        """
        if not isinstance(obj, Handler): raise TypeError()
        self.timed_queue[obj] = ScheduledMessage(
                time.monotonic() + delay,
                Message(obj, message, payload)
                )


    def deschedule(self, handler):
        """
        Removes any scheduled events for the given Handler object from the timed
        queue.
        """
        if handler in self.timed_queue: del self.timed_queue[handler]


    def run(self, catch_exceptions = True):
        """
        Executes the main event loop. The function:

        1. Adds the main handler's "run" method to the queue
        2. Executes the queue so long as it is not empty. The "run" handler is
           responsible for adding itself back onto the queue.

        Exceptions raised during event handling are printed but do not terminate
        the event loop. Other BaseExceptions will terminate the event loop.
        """
        self.send(main_handler, 'run')
        try:
            while self.queue:
                message = self.queue.pop(0)

                try:
                    message.handler.handle(message.event, message.payload)
                except Exception:
                    if catch_exceptions:    traceback.print_exc()
                    else:                   raise(e)
        except KeyboardInterrupt:
            print("Keyboard interrupt; terminating")
        finally:
            for h in list(self.fd_handlers): h.terminate()




#
# The one MainHandler of this object
#
main_handler = MainHandler()

#
# Delegate methods of the module to the singleton MainHandler
send = main_handler.send
schedule = main_handler.schedule
deschedule = main_handler.deschedule
run = main_handler.run
register_reader = main_handler.register_reader

