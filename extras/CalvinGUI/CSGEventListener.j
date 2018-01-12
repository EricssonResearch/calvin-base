@import <Foundation/Foundation.j>

@typedef CSGEventDataFormat
CSGInvalidDataFormat = 0;
CSGRawDataFormat = 1;
CSGJSONStringDataFormat = 2;
CSGJSONDataFormat = 3;


@protocol CSGEventListening
- (void)eventWithData:(id)data sender:(CSGEventListener)sender;
@end

@implementation CSGEventListener : CPObject
{
    CSGEventDataFormat dataFormat @accessors(getter=dataFormat);
    CPString eventName @accessors(getter=eventType);
    id<CSGEventListening> delegate @accessors();
    Object eventSource;
    Function dataConverter;
    Function listener;
}

- (id)initWithURL:(CPURL)anURL eventType:(CPString)eventType dataFormat:(CSGEventDataFormat)fmt
{
    if(self = [super init])
    {
        eventSource = new EventSource(anURL);
        eventName = eventType;
        [self _setDataFormat:fmt];
        eventSource.onerror = function(e) {
            console.log("EventSource failed ", self);
        };
    }
    return self;
}

- (void)_setDataFormat:(CSGEventDataFormat)fmt
{
    switch (fmt) {
    case CSGRawDataFormat:
        dataFormat = fmt;
        dataConverter = function(x) {return x;};
        break;
    case CSGJSONStringDataFormat:
        dataFormat = fmt;
        dataConverter = JSON.parse;
        break;
    default:
        dataFormat = CSGInvalidDataFormat;
        dataConverter = function(x) {return x;};
        break;
    }
}

- (BOOL)isListening
{
    return listener != nil;
}

- (void)startListening
{
    if (listener) {
        return;
    }
    listener = function(evt) {
        if (delegate) {
            [delegate eventWithData:dataConverter(evt.data) sender:self];
            [[CPRunLoop currentRunLoop] limitDateForMode:CPDefaultRunLoopMode];
        } else {
            console.log("No delegate, dropping event:", evt);
        }
    }
    eventSource.addEventListener(eventName, listener, false);
}

- (void)stopListening
{
    if (!listener) {
        return;
    }
    eventSource.removeEventListener(eventName, listener, false);
    eventSource.close()
    listener = nil;
}

@end
