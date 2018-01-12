@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@import "CSGComponent.j"
@import "CSGActor.j"
@import "CSGConnection.j"
@import "CSGBackend.j"


@implementation CSGRuntimeInspector : CPViewController
{
    CSGComponent component; // Component to inspect.
    // id delegate; // delegate is CSGBackend
    @outlet CPArray ports @accessors;
    // Inspector view items
    @outlet CPTextField panelNameField;
    @outlet CPTextField panelTypeField;
    CPMutableDictionary runtimeDict;
    CPArray runtimeList;
    CSGBackend backend;
}

- (id)init
{
    self = [super initWithCibName:"RuntimeInspectorView" bundle:nil externalNameTable:nil];
    if (self) {
        backend = [CSGBackend sharedBackend];
        [[self view] setHidden:YES];
        runtimeList = [];
        runtimeDict = @{};
        [backend getRuntimeInfoResponseBlock:function(dict){
            [self setRuntimeDict:dict];
        }];

    }
    return self;
}

- (void) setRuntimeDict:(id)dict
{
    var names = [dict allKeys];
    names.sort();
    self.runtimeDict = dict;
    [self setRuntimeList:names];
}

- (CPDictionary) runtimeDict
{
    return self.runtimeDict;
}

- (void) setRuntimeList:(id)list
{
    self.runtimeList = list;
}

- (CPArray) runtimeList
{
    return self.runtimeList;
}

- (void)observeValueForKeyPath:(CPString)keyPath
                      ofObject:(id)object
                        change:(CPDictionary)change
                       context:(id)context
{
    // console.log("CSGRuntimeInspector:observeValueForKeyPath");
    var newSel = [change objectForKey:"CPKeyValueChangeNewKey"];
    [self setComponent:newSel];

    [backend getRuntimeInfoResponseBlock:function(dict){
        [self setRuntimeDict:dict];
    }];
}

- (void)setComponent:(CGSComponent)comp
{
    //console.log("CSGRuntimeInspector:setComponent");
    self.component = comp;
    if ([comp isKindOfClass:[CSGActor class]]) {
        // console.log("actor identifier", [comp identifier]);
        [[self view] setHidden:NO];
        [panelNameField setStringValue:comp.name];
        [panelTypeField setStringValue:comp.type];
        // [panelDocField setStringValue:comp.docs];
        [backend infoForActorID:[comp identifier] withResponseBlock:function(info){
            [self setActorInfo:info];
        }];
    } else {
        [[self view] setHidden:YES];
    }
}

- (void)setActorInfo:(JSObject)info
{
    // console.log("CSGRuntimeInspector:setActorInfo", info);
    if (info.is_shadow === undefined) {
        [component setStatus:"Undefined"];
    } else {
        [component setStatus:info.is_shadow ? "Shadow" : "Running"];
    }
    // [component setNodeID:info.node_id.slice(0, 8)];
    var tmpPorts = [];
    var inports = info.inports;
    for (var i=0; i<inports.length; i++) {
        var port = [CPMutableDictionary dictionaryWithJSObject:inports[i]];
        [port setValue:"in" forKey:"direction"];
        [port setValue:0 forKey:"tokenCount"];
        [tmpPorts addObject:port];
        // [delegate infoForNode:info.node_id actor:[component identifier] port:[port valueForKey:"id"] sender:self];
        var port_id = [port valueForKey:"id"];
        [backend infoForNode:info.node_id actor:[component identifier] port:port_id responseBlock:function(info) {
            [self setPort:port_id info:info];
        }];
    }
    var outports = info.outports;
    for (var i=0; i<outports.length; i++) {
        var port = [CPMutableDictionary dictionaryWithJSObject:outports[i]];
        [port setValue:"out" forKey:"direction"];
        [port setValue:0 forKey:"tokenCount"];
        [tmpPorts addObject:port];
        // [delegate infoForNode:info.node_id actor:[component identifier] port:[port valueForKey:"id"] sender:self];
        var port_id = [port valueForKey:"id"];
        [backend infoForNode:info.node_id actor:[component identifier] port:port_id responseBlock:function(info) {
            [self setPort:port_id info:info];
        }];
    }
    [self setPorts:tmpPorts];
    // console.log([self ports]);
}

- (void)setPort:(CPString)portID info:(JSObject)info
{
    //console.log("CSGRuntimeInspector:setPort");
    [self willChangeValueForKey:"ports"];
    // console.log("willChangeValueForKey", portID, info);
    var wpos = info.write_pos; // Integer
    var rpos_object = info.read_pos; // Object
    var rpos_list = [];
    for (var property in rpos_object) {
        if (rpos_object.hasOwnProperty(property)) {
            [rpos_list addObject:rpos_object[property]];
            // console.log(property, jsobject[property]);
        }
    }
    var rpos = Math.min.apply(null, rpos_list);
    // Find the right port to change
    for (var i=0; i<ports.length; i++) {
        var port = ports[i];
        if ([port valueForKey:"id"] === portID) {
            [port setValue:(wpos - rpos) forKey:"tokenCount"];
            break;
        }
    }
    [self didChangeValueForKey:"ports"];
}

- (@action)migrate:(id)sender
{
    var selection = [[sender selectedItem] title];
    var rtID = [runtimeDict valueForKey:selection];
    [backend migrateActor:component toNode:rtID];
}

@end
