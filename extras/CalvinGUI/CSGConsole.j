@import <Foundation/Foundation.j>
@import "CSGEventListener.j"
@import "CSGHostConfig.j"

@implementation CSGConsole : CPObject <CSGEventListening>
{
    CPString consoleBase @accessors();
    int maxItems @accessors;
    CPMutableArray items @accessors;
    CSGEventListener listener;
}

- (id)init
{
    self = [super init];
    if (self) {
        var config = [CSGHostConfig sharedHostConfig];
        [self setItems:[]];
        [self setConsoleBase:[CPString stringWithFormat:"http://%@:%d", [config valueForKey:CSGConsoleHostKey], [config valueForKey:CSGConsolePortKey]]];
        maxItems = 100;
        // listener = [[CSGEventListener alloc] initWithURL:consoleBase + "/event_stream" eventType:"console" dataFormat:CSGJSONDataFormat];
        // [listener setDelegate:self];
        // [listener startListening];
    }
    return self;
}

//
// EventListener delegate methods
//
- (void)eventWithData:(id)data sender:(CSGEventListener)sender
{
    [self willChangeValueForKey:"items"];
    if (items.length == maxItems) {
        // Drop oldest item...
        items.shift();
    }
    items.push(JSON.parse(data).msg);
    [self didChangeValueForKey:"items"];
}

- (void)setMaxItems:(int)n
{
    if (n < maxItems) {
        [self setItems: items.slice(-n)];
    }
    maxItems = n;
}

@end
