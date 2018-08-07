@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@implementation CSGScriptViewer : CPWindowController
{
    @outlet CPTextView scriptView;
}

- (id)init
{
    self = [super initWithWindowCibName:"ScriptViewer"];
    if (self) {
    }
    return self;
}

- (void)setReleasedWhenClosed:(BOOL)flag
{
    console.log("FIXME: [[self window] setReleasedWhenClosed:flag];");
}

- (void)setTitle:(CPString)title
{
    [[self window] setTitle:title];
}


- (void)setScript:(CPString)script
{
    [[self window] orderFront:self];
    [scriptView setString:script];
}
@end