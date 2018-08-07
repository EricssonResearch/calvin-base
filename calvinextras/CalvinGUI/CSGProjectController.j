@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@import "CSGProgram.j"
@import "CSGProgramView.j"
@import "CSGProject.j"
@import "CSGBackend.j"
@import "CSGDataPersistance.j"

// FIXME: Don't forget to handle auth tokens on save when not localstore
//        Keep token per project, invalidate if fails to save.


@implementation CSGProjectController : CPViewController
{
    /* Used by popup controller (items) */
    CPMutableArray projects @accessors();
    /* Used by popup for selection and the program view */
    CSGProject currentProject @accessors();
    CSGBackend backend;

    @outlet CPWindow    openSheet;
    @outlet CPTableView projectTable;
            CPArray     availableProjects @accessors;
            CPString    tentativeProjectName;

    @outlet CPWindow    saveSheet;
    @outlet CPTextField saveProjectName;
    @outlet CPTextField    saveUserName;
    @outlet CPSecureTextField savePassword;

    @outlet CSGProgramView programView @accessors(readonly);

    int untitled_count;
}

- (id)init
{
    self = [super initWithCibName:"ProjectView" bundle:nil externalNameTable:nil];
    if (self) {
        untitled_count = 0;
        projects = @[];
        backend = [CSGBackend sharedBackend];
    }
    return self;
}

- (BOOL)acceptsFirstResponder
{
    return YES;
}

- (CPString)nameForUntitled
{
    var suffix = untitled_count ? [CPString stringWithFormat:"-%d", untitled_count] : "";
    untitled_count++;
    return "Untitled" + suffix;
}

- (void)setCurrentProject:(CSGProject)project
{
    if (project == currentProject) {
        return;
    }
    [currentProject deactivate];
    currentProject = project;
    [currentProject activate];
}

-(CSGProgram)currentProgram
{
    return [currentProject program];
}

-(CSGProject)projectWithAppID:(CPString)app_id
{
    for (var i=0; i<projects.length; i++) {
        var proj = projects[i];
        if ([proj appID] === app_id) {
            return proj;
        }
    }
    return nil;
}

- (void)awakeFromCib
{
    if (untitled_count > 0) {
        CPLog.debug("CSGProjectController::awakeFromCib - been here, done that.");
        return;
    }
    // Insert us into responder chain after main window to catch menu actions
    // regardless of which view has focus.
    var win = [[CPApp delegate] theWindow];
    var nextResponder = [win nextResponder];
    [win setNextResponder:self];
    [self setNextResponder:nextResponder];

    // FIXME: awakeFromCib is called when save/load panels are thawed, not only when
    //        project controller cib is thawed. Will that result in in multiple
    //        observers in notification center?
    [self addObserver:programView
           forKeyPath:@"currentProject"
              options:CPKeyValueObservingOptionNew | CPKeyValueObservingOptionOld
              context:nil
    ];
    [self addObserver:[CPApp delegate]
           forKeyPath:@"currentProject.appID"
              options:CPKeyValueObservingOptionNew
              context:nil
    ];
    var proj = [[CSGProject alloc] initWithName:[self nameForUntitled]];
    [self setProjects:@[proj]];
    [self setCurrentProject:proj];
}

//
// New/Save/Open etc.
//
- (@action)newProject:(id)sender
{
    var proj = [[CSGProject alloc] initWithName:[self nameForUntitled]];
    [self willChangeValueForKey:@"projects"];
    [projects addObject:proj];
    [self didChangeValueForKey:@"projects"];
    [self setCurrentProject:proj];
}

- (@action)closeProject:(id)sender
{
    var index = [projects indexOfObject:currentProject];
    [self willChangeValueForKey:@"projects"];
    [projects removeObjectAtIndex:index];
    if (projects.length === 0) {
        // There will always be a current project...
        var proj = [[CSGProject alloc] initWithName:[self nameForUntitled]];
        [projects addObject:proj];
    }
    [self didChangeValueForKey:@"projects"];
    index--;
    index = (index + projects.length) % projects.length;
    [self setCurrentProject:[projects objectAtIndex:index]];
}

- (@action)saveProject:(id)sender
{
    var current = [self currentProject];
    if ([current isUntitled]) {
        [self saveProjectAs:self];
    } else {
        var db = [[CSGLocalPersistence alloc] init];
        [db setValue:current forKey:[current name]];
    }
}

