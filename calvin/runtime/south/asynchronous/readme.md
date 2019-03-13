# Asynchronous

This module should be ported to asyncio. The API is described below and also grouped based on whether they relate to IO-bound operations, to CPU-bound operations, or scheduling in general.

One of the goals is to get rid of as many callback avalanches as possible.

## Scheduling

### run_ioloop

    run_ioloop()

Start the scheduler

### stop_ioloop

    stop_ioloop()

Stop the scheduler

### DelayedCall: Scheduling tasks for the future

    DelayedCall(delay, func, *func_args, **func_kwargs)

Tell scheduler to call `func(*func_args, **func_kwargs)` after delay seconds.
If a return value is required, it must be in the form of a callback passed to `func` as an argument or in its closure.  

- [ ] Rename

## IO-bound operations (async)

  
### GenericFileDescriptor: Non-blocking file IO

    GenericFileDescriptor(actor, trigger, fname, mode)
      fname : filepath
      mode : 'r' or 'w'
      actor : argument for trigger
      trigger : a function to be called when data becomes available, typically `calvinsys.scheduler_wakeup`
      
      methods:
        write(data)
        writeLine(data)
        read() -> data
        hasData() -> bool
        close()

- [ ] Simplify trigger(actor_id) handling (partial?)
- [ ] Rename


### StdInFileDescriptor: Non-blocking read from stdin

    StdInFileDescriptor(actor, trigger)
      actor : argument for trigger()
      trigger : a function to be called when data becomes available, typically `calvinsys.scheduler_wakeup`
      
      methods:
        read() -> data
        hasData() -> bool
        close()

- [ ] Simplify trigger(actor_id) handling (partial?)
- [ ] Rename?

`StdInFileDescriptor` is a subclass of `GenericFileDescriptor`


### ServerProtocolFactory: Non-blocking servers

    ServerProtocolFactory(trigger, mode='line', delimiter=b'\r\n', max_length=8192, actor_id=None, node_name=None)
      mode : 'line', 'raw', or 'http'
      delimiter : applicable to 'line' only ('http' supplies its own) 
      max_length : maximum chunk size, applicable to 'raw' only
      trigger : a function to be called when data becomes available, typically `scheduler_wakeup`
      actor_id : argument for trigger()
      node_name : required for TLS to find certificates

This is the basis for TCPServer and HTTPServer instances. 

- [√] Split API into TCPServer() and HTTPServer()
- [√] Drop moot arguments accordingly
- [ ] Simplify trigger(actor_id) handling (partial?)
 

### TCPClientProtocolFactory: Non-blocking TCP socket client

      TCPClientProtocolFactory(mode, delimiter="\r\n", node_name=None, server_node_name=None, callbacks=None)
         mode : as above
         delimiter : as above
         node_name : unused?
         server_node_name : unused?
         callbacks : dict with key:[callbacks] where callbacks are called when 'key' happens 

- [√] Rename to TCPClient for consistency
- [ ] Drop unused arguments
- [ ] Don't expose callbacks this way (needs knowledge of implementation details)


### UDPServerProtocol: Non-blocking UDP server

    UDPServerProtocol(trigger, actor_id)
      trigger : a function to be called when data becomes available, typically `scheduler_wakeup`
      actor_id : argument for trigger()

- [√] Rename to UDPServer for consistency
- [ ] Simplify trigger(actor_id) handling (partial?)


### UDPClientProtocolFactory: Non-blocking UDP client

    UDPClientProtocolFactory(callbacks=None):
      callbacks : dict with callbacks for event, e.g. {'data_received': [CalvinCB(self._data_received)]}

- [√] Rename to UDPClient for consistency
- [ ] Don't expose callbacks this way (needs knowledge of implementation details)


### EventSource: Internal use only

    EventSource()
    
    methods:
      send(client_id, data)

For GUI state updates (push actor state changes to UI)

- [ ] Rework later when the rest has settled (GUI will need fixes anyway)


## CPU-bound operations (threading)


### defer_to_thread: Detach worker thread

    defer_to_thread(func, *args, **kwargs) -> deferred
    
    Usage:
      defer = defer_to_thread(foo)
      defer.addCallback(success_cb)
      defer.addErrback(error_cb)
      defer.addBoth(sched_wakeup)

Execute function in thread of its own, return result/error in callbacks  

- [ ] Rename
- [ ] Figure out how to handle callbacks in a better way
- [ ] Figure out how to handle scheduler wakeup in a better way


### call_in_thread: Detach worker thread

    call_in_thread(func, *args, **kwargs)
      func : function not returning a result

Call, potentially slow, function in thread of its own. 

- [ ] Rename


### call_from_thread: Call main thread from worker thread

    call_from_thread(func, *args, **kwargs)
      func : function to be scheduled on main thread

If already in main thread, use `DelayedCall` with delay=0 instead.

- [ ] Rename


 