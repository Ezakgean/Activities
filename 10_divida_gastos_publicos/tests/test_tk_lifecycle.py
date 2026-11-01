import gc
import threading
import unittest

from app.tk_lifecycle import gui_session, run_mainloop


class LifecycleTests(unittest.TestCase):
    def test_session_collects_local_cycles_before_restoring_gc(self):
        finalized = []
        original_state = gc.isenabled()

        class GuiObject:
            def __init__(self):
                self.cycle = self

            def __del__(self):
                finalized.append((threading.get_ident(), gc.isenabled()))

        @gui_session
        def main():
            local_variable = GuiObject()
            self.assertFalse(gc.isenabled())

        main()
        self.assertEqual(finalized, [(threading.get_ident(), False)])
        self.assertEqual(gc.isenabled(), original_state)

    def test_worker_allocations_do_not_finalize_gui_cycles(self):
        finalized = []
        main_thread = threading.get_ident()
        original_state = gc.isenabled()

        class GuiObject:
            def __init__(self):
                self.cycle = self

            def __del__(self):
                finalized.append(threading.get_ident())

        class Root:
            def after(self, delay, callback):
                self.callback = callback
                return 'timer'

            def after_cancel(self, callback):
                self.cancelled = callback

            def mainloop(self):
                GuiObject()

                def work():
                    self.worker_gc_enabled = gc.isenabled()
                    # Enough allocations to trigger automatic collection if enabled.
                    objects = [[i] for i in range(10000)]
                    self.allocations = len(objects)

                worker = threading.Thread(target=work)
                worker.start()
                worker.join()
                self.before_collection = list(finalized)
                self.callback()

        root = Root()
        run_mainloop(root)
        self.assertFalse(root.worker_gc_enabled)
        self.assertEqual(root.before_collection, [])
        self.assertEqual(finalized, [main_thread])
        self.assertEqual(root.cancelled, 'timer')
        self.assertEqual(gc.isenabled(), original_state)

    def test_gc_state_restored_if_event_loop_fails(self):
        class Root:
            def after(self, delay, callback):
                return 'timer'

            def after_cancel(self, callback):
                pass

            def mainloop(self):
                raise ValueError('event loop failed')

        original_state = gc.isenabled()
        try:
            for enabled in (True, False):
                gc.enable() if enabled else gc.disable()
                with self.assertRaisesRegex(ValueError, 'event loop failed'):
                    run_mainloop(Root())
                self.assertEqual(gc.isenabled(), enabled)
        finally:
            gc.enable() if original_state else gc.disable()


if __name__ == '__main__':
    unittest.main()
