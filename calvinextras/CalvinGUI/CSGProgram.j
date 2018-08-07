@import <Foundation/Foundation.j>

@import "CSGConnection.j"
@class CSGActor;
@class CSGComponent;


@implementation CSGProgram : CPObject <CPCoding>
{
    CPMutableArray instances @accessors(getter=actors, readonly);
    CPMutableArray connections;
    int _counter;
    CPString name @accessors;
}

- (id)init
{
    self = [super init];
    if (self) {
        instances = [];
        connections = [];
        _counter = 0;
        var fmt = [[CPDateFormatter alloc] initWithDateFormat:"yyMMddHHmmss" allowNaturalLanguage:NO];
        name = [fmt stringFromDate:[CPDate date]];
    }
    return self;
}

//
// Implement CPCoding protocol for serialization
//
- (id)initWithCoder:(CPCoder)coder
{
    self = [super init];
    if (self) {
        instances =   [coder decodeObjectForKey:@"instances"];
        connections = [coder decodeObjectForKey:@"connections"];
        _counter =    [coder decodeIntForKey:@"counter"];
    }
    return self;
}

- (void)encodeWithCoder:(CPCoder)coder
{
    [coder encodeObject:instances forKey:@"instances"];
    [coder encodeObject:connections forKey:@"connections"];
    [coder encodeInt:_counter forKey:@"counter"];
}

//
// CSGProgram methods
//
- (void)addInstance:(CSGActor)actor
{
    // Create a default name
    [self willChangeValueForKey:@"instances"];
    var typeParts = [actor.type componentsSeparatedByString:"."],
        tmpName = [typeParts[typeParts.length - 1] lowercaseString];
    actor.name = [CPString stringWithFormat:"%@%d", tmpName, ++_counter];
    [instances insertObject:actor atIndex:0];
    [self didChangeValueForKey:@"instances"];
}

- (BOOL)isValidActorName:(CPString)actorName
{
    var syntax_ok = /^[a-z][a-z0-9_]*$/i.test(actorName);
    if (!syntax_ok) {
        return NO;
    }
    for (var i=0; i<instances.length; i++) {
        if (actorName === instances[i].name) {
            return NO;
        }
    }
    return YES;
}

- (BOOL)addConnectionFrom:(CSGActor)fromActor fromPort:(CSGPort)fromPort to:(CSGActor)toActor toPort:(CSGPort)toPort
{
    // Sanity check that we have an in- and an outport
    if ([fromPort isInport] === [toPort isInport]) {
         return false;
    }
    var conn;
    if ([fromPort isInport]) {
        conn = [[CSGConnection alloc] initWithSrc:toActor srcPort:toPort dst:fromActor dstPort:fromPort];
    } else {
        conn = [[CSGConnection alloc] initWithSrc:fromActor srcPort:fromPort dst:toActor dstPort:toPort];
    }
    // Prevent multiple identical connections and fan-in
    for (var i=0; i<connections.length; i++) {
        var present = connections[i];
        if ([conn isEqualToConnection:present] || [conn hasSameDestinationPortAsConnection:present]) {
            return false;
        }
    }
    [connections addObject:conn];
    return true;
}

- (CSGConnection)connectionForActor:(CSGActor)actor inport:(CSGPort)port
{
    for (var i=0; i<connections.length; i++) {
        if ([connections[i] isConnectedToActor:actor inport:port]) {
            return connections[i];
        }
    }
    return nil;
}

- (CPArray)connectionsForActor:(CSGActor)actor outport:(CSGPort)port
{
    var conns = [CPMutableArray array];
    for (var i=0; i<connections.length; i++) {
        if ([connections[i] isConnectedToActor:actor outport:port]) {
            [conns addObject:connections[i]];
        }
    }
    return conns;
}


- (void)removeComponent:(CSGComponent)comp
{
    if (comp === nil) {
        return;
    }
    if ([comp isKindOfClass:[CSGActor class]]) {
        // Remove actor, but firs remove connections to/from it
        var index = connections.length;
        while (index--) {
            if ([connections[index] isConnectedToActor:comp]) {
                [connections removeObjectAtIndex:index];
            }
        }
        [self willChangeValueForKey:@"instances"];
        [instances removeObject:comp];
        [self didChangeValueForKey:@"instances"];
    } else if ([comp isKindOfClass:[CSGConnection class]]) {
        [connections removeObject:comp]
    } else {
        console.log("Can't remove component", comp);
    }
}


// - (void)makeFront:(CSGComponent)comp;

- (CPString)scriptRepresentation
{
    var reps = [CPMutableArray array];
    for (var i=0; i<instances.length; i++) {
        [reps addObject:[instances[i] scriptRepresentation]];
    }
    [reps addObject:@""];
    for (var i=0; i<connections.length; i++) {
        [reps addObject:[connections[i] scriptRepresentation]];
    }
    var script = [reps componentsJoinedByString: "\n"];
    return script;
}
@end
