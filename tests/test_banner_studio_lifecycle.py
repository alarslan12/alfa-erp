"""Banner Studio lifecycle: a closed browser must not leave orphan server EXEs."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'banner_studio'))
from studio_lifecycle import BrowserSessions


class Clock:
    def __init__(self): self.now=0
    def __call__(self): return self.now
    def advance(self, seconds): self.now+=seconds


class StudioLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.clock=Clock()
        self.life=BrowserSessions(clock=self.clock, startup_timeout=120,
                                  close_grace=12, heartbeat_timeout=900)

    def test_unopened_server_reaps_itself(self):
        self.clock.advance(119)
        self.assertFalse(self.life.should_exit())
        self.clock.advance(1)
        self.assertTrue(self.life.should_exit())

    def test_closed_last_tab_reaps_server(self):
        self.life.event('browser-page-001','open')
        self.clock.advance(1)
        self.life.event('browser-page-001','closed')
        self.clock.advance(11)
        self.assertFalse(self.life.should_exit())
        self.clock.advance(1)
        self.assertTrue(self.life.should_exit())

    def test_duplicate_tab_prevents_early_exit(self):
        self.life.event('browser-page-001','open')
        self.life.event('browser-page-002','open')
        self.life.event('browser-page-001','closed')
        self.clock.advance(60)
        self.assertFalse(self.life.should_exit())
        self.life.event('browser-page-002','heartbeat')
        self.life.event('browser-page-002','closed')
        self.clock.advance(12)
        self.assertTrue(self.life.should_exit())

    def test_refresh_and_delayed_heartbeat(self):
        self.life.event('browser-page-001','open')
        self.life.event('browser-page-001','closed')
        self.life.event('browser-page-001','heartbeat')
        self.clock.advance(5)
        self.assertFalse(self.life.should_exit())
        self.life.event('browser-page-002','open')
        self.clock.advance(90)
        self.assertFalse(self.life.should_exit())

    def test_crashed_browser_reaps_eventually(self):
        self.life.event('browser-page-001','open')
        self.clock.advance(900)
        self.assertFalse(self.life.should_exit())
        self.clock.advance(1)
        self.assertFalse(self.life.should_exit())
        self.clock.advance(12)
        self.assertTrue(self.life.should_exit())


if __name__ == '__main__': unittest.main()
