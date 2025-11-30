import unittest
import em
import time
import os

class StubHandler(em.FDHandler):

    def __init__(self, timeout = 0.1):
        rfd, self.wfd = os.pipe()
        self.bufs = []
        super().__init__(rfd, timeout)

    def handle_read(self, payload):
        self.bufs.append(os.read(self.fd, 4096))
        if not self.bufs[-1]: self.terminate()


class TestEMSelect(unittest.TestCase):

    def test_run_select_empty(self):
        mh = em.MainHandler()
        start = time.monotonic()
        mh.run_select(0.01)
        elapsed = time.monotonic() - start
        self.assertAlmostEqual(elapsed, 0.01, delta = 0.005)

    def test_handle_read(self):
        th = StubHandler()
        os.write(th.wfd, b'hello world')
        th.handle('read', th.fileobj)
        self.assertEqual(th.bufs, [ b'hello world' ])

    def test_register(self):
        mh = em.MainHandler()
        th = StubHandler()
        mh.register_reader(th)
        self.assertIn(th, mh.fd_handlers)
        self.assertTrue(mh.selector.get_key(th.fileobj))

    def test_terminate(self):
        mh = em.MainHandler()
        th = StubHandler()
        mh.register_reader(th)

        mh.send(th, 'read')
        self.assertEqual(len(mh.queue), 1)
        self.assertEqual(len(mh.timed_queue), 1)

        th.terminate()
        self.assertNotIn(th, mh.fd_handlers)
        self.assertEqual(len(mh.queue), 0)
        self.assertEqual(len(mh.timed_queue), 0)
        with self.assertRaises(KeyError):
            mh.selector.get_key(th.fileobj)

    def test_run_select(self):
        mh = em.MainHandler()
        th = StubHandler()
        os.write(th.wfd, b'hello world')
        mh.register_reader(th)
        start = time.monotonic()
        mh.run_select(1)
        elapsed = time.monotonic() - start
        self.assertAlmostEqual(elapsed, 0, delta = 0.005)

        self.assertEqual(len(mh.queue), 1)
        message = mh.queue[0]
        self.assertIs(message.handler, th)
        self.assertEqual(message.event, 'read')

    def test_run_select_close(self):
        mh = em.MainHandler()
        th = StubHandler()
        os.close(th.wfd)
        mh.register_reader(th)
        start = time.monotonic()
        mh.run_select(1)
        elapsed = time.monotonic() - start
        self.assertAlmostEqual(elapsed, 0, delta = 0.005)

        self.assertEqual(len(mh.queue), 1)
        message = mh.queue[0]
        self.assertIs(message.handler, th)
        self.assertEqual(message.event, 'read')

    def test_timeout_update(self):
        mh = em.MainHandler()
        th = StubHandler(0.1)
        start = time.monotonic()
        mh.register_reader(th)

        orig_time = mh.timed_queue[th].time
        self.assertIn(th, mh.timed_queue)
        self.assertAlmostEqual(orig_time - start, 0.1, delta = 0.005)

        time.sleep(0.01)
        os.close(th.wfd)
        mh.run_select(0.01)

        self.assertEqual(len(mh.timed_queue), 1)
        self.assertIn(th, mh.timed_queue)

        new_time = mh.timed_queue[th].time
        self.assertAlmostEqual(
                new_time - start, 0.11, delta = 0.005)
        self.assertGreaterEqual(new_time - orig_time, 0.01)



    def test_timeout(self):
        mh = em.MainHandler()
        th = StubHandler(0.01)
        mh.register_reader(th)
        self.assertEqual(len(mh.timed_queue), 1)

        time.sleep(0.01)
        mh.run_timed()
        self.assertEqual(len(mh.timed_queue), 0)
        self.assertEqual(len(mh.queue), 1)
        message = mh.queue[0]
        self.assertIs(message.handler, th)
        self.assertEqual(message.event, 'timeout')

