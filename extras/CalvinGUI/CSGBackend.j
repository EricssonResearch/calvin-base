@import <Foundation/Foundation.j>
@import "CSGHostConfig.j"

//
// Subclass CPURLConnection to override some of its behaviors (_isLocalFileConnection)
// Provides better handling of mapping responses to the original caller
//
@implementation CSGURLConnection : CPURLConnection
{
    CPDictionary header;
    Function responseHandler;
}

// Designated initializer
- (id)initWithRequest:(CPURLRequest)aRequest responseBlock:(Function /* ((CPDictionary)header, (CPString)body, (CPError)error) */)aFunction
{
    self = [super initWithRequest:aRequest delegate:self startImmediately:NO];

    if (self) {
        _isLocalFileConnection = NO;
        responseHandler = aFunction;
        [self start];
    }
    return self;
}

+ (CSGURLConnection)connectionWithRequest:(CPURLRequest)aRequest responseBlock:(Function /* ((CPDictionary)header, (CPString)body, (CPError)error) */)aFunction
{
    return [[self alloc] initWithRequest:aRequest responseBlock:aFunction];
}

//
// CPConnection delegate methods. Will accumulate information that will be sent to handler
//
- (void)connection:(CSGURLConnection)connection didReceiveData:(CPString)data
{
    responseHandler(header, data, nil);
}

- (void)connection:(CSGURLConnection)connection didFailWithError:(CPError)error
{
    responseHandler(header, nil, error);
}

- (void)connection:(CSGURLConnection)connection didReceiveResponse:(CPURLResponse)response
{
    if ([response isKindOfClass:[CPHTTPURLResponse class]]) {
        header = [response allHeaderFields];
    }
}

@end

//
// This is the backend providing an interface towards a number of REST services for
// documentation, runtime control, project storage, and authentication.
//

// Singleton instance
var sharedBackendInstance = nil;

@implementation CSGBackend : CPObject
{
    CSGHostConfig config;
}

+ (id)sharedBackend
{
    if (!sharedBackendInstance)
    {
        sharedBackendInstance = [[CSGBackend alloc] _init];
    }
    return sharedBackendInstance;
}

- (id)init
{
    [CPException raise:@"CSGHostConfig" reason:@"Singleton. Use +sharedHostConfig"];
}

- (id)_init
{
    if (self = [super init])
    {
        config = [CSGHostConfig sharedHostConfig];
    }
    return self;
}

//
// UI device interaction
//
- (void)generateEventForActor:(CPString)actorID withData:(JSObject)data
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/uicalvinsys"],
        body = {"client_id": actorID, "state": data};
    [request setHTTPMethod:@"POST"];
    [request setValue:"application/json" forHTTPHeaderField:"Content-Type"];
    [request setHTTPBody:[CPString JSONFromObject:body]];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        if (error !== nil) {
            console.log("Error sending update event", error);
            return;
        }
    }];
}

- (void)getUIDefinitions:(CPString)appID responseBlock:(Function /* defs */)responseBlock
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/uicalvinsys/" + appID];
    var req = [CSGURLConnection connectionWithRequest:request responseBlock:function(header, body, error) {
        var defs = [body objectFromJSON];
        responseBlock(defs);
    }];
}

//
// Runtime information
//
- (void)getRuntimeCapabilitiesResponseBlock:(Function /* runtime_caps */)responseBlock
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/index/node/attribute/node_name"];
    var req = [CSGURLConnection connectionWithRequest:request responseBlock:function(header, body, error) {
        var response = [body objectFromJSON];
        var runtimeList = response.result;
        var capabilities = @{}

        runtimeList.forEach(
            function(rtID) {
                [self _namedRuntime:rtID action:function(name, url) {
                    var info = @{"id":rtID, "url":url, "capabilities":[]};
                    [capabilities setValue:info forKey:name];
                    var request = [CPURLRequest requestWithURL:url + "/capabilities"];
                    var req = [CSGURLConnection connectionWithRequest:request responseBlock:function(header, body, error) {
                        [info setValue:[body objectFromJSON] forKey:"capabilities"];
                        responseBlock(capabilities);
                    }];
                }];
            })
        }];
}

- (void)getRuntimeInfoResponseBlock:(Function /* runtime_name */)responseBlock
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/index/node/attribute/node_name"];
    var req = [CSGURLConnection connectionWithRequest:request responseBlock:function(header, body, error) {
        var response = [body objectFromJSON];
        var runtimeList = response.result;
        var runtimeNameAndID = @{}

        runtimeList.forEach(
            function(rtID) {
                [self _namedRuntime:rtID action:function(name, url) {
                    [runtimeNameAndID setValue:rtID forKey:name];
                    responseBlock(runtimeNameAndID);
                }];
            })
        }];
}

