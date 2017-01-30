from twisted.internet import defer, reactor
from calvin.runtime.south.plugins.async import threads
from calvin.utilities.calvin_callback import CalvinCB
import pytest
import time

# So it skipps if we dont have twisted plugin
def _dummy_inline(*args):
    pass

if not hasattr(pytest, 'inlineCallbacks'):
    pytest.inlineCallbacks = _dummy_inline

class TimeoutError(Exception):
    """Raised when time expires in timeout decorator"""

def timeout(secs):
    """
    Decorator to add timeout to Deferred calls
    """
    def wrap(func):
        @defer.inlineCallbacks
        def _timeout(*args, **kwargs):
            rawD = func(*args, **kwargs)
            if not isinstance(rawD, defer.Deferred):
                defer.returnValue(rawD)

            timeoutD = defer.Deferred()
            timesUp = reactor.callLater(secs, timeoutD.callback, None)

            try:
                rawResult, timeoutResult = yield defer.DeferredList([rawD, timeoutD], fireOnOneCallback=True, fireOnOneErrback=True, consumeErrors=True)
            except defer.FirstError, e:
                #Only rawD should raise an exception
                assert e.index == 0
                timesUp.cancel()
                e.subFailure.raiseException()
            else:
                #Timeout
                if timeoutD.called:
                    rawD.cancel()
                    raise TimeoutError("%s secs have expired" % secs)

            #No timeout
            timesUp.cancel()
            defer.returnValue(rawResult)
        return _timeout
    return wrap

def create_callback(timeout=.5):

    def dummy_callback(d, *args, **kwargs):
        if d.called:
            return
        tout = kwargs.pop('__timeout', False)
        if tout:
            d.errback("Timeout waiting for deferred")
            return args, kwargs
        d.callback((args, kwargs))
        return args, kwargs

    d = defer.Deferred()
    reactor.callLater(timeout, dummy_callback, d, __timeout=True)
    cb = CalvinCB(dummy_callback, d)
    return cb, d

@pytest.inlineCallbacks
def wait_for(function, condition=lambda x: x(), timeout=1):
    for a in range(int(timeout/.1)):
        if condition(function):
            break
        yield threads.defer_to_thread(time.sleep, .1)

    if not condition(function):
        print("Timeout while waiting for function %s with condition %s" % (function, condition))

