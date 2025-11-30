import unittest
import em
import time
import gpio_handlers

class GPIOStub(em.FDHandler):
    """
    A stub class for a GPIOHandler, providing the same API without the need for
    the GPIO itself.
    """
    def __init__(self, lines_array):

class TestGPIOHandler(em.Handler):