- (void)_namedRuntime:(CPString)rtID action:(Function /* runtime_name */)action
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/node/" + rtID];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        var shield = "[" + body + "]";
        var jsObject = [shield objectFromJSON];
        if (jsObject.length === 0) {
            console.log("-_namedRuntime:action: - Empty body returned, BAILING!");
            return;
        } else {
            // console.log("_namedRuntime:jsObject:", jsObject);
            var attrs = jsObject[0].attributes.indexed_public;
            var re = /\/node\/attribute\/node_name\/[A-Za-z0-9_\-\.\/]*\/([A-Za-z0-9_-]+)/;
            for (var i=0; i<attrs.length; i++) {
                var m = attrs[i].match(re);
                if (m) {
                    action(m[1], jsObject[0].control_uris);
                }
            }
        }
    }];
}

//
// Get authentication token from auth server
//
- (void)authenticatePersistanceUser:(CPString)user withPassword:(CPString)passwd responseBlock:(Function /* (CPString)token */ )responseBlock
{
    var request = [CPURLRequest requestWithURL:[config authBase] + "/token"],
        body = {"username": user, "password": passwd};
    [request setHTTPMethod:@"POST"];
    [request setValue:"application/json" forHTTPHeaderField:"Content-Type"];
    [request setHTTPBody:[CPString JSONFromObject:body]];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        if (error !== nil) {
            console.log("Error authenticating", error);
            return;
        }
        // [sender persistanceUserAuthenticated:body];
        responseBlock(body);
    }];
}

//
// Generic persistance methods
//
- (void)storeValue:(id)value forKey:(CPString)key authToken:(CPString)authToken
{
    var dataString = [[CPKeyedArchiver archivedDataWithRootObject:value] rawString];
    var request = [CPURLRequest requestWithURL:[config persistanceBase] + "/store/" + key];
    [request setHTTPMethod:@"POST"];
    [request setValue:"application/json" forHTTPHeaderField:"Content-Type"];
    var body = {"token": authToken, "data":dataString};
    [request setHTTPBody:[CPString JSONFromObject:body]];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        if (error !== nil) {
            console.log("Error saving", error);
            return;
        }
        console.log("saveHandler - save complete");
    }];
}

- (void)fetchValueForKey:(CPString)key responseBlock:(Function /* (id)value */)responseBlock
{
    var request = [CPURLRequest requestWithURL:[config persistanceBase] + "/fetch/" + key];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        if (error !== nil) {
            console.log("Error loading", error);
            return;
        }
        responseBlock([CPKeyedUnarchiver unarchiveObjectWithData:[CPData dataWithRawString:body]]);
    }];
}

- (void)fetchAllKeysUsingResponseBlock:(Function /* (CPArray)keys */)responseBlock
{
    var request = [CPURLRequest requestWithURL:[config persistanceBase] + "/fetch/"];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        if (error !== nil) {
            console.log("Error loading", error);
            return;
        }
        responseBlock([body componentsSeparatedByString:"\n"]);
    }];
}

//
// Request actor documentation
//
- (void)docFor:(CPString)what responseBlock:(Function /* ((JSObject)body) */)responseBlock
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/actor_doc/" + what];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        if (error !== nil) {
            console.log("Error getting docs", error);
            return;
        }
        responseBlock([body objectFromJSON]);
    }];
}

//
// Start/stop script
//
- (void)deployScript:(CPString)script withName:(CPString)name responseBlock:(Function /* (JSObject)response */)responseBlock
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/deploy"];
    [request setHTTPMethod:@"POST"];
    [request setHTTPBody:[CPString JSONFromObject:{"name":name, "script":script}]];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        if (error !== nil) {
            console.log("Error deploying script", error);
            return;
        }
        var response = [body objectFromJSON];
        responseBlock(response);
    }];
}

- (void)stopAppWithID:(CPString)appID responseBlock:(Function /* ((CPString)appID) */)responseBlock
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/application/" + appID];
    [request setHTTPMethod:@"DELETE"];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        if (error !== nil) {
            console.log("Error stopping script", error);
            return;
        }
        responseBlock();
    }];
}

// FIXME: Update
- (void)setDeployInfo:(CPString)deployInfo forAppID:(CPString)appID sender:(id)sender
{
    // POST /application/{application-id}/migrate
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/application/" + appID + "/migrate"];
    [request setHTTPMethod:@"POST"];
    [request setHTTPBody:deployInfo];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        if (error !== nil) {
            console.log("Error sending deploy info", error);
            return;
        }
        // var response = [body objectFromJSON];
        setTimeout(function () {
            [sender updateActorViewForApp:appID reason:"migrate"];
        }, 2000);
    }];
}

