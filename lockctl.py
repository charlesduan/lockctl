#!/usr/bin/env python3

import gpiod
import datetime
import time
import yaml

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



with gpiod.Chip("/dev/gpiochip0") as chip:

    req = chip.request_lines(
            { in_line: in_ls, out_line: out_ls },
            consumer = "lock-controller"
            )
    req.set_value(out_line, gpiod.line.Value.ACTIVE)
    time.sleep(1)
    req.set_value(out_line, gpiod.line.Value.INACTIVE)





