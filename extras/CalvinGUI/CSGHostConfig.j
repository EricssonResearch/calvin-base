@import <Foundation/Foundation.j>
@import <AppKit/CPApplication.j>
//
// Server configuration
//
// FIXME: Add preference dialog for user to change these.

CSGCalvinHostKey = "calvinHost";
CSGCalvinPortKey = "calvinPort";
CSGPersistanceHostKey = "persistanceHost";
CSGPersistancePortKey = "persistancePort";
CSGAuthHostKey = "authHost";
CSGAuthPortKey = "authPort";
CSGConsoleHostKey = "consoleHost";
CSGConsolePortKey = "consolePort";
CSGContainerIDKey = "containerID";


#if HOSTED
// Default settings when deployed on server
CGSDefaultConfigPrivate = @{
    CSGCalvinHostKey:"136.225.157.81",
    CSGCalvinPortKey:5001,
    CSGPersistanceHostKey:"136.225.157.81",
    CSGPersistancePortKey:80,
    CSGAuthHostKey:"136.225.157.81",
    CSGAuthPortKey:80,
    CSGConsoleHostKey:"136.225.157.81",
    CSGConsolePortKey:8087,
    CSGContainerIDKey:"1",
};

#else

// Default settings when deployed locally (debugging)
// Using local proxy
CGSDefaultConfigPrivate = @{
    CSGCalvinHostKey:"127.0.0.1",
    CSGCalvinPortKey:5001,
    CSGPersistanceHostKey:"localhost",
    CSGPersistancePortKey:8081,
    CSGAuthHostKey:"localhost",
    CSGAuthPortKey:8081,
    CSGConsoleHostKey:"localhost",
    CSGConsolePortKey:8087,
    CSGContainerIDKey:"",
};

#endif

var sharedHostConfigInstance = nil;

@implementation CSGHostConfig : CPObject
{
    CPString calvinHost @accessors();
    CPString persistanceHost @accessors();
    CPString authHost @accessors();
    CPString consoleHost @accessors();
    int calvinPort @accessors();
    int persistancePort @accessors();
    int authPort @accessors();
    int consolePort @accessors();
    CPString containerID @accessors();

}

+ (id)sharedHostConfig
{
    if (!sharedHostConfigInstance)
    {
        sharedHostConfigInstance = [[CSGHostConfig alloc] _init];
    }
    return sharedHostConfigInstance;
}

- (id)init
{
    [CPException raise:@"CSGHostConfig" reason:@"Singleton. Use +sharedHostConfig"];
}

- (id)_init
{
    self = [super init];
    if (self) {
        var defaults = CGSDefaultConfigPrivate;
        // Override?
        var kwargs = [[CPApplication sharedApplication] namedArguments];
        [defaults addEntriesFromDictionary:kwargs];
        // Will throw exception for invalid keys
        var keys = [defaults allKeys];
        for (var i=0; i<keys.length; i++) {
            var key = keys[i];
            var value = [defaults valueForKey:key];
            try {
                [self setValue:value forKey:key];
            }
            catch(err) {
                console.log(err, key);
            }
        }
    }
    return self;
}

- (CPString)runtimeBase
{
    if (containerID !== "") {
        return [CPString stringWithFormat:"http://%@:%d/calvin/%@", calvinHost, calvinPort, containerID];
    }
    return [CPString stringWithFormat:"http://%@:%d", calvinHost, calvinPort];
}

- (CPString)authBase
{
    return [CPString stringWithFormat:"http://%@:%d", authHost, authPort];
}

- (CPString)persistanceBase
{
    return [CPString stringWithFormat:"http://%@:%d", persistanceHost, persistancePort];
}
@end
