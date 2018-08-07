@import <Foundation/Foundation.j>
@import "CSGBackend.j"

@protocol CSGPersistance
- (BOOL)needsAuthentication;
- (void)setValue:(id)value forKey:(CPString)key;
- (void)valueForKey:(CPString)key responseBlock:(Function /* ((id)value) */)responseBlock;
- (void)allKeysUsingResponseBlock:(Function /* ((CPArray)keys) */)responseBlock;
- (void)deleteValueForKey:(CPString)key;
@end

//
// CSGBasePersistence also works as a dummy storage if real storage is unavailable
//
@implementation CSGBasePersistence : CPObject <CSGPersistance>
{
}

- (id)init
{
    return [super init];
}

- (BOOL)needsAuthentication
{
    return NO;
}

- (void)setValue:(id)value forKey:(CPString)key
{
}

- (void)valueForKey:(CPString)key responseBlock:(Function /* ((id)value) */)responseBlock
{
    responseBlock(nil);
}

- (void)allKeysUsingResponseBlock:(Function /* ((CPArray)keys) */)responseBlock
{
    responseBlock([]);
}

- (void)deleteValueForKey:(CPString)key
{
}

@end

@implementation CSGLocalPersistence : CSGBasePersistence
{
}

- (id)init
{
    if (self=[super init]) {
    	try {
    		var x = '__storage_test__';
    		window.localStorage.setItem(x, x);
    		window.localStorage.removeItem(x);
    	}
    	catch(e) {
    		CPLogAlert("\nHTML5 local storage not available.\nSaving and loading will be disabled.");
            // Return a dummy object
            return [[CSGBasePersistence alloc] init];
    	}
    }
    return self;
}

- (BOOL)needsAuthentication
{
    return NO;
}

- (void)setValue:(id)value forKey:(CPString)key
{
    var dataString = [[CPKeyedArchiver archivedDataWithRootObject:value] rawString];
    window.localStorage.setItem(key, dataString);
}

- (void)valueForKey:(CPString)key responseBlock:(Function /* ((id)value) */)responseBlock
{
    var dataString = window.localStorage.getItem(key);
    var value = (dataString !== null)?[CPKeyedUnarchiver unarchiveObjectWithData:[CPData dataWithRawString:dataString]]:nil;
    responseBlock(value);
}

- (void)allKeysUsingResponseBlock:(Function /* ((CPArray)keys) */)responseBlock
{
    var n = window.localStorage.length;
    var keys = [];
    for (var i=0; i<n; i++) {
        keys[i] = window.localStorage.key(i);
    }
    responseBlock(keys);
}

- (void)deleteValueForKey:(CPString)key
{
    window.localStorage.removeItem(key);
}
@end


@implementation CSGRemotePersistence : CPObject <CSGPersistance>
{
    CSGBackend backend;
    CPString authToken @accessors();
}

- (id)init
{
    if (self = [super init]) {
        backend = [CSGBackend sharedBackend];
        authToken = nil;
    }
    return self;
}

- (BOOL)needsAuthentication
{
    return YES;
}

- (void)setValue:(id)value forKey:(CPString)key
{
    [backend storeValue:value forKey:key authToken:authToken];
}

- (void)valueForKey:(CPString)key responseBlock:(Function /* ((id)value) */)responseBlock
{
    [backend fetchValueForKey:key responseBlock:responseBlock];
}

- (void)allKeysUsingResponseBlock:(Function /* ((CPArray)keys) */)responseBlock
{
    [backend fetchAllKeysUsingResponseBlock:responseBlock];
}

- (void)deleteValueForKey:(CPString)key
{
    CPLog("Not implemented");
}

@end

