import gpiod
from gpiod.line import Direction, Value
import em
import datetime



class InputHandler(em.Handler):
    """
    Manages an input line of a GPIO. This handler must respond to the events
    "rise" and "fall", indicating that the input has changed to the active and
    inactive states respectively.
    """

    def __init__(self, gpio_handler, line):
        self.gpio_handler = gpio_handler
        self.offset = gpio_handler.offset_for_line(line)

    def settings(self):
        """
        Provides the GPIO line settings for this handler. Subclasses may
        override this method to customize the settings.
        """
        return gpiod.LineSettings(
            direction = gpiod.line.Direction.INPUT,
            active_low = False,
            bias = gpiod.line.Bias.DISABLED,
            debounce_period = datetime.timedelta(milliseconds = 3),
            edge_detection = gpiod.line.Edge.BOTH)


class OutputHandler(em.Handler):
    """
    Manages an output line of a GPIO.
    """

    def __init__(self, gpio_handler, line):
        self.gpio_handler = gpio_handler
        self.offset = gpio_handler.offset_for_line(line)
        self.active = False
        self.pulsing = False

    def settings(self):
        return gpiod.LineSettings(
            direction = gpiod.line.Direction.OUTPUT,
            active_low = False,
            drive = gpiod.line.Drive.PUSH_PULL,
            output_value = Value.INACTIVE)

    def update_gpio(self):
        """ Updates the GPIO line to be compatible with self.active """
        em.send(self.gpio_handler, 'set_line', (self.offset, self.active))

    def handle_pulse(self, duration = None):
        """
        Turn the line on for a short period of time. The payload should be the
        duration; if None then it will be 0.2.
        """
        # Return if already beeping. Perhaps in the future, figure out whether
        # to extend the current beep length?
        if duration is None: duration = 0.2
        if self.pulsing or self.active: return
        self.handle_on()
        self.pulsing = True
        em.schedule(self, duration, "off", None)

    def _cancel_pulse(self):
        """
        Turn off any scheduled events relating to a pulse (because of an
        intentional on or off event).
        """
        if not self.pulsing: return
        self.pulsing = False
        em.deschedule(self)

    def handle_on(self, payload = None):
        """ Turn on the GPIO output """
        if self.active: return
        self.active = True
        self.update_gpio()
        self._cancel_pulse()

    def handle_off(self, payload):
        """ Turn off the GPIO output """
        if not self.active: return
        self.active = False
        self.update_gpio()
        self._cancel_pulse()


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
    def __init__(self, chip_path, consumer):
        self.chip = gpiod.Chip(chip_path)
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

