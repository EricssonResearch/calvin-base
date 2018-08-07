@import <Foundation/Foundation.j>
@import "CSGComponent.j"
@import "CSGPort.j"

function CSGActorDocsFromJSONRep(jrep)
{
    // FIXME: Modules have documentation, but name is ""
    if (!jrep) {
        return [CPString stringWithFormat:"No documentation"];
    }
    if (!jrep.name) {
        return [CPString stringWithFormat:"%@\n", jrep["long_desc"]];
    }
    var docs = [CPString stringWithFormat:"%@.%@\n\n%@\n", jrep["ns"], jrep["name"], jrep["long_desc"]],
        ports = jrep["inputs"];
    if (ports.length > 0) {
        docs = [docs stringByAppendingString:"\nInports:\n"];
    }
    for (var i=0; i<ports.length; i++) {
        var pstring = [CPString stringWithFormat:"\t%s : %s\n", ports[i], jrep.input_docs[ports[i]]];
        docs = [docs stringByAppendingString:pstring];
    }
    ports = jrep["outputs"]
    if (ports.length > 0) {
        docs = [docs stringByAppendingString:"\nOutports:\n"];
    }
    for (var i=0; i<ports.length; i++) {
        var pstring = [CPString stringWithFormat:"\t%s : %s\n", ports[i], jrep.output_docs[ports[i]]];
        docs = [docs stringByAppendingString:pstring];
    }
    var reqs = jrep["requires"] || [];
    if (reqs.length > 0) {
        docs = [docs stringByAppendingString:"\nRequirements:\n\t" + reqs.join(", ")];
    }
    return docs;
}

// FIXME: Constrain accessors
@implementation CSGActor : CSGComponent <CPCoding>
{
    CPMutableDictionary mandatoryArgs @accessors;
    CPMutableDictionary argOK         @accessors;
    CPMutableDictionary optionalArgs  @accessors;
    CPArray inports                   @accessors;
    CPArray outports                  @accessors;
    CPString type                     @accessors;
    CPString name                     @accessors;
    BOOL isComponent                  @accessors;
    CPString docs                     @accessors(readonly);
    // Private
    CGRect bounds;
    BOOL validBounds;
    CPString identifier               @accessors;
    CPString status                   @accessors;
    CPString nodeID                   @accessors;
    CPString nodeName                 @accessors;
    CPString uiState                  @accessors;
}

- (id)initWithJSObject:(Object)jrep
{
    self = [super init];
    if (self) {
        // Fill in the CSGActor members
        // Mandatory args, using CPNull as placeholder for arg
        mandatoryArgs = [CPMutableDictionary dictionary];
        var keys = jrep["args"]["mandatory"];
        for (var i=0; i<keys.length; i++) {
            [mandatoryArgs setObject:"" forKey:keys[i]];
        }
        // Optional args
        var proto = jrep["args"]["optional"];
        keys = Object.keys(proto);
        optionalArgs = [CPMutableDictionary dictionary];
        for (var i=0; i<keys.length; i++) {
            var key = keys[i];
            var arg = JSON.stringify(proto[key]);
            [optionalArgs setObject:arg forKey:key];
        }
        // Input ports
        inports = [CPMutableArray array];
        proto = jrep["inputs"];
        for (var i=0; i<proto.length; i++) {
            var pname = proto[i];
            [inports addObject:[CSGPort inportWithName:pname]];
        }
        // Output ports
        outports = [CPMutableArray array];
        proto = jrep["outputs"];
        for (var i=0; i<proto.length; i++) {
            var pname = proto[i];
            [outports addObject:[CSGPort outportWithName:pname]];
        }
        // Actor type
        type = [CPString stringWithFormat:"%@.%@", jrep["ns"], jrep["name"]];
        // Actor name
        name = @"prototype";
        // Kind
        isComponent = !["actor" isEqualToString:jrep["type"]];
        // Docs
        docs = CSGActorDocsFromJSONRep(jrep);
        // Bounds
        bounds = CPMakeRect(0,0,0,0);
        validBounds = NO;
        // Check validity of arguments
        argOK = @{};
        [self validateAll:mandatoryArgs];
        [self validateAll:optionalArgs];
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
        mandatoryArgs = [coder decodeObjectForKey:@"mandatoryArgs"];
        optionalArgs  = [coder decodeObjectForKey:@"optionalArgs"];
        inports       = [coder decodeObjectForKey:@"inports"];
        outports      = [coder decodeObjectForKey:@"outports"];
        type          = [coder decodeObjectForKey:@"type"];
        name          = [coder decodeObjectForKey:@"name"];
        isComponent   = [coder decodeBoolForKey:@"isComponent"];
        docs          = [coder decodeObjectForKey:@"docs"];
        // Bounds contains origin of actor as positioned by user,
        // but the visual parts need to be recreated so we do NOT
        // serialize validBounds forcing them to be recreated.
        bounds        = [coder decodeRectForKey:@"bounds"];
        validBounds = NO;
        // Recreate arg validity (not stored)
        argOK = @{};
        [self validateAll:mandatoryArgs];
        [self validateAll:optionalArgs];
    }
    return self;
}

