@import <Foundation/Foundation.j>

@import "CSGComponent.j"
@import "CSGPort.j"

@class CSGActor;

@implementation CSGConnection : CSGComponent <CPCoding>
{
    CSGActor src       @accessors(getter=srcActor);
    CSGActor dst;
    CSGPort srcPort   @accessors(getter=srcPort);
    CSGPort dstPort;
}

- (id)initWithSrc:(CSGActor)theSrcActor srcPort:(CSGPort)theSrcPort dst:(CSGActor)theDstActor dstPort:(CSGPort)theDstPort
{
    if (self = [super init]) {
        src = theSrcActor;
        dst = theDstActor;
        srcPort = theSrcPort;
        dstPort = theDstPort;
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
        src =     [coder decodeObjectForKey:@"src"];
        dst =     [coder decodeObjectForKey:@"dst"];
        srcPort = [coder decodeObjectForKey:@"srcPort"];
        dstPort = [coder decodeObjectForKey:@"dstPort"];
    }
    return self;
}

- (void)encodeWithCoder:(CPCoder)coder
{
    [coder encodeObject:src forKey:@"src"];
    [coder encodeObject:dst forKey:@"dst"];
    [coder encodeObject:srcPort forKey:@"srcPort"];
    [coder encodeObject:dstPort forKey:@"dstPort"];
}

//
// CSGConnection methods
//
- (BOOL)isEqualToConnection:(CSGConnection)connection
{
    if (!connection) {
        return NO;
    }
    if (![src isEqual:connection.src] || ![dst isEqual:connection.dst]) {
        return NO;
    }
    if ((srcPort !== connection.srcPort) || (dstPort !== connection.dstPort)) {
        return NO;
    }
    return YES;
}

- (BOOL)isEqual:(id)object
{
    if (self === object) {
        return YES;
    }
    if (![object isKindOfClass:[CSGConnection class]]) {
        return NO;
    }
    return [self isEqualToConnection:object];
}

- (BOOL)hasSameDestinationPortAsConnection:(CSGConnection)conn
{
    return conn.dst === dst && conn.dstPort === dstPort;
}

- (BOOL)isConnectedToActor:(CSGActor)actor
{
    return src === actor || dst === actor;
}

- (BOOL)isConnectedToActor:(CSGActor)actor inport:(CSGPort)port
{
    return dst === actor && dstPort === port;
}

- (BOOL)isConnectedToActor:(CSGActor)actor outport:(CSGPort)port
{
    return src === actor && srcPort === port;
}

- (CPString)description
{
    return [CPString stringWithFormat:@"%@:%@ -> %@:%@", src, srcPort, dst, dstPort];
}

- (CPString)scriptRepresentation
{
    var line = [CPString stringWithFormat:@"%@.%@ > %@.%@", [src name], [srcPort name], [dst name], [dstPort name]];
    return line;
}

@end
