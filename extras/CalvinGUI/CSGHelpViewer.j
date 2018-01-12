@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@implementation CSGHelpViewer : CPWindowController
{
    @outlet CPWebView webView;
    CPURL helpURL;
}

- (id)init
{
    self = [super initWithWindowCibName:"HelpViewer"];
    if (self) {
        helpURL = [[CPURL alloc] initWithString:"help/help.html"];
    }
    return self;
}

- (void)showHelp
{
    [[self window] orderFront:self];
    [webView setMainFrameURL:helpURL];
    [webView setNeedsDisplay:YES];
}


@end