//
// Runtime queries
//
- (void)updateAvailableApplicationsUsingBlock:(Function)block
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/applications"];
    var req = [CSGURLConnection connectionWithRequest:request responseBlock:function(header, body, error) {
        var data = [body objectFromJSON];
        block(data);
    }];
}

- (void)infoForAppID:(CPString)appid usingBlock:(Function)block
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/application/" + appid];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        var data = [body objectFromJSON];
        block(data);
    }];

}

- (void)infoForActorID:(CPString)actorID withResponseBlock:(Function)block
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/actor/" + actorID];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        var shield = "[" + body + "]";
        var jsObject = [shield objectFromJSON];
        if (jsObject.length === 0) {
            console.log("-infoForActorID:withResponseBlock: - Empty body returned, BAILING!");
            return;
        } else {
            block(jsObject[0]);
        }
    }];
}

- (void)infoForNode:(CPString)nodeID actor:(CPString)actorID port:(CPString)portID responseBlock:(Function /* (info) */)responseBlock
{
    if (actorID === nil || portID === nil) {
        return;
    }
    [self getControlURI_OfNodeId:nodeID withResponseBlock:function(url) {
            var request = [CPURLRequest requestWithURL:url + "/actor/" + actorID + "/port/" + portID + "/state"];
            // Nested request
            [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
                    // [sender setPort:portID info:[body objectFromJSON]];
                    responseBlock([body objectFromJSON]);
                }];
        }];
}

- (void)setNodeNameForActorID:(CPString)actorID sender:(id)sender
{
    // console.log("setNodeNameForActorID:sender:", actorID, sender);
    var ip_request = [CPURLRequest requestWithURL:[config runtimeBase] + "/actor/" + actorID];
    [CSGURLConnection connectionWithRequest:ip_request responseBlock:function (header, body, error) {
        var shield = "[" + body + "]";
        var jsObject = [shield objectFromJSON];
        if (jsObject.length === 0) {
            console.log("-setNodeNameForActorID:sender: - Empty body returned, BAILING!");
            return;
        } else {
            var nodeID = jsObject[0].node_id;
            [sender setNodeID:nodeID];
        }
        // Nested request
        [self _namedRuntime:nodeID action:function(name, url) {
            [sender setNodeName:name];
        }];
    }];

}

- (void)actorsOnUIRuntime:(Function /* (actor list) */)responseBlock
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/actors"];
    [CSGURLConnection connectionWithRequest:request responseBlock:function(header, body, error) {
        var actors = [body objectFromJSON];
        responseBlock(actors);
    }];
}


//
// Migration
//
- (void)migrateActor:(CSGActor)actor toNode:(CPString)peer_nodeID onURL:(CPString)url withResponseBlock:(Function)block
{
    var request = [CPURLRequest requestWithURL:url + "/actor/" + [actor identifier] + "/migrate"];
    [request setHTTPMethod:@"POST"];
    [request setHTTPBody:[CPString JSONFromObject:{"peer_node_id":peer_nodeID}]];
    //@tif: TBD, add requiremnts...
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
        block(body);
        [actor setNodeName:"<migrating>"]
        setTimeout(function () {
            [self setNodeNameForActorID:[actor identifier] sender:actor]
        }, 2000);
    }];
}


- (void)getControlURI_OfNodeId:(CPString)nodeID withResponseBlock:(Function)block
{
    var request = [CPURLRequest requestWithURL:[config runtimeBase] + "/node/" + nodeID];
    [CSGURLConnection connectionWithRequest:request responseBlock:function (header, body, error) {
            var shield = "[" + body + "]";
            var jsObject = [shield objectFromJSON];
            if (jsObject.length === 0) {
                console.log("-getControlURI_OfNodeId:withResponseBlock: - Empty body returned, BAILING!");
                return;
            }
            else{
                block(jsObject[0].control_uris[0]);
            }
        }];
}

- (void)migrateActor:(CSGActor)actor toNode:(CPString)peer_nodeID
{
    [self infoForActorID:[actor identifier] withResponseBlock:function (actorInfo) {
            [self getControlURI_OfNodeId:actorInfo.node_id withResponseBlock:function(url) {
                    [self migrateActor:actor toNode:peer_nodeID onURL:url withResponseBlock:function(){}];
                }];
        }];
}

@end
