#!/usr/bin/env python3

import event_loop as e
import sys
import os

try:

    e.SocketListener(
            'localhost', 1234,
            e.read_to_delimiter(
                   lambda x : print("Got " + x + "!"), delimiter = "e"),
            5,
        )

    e.run_loop()

finally:
    pass
