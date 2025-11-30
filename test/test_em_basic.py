import unittest
import em
import time

class TestHandlerBasics(em.Handler):
    def __init__(self):
        self.var = None

    def handle_test(self, payload):
        self.var = payload

class TestEMBasic(unittest.TestCase):

    def test_instantiate(self):
        h = em.MainHandler()
        self.assertIsInstance(h, em.MainHandler)

    def test_send(self):
        mh = em.MainHandler()
        th = TestHandler()
        mh.send(th, 'test', 'hello')
        self.assertEqual(len(mh.queue), 1)

    def test_run(self):
        mh = em.MainHandler()
        th = TestHandler()
        mh.send(th, 'test', 'hello')
        mh.run(catch_exceptions = False)
        self.assertEqual(th.var, 'hello')

    def test_run_empty(self):
        mh = em.MainHandler()
        mh.handle_run()
        self.assertEqual(len(mh.queue), 0)

    def test_run_one(self):
        mh = em.MainHandler()
        th = TestHandler()
        mh.send(th, 'test', 'hello')
        mh.handle_run()
        self.assertEqual(len(mh.queue), 2)

        self.assertIs(mh.queue[0].handler, th)
        self.assertEqual(mh.queue[0].event, 'test')

        self.assertIs(mh.queue[1].handler, mh)
        self.assertEqual(mh.queue[1].event, 'run')

    def test_run_timeout(self):
        mh = em.MainHandler()
        th = TestHandler()
        mh.schedule(th, 0.01, 'test', 'hello')
        start = time.monotonic()
        mh.handle_run()
        stop = time.monotonic()
        self.assertAlmostEqual(stop - start, 0.01, delta = 0.005)

        self.assertEqual(len(mh.queue), 1)
        self.assertIs(mh.queue[0].handler, mh)
        self.assertEqual(mh.queue[0].event, 'run')

