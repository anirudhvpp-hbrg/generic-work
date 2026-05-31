"""Monarch OS — the local runtime with Shadow OS operating within it.

Run it::

    python -m monarchos                      # interactive shell
    python -m monarchos "tighten this deck"  # one-shot

Or embed it::

    from monarchos import boot
    os_rt = boot()                # durable local memory; Claude if a key is set
    task = os_rt.run("research why retention dropped")
    print(task.final_output)
"""

from monarchos.runtime import MonarchOS, boot, DEFAULT_STATE

__all__ = ["MonarchOS", "boot", "DEFAULT_STATE"]
__version__ = "1.0.0"
