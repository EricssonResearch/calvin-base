import asyncio
import functools

PENDING_START = []

class DelayedCall(object):

    def __init__(self, delay, dc_callback, *args, **kwargs):
        self.delay = delay
        self.callback = functools.partial(dc_callback, *args, **kwargs)
        self.callback.__name__ = dc_callback.__name__
        self.delayedCall = None # asyncio.TimerHandle
        self.dispatch()
        
    def dispatch(self):
        loop = asyncio.get_event_loop()
        self.delayedCall = loop.call_later(self.delay, self.callback)
                
    def reset(self, new_delay = None):
        self.cancel()
        if new_delay is not None:
            self.delay = new_delay
        self.dispatch()
 
    def active(self):
        return self.delayedCall and not self.delayedCall.cancelled()

    def cancel(self):
        if self.delayedCall:
            self.delayedCall.cancel()

    # Unused
    # def nextcall(self):
    #     # Return time left until this will be called
    #     if self.delayedCall.active():
    #         loop = asyncio.get_event_loop()
    #         return self.delayedCall.when() - loop.time()
    #     else:
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

