@import <Foundation/Foundation.j>

@import "CSGProgram.j"
@import "CSGBackend.j"
@import "CSGScriptViewer.j"
@import "CSGAppUIViewer.j"
@import "CSGEventListener.j"


@implementation CSGProject : CPObject <CPCoding>
{
    CSGProgram program @accessors();
    CPString name @accessors();
    CPString appID @accessors();
    BOOL isUntitled @accessors();

    BOOL showUIView @accessors();
    CSGAppUIViewer appUIViewer;
    CSGEventListener eventListener;
    JSObject uiDefinitions @accessors();
    CPTimer uiTimer;
}

- (id)initWithName:(CPString)projectName
{
    if (self = [super init]) {
        name = projectName;
        program = [[CSGProgram alloc] init];
        appID = nil;
        isUntitled = YES;
        uiDefinitions = {};
        [self setShowUIView:YES];
    }
    return self;
}

//
// Implement CPCoding protocol for serialization
//
- (id)initWithCoder:(CPCoder)coder
{
    self = [super initWithName:"_DUMMY_"];
    if (self) {
        program =   [coder decodeObjectForKey:@"program"];
        name = [coder decodeObjectForKey:@"name"];
        isUntitled = [coder decodeBoolForKey:@"isUntitled"];
        appID = nil;
    }
    return self;
}

- (void)encodeWithCoder:(CPCoder)coder
{
    [coder encodeObject:program forKey:@"program"];
    [coder encodeObject:name forKey:@"name"];
    [coder encodeBool:isUntitled forKey:@"isUntitled"];
}

- (void)setErrors:(id)errors andWarnings:(id)warnings
{
    errors.forEach(function(error, i, list){
        list[i] = (i+1) + " : " + error.reason;
    });
    warnings.forEach(function(warning, i, list){
        list[i] =  (i+1) + " : " + warning.reason;
    });
    var errorViewer = [[CSGScriptViewer alloc] init];
    var errorText = [errors componentsJoinedByString: "\n"];
    var warningText = [warnings componentsJoinedByString: "\n"];
    var text = [["Errors:", errorText, "", "Warnings:", warningText] componentsJoinedByString: "\n"];
    [errorViewer setTitle:"Errors and Warnings"];
    [errorViewer setScript:text];
    [errorViewer setReleasedWhenClosed:YES];
}

- (BOOL)isRunning
{
    return (appID !== nil);
}

- (void)run
{
    if ([self isRunning]) {
        return;
    }
    var backend = [CSGBackend sharedBackend];
    var script = [program scriptRepresentation];
    [backend deployScript:script withName:name responseBlock:function(response){
        var app_id = response.application_id;
        if (app_id === undefined) {
            [self setErrors:response.errors andWarnings:response.warnings];
        } else {
            [backend infoForAppID:app_id usingBlock:function(info){
                [self setRuntimeInfo:info];
                [self setAppID:app_id]; // Do this AFTER updating info since it triggers view updates
                [self startUI];
            }];
        }
    }];
}

- (void)stop
{
    if (![self isRunning]) {
        return;
    }
    var backend = [CSGBackend sharedBackend];
    [backend stopAppWithID:appID responseBlock:function(){
        [self stopUI];
        [[program actors] setValue:nil forKey:@"identifier"];
        [[program actors] setValue:nil forKey:@"nodeName"];
        [self setAppID:nil]; // Do this AFTER updating info since it triggers view updates
    }];
}

- (void)startUI
{
    var backend = [CSGBackend sharedBackend];
    [backend getUIDefinitions:appID responseBlock:function(defs){
        uiDefinitions = defs;
        if (uiDefinitions && [self hasUIActors]) {
            appUIViewer = [[CSGAppUIViewer alloc] initWithProject:self];
            [self addUIEventListener];
            [self showUI];
        }
    }];
}

- (void)addUIEventListener
{
    var HAS_NGINX_REWRITE = NO;

    var host = [[CSGHostConfig sharedHostConfig] calvinHost];
    var containerID = [[CSGHostConfig sharedHostConfig] containerID];
    var url = "";
    if (containerID !== "") {
        if (HAS_NGINX_REWRITE) {
            url = "http://" + host + ":7777/" + containerID + "/client_id/" + appID;
        } else {
            // FIXME: Temporary while debugging without nginx rewrite
            url = "http://" + host + ":5000/event_stream/" + containerID + "/client_id/" + appID;
        }
    } else {
        url = "http://" + host + ":7777/client_id/" + appID;
    }
    console.log("Adding eventlistener:", url);
    eventListener = [[CSGEventListener alloc] initWithURL:url eventType:"message" dataFormat:CSGJSONStringDataFormat];
    [eventListener setDelegate:appUIViewer];
    [eventListener startListening];
}

- (void)stopUI
{
    [self hideUI];
    [eventListener stopListening];
    [appUIViewer close];
    uiDefinitions = {};
    appUIViewer = nil;
}

- (BOOL)hasUIActors
{
    return [self uiActors].length > 0;
}

- (CPArray)uiActors
{
    var ui_actors = [];
    var actors = [program actors];
    for (var i=0; i<actors.length; i++) {
        var actor = actors[i];
        if (uiDefinitions[actor.type]) {
            ui_actors.push(actor);
        }
    }
    return ui_actors;
}

- (void)startUITimer
{
    if (!uiTimer || ![uiTimer isValid]) {
        uiTimer = [CPTimer scheduledTimerWithTimeInterval:1 callback:function() {[self updateUIVisibility];} repeats:YES];
    }
}

- (void)stopUITimer
{
    if (uiTimer && [uiTimer isValid]) {
        [uiTimer invalidate];
    }
}

- (void)updateUIVisibility
{
    [[CSGBackend sharedBackend] actorsOnUIRuntime:function(list){
        // Propagate the list of actors present on this runtime down the line.
        [appUIViewer updateVisibility:list];
    }];
}

- (void)setRuntimeInfo:(JSObject)rti
{
    if (!rti) {
        return;
    }
    var actor_ids = rti.actors;
    var namespace = rti.ns;
    var name_map = [CPDictionary dictionaryWithJSObject:rti.actors_name_map];
    var actors = [program actors];
    for (var i=0; i<actors.length; i++) {
        var actor = actors[i];
        var qualified_name = namespace + ":" + actor.name;
        var id = [name_map allKeysForObject:qualified_name][0];
        [actor setIdentifier:id];
    }
}

- (void)setShowUIView:(BOOL)flag
{
    if (flag === showUIView) {
        return;
    }
    showUIView = flag;
    if (showUIView) {
        [self showUI];
    } else {
        [self hideUI];
    }
}

- (void)showUI
{
    if (appUIViewer && showUIView) {
        [self startUITimer];
        [appUIViewer showWindow:self];
    }
}

- (void)hideUI
{
    if (appUIViewer) {
        [[appUIViewer window] orderOut:self];
        [self stopUITimer];
    }
}


// Switching to this project
- (void)activate
{
    [self showUI];
}

// Switching to another project
- (void)deactivate
{
    [self hideUI];
}


@end