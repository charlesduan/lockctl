#!/usr/bin/env python3

import gpiod
import datetime
import time
import yaml
import event_loop

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



with gpiod.Chip(config['chip']) as chip:
    with chip.request_lines(
            { in_line: in_ls, out_line: out_ls, piezo_line: out_ls },
            consumer = config["consumer"]
            ) as req:

        def beep():
            req.set_value(piezo_line, Value.ACTIVE)
            event_loop.TimedEvent(
                    lambda x: req.set_value(piezo_line, Value.INACTIVE),
                    0.2)

        def read_fn(obj):
            print("Read event")
            for e in req.read_edge_events():
                beep()
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





