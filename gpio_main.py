import gpiod
from gpiod.line import Direction, Value
from gpio_handlers import InputHandler, OutputHandler

class GPIOHandler(em.FDHandler):
    """
    An event handler class for managing a GPIO chip. The class has two main
    responsibilities. First, it provides methods for InputHandler and
    OutputHandler objects to access the GPIO chip. Second, it listens on input
    events and dispatches them to InputHandler objects.

    The general usage is as follows. First, a GPIOHandler object is
    constructed. Then, various InputHandler and OutputHandler objects are
    passed to it. After that, the make_request method is invoked, requesting
    the relevant GPIO lines from the chip and initiating the listening on input
    lines. (The em.register_reader method is automatically called within
    make_request.)
    """
    def __init__(self, chip, consumer):
        self.chip = gpiod.Chip(chip) if type(chip) is str else chip
        self.lines = {}
        self.request = None
        self.consumer = consumer

    def offset_for_line(self, line):
        """
        Computes the line offset given a line name. (If an offset is given as
        an integer, it is returned unchanged.)
        """
        if type(line) is int: return line
        else: return self.chip.line_offset_from_id(line)

    def default_settings(self, direction):
        if direction == 'input':
            return gpiod.LineSettings(
                direction = gpiod.line.Direction.INPUT,
                active_low = False,
                bias = gpiod.line.Bias.DISABLED,
                debounce_period = datetime.timedelta(milliseconds = 3),
                edge_detection = gpiod.line.Edge.BOTH)
        elif direction == 'output':
            return gpiod.LineSettings(
                direction = gpiod.line.Direction.OUTPUT,
                active_low = False,
                drive = gpiod.line.Drive.PUSH_PULL,
                output_value = Value.INACTIVE)
        else:
            raise ValueError("Invalid direction")


    def add(self, handler):
        """
        Adds a GPIO line to be controlled. The handler must be an InputHandler
        or OutputHandler. This overwrites any previously added GPIO handler for
        the same line.
        """
        if not isinstance(handler, (InputHandler, OutputHandler)):
            raise TypeError("Invalid handler type for GPIO")
        self.lines[handler.offset] = handler

    def make_request(self):
        """
        Requests all lines added to this handler, and registers the GPIO file
        descriptor with the event manager.

        Upon making the request, this method also initializes all the outputs
        to off. Then, if any inputs are already active, the corresponding
        handler is sent a "rise" message.
        """
        settings = { h.offset: h.settings() for h in self.lines.values() }
        self.request = self.chip.request_lines(
                settings, consumer = self.consumer
                )
        super().__init__(self.request.fd)
        em.register_reader(self)

        self.deactivate_outputs()
        for offset, handler in self.lines.items():
            if not isinstance(handler, InputHandler): continue
            if self.request.get_value(offset) != Value.ACTIVE: continue
            em.send(handler, 'rise')



    def handle_read(self, payload):
        """
        Reads one or more events from the GPIO chip, and transmit messages to
        the corresponding handlers for the changed lines.
        """
        for e in self.request.read_edge_events():
            if e.line_offset not in self.lines:
                # Consider issuing a warning message
                continue
            msg = {
                    gpiod.EdgeEvent.Type.RISING_EDGE: "rise",
                    gpiod.EdgeEvent.Type.FALLING_EDGE: "fall",
                    }[e.event_type]
            em.send(self.lines[e.line_offset], msg)



    def handle_set_line(self, payload):
        """
        Sets the value of an output line. The payload is a 2-element tuple of
        the offset and a boolean for the new state.
        """
        offset, active = payload
        if offset not in self.lines:
            raise KeyError(f"GPIO did not request line {offset}")
        if not isinstance(self.lines[offset], OutputHandler):
            raise TypeError(f"GPIO line {offset} is not configured for output")
        if self.request is None:
            raise RuntimeError("GPIO lines have not been requested yet")

        flag = Value.ACTIVE if active else Value.INACTIVE
        self.request.set_value(offset, flag)


    def deactivate_outputs(self):
        """
        Set outputs to inactive. This should be done upon the initial request,
        and upon termination.
        """
        for handler in self.lines.values():
            if isinstance(handler, OutputHandler):
                self.request.set_value(handler.offset, Value.INACTIVE)


    def terminate(self):
        """
        Closes the connection to the GPIO. All output lines are set to the
        inactive state.
        """
        try:
            # Turn off all output lines before terminating
            self.deactivate_outputs()

            # Close filehandles
            if self.request is not None: self.request.release()
            if self.chip: self.chip.close()
        except:
            pass
        finally:
            self.main_handler.unregister(self)

