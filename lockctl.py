#!/usr/bin/env python3

import gpiod
import datetime
import time
import yaml
import em

from gpiod.line import Value

with open('config.yaml', 'r') as io:
    config = yaml.safe_load(io)



class OutLineHandler(em.Handler):
    """
    Manages unlocking and locking the door via the GPIO output. Responds to
    events "on", "off", and "pulse".
    """

    def __init__(self, line_request, offset):
        self.line_request = line_request
        self.offset = offset
        self.active = False
        # Just to make sure
        self.update_gpio()

    def update_gpio(self):
        """ Updates the GPIO line to be compatible with self.active """
        self.line_request.set_value(
                self.offset, Value.ACTIVE if self.active else Value.INACTIVE)

    def handle_pulse(self, duration = None):
        """
        Turn the line on for a short period of time. The payload should be the
        duration; if None then it will be 0.2.
        """
        # Return if already beeping. Perhaps in the future, figure out whether
        # to extend the current beep length?
        if duration is None: duration = 0.2
        if self.active: return
        self.handle_on()
        em.schedule(self, 0.2, "off", None)

    def handle_on(self, payload = None):
        """ Turn on the GPIO output """
        if self.active: return
        self.active = True
        self.update_gpio()

    def handle_off(self, payload):
        """ Turn off the GPIO output """
        if not self.active: return
        self.active = False
        self.update_gpio()


class LockSwitchHandler(em.Handler):
    """
    Handles the GPIO switch indicating lock state.
    """
    def __init__(self, beeper: GPIOOutHandler, unlocker: GPIOOutHandler):
        self.beeper = beeper
        self.unlocker = unlocker

    def handle_rise(self, payload):
        """
        A rise (so the lock state is active) indicates that the door has been
        unlocked.
        """
        em.send(self.beeper, "beep")
        em.send(self.unlocker, "on")

    def handle_fall(self, payload):
        em.send(self.unlocker, "off")




class GPIOHandler(em.FDHandler):
    def __init__(self, chip_path):
        self.chip = gpiod.Chip(chip_path)
        self.in_lines = {}
        self.out_lines = {}
        self.request = None

    def add_input_line(self, line, handler, settings = None):
        if type(line) is int: offset = line
        else: offset = self.chip.line_offset_from_id(line)
        if settings is None: settings = self.in_line_settings()
        self.in_lines[offset] = (settings, handler)

    def add_output_line(self, line, handler, settings = None):
        if type(line) is int: offset = line
        else: offset = self.chip.line_offset_from_id(line)
        if settings is None: settings = self.out_line_settings()
        self.out_lines[offset] = (settings, handler)

    def out_line_settings(self):
        return gpiod.LineSettings(
            direction = gpiod.line.Direction.OUTPUT,
            active_low = False,
            drive = gpiod.line.Drive.PUSH_PULL,
            output_value = Value.INACTIVE)

    def in_line_settings(self):
        return gpiod.LineSettings(
            direction = gpiod.line.Direction.INPUT,
            active_low = False,
            bias = gpiod.line.Bias.DISABLED,
            debounce_period = datetime.timedelta(milliseconds = 3),
            edge_detection = gpiod.line.Edge.BOTH)

    def make_request(self):
        in_settings = { x, y[0] for x, y in self.in_lines.items() }
        out_settings = { x, y[0] for x, y in self.out_lines.items() }
        self.request = self.chip.request_lines(
                in_settings.update(out_settings),
                consumer = config["consumer"]
                )

        super().__init__(self.request.fd)
        em.register_reader(self)

        # Set the request for the output handlers, since they need access to it.
        for settings, handler in self.out_lines.values():
            handler.line_request = self.request


    def handle_read(self, payload)
        for e in self.request.read_edge_events():
            if e.event_type == gpiod.EdgeEvent.Type.RISING_EDGE:
                msg = "rise"
            else:
                msg = "fall"

        if e.line_offset in self.in_lines:
            em.send(self.in_lines[e.line_offset], msg)
        else:
            pass # Should cause a warning message

    def terminate(self):
        self.main_handler.unregister(self)
        try:
            if self.request is not None: self.request.release()
            if self.chip: self.chip.close()
        except:
            pass


def 

gpio_handler = GPIOHandler(config['chip'])

unlocker = OutLineHandler()
gpio_handler.add_output_line(config['out_line'], unlocker)

beeper = OutLineHandler()
gpio_handler.add_output_line(config['piezo_line'], beeper)

gpio_handler.add_input_line(
        config['in_line'], LockSwitchHandler(unlocker, beeper))

gpio_handler.make_request()



        def read_fn(obj):
            print("Read event")
            for e in req.read_edge_events():
                em.send(beeper, 'beep')
                if e.event_type == gpiod.EdgeEvent.Type.FALLING_EDGE:
                    req.set_value(out_line, Value.INACTIVE)
                else:
                    req.set_value(out_line, Value.ACTIVE)

        event_loop.FDReader(req.fd, read_fn)

        def check(obj):
            print(f"In line is {req.get_value(in_line)}")
            event_loop.TimedEvent(check, 3)
        event_loop.TimedEvent(check, 3)

        event_loop.run_loop()