- (void)encodeWithCoder:(CPCoder)coder
{
    [coder encodeObject:mandatoryArgs forKey:@"mandatoryArgs"];
    [coder encodeObject:optionalArgs forKey:@"optionalArgs"];
    [coder encodeObject:inports forKey:@"inports"];
    [coder encodeObject:outports forKey:@"outports"];
    [coder encodeObject:type forKey:@"type"];
    [coder encodeObject:name forKey:@"name"];
    [coder encodeBool:isComponent forKey:@"isComponent"];
    [coder encodeObject:docs forKey:@"docs"];
    // Bounds contains origin of actor as positioned by user,
    // but the visual parts need to be recreated so we do NOT
    // serialize validBounds forcing them to be recreated.
    [coder encodeRect:bounds forKey:@"bounds"];
}

//
// CSGActor methods
//
- (BOOL)hasValidMandatoryArgs
{
    var ok_list = [argOK allValues];
    for (var i=0; i<ok_list.length; i++) {
        if (!ok_list[i]) {
            return NO;
        }
    }
    return YES;
}

- (BOOl)isValidArg:(CPString)arg
{
    // Argument is a string with potentially valid JSON
    try {
        var json_value = JSON.parse(arg);
    }
    catch(e) {
        // Do not accept bad argument, but don't remove it either.
        // console.log("ERROR: controlTextDidEndEditing:", e);
        return NO;
    }
    // If we get here, the entered value was as string representation of a
    // valid JSON construct. Without type information, we can't do more.
    return YES;
}

- (void)validateAll:(CPDictionary)argDict
{
    var keys = [argDict allKeys];
    keys.forEach(function(key){
        [self validate:argDict forKey:key];
    });
}

- (void)validate:(CPDictionary)argDict forKey:(CPString)key
{
    var value = [argDict valueForKey:key];
    var isValid = [self isValidArg:value];
    [argOK setValue:isValid forKey:key];
}

- (void)setMandatoryValue:(id)value forKey:(CPString)key
{
    [mandatoryArgs setValue:value forKey:key];
    [self validate:mandatoryArgs forKey:key];
}

- (void)setOptionalValue:(id)value forKey:(CPString)key
{
    [optionalArgs setValue:value forKey:key];
    [self validate:optionalArgs forKey:key];
}

// FIXME: move origin/size accessors to Rendering category
- (CGPoint)origin
{
    return bounds.origin;
}

- (void)setOrigin:(CGPoint)origin
{
    bounds.origin = origin;
}

// FIXME: Replace size/setSize with width and height
- (CGSize)size
{
    return bounds.size;
}

- (void)setSize:(CGSize)size
{
    bounds.size = size;
}

- (CSGPort)inportWithName:(CPString)aName
{
    return [self portWithName:aName isOutport:NO];
}

- (CSGPort)outportWithName:(CPString)aName
{
    return [self portWithName:aName isOutport:YES];
}

- (CSGPort)portWithName:(CPString)aName isOutport:(BOOL)isOutport
{
    var ports = isOutport ? outports : inports;
    for (var i=0; i<ports.length; i++) {
        var port = ports[i];
        if ([port name] === aName) {
            return port;
        }
    }
    return [CPNull null];
}


- (CPString)scriptRepresentation
{
    function formatArg(key, value) {
        return [CPString stringWithFormat:@"%@=%@", key, value];
    }
    var args = [[CPMutableArray alloc] init],
        keys = [[mandatoryArgs allKeys] sortedArrayUsingSelector: @selector(caseInsensitiveCompare:)],
        optKeys = [[optionalArgs allKeys] sortedArrayUsingSelector: @selector(caseInsensitiveCompare:)];
    // Mandatory arguments
    for (var i=0; i<keys.length; i++) {
        var key = keys[i];
        var validArg = [argOK valueForKey:key];
        if (validArg) {
            [args addObject:formatArg(key, [mandatoryArgs valueForKey:key])];
        }
    }
    // Optional arguments
    for (var i=0; i<optKeys.length; i++) {
        var key = optKeys[i];
        [args addObject:formatArg(key, [optionalArgs valueForKey:key])];
    }
    var argRep = [args componentsJoinedByString:@", "];
    return [CPString stringWithFormat:@"%@ : %@(%@)", name, type, argRep];
}

@end
