#!/usr/bin/env python3

import gpiod
import datetime
import time
import yaml
import em

from gpiod.line import Value

with open('config.yaml', 'r') as io:
    config = yaml.safe_load(io)

in_line = config['in_line']
out_line = config['out_line']
piezo_line = config['piezo_line']

out_ls = gpiod.LineSettings(
        direction = gpiod.line.Direction.OUTPUT,
        active_low = False,
        drive = gpiod.line.Drive.PUSH_PULL,
        output_value = Value.INACTIVE)

in_ls = gpiod.LineSettings(
        direction = gpiod.line.Direction.INPUT,
        active_low = False,
        bias = gpiod.line.Bias.DISABLED,
        debounce_period = datetime.timedelta(milliseconds = 3),
        edge_detection = gpiod.line.Edge.BOTH)


class GPIOOutHandler(em.Handler):
    """
    Manages actions for a GPIO output line.
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

class GPIOInHandler(em.Handler):
    """
    Handles all GPIO input events, by dispatching each line's events to a
    specific handler.
    """

    def __init__(self, line_request):
        self.line_request = line_request
        self.handlers = {}
        self.states = {}

    def register(self, offset: int, handler: em.Handler):
        """
        Registers a handler for a GPIO input event. The handler must respond to
        the messages "rise" and "fall", indicating the change to the state of
        the GPIO input line.
        """
        self.handlers[offset] = handler

        # TODO: occasionally check the state of the lines to make sure they're
        # consistent.
        self.states[offset] = self.line_request.get_value(offset)

    def handle_input(self, payload):
        for e in self.line_request.read_edge_events():
            if e.event_type == gpiod.EdgeEvent.Type.RISING_EDGE:
                msg = "rise"
            else:
                msg = "fall"

            if e.line_offset in self.handlers:
                em.send(self.handlers[e.line_offset], msg)
            else:
                pass # Should cause a warning message

class LockStateHandler(em.Handler):
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

with gpiod.Chip(config['chip']) as chip:
    in_offset = chip.line_offset_from_id(in_line)
    out_offset = chip.line_offset_from_id(out_line)
    piezo_offset = chip.line_offset_from_id(piezo_line)

    with chip.request_lines(
            { in_offset: in_ls, out_offset: out_ls, piezo_offset: out_ls },
            consumer = config["consumer"]
            ) as req:

        beeper = BeepHandler(req, piezo_offset)
        in_handler = GPIOInHandler(req)
        ls_handler = LockStateHandler(req, out_offset, beeper)

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





