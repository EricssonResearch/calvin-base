@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>
@import "CSGBackend.j"


@implementation CSGCapabilitiesInspector : CPViewController
{
    @outlet CPPopUpButton rtSelect;
    @outlet CPMutableArray runtimeNames @accessors;
    @outlet CPMutableArray capabilities @accessors;
    @outlet CPTextField url;
    CPDictionary runtimeCapabilities @accessors();
}

- (id)init
{
    self = [super initWithCibName:"CapabilitiesView" bundle:nil externalNameTable:nil];
    if (self) {
        runtimeNames = [];
        url = "";
        runtimeCapabilities = @{};
        capabilities = @["loading..."];
    }
    return self;
}

- (void)awakeFromCib
{
    [self reload];
}

- (void)reload
{
    var backend = [CSGBackend sharedBackend];
    [backend getRuntimeCapabilitiesResponseBlock:function(caps){
        [self setRuntimeCapabilities:caps];
    }];
}

- (@action)updateDetail:(id)sender
{
    var key = [[rtSelect selectedItem] title];
    if (![runtimeCapabilities containsKey:key]) {
        // console.log("updateDetail - no such key", key, [runtimeCapabilities allKeys]);
        setTimeout(function () { [self updateDetail:self]; }, 2000);
        return;
    }
    // console.log("updateDetail", key);
    var info = [runtimeCapabilities valueForKey:key];
    [url setStringValue:[info valueForKey:"url"]];
    var capList = [info valueForKey:"capabilities"];
    if (!capList) {
        return;
    }
    capList.forEach(function(cap, i, list){
        list[i] = cap.replace(/^calvinsys\./, "");
    });
    [self setCapabilities:capList.sort()];
    // console.log(capabilities);
    if (capabilities.length == 0) {
        setTimeout(function () { [self updateDetail:self]; }, 2000);
    }
}

- (void) setRuntimeCapabilities:(CPDictionary)dict
{
    // CPLog("setRuntimeCapabilities %@", [dict valueForKeyPath:"First.capabilities"]);
    runtimeCapabilities = [dict copy];
    var names = [dict allKeys];
    names.sort();
    [self setRuntimeNames:names];
    [self updateDetail:self];
}

- (@action)refresh:(id)sender
{
    // console.log("refresh");
    [self reload];
}

@end
