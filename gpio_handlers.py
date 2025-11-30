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
        return self.gpio_handler.default_settings('input')

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
        return self.gpio_handler.default_settings('output')

    def update_gpio(self):
        """ Updates the GPIO line to be compatible with self.active """
        self.gpio_handler.handle_set_line((self.offset, self.active))

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
        self._cancel_pulse()
        if self.active: return
        self.active = True
        self.update_gpio()

    def handle_off(self, payload = None):
        """ Turn off the GPIO output """
        self._cancel_pulse()
        if not self.active: return
        self.active = False
        self.update_gpio()


