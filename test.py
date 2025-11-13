#!/usr/bin/env python3

import event_loop as e
import sys
import os

path = "test.fifo"
os.mkfifo(path)
fifo = os.open(path, os.O_RDONLY | os.O_NONBLOCK)

try:

    e.FDReader(
            fifo,
            e.read_to_delimiter(
                   lambda x : print("Got " + x + "!"), delimiter = "e"),
            timeout = 5,
        )

    def next_event(ev):
        print("Tick!")
        e.TimedEvent(next_event, 1)

    e.TimedEvent(next_event, 1)

    e.run_loop()

finally:
    os.remove(path)