- (@action)revertProjectToSaved:(id)sender
{
    if ([currentProject isUntitled]) {
        return;
    }
    var index = [projects indexOfObject:currentProject];
    var db = [[CSGLocalPersistence alloc] init];
    [db valueForKey:[currentProject name] responseBlock:function(proj) {
        [self willChangeValueForKey:@"projects"];
        [projects replaceObjectAtIndex:index withObject:proj];
        [self didChangeValueForKey:@"projects"];
        [self setCurrentProject:proj];
    }];
}

- (void)addProject:(CSGProject)aProject
{
    [self willChangeValueForKey:@"projects"];
    var name = [aProject name];
    var didReplace = NO;
    for (var i=0; i<projects.length; i++) {
        var proj = projects[i];
        if ([proj name] === name) {
            projects[i] = aProject;
            didReplace = YES;
            break;
        }
    }
    if (!didReplace) {
        [projects addObject:aProject];
    }
    [self didChangeValueForKey:@"projects"];
    [self setCurrentProject:aProject];
}

// Interactive commands (save as, open)
- (@action)closeSheet:(id)sender
{
    var retCode = ([sender title] === "OK") ? 1 :0;
    [CPApp endSheet:[sender window] returnCode:retCode];
}

- (@action)saveProjectAs:(id)sender
{
    var db = [[CSGLocalPersistence alloc] init];
    var win = [CPApp mainWindow];
    if (saveSheet === nil) {
        var cib = [db needsAuthentication]?@"SaveAuthSheet":@"SaveSheet";
        [CPBundle loadCibNamed:cib owner:self];
    }
    [saveProjectName setStringValue:[currentProject name]];
    [CPApp beginSheet:saveSheet
       modalForWindow:win
        modalDelegate:self
       didEndSelector:@selector(didEndSaveSheet:returnCode:contextInfo:)
          contextInfo:db];
}

- (void)didEndSaveSheet:(CPWindow)sheet returnCode:(CPInteger)returnCode contextInfo:(id)contextInfo
{
    [sheet orderOut:self];
    var db = contextInfo;
    if (returnCode == 1) {
        var aName = [saveProjectName stringValue];
        [self willChangeValueForKey:@"projects"];
        [currentProject setName:aName];
        // [currentProject setIsUntitled:NO];
        [self didChangeValueForKey:@"projects"];
        if ([db needsAuthentication]) {
            [backend authenticatePersistanceUser:[saveUserName stringValue] withPassword:[savePassword stringValue] responseBlock:function(token) {
                [db setAuthToken:token];
                [db setValue:currentProject forKey:aName];
            }];
        } else {
            [db setValue:currentProject forKey:aName];
        }
    }
}

- (@action)loadProject:(id)sender
{
    var db = [[CSGLocalPersistence alloc] init];
    var win = [CPApp mainWindow];
    [self setAvailableProjects:[]];
    [db allKeysUsingResponseBlock:function(keys) {
        [self setAvailableProjects:keys];
    }];
    if (openSheet === nil) {
        [CPBundle loadCibNamed:@"OpenSheet" owner:self];
    }
    [CPApp beginSheet:openSheet
       modalForWindow:win // FIXME: Can't use [CPApp mainWindow] here. Why?
        modalDelegate:self
       didEndSelector:@selector(didEndOpenSheet:returnCode:contextInfo:)
          contextInfo:db];
}

- (void)didEndOpenSheet:(CPWindow)sheet returnCode:(CPInteger)returnCode contextInfo:(id)contextInfo
{
    [sheet orderOut:self];
    var db = contextInfo;
    var selectionIndex = [projectTable selectedRow];
    var validSelection = returnCode == 1 && selectionIndex >= 0;
    if (validSelection) {
        tentativeProjectName = availableProjects[selectionIndex];
        [db valueForKey:tentativeProjectName responseBlock:function(proj) {
            [self addProject:proj];
        }];
    }
}

//
// Run/Stop
//
- (@action)runProject:(id)sender
{
    [currentProject run];
}

- (@action)stopProject:(id)sender
{
    [currentProject stop];
}

- (@action)stopAll:(id)sender
{
    [backend updateAvailableApplicationsUsingBlock: function(applist) {
        // Build program for all appIDs not in running, then call setAppID:forProgram:
        for (var i=0; i<applist.length; i++) {
            var app_id = applist[i];
            var proj = [self projectWithAppID:app_id];
            if (proj) {
                [proj stop];
            } else {
                [backend stopAppWithID:app_id responseBlock:function(){
                    CPLog("Stopping application not started in this session.");
                }];
            }
        }
    }];
}

@end
