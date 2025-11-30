import unittest
import em
import time

class StubHandler(em.Handler):
    def __init__(self):
        self.var = None

    def handle_test(self, payload):
        self.var = payload

class TestEMSchedule(unittest.TestCase):

    def test_schedule_type(self):
        mh = em.MainHandler()
        with self.assertRaises(TypeError):
            mh.schedule("abc", 0.1, 'test', 'hello')

    def test_schedule(self):
        mh = em.MainHandler()
        th = StubHandler()
        mh.schedule(th, 0.1, 'test', 'hello')
        self.assertEqual(len(mh.timed_queue), 1)
        self.assertIn(th, mh.timed_queue)

    def test_schedule_run_timed(self):
        mh = em.MainHandler()
        th = StubHandler()
        mh.schedule(th, 0.1, 'test', 'hello')
        delay = mh.run_timed()
        self.assertEqual(len(mh.timed_queue), 1)
        self.assertIn(th, mh.timed_queue)
        self.assertAlmostEqual(delay, 0.1, delta = 0.01)

    def test_schedule_run_timed_min(self):
        mh = em.MainHandler()
        th = StubHandler()
        th2 = StubHandler()
        mh.schedule(th2, 0.2, 'test', 'hello')
        mh.schedule(th, 0.1, 'test', 'hello')
        delay = mh.run_timed()
        self.assertAlmostEqual(delay, 0.1, delta = 0.01)

    def test_schedule_run_timed_two(self):
        mh = em.MainHandler()
        th = StubHandler()
        th2 = StubHandler()
        mh.schedule(th, 0.1, 'test', 'hello')
        mh.schedule(th2, 0, 'test', 'hello2')
        delay = mh.run_timed()
        self.assertEqual(delay, 0)
        self.assertEqual(len(mh.queue), 1)
        self.assertEqual(len(mh.timed_queue), 1)
        self.assertIn(th, mh.timed_queue)

    def test_schedule_run_timed_queued(self):
        mh = em.MainHandler()
        th = StubHandler()
        th2 = StubHandler()
        mh.schedule(th, 0.1, 'test', 'hello')
        mh.send(th2, 'test', 'hello2')
        delay = mh.run_timed()
        self.assertEqual(delay, 0) # Because the queue still has an event
        self.assertEqual(len(mh.timed_queue), 1)
        self.assertIn(th, mh.timed_queue)

    def test_schedule_run_timed_delayed(self):
        mh = em.MainHandler()
        th = StubHandler()
        th2 = StubHandler()
        mh.schedule(th, 0.01, 'test', 'hello')
        mh.schedule(th2, 0, 'test', 'hello2')
        time.sleep(0.01)
        delay = mh.run_timed()
        self.assertEqual(delay, 0)
        self.assertEqual(len(mh.timed_queue), 0)
        self.assertEqual(len(mh.queue), 2)

    def test_schedule_run_timed_empty(self):
        mh = em.MainHandler()
        delay = mh.run_timed()
        self.assertIs(delay, None)
