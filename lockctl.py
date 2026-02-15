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
    Handles the GPIO output switch that unlocks the door. Typically this event
    handler should be given a "pulse" message to cause the door to be unlocked
    for a brief period of time.
    """

    def handle_pulse(self, duration = None):
        """
        In addition to unlocking the door for the given duration, logs the fact
        that the door was unlocked.
        """
        global beeper
        if duration is None: duration = 10
        em.log(f"Authorized door unlocking for {duration} seconds")
        em.send(beeper, 'pulse', 2)
        super().handle_pulse(duration)

class LockSwitchHandler(gpio_handlers.InputHandler):
    """
    Handles the GPIO input switch indicating whether the door is locked or
    unlocked.
    """
    def __init__(self, gpio_handler, line):
        global config
        self.beep_delays = config['unlock_beep_times']
        self.unlocked = False
        super().__init__(gpio_handler, line)

    def handle_rise(self, payload):
        """
        A rise (so the lock state is active) indicates that the door has been
        unlocked.
        """
        global unlocker
        self.unlocked = True
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
        self.unlocked = False
        em.send(unlocker, "off")
        em.send(em.logger, 'log', "Door manually locked")
        em.deschedule(self)


class SocketUnlockReader(em.LineReader):
    def __init__(self, fileobj):
        global config

        if "password" not in config:
            raise RuntimeError("No unlock password given")
        self.password = config["password"]
        self.unlock_time = config.get("unlock_time", 10)

        em.send(em.logger, 'log', f"Connection from {fileobj.getpeername()}")

        # The 60 below is the timeout for network reads.
        super().__init__(fileobj, timeout = 60)


    def handle_line(self, line):
        words = line.split()
        if not words: return

        match words.pop(0).lower():
            case "unlock":
                self.handle_unlock(words)
            case "status":
                self.handle_status(words)
            case _:
                self.fileobj.send(b"Unknown command\n")


    def handle_unlock(self, args):
        if args and args[0] == self.password:
            em.send(em.logger, 'log',
                    f"Access granted to {self.fileobj.getpeername()}")
            em.send(unlocker, 'pulse', self.unlock_time)
            self.fileobj.send(b"Access granted\n")
        else:
            self.fileobj.send(b"Access denied\n")


    def handle_status(self, args):
        global lock_tester
        if lock_tester.unlocked:
            self.fileobj.send(b"Unlocked\n")
        else:
            self.fileobj.send(b"Locked\n")


    def terminate(self):
        try:    self.fileobj.shutdown(socket.SHUT_RDWR)
        except: pass
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
        'localhost', config['port'], lambda c: SocketUnlockReader(c)
        )

em.register_reader(socket_listener)

em.run()


