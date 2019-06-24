import asyncio
import functools


class DeferToThread(object):
    """docstring for DeferToThread"""
    def __init__(self, fn, *args, **kwargs):
        super(DeferToThread, self).__init__()
        self._fn = functools.partial(fn, *args, **kwargs)
        self._done_callbacks = []
        self._error_callbacks = []
        self._dispatch()

    def _dispatch(self):
        loop = asyncio.get_running_loop()
        task = loop.run_in_executor(None, self._fn)
        task.add_done_callback(self._execute_callbacks)

    def _execute_callbacks(self, future):
        try:
            _ = future.result()
        except CancelledError:
            pass
        except:
            for callback in self._error_callbacks:
                callback()
        else:
            for callback in self._done_callbacks:
                callback()

    def addCallback(self, cb):
        self._done_callbacks.append(cb)

    def addErrback(self, cb):
        self._error_callbacks.append(cb)

    def addBoth(self, cb):
        self.addCallback(cb)
        self.addErback(cb)

defer_to_thread = DeferToThread

