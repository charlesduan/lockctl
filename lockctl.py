#!/usr/bin/env python3

import gpiod
import datetime
import time
import yaml
import event_loop

with open('config.yaml', 'r') as io:
    config = yaml.safe_load(io)

in_line = config['in_line']
out_line = config['out_line']

out_ls = gpiod.LineSettings(
        direction = gpiod.line.Direction.OUTPUT,
        active_low = False,
        drive = gpiod.line.Drive.PUSH_PULL,
        output_value = gpiod.line.Value.INACTIVE)

in_ls = gpiod.LineSettings(
        direction = gpiod.line.Direction.INPUT,
        active_low = False,
        bias = gpiod.line.Bias.DISABLED,
        debounce_period = datetime.timedelta(milliseconds = 3),
        edge_detection = gpiod.line.Edge.BOTH)



with gpiod.Chip(config['chip']) as chip:

    # Get the lines
    req = chip.request_lines(
            { in_line: in_ls, out_line: out_ls },
            consumer = config["consumer"]
            )

    def read_fn(obj):
        for e in req.read_edge_events():
            if e.event_type == gpiod.EdgeEvent.FALLING_EDGE:
                t = "falling"
            else:
                t = "rising"
            print(f"Line {e.line_offset} is {t}")

    event_loop.FDReader(chip.fd, read_fn)

    event_loop.run_loop()





