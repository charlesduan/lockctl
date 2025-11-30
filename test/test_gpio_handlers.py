import unittest
import em
import time
import gpio_handlers

class GPIOStub:
    """
    A stub class for a GPIO handler, providing the same API without the need for
    the GPIO handler itself.
    """
    def __init__(self, active_ins = ()):
        self.log = []
        self.lines_array = { "GPIO1": 1, "GPIO2": 2, "GPIO3": 3, "GPIO4": 4 }
        self.lines = {}
        self.request = None
        self.active_ins = active_ins

    def offset_for_line(self, line):
        return self.lines_array[line]

    def default_settings(self, direction):
        if direction not in ('input', 'output'):
            raise ValueError("Invalid direction")
        return direction

    def add(self, handler):
        self.lines[handler.offset] = handler

    def make_request(self):
        self.request = True
        self.deactivate_outputs()
        for in_line in self.active_ins:
            em.send(self.lines[in_line], 'rise')

    def handle_read(self, payload):
        # The payload will be a hash of which lines to rise/fall
        for offset, event in payload.items():
            if event not in ('rise', 'fall'): raise ValueError('Bad event')
            em.send(self.lines[offset], event)

    def handle_set_line(self, payload):
        offset, active = payload
        if offset not in self.lines:
            raise KeyError(f"GPIO did not request line {offset}")
        if not isinstance(self.lines[offset], gpio_handlers.OutputHandler):
            raise TypeError(f"GPIO line {offset} is not configured for output")
        if self.request is None:
            raise RuntimeError("GPIO lines have not been requested yet")
        self.log.append(f"Set line {offset} to {active}")

    def terminate(self):
        self.deactivate_outputs()

    def deactivate_outputs(self):
        pass



class TestGPIOHandler(unittest.TestCase):

    def test_in_init(self):
        gh = GPIOStub()
        ih = gpio_handlers.InputHandler(gh, 'GPIO1')
        self.assertEqual(ih.offset, 1)

    def test_in_settings(self):
        gh = GPIOStub()
        ih = gpio_handlers.InputHandler(gh, 'GPIO1')
        self.assertEqual(ih.settings(), gh.default_settings('input'))

    def test_out_init(self):
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        self.assertEqual(oh.offset, 2)
        self.assertFalse(oh.active)
        self.assertFalse(oh.pulsing)

    def test_out_settings(self):
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        self.assertEqual(oh.settings(), gh.default_settings('output'))

    def test_out_update(self):
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        gh.add(oh)
        gh.make_request()

        oh.active = True
        oh.update_gpio()
        oh.active = False
        oh.update_gpio()

        self.assertEqual(gh.log, [
            "Set line 2 to True", "Set line 2 to False"
            ])


    def test_out_on(self):
        em.main_handler.reset()
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        gh.add(oh)
        gh.make_request()

        oh.handle_on()
        self.assertEqual(gh.log, [ "Set line 2 to True" ])
        self.assertTrue(oh.active)
        self.assertFalse(oh.pulsing)

    def test_out_on_twice(self):
        em.main_handler.reset()
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        gh.add(oh)
        gh.make_request()

        oh.handle_on()
        oh.handle_on()
        self.assertEqual(gh.log, [ "Set line 2 to True" ])
        self.assertTrue(oh.active)

    def test_out_off(self):
        em.main_handler.reset()
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        gh.add(oh)
        gh.make_request()

        oh.active = True
        oh.handle_off()
        self.assertEqual(gh.log, [ "Set line 2 to False" ])
        self.assertFalse(oh.active)
        self.assertFalse(oh.pulsing)

    def test_out_off_twice(self):
        em.main_handler.reset()
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        gh.add(oh)
        gh.make_request()

        oh.active = True
        oh.handle_off()
        oh.handle_off()
        self.assertEqual(gh.log, [ "Set line 2 to False" ])
        self.assertFalse(oh.active)

    def test_out_pulse(self):
        em.main_handler.reset()
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        gh.add(oh)
        gh.make_request()

        start = time.monotonic()
        oh.handle_pulse(1)
        self.assertEqual(gh.log, [ "Set line 2 to True" ])
        self.assertTrue(oh.active)
        self.assertTrue(oh.pulsing)

        self.assertIn(oh, em.main_handler.timed_queue)
        m = em.main_handler.timed_queue[oh]
        self.assertAlmostEqual(m.time - start, 1, delta = 0.005)

    def test_out_pulse_on(self):
        em.main_handler.reset()
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        gh.add(oh)
        gh.make_request()

        oh.handle_pulse(1)
        oh.handle_on()
        self.assertEqual(gh.log, [ "Set line 2 to True" ])
        self.assertTrue(oh.active)
        self.assertFalse(oh.pulsing)
        self.assertNotIn(oh, em.main_handler.timed_queue)

    def test_out_pulse_off(self):
        em.main_handler.reset()
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        gh.add(oh)
        gh.make_request()

        oh.handle_pulse(1)
        oh.handle_off()
        self.assertEqual(gh.log, [
            "Set line 2 to True", "Set line 2 to False"
            ])
        self.assertFalse(oh.active)
        self.assertFalse(oh.pulsing)
        self.assertNotIn(oh, em.main_handler.timed_queue)

    def test_out_pulse_twice(self):
        em.main_handler.reset()
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        gh.add(oh)
        gh.make_request()

        start = time.monotonic()
        oh.handle_pulse(1)
        time.sleep(0.01)
        oh.handle_pulse(2)
        self.assertEqual(gh.log, [ "Set line 2 to True" ])
        self.assertTrue(oh.active)
        self.assertTrue(oh.pulsing)

        self.assertIn(oh, em.main_handler.timed_queue)
        m = em.main_handler.timed_queue[oh]
        self.assertAlmostEqual(m.time - start, 1, delta = 0.005)

    def test_out_on_pulse(self):
        em.main_handler.reset()
        gh = GPIOStub()
        oh = gpio_handlers.OutputHandler(gh, 'GPIO2')
        gh.add(oh)
        gh.make_request()

        oh.handle_on()
        oh.handle_pulse(1)
        self.assertEqual(gh.log, [ "Set line 2 to True" ])
        self.assertTrue(oh.active)
        self.assertFalse(oh.pulsing)
        self.assertNotIn(oh, em.main_handler.timed_queue)
