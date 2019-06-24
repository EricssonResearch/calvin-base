import asyncio
import functools

PENDING_START = []

class DelayedCall(object):

    def __init__(self, delay, dc_callback, *args, **kwargs):
        self.delay = delay
        self.callback = functools.partial(dc_callback, *args, **kwargs)
        self.callback.__name__ = dc_callback.__name__
        self.delayedCall = None # asyncio.TimerHandle
        loop = asyncio.get_event_loop()
        self.dispatch(loop)
        
    def dispatch(self, loop):
        self.delayedCall = loop.call_later(self.delay, self.callback)
                

    # def reset(self, new_delay = None):
    #     if new_delay is not None:
    #         self.delay = new_delay
    #     try:
    #         loop = asyncio.get_running_loop()
    #         self.delayedCall = loop.call_later(self.delay, self.callback)
    #     except RuntimeError:
    #         # Not yet started, queue the requested call
    #         PENDING_START.append(self)
 
                

    def active(self):
        return self.delayedCall and not self.delayedCall.cancelled()
    #
    def cancel(self):
        if self.delayedCall:
            self.delayedCall.cancel()
    #
    # def nextcall(self):
    #     if self.delayedCall.active():
    #         return self.delayedCall.getTime()
    #     else :
    #         return None

def run_ioloop():
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    loop.run_forever()


def stop_ioloop():
    try:
        loop = asyncio.get_running_loop()
        loop.stop()
    except RuntimeError:
        pass

