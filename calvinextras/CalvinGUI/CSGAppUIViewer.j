@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>
@import "CSGAppUIView.j"
@import "CSGBackend.j"
@import "CSGEventListener.j" // CSGEventListening protocol


@class CSGProject;
@class CSGButton;

@implementation CSGAppUIViewer : CPWindowController <CSGEventListening>
{
    CSGProject project;
    @outlet CSGAppUIView appUIView;
}

- (id)initWithProject:(CSGProject)aProject
{
    self = [super initWithWindowCibName:"AppUIViewer"];
    if (self) {
        project = aProject;
        [[self window] setTitle:"Device Simulation"]; // Also trigger CIB loading (via window method) or appUIView will be nil
        [appUIView addActors:[project uiActors] definitions:[project uiDefinitions]];
    }
    return self;
}

- (void)updateVisibility:(CPArray)actorsOnRuntime
{
    [appUIView updateVisibility:actorsOnRuntime];
}

- (void)uiAction:(id)sender
{
    var data = nil;
    switch ([sender class]) {
      case CPButton:
      case CSGButton:
          data = [sender state];
          break;
      case CPSlider:
          data = [sender floatValue];
        break;
    default:
        console.log("FIXME: get value", sender);
        break;
    }
    if (data !== nil) {
        [self eventFor:sender withData:data];
    }
}

- (void)eventFor:(id)control withData:(JSObject)data
{
    var actor_id = [[control superview] actor].identifier;
    var backend = [CSGBackend sharedBackend];
    [backend generateEventForActor:actor_id withData:data];
}

- (void)uiSetAction:(id)sender
{
    [self eventFor:sender withData:1];
}

- (void)uiResetAction:(id)sender
{
    [self eventFor:sender withData:0];
}

- (void)eventWithData:(id)data sender:(CSGEventListener)sender
{
    var actors = [project.program actors];
    for (var i=0; i<actors.length; i++) {
        var actor = actors[i];
        if (data.client_id == actor.identifier) {
            [actor setUiState:data.state];
            break;
        }
    }
}


@end