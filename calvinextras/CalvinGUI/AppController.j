/*
 * AppController.j
 * CalvinGUI
 *
 * Created by You on October 5, 2015.
 * Copyright 2015, Your Company All rights reserved.
 */

@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>
@import "CSGActorTreeController.j"
@import "CSGProjectController.j"
@import "CSGProgramView.j"
@import "CSGActor.j"
@import "CSGInspector.j"
@import "CSGRuntimeInspector.j"
@import "CSGScriptViewer.j"
@import "CSGCapabilitiesInspector.j"
@import "CSGHelpViewer.j"
@import "CSGHostConfig.j"

@import "CSGConsole.j" // Required as long as the console is part of UI in cib


@implementation AppController : CPObject
{
    CSGInspector inspector;
    CSGRuntimeInspector runtimeInspector;
    id activeInspector @accessors;
    CSGCapabilitiesInspector capsInspector;
    CSGScriptViewer scriptViewer;
    CSGHelpViewer helpViewer;
    CSGAppUIViewer appUIViewer;

    CSGActorTreeController actorTreeController;
    CSGProjectController projectController;

    @outlet CPWindow theWindow @accessors();
    @outlet CPView projectView;
    @outlet CPView inspectorView;
    @outlet CPView capsView;
    @outlet CPView actorView;

    @outlet CPWindow preferencesSheet;
    @outlet CPTextField preferencesCalvinHost;
    @outlet CPTextField preferencesCalvinPort;
}

//
// Debugging
//

// - (BOOL)respondsToSelector:(SEL)aSelector
// {
//     var responds = [[self class] instancesRespondToSelector:aSelector];
//     if (responds) {
//         console.log("YES :", CPStringFromSelector(aSelector));
//         return YES;
//     }
//     console.log("NO  :", CPStringFromSelector(aSelector));
//     return NO;
// }

- (void)insertAndSetupView:(CPView)view intoSuperview:(CPView)superview
{
    [superview addSubview:view];
    [view setFrame:[superview bounds]];
    [view setAutoresizingMask:CPViewWidthSizable | CPViewHeightSizable];
}

- (void)applicationDidFinishLaunching:(CPNotification)aNotification
{
    var infoDict = [[CPBundle mainBundle] infoDictionary];
    CPLog("infoDict:\n%@", [infoDict valueForKey:@"CalvinInfo"]);

    // Comment out the following two lines after Calvin 0.7 release, modify Info.plist instead
    var reqVersion = [infoDict valueForKeyPath:"CalvinInfo.RequiredVersion.Commit"];
    var opts = @{"Version":"Requires Calvin >= " + reqVersion};
    [CPApp orderFrontStandardAboutPanelWithOptions:opts];
    setTimeout(function () {
        [CPApp._aboutPanel orderOut:self];
    }, 10000);

    projectController = [[CSGProjectController alloc] init];
    [self insertAndSetupView:[projectController view] intoSuperview:projectView];

    actorTreeController = [[CSGActorTreeController alloc] init];
    [self insertAndSetupView:[actorTreeController view] intoSuperview:actorView];

    capsInspector = [[CSGCapabilitiesInspector alloc] init];
    [self insertAndSetupView:[capsInspector view] intoSuperview:capsView];

    // Set up an inspector for actors
    // FIXME: Connections too
    inspector = [[CSGInspector alloc] initWithDelegate:self];
    [self insertAndSetupView:[inspector view] intoSuperview:inspectorView];
    runtimeInspector = [[CSGRuntimeInspector alloc] init];
    [self insertAndSetupView:[runtimeInspector view] intoSuperview:inspectorView];
    [self setActiveInspector:inspector];

    // Window to display program in CalvinScript format
    scriptViewer = [[CSGScriptViewer alloc] init];
    // Window to show basic help
    helpViewer = [[CSGHelpViewer alloc] init];

}


- (void)awakeFromCib
{
    // FIXME: [actorOutline setBackgroundColor:[CPColor colorWithHexString:CSGOutlineViewBgColorHEX]];
    // FIXME: [[infoView superview] setBackgroundColor:[CPColor colorWithHexString:CSGInfoViewBgColorHEX]];
    [[projectController programView] setNeedsDisplay:YES];
    [theWindow setFullPlatformWindow:YES];
}

// Observe changes in certain variables to keep different parts synchronized
- (void)observeValueForKeyPath:(CPString)keyPath
                      ofObject:(id)object
                        change:(CPDictionary)change
                       context:(id)context
{
    // console.log("AppController::observeValueForKeyPath", keyPath, object, change, context);
    if (keyPath === @"currentProject.appID") {
        [self updateInspector];
    }
}

//
// Menu actions
//
// FIXME: Move to preference manager
- (@action)preferences:(id)sender
{
    if (preferencesSheet === nil) {
        [CPBundle loadCibNamed: @"PreferencesSheet" owner:self];
    }
    // Grab current values
    var config = [CSGHostConfig sharedHostConfig];
    [preferencesCalvinHost setStringValue:[config calvinHost]];
    [preferencesCalvinPort setIntegerValue:[config calvinPort]];
    [[CPApplication sharedApplication] beginSheet:preferencesSheet
                                   modalForWindow:theWindow
                                    modalDelegate:self
                                  didEndSelector:@selector(didEndPreferencesSheet:returnCode:contextInfo:)
                                      contextInfo:@""];
}

- (@action)closePreferencesSheet:(id)sender
{
    var retCode = ([sender title] === "OK") ? 1 :0;
    [[CPApplication sharedApplication] endSheet:preferencesSheet returnCode:retCode];
}

- (void)didEndPreferencesSheet:(CPWindow)sheet returnCode:(CPInteger)returnCode contextInfo:(id)contextInfo
{
    [sheet orderOut:self];
    if (returnCode == 1) {
        var config = [CSGHostConfig sharedHostConfig];
        [config setCalvinHost:[preferencesCalvinHost stringValue]];
        [config setCalvinPort:[preferencesCalvinPort integerValue]];
        // We have a new runtime host => recreate actor store
        [actorTreeController reload];
        [capsInspector reload];
    }
}

- (@action)showHelp:(id)sender
{
    [helpViewer showHelp];
}

- (@action)showScript:(id)sender
{
    var script = [[projectController currentProgram] scriptRepresentation];
    [scriptViewer setScript:script];
}

- (void)updateInspector
{
    [self setActiveInspector:[[projectController currentProject] isRunning] ? runtimeInspector : inspector];
}

- (void)setActiveInspector:(id)newInspector
{
    var mainView = [projectController programView];
    if (activeInspector) {
        [mainView removeObserver:activeInspector forKeyPath:@"selection"];
        [activeInspector setComponent:nil];
    }
    activeInspector = newInspector;
    [mainView addObserver:newInspector
              forKeyPath:@"selection"
                 options:CPKeyValueObservingOptionNew | CPKeyValueObservingOptionOld
                 context:nil];

    // Update inspector by dummy updating selection
    [mainView setSelection:[mainView selection]];
    [mainView setNeedsDisplay:YES];
}

//
// Inspector delegate methods
//
- (BOOL)shouldSetName:(CPString)newName forActor:(CSGActor)actor
{
    return [[[projectController currentProject] program] isValidActorName:newName];
}

- (void)refreshViewForActor:(CSGActor)actor
{
    // FIXME: Should be able to use actor bounds as dirtyRect
    [[projectController programView] setNeedsDisplay:YES];
}

@end
