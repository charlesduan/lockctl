#!/usr/bin/env python3

import gpiod
import datetime
import time
import yaml
import em
import socket
import gpio_handlers
from gpio_main import GPIOHandler
from collections import namedtuple

from gpiod.line import Value

with open('config.yaml', 'r') as io:
    config = yaml.safe_load(io)


class UnlockHandler(gpio_handlers.OutputHandler):
    """
    Handles the GPIO switch indicating lock state.
    """
    def handle_pulse(self, duration = None):
        if duration is None: duration = 10
        em.log(f"Authorized door unlocking for {duration} seconds")
        super().handle_pulse(duration)

class LockSwitchHandler(gpio_handlers.InputHandler):
    """
    Handles the GPIO switch indicating lock state.
    """
    def __init__(self, gpio_handler, line):
        global config
        self.beep_delays = config['unlock_beep_times']
        super().__init__(gpio_handler, line)

    def handle_rise(self, payload):
        """
        A rise (so the lock state is active) indicates that the door has been
        unlocked.
        """
        global unlocker
        em.send(unlocker, "on")
        em.send(em.logger, 'log', "Door manually unlocked")
        self.beep_index = 0
        em.schedule(self, 0, 'beep')

    def handle_beep(self, payload):
        global beeper
        em.send(beeper, 'pulse')
        self.beep_index += 1
        i = self.beep_index
        if i < len(self.beep_delays):
            interval = self.beep_delays[i] - self.beep_delays[i - 1]
            em.schedule(self, interval, 'beep')

    def handle_fall(self, payload):
        global unlocker
        em.send(unlocker, "off")
        em.send(em.logger, 'log', "Door manually locked")
        em.deschedule(self)


class SocketUnlockReader(em.LineReader):
    def __init__(self, fileobj, password, unlock_time):
        self.password = password
        self.unlock_time = unlock_time
        em.send(em.logger, 'log', f"Connection from {fileobj.getpeername()}")
        super().__init__(fileobj, timeout = 10)

    def handle_line(self, line):
        if self.password in line:
            em.send(em.logger, 'log',
                    f"Access granted to {self.fileobj.getpeername()}")
            em.send(unlocker, 'pulse', self.unlock_time)

    def terminate(self):
        self.fileobj.shutdown(socket.SHUT_RDWR)
        super().terminate()

gpio_handler = GPIOHandler(config['chip'], config['consumer'])

unlocker = UnlockHandler(gpio_handler, config['out_line'])
beeper = gpio_handlers.OutputHandler(gpio_handler, config['piezo_line'])
lock_tester = LockSwitchHandler(gpio_handler, config['in_line'])

gpio_handler.add(unlocker)
gpio_handler.add(beeper)
gpio_handler.add(lock_tester)

gpio_handler.make_request()

socket_listener = em.SocketListener(
        'localhost', config['port'],
        lambda c: SocketUnlockReader(c, config['password'], 10)
        )

em.register_reader(socket_listener)

em.run()


