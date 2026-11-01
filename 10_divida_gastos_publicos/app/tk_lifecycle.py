"""Keep cyclic Tk object finalizers on the thread that owns the interpreter."""

from __future__ import annotations

import gc
from functools import wraps
import threading
import tkinter as tk


def gui_session(entrypoint):
    """Also collect the GUI's local reference cycles after its function returns."""
    @wraps(entrypoint)
    def wrapped(*args, **kwargs):
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("A interface deve executar na thread principal.")
        was_enabled = gc.isenabled()
        gc.disable()
        try:
            return entrypoint(*args, **kwargs)
        finally:
            gc.collect()
            if was_enabled:
                gc.enable()

    return wrapped


def run_mainloop(root: tk.Misc) -> None:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("A interface deve executar na thread principal.")

    # Automatic GC can run in the collection worker and finalize unreachable
    # Tk variables/images left in cycles by closed windows or replaced charts.
    # Reference counting stays active; cyclic garbage is collected by Tk's loop.
    was_enabled = gc.isenabled()
    gc.disable()
    callback = None

    def collect() -> None:
        nonlocal callback
        gc.collect()
        callback = root.after(1000, collect)

    try:
        callback = root.after(1000, collect)
        root.mainloop()
    finally:
        if callback is not None:
            try:
                root.after_cancel(callback)
            except tk.TclError:
                pass
        gc.collect()
        if was_enabled:
            gc.enable()
