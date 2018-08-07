@STATIC;1.0;p;6;main.jt;292;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;15;AppController.jt;206;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("AppController.j", YES);main = function(args, namedArgs)
{
    CPApplicationMain(args, namedArgs);
}
p;15;AppController.jt;15909;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;24;CSGActorTreeController.ji;22;CSGProjectController.ji;16;CSGProgramView.ji;10;CSGActor.ji;14;CSGInspector.ji;21;CSGRuntimeInspector.ji;17;CSGScriptViewer.ji;26;CSGCapabilitiesInspector.ji;15;CSGHelpViewer.ji;15;CSGHostConfig.ji;12;CSGConsole.jt;15594;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGActorTreeController.j", YES);objj_executeFile("CSGProjectController.j", YES);objj_executeFile("CSGProgramView.j", YES);objj_executeFile("CSGActor.j", YES);objj_executeFile("CSGInspector.j", YES);objj_executeFile("CSGRuntimeInspector.j", YES);objj_executeFile("CSGScriptViewer.j", YES);objj_executeFile("CSGCapabilitiesInspector.j", YES);objj_executeFile("CSGHelpViewer.j", YES);objj_executeFile("CSGHostConfig.j", YES);objj_executeFile("CSGConsole.j", YES);
{var the_class = objj_allocateClassPair(CPObject, "AppController"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("inspector", "CSGInspector"), new objj_ivar("runtimeInspector", "CSGRuntimeInspector"), new objj_ivar("activeInspector", "id"), new objj_ivar("capsInspector", "CSGCapabilitiesInspector"), new objj_ivar("scriptViewer", "CSGScriptViewer"), new objj_ivar("helpViewer", "CSGHelpViewer"), new objj_ivar("appUIViewer", "CSGAppUIViewer"), new objj_ivar("actorTreeController", "CSGActorTreeController"), new objj_ivar("projectController", "CSGProjectController"), new objj_ivar("theWindow", "CPWindow"), new objj_ivar("projectView", "CPView"), new objj_ivar("inspectorView", "CPView"), new objj_ivar("capsView", "CPView"), new objj_ivar("actorView", "CPView"), new objj_ivar("preferencesSheet", "CPWindow"), new objj_ivar("preferencesCalvinHost", "CPTextField"), new objj_ivar("preferencesCalvinPort", "CPTextField")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("activeInspector"), function $AppController__activeInspector(self, _cmd)
{
    return self.activeInspector;
}

,["id"]), new objj_method(sel_getUid("setActiveInspector:"), function $AppController__setActiveInspector_(self, _cmd, newValue)
{
    self.activeInspector = newValue;
}

,["void","id"]), new objj_method(sel_getUid("theWindow"), function $AppController__theWindow(self, _cmd)
{
    return self.theWindow;
}

,["CPWindow"]), new objj_method(sel_getUid("setTheWindow:"), function $AppController__setTheWindow_(self, _cmd, newValue)
{
    self.theWindow = newValue;
}

,["void","CPWindow"]), new objj_method(sel_getUid("insertAndSetupView:intoSuperview:"), function $AppController__insertAndSetupView_intoSuperview_(self, _cmd, view, superview)
{
    (superview == null ? null : (superview.isa.method_msgSend["addSubview:"] || _objj_forward)(superview, "addSubview:", view));
    (view == null ? null : (view.isa.method_msgSend["setFrame:"] || _objj_forward)(view, "setFrame:", (superview == null ? null : (superview.isa.method_msgSend["bounds"] || _objj_forward)(superview, "bounds"))));
    (view == null ? null : (view.isa.method_msgSend["setAutoresizingMask:"] || _objj_forward)(view, "setAutoresizingMask:", CPViewWidthSizable | CPViewHeightSizable));
}

,["void","CPView","CPView"]), new objj_method(sel_getUid("applicationDidFinishLaunching:"), function $AppController__applicationDidFinishLaunching_(self, _cmd, aNotification)
{
    var infoDict = ((___r1 = (CPBundle.isa.method_msgSend["mainBundle"] || _objj_forward)(CPBundle, "mainBundle")), ___r1 == null ? null : (___r1.isa.method_msgSend["infoDictionary"] || _objj_forward)(___r1, "infoDictionary"));
    CPLog("infoDict:\n%@", (infoDict == null ? null : (infoDict.isa.method_msgSend["valueForKey:"] || _objj_forward)(infoDict, "valueForKey:", "CalvinInfo")));
    var reqVersion = (infoDict == null ? null : (infoDict.isa.method_msgSend["valueForKeyPath:"] || _objj_forward)(infoDict, "valueForKeyPath:", "CalvinInfo.RequiredVersion.Commit"));
    var opts = (___r1 = (CPDictionary.isa.method_msgSend["alloc"] || _objj_forward)(CPDictionary, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithObjects:forKeys:"] || _objj_forward)(___r1, "initWithObjects:forKeys:", ["Requires Calvin >= " + reqVersion], ["Version"]));
    (CPApp == null ? null : (CPApp.isa.method_msgSend["orderFrontStandardAboutPanelWithOptions:"] || _objj_forward)(CPApp, "orderFrontStandardAboutPanelWithOptions:", opts));
    setTimeout(    function()
    {
        ((___r1 = CPApp._aboutPanel), ___r1 == null ? null : (___r1.isa.method_msgSend["orderOut:"] || _objj_forward)(___r1, "orderOut:", self));
        var ___r1;
    }, 10000);
    self.projectController = ((___r1 = (CSGProjectController.isa.method_msgSend["alloc"] || _objj_forward)(CSGProjectController, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
    (self.isa.method_msgSend["insertAndSetupView:intoSuperview:"] || _objj_forward)(self, "insertAndSetupView:intoSuperview:", ((___r1 = self.projectController), ___r1 == null ? null : (___r1.isa.method_msgSend["view"] || _objj_forward)(___r1, "view")), self.projectView);
    self.actorTreeController = ((___r1 = (CSGActorTreeController.isa.method_msgSend["alloc"] || _objj_forward)(CSGActorTreeController, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
    (self.isa.method_msgSend["insertAndSetupView:intoSuperview:"] || _objj_forward)(self, "insertAndSetupView:intoSuperview:", ((___r1 = self.actorTreeController), ___r1 == null ? null : (___r1.isa.method_msgSend["view"] || _objj_forward)(___r1, "view")), self.actorView);
    self.capsInspector = ((___r1 = (CSGCapabilitiesInspector.isa.method_msgSend["alloc"] || _objj_forward)(CSGCapabilitiesInspector, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
    (self.isa.method_msgSend["insertAndSetupView:intoSuperview:"] || _objj_forward)(self, "insertAndSetupView:intoSuperview:", ((___r1 = self.capsInspector), ___r1 == null ? null : (___r1.isa.method_msgSend["view"] || _objj_forward)(___r1, "view")), self.capsView);
    self.inspector = ((___r1 = (CSGInspector.isa.method_msgSend["alloc"] || _objj_forward)(CSGInspector, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithDelegate:"] || _objj_forward)(___r1, "initWithDelegate:", self));
    (self.isa.method_msgSend["insertAndSetupView:intoSuperview:"] || _objj_forward)(self, "insertAndSetupView:intoSuperview:", ((___r1 = self.inspector), ___r1 == null ? null : (___r1.isa.method_msgSend["view"] || _objj_forward)(___r1, "view")), self.inspectorView);
    self.runtimeInspector = ((___r1 = (CSGRuntimeInspector.isa.method_msgSend["alloc"] || _objj_forward)(CSGRuntimeInspector, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
    (self.isa.method_msgSend["insertAndSetupView:intoSuperview:"] || _objj_forward)(self, "insertAndSetupView:intoSuperview:", ((___r1 = self.runtimeInspector), ___r1 == null ? null : (___r1.isa.method_msgSend["view"] || _objj_forward)(___r1, "view")), self.inspectorView);
    (self.isa.method_msgSend["setActiveInspector:"] || _objj_forward)(self, "setActiveInspector:", self.inspector);
    self.scriptViewer = ((___r1 = (CSGScriptViewer.isa.method_msgSend["alloc"] || _objj_forward)(CSGScriptViewer, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
    self.helpViewer = ((___r1 = (CSGHelpViewer.isa.method_msgSend["alloc"] || _objj_forward)(CSGHelpViewer, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
    var ___r1;
}

,["void","CPNotification"]), new objj_method(sel_getUid("awakeFromCib"), function $AppController__awakeFromCib(self, _cmd)
{
    ((___r1 = ((___r2 = self.projectController), ___r2 == null ? null : (___r2.isa.method_msgSend["programView"] || _objj_forward)(___r2, "programView"))), ___r1 == null ? null : (___r1.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(___r1, "setNeedsDisplay:", YES));
    ((___r1 = self.theWindow), ___r1 == null ? null : (___r1.isa.method_msgSend["setFullPlatformWindow:"] || _objj_forward)(___r1, "setFullPlatformWindow:", YES));
    var ___r1, ___r2;
}

,["void"]), new objj_method(sel_getUid("observeValueForKeyPath:ofObject:change:context:"), function $AppController__observeValueForKeyPath_ofObject_change_context_(self, _cmd, keyPath, object, change, context)
{
    if (keyPath === "currentProject.appID")
    {
        (self.isa.method_msgSend["updateInspector"] || _objj_forward)(self, "updateInspector");
    }
}

,["void","CPString","id","CPDictionary","id"]), new objj_method(sel_getUid("preferences:"), function $AppController__preferences_(self, _cmd, sender)
{
    if (self.preferencesSheet === nil)
    {
        (CPBundle.isa.method_msgSend["loadCibNamed:owner:"] || _objj_forward)(CPBundle, "loadCibNamed:owner:", "PreferencesSheet", self);
    }
    var config = (CSGHostConfig.isa.method_msgSend["sharedHostConfig"] || _objj_forward)(CSGHostConfig, "sharedHostConfig");
    ((___r1 = self.preferencesCalvinHost), ___r1 == null ? null : (___r1.isa.method_msgSend["setStringValue:"] || _objj_forward)(___r1, "setStringValue:", (config == null ? null : (config.isa.method_msgSend["calvinHost"] || _objj_forward)(config, "calvinHost"))));
    ((___r1 = self.preferencesCalvinPort), ___r1 == null ? null : (___r1.isa.method_msgSend["setIntegerValue:"] || _objj_forward)(___r1, "setIntegerValue:", (config == null ? null : (config.isa.method_msgSend["calvinPort"] || _objj_forward)(config, "calvinPort"))));
    ((___r1 = (CPApplication.isa.method_msgSend["sharedApplication"] || _objj_forward)(CPApplication, "sharedApplication")), ___r1 == null ? null : (___r1.isa.method_msgSend["beginSheet:modalForWindow:modalDelegate:didEndSelector:contextInfo:"] || _objj_forward)(___r1, "beginSheet:modalForWindow:modalDelegate:didEndSelector:contextInfo:", self.preferencesSheet, self.theWindow, self, sel_getUid("didEndPreferencesSheet:returnCode:contextInfo:"), ""));
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("closePreferencesSheet:"), function $AppController__closePreferencesSheet_(self, _cmd, sender)
{
    var retCode = (sender == null ? null : (sender.isa.method_msgSend["title"] || _objj_forward)(sender, "title")) === "OK" ? 1 : 0;
    ((___r1 = (CPApplication.isa.method_msgSend["sharedApplication"] || _objj_forward)(CPApplication, "sharedApplication")), ___r1 == null ? null : (___r1.isa.method_msgSend["endSheet:returnCode:"] || _objj_forward)(___r1, "endSheet:returnCode:", self.preferencesSheet, retCode));
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("didEndPreferencesSheet:returnCode:contextInfo:"), function $AppController__didEndPreferencesSheet_returnCode_contextInfo_(self, _cmd, sheet, returnCode, contextInfo)
{
    (sheet == null ? null : (sheet.isa.method_msgSend["orderOut:"] || _objj_forward)(sheet, "orderOut:", self));
    if (returnCode == 1)
    {
        var config = (CSGHostConfig.isa.method_msgSend["sharedHostConfig"] || _objj_forward)(CSGHostConfig, "sharedHostConfig");
        (config == null ? null : (config.isa.method_msgSend["setCalvinHost:"] || _objj_forward)(config, "setCalvinHost:", ((___r1 = self.preferencesCalvinHost), ___r1 == null ? null : (___r1.isa.method_msgSend["stringValue"] || _objj_forward)(___r1, "stringValue"))));
        (config == null ? null : (config.isa.method_msgSend["setCalvinPort:"] || _objj_forward)(config, "setCalvinPort:", ((___r1 = self.preferencesCalvinPort), ___r1 == null ? null : (___r1.isa.method_msgSend["integerValue"] || _objj_forward)(___r1, "integerValue"))));
        ((___r1 = self.actorTreeController), ___r1 == null ? null : (___r1.isa.method_msgSend["reload"] || _objj_forward)(___r1, "reload"));
        ((___r1 = self.capsInspector), ___r1 == null ? null : (___r1.isa.method_msgSend["reload"] || _objj_forward)(___r1, "reload"));
    }
    var ___r1;
}

,["void","CPWindow","CPInteger","id"]), new objj_method(sel_getUid("showHelp:"), function $AppController__showHelp_(self, _cmd, sender)
{
    ((___r1 = self.helpViewer), ___r1 == null ? null : (___r1.isa.method_msgSend["showHelp"] || _objj_forward)(___r1, "showHelp"));
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("showScript:"), function $AppController__showScript_(self, _cmd, sender)
{
    var script = ((___r1 = ((___r2 = self.projectController), ___r2 == null ? null : (___r2.isa.method_msgSend["currentProgram"] || _objj_forward)(___r2, "currentProgram"))), ___r1 == null ? null : (___r1.isa.method_msgSend["scriptRepresentation"] || _objj_forward)(___r1, "scriptRepresentation"));
    ((___r1 = self.scriptViewer), ___r1 == null ? null : (___r1.isa.method_msgSend["setScript:"] || _objj_forward)(___r1, "setScript:", script));
    var ___r1, ___r2;
}

,["void","id"]), new objj_method(sel_getUid("updateInspector"), function $AppController__updateInspector(self, _cmd)
{
    (self.isa.method_msgSend["setActiveInspector:"] || _objj_forward)(self, "setActiveInspector:", ((___r1 = ((___r2 = self.projectController), ___r2 == null ? null : (___r2.isa.method_msgSend["currentProject"] || _objj_forward)(___r2, "currentProject"))), ___r1 == null ? null : (___r1.isa.method_msgSend["isRunning"] || _objj_forward)(___r1, "isRunning")) ? self.runtimeInspector : self.inspector);
    var ___r1, ___r2;
}

,["void"]), new objj_method(sel_getUid("setActiveInspector:"), function $AppController__setActiveInspector_(self, _cmd, newInspector)
{
    var mainView = ((___r1 = self.projectController), ___r1 == null ? null : (___r1.isa.method_msgSend["programView"] || _objj_forward)(___r1, "programView"));
    if (self.activeInspector)
    {
        (mainView == null ? null : (mainView.isa.method_msgSend["removeObserver:forKeyPath:"] || _objj_forward)(mainView, "removeObserver:forKeyPath:", self.activeInspector, "selection"));
        ((___r1 = self.activeInspector), ___r1 == null ? null : (___r1.isa.method_msgSend["setComponent:"] || _objj_forward)(___r1, "setComponent:", nil));
    }
    self.activeInspector = newInspector;
    (mainView == null ? null : (mainView.isa.method_msgSend["addObserver:forKeyPath:options:context:"] || _objj_forward)(mainView, "addObserver:forKeyPath:options:context:", newInspector, "selection", CPKeyValueObservingOptionNew | CPKeyValueObservingOptionOld, nil));
    (mainView == null ? null : (mainView.isa.method_msgSend["setSelection:"] || _objj_forward)(mainView, "setSelection:", (mainView == null ? null : (mainView.isa.method_msgSend["selection"] || _objj_forward)(mainView, "selection"))));
    (mainView == null ? null : (mainView.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(mainView, "setNeedsDisplay:", YES));
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("shouldSetName:forActor:"), function $AppController__shouldSetName_forActor_(self, _cmd, newName, actor)
{
    return ((___r1 = ((___r2 = ((___r3 = self.projectController), ___r3 == null ? null : (___r3.isa.method_msgSend["currentProject"] || _objj_forward)(___r3, "currentProject"))), ___r2 == null ? null : (___r2.isa.method_msgSend["program"] || _objj_forward)(___r2, "program"))), ___r1 == null ? null : (___r1.isa.method_msgSend["isValidActorName:"] || _objj_forward)(___r1, "isValidActorName:", newName));
    var ___r1, ___r2, ___r3;
}

,["BOOL","CPString","CSGActor"]), new objj_method(sel_getUid("refreshViewForActor:"), function $AppController__refreshViewForActor_(self, _cmd, actor)
{
    ((___r1 = ((___r2 = self.projectController), ___r2 == null ? null : (___r2.isa.method_msgSend["programView"] || _objj_forward)(___r2, "programView"))), ___r1 == null ? null : (___r1.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(___r1, "setNeedsDisplay:", YES));
    var ___r1, ___r2;
}

,["void","CSGActor"])]);
}
p;24;CSGActorTreeController.jt;10288;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;12;CSGBackend.ji;18;CSGActorTreeNode.jt;10180;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGBackend.j", YES);objj_executeFile("CSGActorTreeNode.j", YES);
{var the_class = objj_allocateClassPair(CPViewController, "CSGActorTreeController"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("outlineView", "CPOutlineView"), new objj_ivar("spinner", "CPProgressIndicator"), new objj_ivar("selectedItem", "CSGActorTreeNode"), new objj_ivar("backend", "CSGBackend"), new objj_ivar("root", "CSGActorTreeNode"), new objj_ivar("outstanding", "int")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("outlineView"), function $CSGActorTreeController__outlineView(self, _cmd)
{
    return self.outlineView;
}

,["CPOutlineView"]), new objj_method(sel_getUid("setOutlineView:"), function $CSGActorTreeController__setOutlineView_(self, _cmd, newValue)
{
    self.outlineView = newValue;
}

,["void","CPOutlineView"]), new objj_method(sel_getUid("spinner"), function $CSGActorTreeController__spinner(self, _cmd)
{
    return self.spinner;
}

,["CPProgressIndicator"]), new objj_method(sel_getUid("setSpinner:"), function $CSGActorTreeController__setSpinner_(self, _cmd, newValue)
{
    self.spinner = newValue;
}

,["void","CPProgressIndicator"]), new objj_method(sel_getUid("selectedItem"), function $CSGActorTreeController__selectedItem(self, _cmd)
{
    return self.selectedItem;
}

,["CSGActorTreeNode"]), new objj_method(sel_getUid("setSelectedItem:"), function $CSGActorTreeController__setSelectedItem_(self, _cmd, newValue)
{
    self.selectedItem = newValue;
}

,["void","CSGActorTreeNode"]), new objj_method(sel_getUid("init"), function $CSGActorTreeController__init(self, _cmd)
{
    self = (objj_getClass("CSGActorTreeController").super_class.method_dtable["initWithCibName:bundle:externalNameTable:"] || _objj_forward)(self, "initWithCibName:bundle:externalNameTable:", "ActorView", nil, nil);
    if (self)
    {
        self.backend = (CSGBackend.isa.method_msgSend["sharedBackend"] || _objj_forward)(CSGBackend, "sharedBackend");
        self.root = ((___r1 = (CSGActorTreeNode.isa.method_msgSend["alloc"] || _objj_forward)(CSGActorTreeNode, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithData:"] || _objj_forward)(___r1, "initWithData:", ""));
        self.outstanding = 0;
    }
    return self;
    var ___r1;
}

,["id"]), new objj_method(sel_getUid("awakeFromCib"), function $CSGActorTreeController__awakeFromCib(self, _cmd)
{
    ((___r1 = self.spinner), ___r1 == null ? null : (___r1.isa.method_msgSend["stopAnimation:"] || _objj_forward)(___r1, "stopAnimation:", self));
    (self.isa.method_msgSend["reload"] || _objj_forward)(self, "reload");
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("reload"), function $CSGActorTreeController__reload(self, _cmd)
{
    self.root = ((___r1 = (CSGActorTreeNode.isa.method_msgSend["alloc"] || _objj_forward)(CSGActorTreeNode, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithData:"] || _objj_forward)(___r1, "initWithData:", ""));
    self.outstanding = 0;
    (self.isa.method_msgSend["getDataForNode:"] || _objj_forward)(self, "getDataForNode:", self.root);
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("_beginUpdate"), function $CSGActorTreeController___beginUpdate(self, _cmd)
{
    if (self.outstanding === 0)
    {
        ((___r1 = self.spinner), ___r1 == null ? null : (___r1.isa.method_msgSend["startAnimation:"] || _objj_forward)(___r1, "startAnimation:", self));
    }
    self.outstanding += 1;
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("_completeUpdate"), function $CSGActorTreeController___completeUpdate(self, _cmd)
{
    self.outstanding -= 1;
    if (self.outstanding === 0)
    {
        ((___r1 = self.spinner), ___r1 == null ? null : (___r1.isa.method_msgSend["stopAnimation:"] || _objj_forward)(___r1, "stopAnimation:", self));
        ((___r1 = self.outlineView), ___r1 == null ? null : (___r1.isa.method_msgSend["reloadData"] || _objj_forward)(___r1, "reloadData"));
    }
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("_createChildren:forNode:isLeaf:"), function $CSGActorTreeController___createChildren_forNode_isLeaf_(self, _cmd, children, node, leaf)
{
    for (var i = 0; i < children.length; i++)
    {
        var newNode = ((___r1 = (CSGActorTreeNode.isa.method_msgSend["alloc"] || _objj_forward)(CSGActorTreeNode, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithData:"] || _objj_forward)(___r1, "initWithData:", children[i]));
        (newNode == null ? null : (newNode.isa.method_msgSend["setIsLeaf:"] || _objj_forward)(newNode, "setIsLeaf:", leaf));
        (node == null ? null : (node.isa.method_msgSend["addChild:"] || _objj_forward)(node, "addChild:", newNode));
        if ((newNode == null ? null : (newNode.isa.method_msgSend["isLeaf"] || _objj_forward)(newNode, "isLeaf")))
        {
            (self.isa.method_msgSend["getDataForNode:"] || _objj_forward)(self, "getDataForNode:", newNode);
        }
    }
    var ___r1;
}

,["void","CPArray","CSGActorTreeNode","BOOL"]), new objj_method(sel_getUid("getDataForNode:"), function $CSGActorTreeController__getDataForNode_(self, _cmd, node)
{
    (self.isa.method_msgSend["_beginUpdate"] || _objj_forward)(self, "_beginUpdate");
    ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["docFor:responseBlock:"] || _objj_forward)(___r1, "docFor:responseBlock:", node.path,     function(body)
    {
        (self.isa.method_msgSend["updateNode:withData:"] || _objj_forward)(self, "updateNode:withData:", node, body);
    }));
    var ___r1;
}

,["void","CSGActorTreeNode"]), new objj_method(sel_getUid("updateNode:withData:"), function $CSGActorTreeController__updateNode_withData_(self, _cmd, node, data)
{
    if (data.actors === undefined && data.modules === undefined && data.type === undefined)
    {
        console.log("skipping", data);
        (self.isa.method_msgSend["_completeUpdate"] || _objj_forward)(self, "_completeUpdate");
        return;
    }
    (node == null ? null : (node.isa.method_msgSend["setInfo:"] || _objj_forward)(node, "setInfo:", data));
    if (!data.hasOwnProperty('type'))
    {
        (self.isa.method_msgSend["_createChildren:forNode:isLeaf:"] || _objj_forward)(self, "_createChildren:forNode:isLeaf:", data.modules.sort(), node, NO);
        (self.isa.method_msgSend["_createChildren:forNode:isLeaf:"] || _objj_forward)(self, "_createChildren:forNode:isLeaf:", data.actors.sort(), node, YES);
    }
    (self.isa.method_msgSend["_completeUpdate"] || _objj_forward)(self, "_completeUpdate");
}

,["void","CSGActorTreeNode","JSObject"]), new objj_method(sel_getUid("outlineView:numberOfChildrenOfItem:"), function $CSGActorTreeController__outlineView_numberOfChildrenOfItem_(self, _cmd, outlineView, item)
{
    if (item === nil)
    {
        item = self.root;
    }
    if (item !== self.root && (item == null ? null : (item.isa.method_msgSend["count"] || _objj_forward)(item, "count")) === 0)
    {
        (self.isa.method_msgSend["getDataForNode:"] || _objj_forward)(self, "getDataForNode:", item);
    }
    return (item == null ? null : (item.isa.method_msgSend["count"] || _objj_forward)(item, "count"));
}

,["int","CPOutlineView","id"]), new objj_method(sel_getUid("outlineView:isItemExpandable:"), function $CSGActorTreeController__outlineView_isItemExpandable_(self, _cmd, outlineView, item)
{
    return !(item == null ? null : (item.isa.method_msgSend["isLeaf"] || _objj_forward)(item, "isLeaf"));
}

,["BOOL","CPOutlineView","id"]), new objj_method(sel_getUid("outlineView:child:ofItem:"), function $CSGActorTreeController__outlineView_child_ofItem_(self, _cmd, outlineView, index, item)
{
    if (item === nil)
    {
        item = self.root;
    }
    return (item == null ? null : (item.isa.method_msgSend["childAtIndex:"] || _objj_forward)(item, "childAtIndex:", index));
}

,["id","CPOutlineView","int","id"]), new objj_method(sel_getUid("outlineView:objectValueForTableColumn:byItem:"), function $CSGActorTreeController__outlineView_objectValueForTableColumn_byItem_(self, _cmd, outlineView, tableColumn, item)
{
    return item;
}

,["id","CPOutlineView","CPTableColumn","id"]), new objj_method(sel_getUid("outlineView:shouldEditTableColumn:item:"), function $CSGActorTreeController__outlineView_shouldEditTableColumn_item_(self, _cmd, outlineView, tableColumn, item)
{
    return NO;
}

,["BOOL","CPOutlineView","CPTableColumn","id"]), new objj_method(sel_getUid("outlineViewSelectionDidChange:"), function $CSGActorTreeController__outlineViewSelectionDidChange_(self, _cmd, notification)
{
    var ov = (notification == null ? null : (notification.isa.method_msgSend["object"] || _objj_forward)(notification, "object"));
    var si = (ov == null ? null : (ov.isa.method_msgSend["itemAtRow:"] || _objj_forward)(ov, "itemAtRow:", (ov == null ? null : (ov.isa.method_msgSend["selectedRow"] || _objj_forward)(ov, "selectedRow"))));
    (self.isa.method_msgSend["setSelectedItem:"] || _objj_forward)(self, "setSelectedItem:", si);
}

,["void","CPNotification"]), new objj_method(sel_getUid("outlineView:writeItems:toPasteboard:"), function $CSGActorTreeController__outlineView_writeItems_toPasteboard_(self, _cmd, outlineView, items, pboard)
{
    var item = items[0];
    if (!(item == null ? null : (item.isa.method_msgSend["isLeaf"] || _objj_forward)(item, "isLeaf")))
    {
        return NO;
    }
    if ((pboard == null ? null : (pboard.isa.method_msgSend["availableTypeFromArray:"] || _objj_forward)(pboard, "availableTypeFromArray:", [CPStringPboardType])) === nil)
    {
        (pboard == null ? null : (pboard.isa.method_msgSend["declareTypes:owner:"] || _objj_forward)(pboard, "declareTypes:owner:", [CPStringPboardType], self));
    }
    (pboard == null ? null : (pboard.isa.method_msgSend["setData:forType:"] || _objj_forward)(pboard, "setData:forType:", (CPString.isa.method_msgSend["JSONFromObject:"] || _objj_forward)(CPString, "JSONFromObject:", item.info), CPStringPboardType));
    return YES;
}

,["BOOL","CPOutlineView","CPArray","CPPasteboard"])]);
}
p;12;CSGBackend.jt;31456;@STATIC;1.0;I;23;Foundation/Foundation.ji;15;CSGHostConfig.jt;31388;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("CSGHostConfig.j", YES);
{var the_class = objj_allocateClassPair(CPURLConnection, "CSGURLConnection"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("header", "CPDictionary"), new objj_ivar("responseHandler", "Function")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("initWithRequest:responseBlock:"), function $CSGURLConnection__initWithRequest_responseBlock_(self, _cmd, aRequest, aFunction)
{
    self = (objj_getClass("CSGURLConnection").super_class.method_dtable["initWithRequest:delegate:startImmediately:"] || _objj_forward)(self, "initWithRequest:delegate:startImmediately:", aRequest, self, NO);
    if (self)
    {
        self._isLocalFileConnection = NO;
        self.responseHandler = aFunction;
        (self == null ? null : (self.isa.method_msgSend["start"] || _objj_forward)(self, "start"));
    }
    return self;
}

,["id","CPURLRequest","Function"]), new objj_method(sel_getUid("connection:didReceiveData:"), function $CSGURLConnection__connection_didReceiveData_(self, _cmd, connection, data)
{
    self.responseHandler(self.header, data, nil);
}

,["void","CSGURLConnection","CPString"]), new objj_method(sel_getUid("connection:didFailWithError:"), function $CSGURLConnection__connection_didFailWithError_(self, _cmd, connection, error)
{
    self.responseHandler(self.header, nil, error);
}

,["void","CSGURLConnection","CPError"]), new objj_method(sel_getUid("connection:didReceiveResponse:"), function $CSGURLConnection__connection_didReceiveResponse_(self, _cmd, connection, response)
{
    if ((response == null ? null : (response.isa.method_msgSend["isKindOfClass:"] || _objj_forward)(response, "isKindOfClass:", (CPHTTPURLResponse.isa.method_msgSend["class"] || _objj_forward)(CPHTTPURLResponse, "class"))))
    {
        self.header = (response == null ? null : (response.isa.method_msgSend["allHeaderFields"] || _objj_forward)(response, "allHeaderFields"));
    }
}

,["void","CSGURLConnection","CPURLResponse"])]);
class_addMethods(meta_class, [new objj_method(sel_getUid("connectionWithRequest:responseBlock:"), function $CSGURLConnection__connectionWithRequest_responseBlock_(self, _cmd, aRequest, aFunction)
{
    return ((___r1 = (self.isa.method_msgSend["alloc"] || _objj_forward)(self, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithRequest:responseBlock:"] || _objj_forward)(___r1, "initWithRequest:responseBlock:", aRequest, aFunction));
    var ___r1;
}

,["CSGURLConnection","CPURLRequest","Function"])]);
}
var sharedBackendInstance = nil;

{var the_class = objj_allocateClassPair(CPObject, "CSGBackend"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("config", "CSGHostConfig")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("init"), function $CSGBackend__init(self, _cmd)
{
    (CPException.isa.method_msgSend["raise:reason:"] || _objj_forward)(CPException, "raise:reason:", "CSGHostConfig", "Singleton. Use +sharedHostConfig");
}

,["id"]), new objj_method(sel_getUid("_init"), function $CSGBackend___init(self, _cmd)
{
    if (self = (objj_getClass("CSGBackend").super_class.method_dtable["init"] || _objj_forward)(self, "init"))
    {
        self.config = (CSGHostConfig.isa.method_msgSend["sharedHostConfig"] || _objj_forward)(CSGHostConfig, "sharedHostConfig");
    }
    return self;
}

,["id"]), new objj_method(sel_getUid("generateEventForActor:withData:"), function $CSGBackend__generateEventForActor_withData_(self, _cmd, actorID, data)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/uicalvinsys"),
        body = {"client_id": actorID, "state": data};
    (request == null ? null : (request.isa.method_msgSend["setHTTPMethod:"] || _objj_forward)(request, "setHTTPMethod:", "POST"));
    (request == null ? null : (request.isa.method_msgSend["setValue:forHTTPHeaderField:"] || _objj_forward)(request, "setValue:forHTTPHeaderField:", "application/json", "Content-Type"));
    (request == null ? null : (request.isa.method_msgSend["setHTTPBody:"] || _objj_forward)(request, "setHTTPBody:", (CPString.isa.method_msgSend["JSONFromObject:"] || _objj_forward)(CPString, "JSONFromObject:", body)));
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        if (error !== nil)
        {
            console.log("Error sending update event", error);
            return;
        }    });
    var ___r1;
}

,["void","CPString","JSObject"]), new objj_method(sel_getUid("getUIDefinitions:responseBlock:"), function $CSGBackend__getUIDefinitions_responseBlock_(self, _cmd, appID, responseBlock)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/uicalvinsys/" + appID);
    var req = (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        var defs = (body == null ? null : (body.isa.method_msgSend["objectFromJSON"] || _objj_forward)(body, "objectFromJSON"));
        responseBlock(defs);
    });
    var ___r1;
}

,["void","CPString","Function"]), new objj_method(sel_getUid("getRuntimeCapabilitiesResponseBlock:"), function $CSGBackend__getRuntimeCapabilitiesResponseBlock_(self, _cmd, responseBlock)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/index/node/attribute/node_name");
    var req = (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        var response = (body == null ? null : (body.isa.method_msgSend["objectFromJSON"] || _objj_forward)(body, "objectFromJSON"));
        var runtimeList = response.result;
        var capabilities = (___r1 = (CPDictionary.isa.method_msgSend["alloc"] || _objj_forward)(CPDictionary, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
        runtimeList.forEach(        function(rtID)
        {
            (self.isa.method_msgSend["_namedRuntime:action:"] || _objj_forward)(self, "_namedRuntime:action:", rtID,             function(name, url)
            {
                var info = (___r1 = (CPDictionary.isa.method_msgSend["alloc"] || _objj_forward)(CPDictionary, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithObjects:forKeys:"] || _objj_forward)(___r1, "initWithObjects:forKeys:", [rtID, url, []], ["id", "url", "capabilities"]));
                (capabilities == null ? null : (capabilities.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(capabilities, "setValue:forKey:", info, name));
                var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", url + "/capabilities");
                var req = (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,                 function(header, body, error)
                {
                    (info == null ? null : (info.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(info, "setValue:forKey:", (body == null ? null : (body.isa.method_msgSend["objectFromJSON"] || _objj_forward)(body, "objectFromJSON")), "capabilities"));
                    responseBlock(capabilities);
                });
                var ___r1;
            });
        });
        var ___r1;
    });
    var ___r1;
}

,["void","Function"]), new objj_method(sel_getUid("getRuntimeInfoResponseBlock:"), function $CSGBackend__getRuntimeInfoResponseBlock_(self, _cmd, responseBlock)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/index/node/attribute/node_name");
    var req = (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        var response = (body == null ? null : (body.isa.method_msgSend["objectFromJSON"] || _objj_forward)(body, "objectFromJSON"));
        var runtimeList = response.result;
        var runtimeNameAndID = (___r1 = (CPDictionary.isa.method_msgSend["alloc"] || _objj_forward)(CPDictionary, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
        runtimeList.forEach(        function(rtID)
        {
            (self.isa.method_msgSend["_namedRuntime:action:"] || _objj_forward)(self, "_namedRuntime:action:", rtID,             function(name, url)
            {
                (runtimeNameAndID == null ? null : (runtimeNameAndID.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(runtimeNameAndID, "setValue:forKey:", rtID, name));
                responseBlock(runtimeNameAndID);
            });
        });
        var ___r1;
    });
    var ___r1;
}

,["void","Function"]), new objj_method(sel_getUid("_namedRuntime:action:"), function $CSGBackend___namedRuntime_action_(self, _cmd, rtID, action)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/node/" + rtID);
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        var shield = "[" + body + "]";
        var jsObject = (shield == null ? null : (shield.isa.method_msgSend["objectFromJSON"] || _objj_forward)(shield, "objectFromJSON"));
        if (jsObject.length === 0)
        {
            console.log("-_namedRuntime:action: - Empty body returned, BAILING!");
            return;
        }        else
        {
            var attrs = jsObject[0].attributes.indexed_public;
            var re = /\/node\/attribute\/node_name\/[A-Za-z0-9_\-\.\/]*\/([A-Za-z0-9_-]+)/;
            for (var i = 0; i < attrs.length; i++)
            {
                var m = attrs[i].match(re);
                if (m)
                {
                    action(m[1], jsObject[0].control_uris);
                }            }        }    });
    var ___r1;
}

,["void","CPString","Function"]), new objj_method(sel_getUid("authenticatePersistanceUser:withPassword:responseBlock:"), function $CSGBackend__authenticatePersistanceUser_withPassword_responseBlock_(self, _cmd, user, passwd, responseBlock)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["authBase"] || _objj_forward)(___r1, "authBase")) + "/token"),
        body = {"username": user, "password": passwd};
    (request == null ? null : (request.isa.method_msgSend["setHTTPMethod:"] || _objj_forward)(request, "setHTTPMethod:", "POST"));
    (request == null ? null : (request.isa.method_msgSend["setValue:forHTTPHeaderField:"] || _objj_forward)(request, "setValue:forHTTPHeaderField:", "application/json", "Content-Type"));
    (request == null ? null : (request.isa.method_msgSend["setHTTPBody:"] || _objj_forward)(request, "setHTTPBody:", (CPString.isa.method_msgSend["JSONFromObject:"] || _objj_forward)(CPString, "JSONFromObject:", body)));
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        if (error !== nil)
        {
            console.log("Error authenticating", error);
            return;
        }        responseBlock(body);
    });
    var ___r1;
}

,["void","CPString","CPString","Function"]), new objj_method(sel_getUid("storeValue:forKey:authToken:"), function $CSGBackend__storeValue_forKey_authToken_(self, _cmd, value, key, authToken)
{
    var dataString = ((___r1 = (CPKeyedArchiver.isa.method_msgSend["archivedDataWithRootObject:"] || _objj_forward)(CPKeyedArchiver, "archivedDataWithRootObject:", value)), ___r1 == null ? null : (___r1.isa.method_msgSend["rawString"] || _objj_forward)(___r1, "rawString"));
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["persistanceBase"] || _objj_forward)(___r1, "persistanceBase")) + "/store/" + key);
    (request == null ? null : (request.isa.method_msgSend["setHTTPMethod:"] || _objj_forward)(request, "setHTTPMethod:", "POST"));
    (request == null ? null : (request.isa.method_msgSend["setValue:forHTTPHeaderField:"] || _objj_forward)(request, "setValue:forHTTPHeaderField:", "application/json", "Content-Type"));
    var body = {"token": authToken, "data": dataString};
    (request == null ? null : (request.isa.method_msgSend["setHTTPBody:"] || _objj_forward)(request, "setHTTPBody:", (CPString.isa.method_msgSend["JSONFromObject:"] || _objj_forward)(CPString, "JSONFromObject:", body)));
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        if (error !== nil)
        {
            console.log("Error saving", error);
            return;
        }        console.log("saveHandler - save complete");
    });
    var ___r1;
}

,["void","id","CPString","CPString"]), new objj_method(sel_getUid("fetchValueForKey:responseBlock:"), function $CSGBackend__fetchValueForKey_responseBlock_(self, _cmd, key, responseBlock)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["persistanceBase"] || _objj_forward)(___r1, "persistanceBase")) + "/fetch/" + key);
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        if (error !== nil)
        {
            console.log("Error loading", error);
            return;
        }        responseBlock((CPKeyedUnarchiver.isa.method_msgSend["unarchiveObjectWithData:"] || _objj_forward)(CPKeyedUnarchiver, "unarchiveObjectWithData:", (CPData.isa.method_msgSend["dataWithRawString:"] || _objj_forward)(CPData, "dataWithRawString:", body)));
    });
    var ___r1;
}

,["void","CPString","Function"]), new objj_method(sel_getUid("fetchAllKeysUsingResponseBlock:"), function $CSGBackend__fetchAllKeysUsingResponseBlock_(self, _cmd, responseBlock)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["persistanceBase"] || _objj_forward)(___r1, "persistanceBase")) + "/fetch/");
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        if (error !== nil)
        {
            console.log("Error loading", error);
            return;
        }        responseBlock((body == null ? null : (body.isa.method_msgSend["componentsSeparatedByString:"] || _objj_forward)(body, "componentsSeparatedByString:", "\n")));
    });
    var ___r1;
}

,["void","Function"]), new objj_method(sel_getUid("docFor:responseBlock:"), function $CSGBackend__docFor_responseBlock_(self, _cmd, what, responseBlock)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/actor_doc/" + what);
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        if (error !== nil)
        {
            console.log("Error getting docs", error);
            return;
        }        responseBlock((body == null ? null : (body.isa.method_msgSend["objectFromJSON"] || _objj_forward)(body, "objectFromJSON")));
    });
    var ___r1;
}

,["void","CPString","Function"]), new objj_method(sel_getUid("deployScript:withName:responseBlock:"), function $CSGBackend__deployScript_withName_responseBlock_(self, _cmd, script, name, responseBlock)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/deploy");
    (request == null ? null : (request.isa.method_msgSend["setHTTPMethod:"] || _objj_forward)(request, "setHTTPMethod:", "POST"));
    (request == null ? null : (request.isa.method_msgSend["setHTTPBody:"] || _objj_forward)(request, "setHTTPBody:", (CPString.isa.method_msgSend["JSONFromObject:"] || _objj_forward)(CPString, "JSONFromObject:", {"name": name, "script": script})));
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        if (error !== nil)
        {
            console.log("Error deploying script", error);
            return;
        }        var response = (body == null ? null : (body.isa.method_msgSend["objectFromJSON"] || _objj_forward)(body, "objectFromJSON"));
        responseBlock(response);
    });
    var ___r1;
}

,["void","CPString","CPString","Function"]), new objj_method(sel_getUid("stopAppWithID:responseBlock:"), function $CSGBackend__stopAppWithID_responseBlock_(self, _cmd, appID, responseBlock)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/application/" + appID);
    (request == null ? null : (request.isa.method_msgSend["setHTTPMethod:"] || _objj_forward)(request, "setHTTPMethod:", "DELETE"));
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        if (error !== nil)
        {
            console.log("Error stopping script", error);
            return;
        }        responseBlock();
    });
    var ___r1;
}

,["void","CPString","Function"]), new objj_method(sel_getUid("setDeployInfo:forAppID:sender:"), function $CSGBackend__setDeployInfo_forAppID_sender_(self, _cmd, deployInfo, appID, sender)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/application/" + appID + "/migrate");
    (request == null ? null : (request.isa.method_msgSend["setHTTPMethod:"] || _objj_forward)(request, "setHTTPMethod:", "POST"));
    (request == null ? null : (request.isa.method_msgSend["setHTTPBody:"] || _objj_forward)(request, "setHTTPBody:", deployInfo));
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        if (error !== nil)
        {
            console.log("Error sending deploy info", error);
            return;
        }        setTimeout(        function()
        {
            (sender == null ? null : (sender.isa.method_msgSend["updateActorViewForApp:reason:"] || _objj_forward)(sender, "updateActorViewForApp:reason:", appID, "migrate"));
        }, 2000);
    });
    var ___r1;
}

,["void","CPString","CPString","id"]), new objj_method(sel_getUid("updateAvailableApplicationsUsingBlock:"), function $CSGBackend__updateAvailableApplicationsUsingBlock_(self, _cmd, block)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/applications");
    var req = (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        var data = (body == null ? null : (body.isa.method_msgSend["objectFromJSON"] || _objj_forward)(body, "objectFromJSON"));
        block(data);
    });
    var ___r1;
}

,["void","Function"]), new objj_method(sel_getUid("infoForAppID:usingBlock:"), function $CSGBackend__infoForAppID_usingBlock_(self, _cmd, appid, block)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/application/" + appid);
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        var data = (body == null ? null : (body.isa.method_msgSend["objectFromJSON"] || _objj_forward)(body, "objectFromJSON"));
        block(data);
    });
    var ___r1;
}

,["void","CPString","Function"]), new objj_method(sel_getUid("infoForActorID:withResponseBlock:"), function $CSGBackend__infoForActorID_withResponseBlock_(self, _cmd, actorID, block)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/actor/" + actorID);
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        var shield = "[" + body + "]";
        var jsObject = (shield == null ? null : (shield.isa.method_msgSend["objectFromJSON"] || _objj_forward)(shield, "objectFromJSON"));
        if (jsObject.length === 0)
        {
            console.log("-infoForActorID:withResponseBlock: - Empty body returned, BAILING!");
            return;
        }        else
        {
            block(jsObject[0]);
        }    });
    var ___r1;
}

,["void","CPString","Function"]), new objj_method(sel_getUid("infoForNode:actor:port:responseBlock:"), function $CSGBackend__infoForNode_actor_port_responseBlock_(self, _cmd, nodeID, actorID, portID, responseBlock)
{
    if (actorID === nil || portID === nil)
    {
        return;
    }
    (self.isa.method_msgSend["getControlURI_OfNodeId:withResponseBlock:"] || _objj_forward)(self, "getControlURI_OfNodeId:withResponseBlock:", nodeID,     function(url)
    {
        var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", url + "/actor/" + actorID + "/port/" + portID + "/state");
        (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,         function(header, body, error)
        {
            responseBlock((body == null ? null : (body.isa.method_msgSend["objectFromJSON"] || _objj_forward)(body, "objectFromJSON")));
        });
    });
}

,["void","CPString","CPString","CPString","Function"]), new objj_method(sel_getUid("setNodeNameForActorID:sender:"), function $CSGBackend__setNodeNameForActorID_sender_(self, _cmd, actorID, sender)
{
    var ip_request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/actor/" + actorID);
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", ip_request,     function(header, body, error)
    {
        var shield = "[" + body + "]";
        var jsObject = (shield == null ? null : (shield.isa.method_msgSend["objectFromJSON"] || _objj_forward)(shield, "objectFromJSON"));
        if (jsObject.length === 0)
        {
            console.log("-setNodeNameForActorID:sender: - Empty body returned, BAILING!");
            return;
        }        else
        {
            var nodeID = jsObject[0].node_id;
            (sender == null ? null : (sender.isa.method_msgSend["setNodeID:"] || _objj_forward)(sender, "setNodeID:", nodeID));
        }        (self.isa.method_msgSend["_namedRuntime:action:"] || _objj_forward)(self, "_namedRuntime:action:", nodeID,         function(name, url)
        {
            (sender == null ? null : (sender.isa.method_msgSend["setNodeName:"] || _objj_forward)(sender, "setNodeName:", name));
        });
    });
    var ___r1;
}

,["void","CPString","id"]), new objj_method(sel_getUid("actorsOnUIRuntime:"), function $CSGBackend__actorsOnUIRuntime_(self, _cmd, responseBlock)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/actors");
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        var actors = (body == null ? null : (body.isa.method_msgSend["objectFromJSON"] || _objj_forward)(body, "objectFromJSON"));
        responseBlock(actors);
    });
    var ___r1;
}

,["void","Function"]), new objj_method(sel_getUid("migrateActor:toNode:onURL:withResponseBlock:"), function $CSGBackend__migrateActor_toNode_onURL_withResponseBlock_(self, _cmd, actor, peer_nodeID, url, block)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", url + "/actor/" + (actor == null ? null : (actor.isa.method_msgSend["identifier"] || _objj_forward)(actor, "identifier")) + "/migrate");
    (request == null ? null : (request.isa.method_msgSend["setHTTPMethod:"] || _objj_forward)(request, "setHTTPMethod:", "POST"));
    (request == null ? null : (request.isa.method_msgSend["setHTTPBody:"] || _objj_forward)(request, "setHTTPBody:", (CPString.isa.method_msgSend["JSONFromObject:"] || _objj_forward)(CPString, "JSONFromObject:", {"peer_node_id": peer_nodeID})));
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        block(body);
        (actor == null ? null : (actor.isa.method_msgSend["setNodeName:"] || _objj_forward)(actor, "setNodeName:", "<migrating>"));
        setTimeout(        function()
        {
            (self.isa.method_msgSend["setNodeNameForActorID:sender:"] || _objj_forward)(self, "setNodeNameForActorID:sender:", (actor == null ? null : (actor.isa.method_msgSend["identifier"] || _objj_forward)(actor, "identifier")), actor);
        }, 2000);
    });
}

,["void","CSGActor","CPString","CPString","Function"]), new objj_method(sel_getUid("getControlURI_OfNodeId:withResponseBlock:"), function $CSGBackend__getControlURI_OfNodeId_withResponseBlock_(self, _cmd, nodeID, block)
{
    var request = (CPURLRequest.isa.method_msgSend["requestWithURL:"] || _objj_forward)(CPURLRequest, "requestWithURL:", ((___r1 = self.config), ___r1 == null ? null : (___r1.isa.method_msgSend["runtimeBase"] || _objj_forward)(___r1, "runtimeBase")) + "/node/" + nodeID);
    (CSGURLConnection.isa.method_msgSend["connectionWithRequest:responseBlock:"] || _objj_forward)(CSGURLConnection, "connectionWithRequest:responseBlock:", request,     function(header, body, error)
    {
        var shield = "[" + body + "]";
        var jsObject = (shield == null ? null : (shield.isa.method_msgSend["objectFromJSON"] || _objj_forward)(shield, "objectFromJSON"));
        if (jsObject.length === 0)
        {
            console.log("-getControlURI_OfNodeId:withResponseBlock: - Empty body returned, BAILING!");
            return;
        }        else
        {
            block(jsObject[0].control_uris[0]);
        }    });
    var ___r1;
}

,["void","CPString","Function"]), new objj_method(sel_getUid("migrateActor:toNode:"), function $CSGBackend__migrateActor_toNode_(self, _cmd, actor, peer_nodeID)
{
    (self.isa.method_msgSend["infoForActorID:withResponseBlock:"] || _objj_forward)(self, "infoForActorID:withResponseBlock:", (actor == null ? null : (actor.isa.method_msgSend["identifier"] || _objj_forward)(actor, "identifier")),     function(actorInfo)
    {
        (self.isa.method_msgSend["getControlURI_OfNodeId:withResponseBlock:"] || _objj_forward)(self, "getControlURI_OfNodeId:withResponseBlock:", actorInfo.node_id,         function(url)
        {
            (self.isa.method_msgSend["migrateActor:toNode:onURL:withResponseBlock:"] || _objj_forward)(self, "migrateActor:toNode:onURL:withResponseBlock:", actor, peer_nodeID, url,             function()
            {
            });
        });
    });
}

,["void","CSGActor","CPString"])]);
class_addMethods(meta_class, [new objj_method(sel_getUid("sharedBackend"), function $CSGBackend__sharedBackend(self, _cmd)
{
    if (!sharedBackendInstance)
    {
        sharedBackendInstance = ((___r1 = (CSGBackend.isa.method_msgSend["alloc"] || _objj_forward)(CSGBackend, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["_init"] || _objj_forward)(___r1, "_init"));
    }
    return sharedBackendInstance;
    var ___r1;
}

,["id"])]);
}
p;15;CSGHostConfig.jt;7491;@STATIC;1.0;I;23;Foundation/Foundation.jI;22;AppKit/CPApplication.jt;7417;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/CPApplication.j", NO);CSGCalvinHostKey = "calvinHost";
CSGCalvinPortKey = "calvinPort";
CSGPersistanceHostKey = "persistanceHost";
CSGPersistancePortKey = "persistancePort";
CSGAuthHostKey = "authHost";
CSGAuthPortKey = "authPort";
CSGConsoleHostKey = "consoleHost";
CSGConsolePortKey = "consolePort";
CSGContainerIDKey = "containerID";
CGSDefaultConfigPrivate = (___r1 = (CPDictionary.isa.method_msgSend["alloc"] || _objj_forward)(CPDictionary, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithObjects:forKeys:"] || _objj_forward)(___r1, "initWithObjects:forKeys:", ["127.0.0.1", 5001, "localhost", 8081, "localhost", 8081, "localhost", 8087, ""], [CSGCalvinHostKey, CSGCalvinPortKey, CSGPersistanceHostKey, CSGPersistancePortKey, CSGAuthHostKey, CSGAuthPortKey, CSGConsoleHostKey, CSGConsolePortKey, CSGContainerIDKey]));
var sharedHostConfigInstance = nil;

{var the_class = objj_allocateClassPair(CPObject, "CSGHostConfig"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("calvinHost", "CPString"), new objj_ivar("persistanceHost", "CPString"), new objj_ivar("authHost", "CPString"), new objj_ivar("consoleHost", "CPString"), new objj_ivar("calvinPort", "int"), new objj_ivar("persistancePort", "int"), new objj_ivar("authPort", "int"), new objj_ivar("consolePort", "int"), new objj_ivar("containerID", "CPString")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("calvinHost"), function $CSGHostConfig__calvinHost(self, _cmd)
{
    return self.calvinHost;
}

,["CPString"]), new objj_method(sel_getUid("setCalvinHost:"), function $CSGHostConfig__setCalvinHost_(self, _cmd, newValue)
{
    self.calvinHost = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("persistanceHost"), function $CSGHostConfig__persistanceHost(self, _cmd)
{
    return self.persistanceHost;
}

,["CPString"]), new objj_method(sel_getUid("setPersistanceHost:"), function $CSGHostConfig__setPersistanceHost_(self, _cmd, newValue)
{
    self.persistanceHost = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("authHost"), function $CSGHostConfig__authHost(self, _cmd)
{
    return self.authHost;
}

,["CPString"]), new objj_method(sel_getUid("setAuthHost:"), function $CSGHostConfig__setAuthHost_(self, _cmd, newValue)
{
    self.authHost = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("consoleHost"), function $CSGHostConfig__consoleHost(self, _cmd)
{
    return self.consoleHost;
}

,["CPString"]), new objj_method(sel_getUid("setConsoleHost:"), function $CSGHostConfig__setConsoleHost_(self, _cmd, newValue)
{
    self.consoleHost = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("calvinPort"), function $CSGHostConfig__calvinPort(self, _cmd)
{
    return self.calvinPort;
}

,["int"]), new objj_method(sel_getUid("setCalvinPort:"), function $CSGHostConfig__setCalvinPort_(self, _cmd, newValue)
{
    self.calvinPort = newValue;
}

,["void","int"]), new objj_method(sel_getUid("persistancePort"), function $CSGHostConfig__persistancePort(self, _cmd)
{
    return self.persistancePort;
}

,["int"]), new objj_method(sel_getUid("setPersistancePort:"), function $CSGHostConfig__setPersistancePort_(self, _cmd, newValue)
{
    self.persistancePort = newValue;
}

,["void","int"]), new objj_method(sel_getUid("authPort"), function $CSGHostConfig__authPort(self, _cmd)
{
    return self.authPort;
}

,["int"]), new objj_method(sel_getUid("setAuthPort:"), function $CSGHostConfig__setAuthPort_(self, _cmd, newValue)
{
    self.authPort = newValue;
}

,["void","int"]), new objj_method(sel_getUid("consolePort"), function $CSGHostConfig__consolePort(self, _cmd)
{
    return self.consolePort;
}

,["int"]), new objj_method(sel_getUid("setConsolePort:"), function $CSGHostConfig__setConsolePort_(self, _cmd, newValue)
{
    self.consolePort = newValue;
}

,["void","int"]), new objj_method(sel_getUid("containerID"), function $CSGHostConfig__containerID(self, _cmd)
{
    return self.containerID;
}

,["CPString"]), new objj_method(sel_getUid("setContainerID:"), function $CSGHostConfig__setContainerID_(self, _cmd, newValue)
{
    self.containerID = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("init"), function $CSGHostConfig__init(self, _cmd)
{
    (CPException.isa.method_msgSend["raise:reason:"] || _objj_forward)(CPException, "raise:reason:", "CSGHostConfig", "Singleton. Use +sharedHostConfig");
}

,["id"]), new objj_method(sel_getUid("_init"), function $CSGHostConfig___init(self, _cmd)
{
    self = (objj_getClass("CSGHostConfig").super_class.method_dtable["init"] || _objj_forward)(self, "init");
    if (self)
    {
        var defaults = CGSDefaultConfigPrivate;
        var kwargs = ((___r1 = (CPApplication.isa.method_msgSend["sharedApplication"] || _objj_forward)(CPApplication, "sharedApplication")), ___r1 == null ? null : (___r1.isa.method_msgSend["namedArguments"] || _objj_forward)(___r1, "namedArguments"));
        (defaults == null ? null : (defaults.isa.method_msgSend["addEntriesFromDictionary:"] || _objj_forward)(defaults, "addEntriesFromDictionary:", kwargs));
        var keys = (defaults == null ? null : (defaults.isa.method_msgSend["allKeys"] || _objj_forward)(defaults, "allKeys"));
        for (var i = 0; i < keys.length; i++)
        {
            var key = keys[i];
            var value = (defaults == null ? null : (defaults.isa.method_msgSend["valueForKey:"] || _objj_forward)(defaults, "valueForKey:", key));
            try {
                (self == null ? null : (self.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(self, "setValue:forKey:", value, key));
            }
            catch(err) {
                console.log(err, key);
            }
        }
    }
    return self;
    var ___r1;
}

,["id"]), new objj_method(sel_getUid("runtimeBase"), function $CSGHostConfig__runtimeBase(self, _cmd)
{
    if (self.containerID !== "")
    {
        return (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "http://%@:%d/calvin/%@", self.calvinHost, self.calvinPort, self.containerID);
    }
    return (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "http://%@:%d", self.calvinHost, self.calvinPort);
}

,["CPString"]), new objj_method(sel_getUid("authBase"), function $CSGHostConfig__authBase(self, _cmd)
{
    return (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "http://%@:%d", self.authHost, self.authPort);
}

,["CPString"]), new objj_method(sel_getUid("persistanceBase"), function $CSGHostConfig__persistanceBase(self, _cmd)
{
    return (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "http://%@:%d", self.persistanceHost, self.persistancePort);
}

,["CPString"])]);
class_addMethods(meta_class, [new objj_method(sel_getUid("sharedHostConfig"), function $CSGHostConfig__sharedHostConfig(self, _cmd)
{
    if (!sharedHostConfigInstance)
    {
        sharedHostConfigInstance = ((___r1 = (CSGHostConfig.isa.method_msgSend["alloc"] || _objj_forward)(CSGHostConfig, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["_init"] || _objj_forward)(___r1, "_init"));
    }
    return sharedHostConfigInstance;
    var ___r1;
}

,["id"])]);
}
p;18;CSGActorTreeNode.jt;4064;@STATIC;1.0;I;23;Foundation/Foundation.ji;10;CSGActor.jt;4002;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("CSGActor.j", YES);
{var the_class = objj_allocateClassPair(CPObject, "CSGActorTreeNode"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("data", "CPString"), new objj_ivar("path", "CPString"), new objj_ivar("info", "JSObject"), new objj_ivar("documentation", "CPString"), new objj_ivar("isLeaf", "BOOL"), new objj_ivar("children", "CPMutableArray")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("data"), function $CSGActorTreeNode__data(self, _cmd)
{
    return self.data;
}

,["CPString"]), new objj_method(sel_getUid("path"), function $CSGActorTreeNode__path(self, _cmd)
{
    return self.path;
}

,["CPString"]), new objj_method(sel_getUid("setPath:"), function $CSGActorTreeNode__setPath_(self, _cmd, newValue)
{
    self.path = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("info"), function $CSGActorTreeNode__info(self, _cmd)
{
    return self.info;
}

,["JSObject"]), new objj_method(sel_getUid("setInfo:"), function $CSGActorTreeNode__setInfo_(self, _cmd, newValue)
{
    self.info = newValue;
}

,["void","JSObject"]), new objj_method(sel_getUid("documentation"), function $CSGActorTreeNode__documentation(self, _cmd)
{
    return self.documentation;
}

,["CPString"]), new objj_method(sel_getUid("setDocumentation:"), function $CSGActorTreeNode__setDocumentation_(self, _cmd, newValue)
{
    self.documentation = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("isLeaf"), function $CSGActorTreeNode__isLeaf(self, _cmd)
{
    return self.isLeaf;
}

,["BOOL"]), new objj_method(sel_getUid("setIsLeaf:"), function $CSGActorTreeNode__setIsLeaf_(self, _cmd, newValue)
{
    self.isLeaf = newValue;
}

,["void","BOOL"]), new objj_method(sel_getUid("initWithData:"), function $CSGActorTreeNode__initWithData_(self, _cmd, string)
{
    if (self = (objj_getClass("CSGActorTreeNode").super_class.method_dtable["init"] || _objj_forward)(self, "init"))
    {
        self.children = (___r1 = (CPArray.isa.method_msgSend["alloc"] || _objj_forward)(CPArray, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
        self.data = string;
        self.path = string;
        self.documentation = string;
        self.isLeaf = NO;
    }
    return self;
    var ___r1;
}

,["id","CPString"]), new objj_method(sel_getUid("description"), function $CSGActorTreeNode__description(self, _cmd)
{
    return (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "TreeNode%@(%@)", self.isLeaf ? "Leaf" : "", self.path);
}

,["CPString"]), new objj_method(sel_getUid("addChild:"), function $CSGActorTreeNode__addChild_(self, _cmd, child)
{
    if (self.data !== "")
    {
        (child == null ? null : (child.isa.method_msgSend["setPath:"] || _objj_forward)(child, "setPath:", self.data + "." + child.data));
    }
    ((___r1 = self.children), ___r1 == null ? null : (___r1.isa.method_msgSend["addObject:"] || _objj_forward)(___r1, "addObject:", child));
    var ___r1;
}

,["void","CSGActorTreeNode"]), new objj_method(sel_getUid("childAtIndex:"), function $CSGActorTreeNode__childAtIndex_(self, _cmd, index)
{
    return ((___r1 = self.children), ___r1 == null ? null : (___r1.isa.method_msgSend["objectAtIndex:"] || _objj_forward)(___r1, "objectAtIndex:", index));
    var ___r1;
}

,["CSGActorTreeNode","int"]), new objj_method(sel_getUid("count"), function $CSGActorTreeNode__count(self, _cmd)
{
    return ((___r1 = self.children), ___r1 == null ? null : (___r1.isa.method_msgSend["count"] || _objj_forward)(___r1, "count"));
    var ___r1;
}

,["int"]), new objj_method(sel_getUid("setInfo:"), function $CSGActorTreeNode__setInfo_(self, _cmd, actorInfo)
{
    self.info = actorInfo;
    (self.isa.method_msgSend["setDocumentation:"] || _objj_forward)(self, "setDocumentation:", CSGActorDocsFromJSONRep(actorInfo));
}

,["void","JSObject"])]);
}
p;10;CSGActor.jt;20639;@STATIC;1.0;I;23;Foundation/Foundation.ji;14;CSGComponent.ji;9;CSGPort.jt;20559;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("CSGComponent.j", YES);objj_executeFile("CSGPort.j", YES);CSGActorDocsFromJSONRep = function(jrep)
{
    if (!jrep)
    {
        return (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "No documentation");
    }
    if (!jrep.name)
    {
        return (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "%@\n", jrep["long_desc"]);
    }
    var docs = (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "%@.%@\n\n%@\n", jrep["ns"], jrep["name"], jrep["long_desc"]),
        ports = jrep["inputs"];
    if (ports.length > 0)
    {
        docs = (docs == null ? null : (docs.isa.method_msgSend["stringByAppendingString:"] || _objj_forward)(docs, "stringByAppendingString:", "\nInports:\n"));
    }
    for (var i = 0; i < ports.length; i++)
    {
        var pstring = (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "\t%s : %s\n", ports[i], jrep.input_docs[ports[i]]);
        docs = (docs == null ? null : (docs.isa.method_msgSend["stringByAppendingString:"] || _objj_forward)(docs, "stringByAppendingString:", pstring));
    }
    ports = jrep["outputs"];
    if (ports.length > 0)
    {
        docs = (docs == null ? null : (docs.isa.method_msgSend["stringByAppendingString:"] || _objj_forward)(docs, "stringByAppendingString:", "\nOutports:\n"));
    }
    for (var i = 0; i < ports.length; i++)
    {
        var pstring = (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "\t%s : %s\n", ports[i], jrep.output_docs[ports[i]]);
        docs = (docs == null ? null : (docs.isa.method_msgSend["stringByAppendingString:"] || _objj_forward)(docs, "stringByAppendingString:", pstring));
    }
    var reqs = jrep["requires"] || [];
    if (reqs.length > 0)
    {
        docs = (docs == null ? null : (docs.isa.method_msgSend["stringByAppendingString:"] || _objj_forward)(docs, "stringByAppendingString:", "\nRequirements:\n\t" + reqs.join(", ")));
    }
    return docs;
}

{var the_class = objj_allocateClassPair(CSGComponent, "CSGActor"),
meta_class = the_class.isa;
var aProtocol = objj_getProtocol("CPCoding");
if (!aProtocol) throw new SyntaxError("*** Could not find definition for protocol \"CPCoding\"");
class_addProtocol(the_class, aProtocol);class_addIvars(the_class, [new objj_ivar("mandatoryArgs", "CPMutableDictionary"), new objj_ivar("argOK", "CPMutableDictionary"), new objj_ivar("optionalArgs", "CPMutableDictionary"), new objj_ivar("inports", "CPArray"), new objj_ivar("outports", "CPArray"), new objj_ivar("type", "CPString"), new objj_ivar("name", "CPString"), new objj_ivar("isComponent", "BOOL"), new objj_ivar("docs", "CPString"), new objj_ivar("bounds", "CGRect"), new objj_ivar("validBounds", "BOOL"), new objj_ivar("identifier", "CPString"), new objj_ivar("status", "CPString"), new objj_ivar("nodeID", "CPString"), new objj_ivar("nodeName", "CPString"), new objj_ivar("uiState", "CPString")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("mandatoryArgs"), function $CSGActor__mandatoryArgs(self, _cmd)
{
    return self.mandatoryArgs;
}

,["CPMutableDictionary"]), new objj_method(sel_getUid("setMandatoryArgs:"), function $CSGActor__setMandatoryArgs_(self, _cmd, newValue)
{
    self.mandatoryArgs = newValue;
}

,["void","CPMutableDictionary"]), new objj_method(sel_getUid("argOK"), function $CSGActor__argOK(self, _cmd)
{
    return self.argOK;
}

,["CPMutableDictionary"]), new objj_method(sel_getUid("setArgOK:"), function $CSGActor__setArgOK_(self, _cmd, newValue)
{
    self.argOK = newValue;
}

,["void","CPMutableDictionary"]), new objj_method(sel_getUid("optionalArgs"), function $CSGActor__optionalArgs(self, _cmd)
{
    return self.optionalArgs;
}

,["CPMutableDictionary"]), new objj_method(sel_getUid("setOptionalArgs:"), function $CSGActor__setOptionalArgs_(self, _cmd, newValue)
{
    self.optionalArgs = newValue;
}

,["void","CPMutableDictionary"]), new objj_method(sel_getUid("inports"), function $CSGActor__inports(self, _cmd)
{
    return self.inports;
}

,["CPArray"]), new objj_method(sel_getUid("setInports:"), function $CSGActor__setInports_(self, _cmd, newValue)
{
    self.inports = newValue;
}

,["void","CPArray"]), new objj_method(sel_getUid("outports"), function $CSGActor__outports(self, _cmd)
{
    return self.outports;
}

,["CPArray"]), new objj_method(sel_getUid("setOutports:"), function $CSGActor__setOutports_(self, _cmd, newValue)
{
    self.outports = newValue;
}

,["void","CPArray"]), new objj_method(sel_getUid("type"), function $CSGActor__type(self, _cmd)
{
    return self.type;
}

,["CPString"]), new objj_method(sel_getUid("setType:"), function $CSGActor__setType_(self, _cmd, newValue)
{
    self.type = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("name"), function $CSGActor__name(self, _cmd)
{
    return self.name;
}

,["CPString"]), new objj_method(sel_getUid("setName:"), function $CSGActor__setName_(self, _cmd, newValue)
{
    self.name = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("isComponent"), function $CSGActor__isComponent(self, _cmd)
{
    return self.isComponent;
}

,["BOOL"]), new objj_method(sel_getUid("setIsComponent:"), function $CSGActor__setIsComponent_(self, _cmd, newValue)
{
    self.isComponent = newValue;
}

,["void","BOOL"]), new objj_method(sel_getUid("docs"), function $CSGActor__docs(self, _cmd)
{
    return self.docs;
}

,["CPString"]), new objj_method(sel_getUid("identifier"), function $CSGActor__identifier(self, _cmd)
{
    return self.identifier;
}

,["CPString"]), new objj_method(sel_getUid("setIdentifier:"), function $CSGActor__setIdentifier_(self, _cmd, newValue)
{
    self.identifier = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("status"), function $CSGActor__status(self, _cmd)
{
    return self.status;
}

,["CPString"]), new objj_method(sel_getUid("setStatus:"), function $CSGActor__setStatus_(self, _cmd, newValue)
{
    self.status = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("nodeID"), function $CSGActor__nodeID(self, _cmd)
{
    return self.nodeID;
}

,["CPString"]), new objj_method(sel_getUid("setNodeID:"), function $CSGActor__setNodeID_(self, _cmd, newValue)
{
    self.nodeID = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("nodeName"), function $CSGActor__nodeName(self, _cmd)
{
    return self.nodeName;
}

,["CPString"]), new objj_method(sel_getUid("setNodeName:"), function $CSGActor__setNodeName_(self, _cmd, newValue)
{
    self.nodeName = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("uiState"), function $CSGActor__uiState(self, _cmd)
{
    return self.uiState;
}

,["CPString"]), new objj_method(sel_getUid("setUiState:"), function $CSGActor__setUiState_(self, _cmd, newValue)
{
    self.uiState = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("initWithJSObject:"), function $CSGActor__initWithJSObject_(self, _cmd, jrep)
{
    self = (objj_getClass("CSGActor").super_class.method_dtable["init"] || _objj_forward)(self, "init");
    if (self)
    {
        self.mandatoryArgs = (CPMutableDictionary.isa.method_msgSend["dictionary"] || _objj_forward)(CPMutableDictionary, "dictionary");
        var keys = jrep["args"]["mandatory"];
        for (var i = 0; i < keys.length; i++)
        {
            ((___r1 = self.mandatoryArgs), ___r1 == null ? null : (___r1.isa.method_msgSend["setObject:forKey:"] || _objj_forward)(___r1, "setObject:forKey:", "", keys[i]));
        }
        var proto = jrep["args"]["optional"];
        keys = Object.keys(proto);
        self.optionalArgs = (CPMutableDictionary.isa.method_msgSend["dictionary"] || _objj_forward)(CPMutableDictionary, "dictionary");
        for (var i = 0; i < keys.length; i++)
        {
            var key = keys[i];
            var arg = JSON.stringify(proto[key]);
            ((___r1 = self.optionalArgs), ___r1 == null ? null : (___r1.isa.method_msgSend["setObject:forKey:"] || _objj_forward)(___r1, "setObject:forKey:", arg, key));
        }
        self.inports = (CPMutableArray.isa.method_msgSend["array"] || _objj_forward)(CPMutableArray, "array");
        proto = jrep["inputs"];
        for (var i = 0; i < proto.length; i++)
        {
            var pname = proto[i];
            ((___r1 = self.inports), ___r1 == null ? null : (___r1.isa.method_msgSend["addObject:"] || _objj_forward)(___r1, "addObject:", (CSGPort.isa.method_msgSend["inportWithName:"] || _objj_forward)(CSGPort, "inportWithName:", pname)));
        }
        self.outports = (CPMutableArray.isa.method_msgSend["array"] || _objj_forward)(CPMutableArray, "array");
        proto = jrep["outputs"];
        for (var i = 0; i < proto.length; i++)
        {
            var pname = proto[i];
            ((___r1 = self.outports), ___r1 == null ? null : (___r1.isa.method_msgSend["addObject:"] || _objj_forward)(___r1, "addObject:", (CSGPort.isa.method_msgSend["outportWithName:"] || _objj_forward)(CSGPort, "outportWithName:", pname)));
        }
        self.type = (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "%@.%@", jrep["ns"], jrep["name"]);
        self.name = "prototype";
        self.isComponent = !((___r1 = "actor"), ___r1 == null ? null : (___r1.isa.method_msgSend["isEqualToString:"] || _objj_forward)(___r1, "isEqualToString:", jrep["type"]));
        self.docs = CSGActorDocsFromJSONRep(jrep);
        self.bounds = CPMakeRect(0, 0, 0, 0);
        self.validBounds = NO;
        self.argOK = (___r1 = (CPDictionary.isa.method_msgSend["alloc"] || _objj_forward)(CPDictionary, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
        (self == null ? null : (self.isa.method_msgSend["validateAll:"] || _objj_forward)(self, "validateAll:", self.mandatoryArgs));
        (self == null ? null : (self.isa.method_msgSend["validateAll:"] || _objj_forward)(self, "validateAll:", self.optionalArgs));
    }
    return self;
    var ___r1;
}

,["id","Object"]), new objj_method(sel_getUid("initWithCoder:"), function $CSGActor__initWithCoder_(self, _cmd, coder)
{
    self = (objj_getClass("CSGActor").super_class.method_dtable["init"] || _objj_forward)(self, "init");
    if (self)
    {
        self.mandatoryArgs = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "mandatoryArgs"));
        self.optionalArgs = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "optionalArgs"));
        self.inports = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "inports"));
        self.outports = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "outports"));
        self.type = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "type"));
        self.name = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "name"));
        self.isComponent = (coder == null ? null : (coder.isa.method_msgSend["decodeBoolForKey:"] || _objj_forward)(coder, "decodeBoolForKey:", "isComponent"));
        self.docs = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "docs"));
        self.bounds = (coder == null ? null : (coder.isa.method_msgSend["decodeRectForKey:"] || _objj_forward)(coder, "decodeRectForKey:", "bounds"));
        self.validBounds = NO;
        self.argOK = (___r1 = (CPDictionary.isa.method_msgSend["alloc"] || _objj_forward)(CPDictionary, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
        (self == null ? null : (self.isa.method_msgSend["validateAll:"] || _objj_forward)(self, "validateAll:", self.mandatoryArgs));
        (self == null ? null : (self.isa.method_msgSend["validateAll:"] || _objj_forward)(self, "validateAll:", self.optionalArgs));
    }
    return self;
    var ___r1;
}

,["id","CPCoder"]), new objj_method(sel_getUid("encodeWithCoder:"), function $CSGActor__encodeWithCoder_(self, _cmd, coder)
{
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.mandatoryArgs, "mandatoryArgs"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.optionalArgs, "optionalArgs"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.inports, "inports"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.outports, "outports"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.type, "type"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.name, "name"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeBool:forKey:"] || _objj_forward)(coder, "encodeBool:forKey:", self.isComponent, "isComponent"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.docs, "docs"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeRect:forKey:"] || _objj_forward)(coder, "encodeRect:forKey:", self.bounds, "bounds"));
}

,["void","CPCoder"]), new objj_method(sel_getUid("hasValidMandatoryArgs"), function $CSGActor__hasValidMandatoryArgs(self, _cmd)
{
    var ok_list = ((___r1 = self.argOK), ___r1 == null ? null : (___r1.isa.method_msgSend["allValues"] || _objj_forward)(___r1, "allValues"));
    for (var i = 0; i < ok_list.length; i++)
    {
        if (!ok_list[i])
        {
            return NO;
        }
    }
    return YES;
    var ___r1;
}

,["BOOL"]), new objj_method(sel_getUid("isValidArg:"), function $CSGActor__isValidArg_(self, _cmd, arg)
{
    try {
        var json_value = JSON.parse(arg);
    }
    catch(e) {
        return NO;
    }
    return YES;
}

,["BOOl","CPString"]), new objj_method(sel_getUid("validateAll:"), function $CSGActor__validateAll_(self, _cmd, argDict)
{
    var keys = (argDict == null ? null : (argDict.isa.method_msgSend["allKeys"] || _objj_forward)(argDict, "allKeys"));
    keys.forEach(    function(key)
    {
        (self.isa.method_msgSend["validate:forKey:"] || _objj_forward)(self, "validate:forKey:", argDict, key);
    });
}

,["void","CPDictionary"]), new objj_method(sel_getUid("validate:forKey:"), function $CSGActor__validate_forKey_(self, _cmd, argDict, key)
{
    var value = (argDict == null ? null : (argDict.isa.method_msgSend["valueForKey:"] || _objj_forward)(argDict, "valueForKey:", key));
    var isValid = (self.isa.method_msgSend["isValidArg:"] || _objj_forward)(self, "isValidArg:", value);
    ((___r1 = self.argOK), ___r1 == null ? null : (___r1.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(___r1, "setValue:forKey:", isValid, key));
    var ___r1;
}

,["void","CPDictionary","CPString"]), new objj_method(sel_getUid("setMandatoryValue:forKey:"), function $CSGActor__setMandatoryValue_forKey_(self, _cmd, value, key)
{
    ((___r1 = self.mandatoryArgs), ___r1 == null ? null : (___r1.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(___r1, "setValue:forKey:", value, key));
    (self.isa.method_msgSend["validate:forKey:"] || _objj_forward)(self, "validate:forKey:", self.mandatoryArgs, key);
    var ___r1;
}

,["void","id","CPString"]), new objj_method(sel_getUid("setOptionalValue:forKey:"), function $CSGActor__setOptionalValue_forKey_(self, _cmd, value, key)
{
    ((___r1 = self.optionalArgs), ___r1 == null ? null : (___r1.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(___r1, "setValue:forKey:", value, key));
    (self.isa.method_msgSend["validate:forKey:"] || _objj_forward)(self, "validate:forKey:", self.optionalArgs, key);
    var ___r1;
}

,["void","id","CPString"]), new objj_method(sel_getUid("origin"), function $CSGActor__origin(self, _cmd)
{
    return self.bounds.origin;
}

,["CGPoint"]), new objj_method(sel_getUid("setOrigin:"), function $CSGActor__setOrigin_(self, _cmd, origin)
{
    self.bounds.origin = origin;
}

,["void","CGPoint"]), new objj_method(sel_getUid("size"), function $CSGActor__size(self, _cmd)
{
    return self.bounds.size;
}

,["CGSize"]), new objj_method(sel_getUid("setSize:"), function $CSGActor__setSize_(self, _cmd, size)
{
    self.bounds.size = size;
}

,["void","CGSize"]), new objj_method(sel_getUid("inportWithName:"), function $CSGActor__inportWithName_(self, _cmd, aName)
{
    return (self.isa.method_msgSend["portWithName:isOutport:"] || _objj_forward)(self, "portWithName:isOutport:", aName, NO);
}

,["CSGPort","CPString"]), new objj_method(sel_getUid("outportWithName:"), function $CSGActor__outportWithName_(self, _cmd, aName)
{
    return (self.isa.method_msgSend["portWithName:isOutport:"] || _objj_forward)(self, "portWithName:isOutport:", aName, YES);
}

,["CSGPort","CPString"]), new objj_method(sel_getUid("portWithName:isOutport:"), function $CSGActor__portWithName_isOutport_(self, _cmd, aName, isOutport)
{
    var ports = isOutport ? self.outports : self.inports;
    for (var i = 0; i < ports.length; i++)
    {
        var port = ports[i];
        if ((port == null ? null : (port.isa.method_msgSend["name"] || _objj_forward)(port, "name")) === aName)
        {
            return port;
        }
    }
    return (CPNull.isa.method_msgSend["null"] || _objj_forward)(CPNull, "null");
}

,["CSGPort","CPString","BOOL"]), new objj_method(sel_getUid("scriptRepresentation"), function $CSGActor__scriptRepresentation(self, _cmd)
{
    formatArg = function(key, value)
    {
        return (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "%@=%@", key, value);
    }
    var args = ((___r1 = (CPMutableArray.isa.method_msgSend["alloc"] || _objj_forward)(CPMutableArray, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init")),
        keys = ((___r1 = ((___r2 = self.mandatoryArgs), ___r2 == null ? null : (___r2.isa.method_msgSend["allKeys"] || _objj_forward)(___r2, "allKeys"))), ___r1 == null ? null : (___r1.isa.method_msgSend["sortedArrayUsingSelector:"] || _objj_forward)(___r1, "sortedArrayUsingSelector:", sel_getUid("caseInsensitiveCompare:"))),
        optKeys = ((___r1 = ((___r2 = self.optionalArgs), ___r2 == null ? null : (___r2.isa.method_msgSend["allKeys"] || _objj_forward)(___r2, "allKeys"))), ___r1 == null ? null : (___r1.isa.method_msgSend["sortedArrayUsingSelector:"] || _objj_forward)(___r1, "sortedArrayUsingSelector:", sel_getUid("caseInsensitiveCompare:")));
    for (var i = 0; i < keys.length; i++)
    {
        var key = keys[i];
        var validArg = ((___r1 = self.argOK), ___r1 == null ? null : (___r1.isa.method_msgSend["valueForKey:"] || _objj_forward)(___r1, "valueForKey:", key));
        if (validArg)
        {
            (args == null ? null : (args.isa.method_msgSend["addObject:"] || _objj_forward)(args, "addObject:", formatArg(key, ((___r1 = self.mandatoryArgs), ___r1 == null ? null : (___r1.isa.method_msgSend["valueForKey:"] || _objj_forward)(___r1, "valueForKey:", key)))));
        }
    }
    for (var i = 0; i < optKeys.length; i++)
    {
        var key = optKeys[i];
        (args == null ? null : (args.isa.method_msgSend["addObject:"] || _objj_forward)(args, "addObject:", formatArg(key, ((___r1 = self.optionalArgs), ___r1 == null ? null : (___r1.isa.method_msgSend["valueForKey:"] || _objj_forward)(___r1, "valueForKey:", key)))));
    }
    var argRep = (args == null ? null : (args.isa.method_msgSend["componentsJoinedByString:"] || _objj_forward)(args, "componentsJoinedByString:", ", "));
    return (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "%@ : %@(%@)", self.name, self.type, argRep);
    var ___r1, ___r2;
}

,["CPString"])]);
}
p;14;CSGComponent.jt;885;@STATIC;1.0;I;23;Foundation/Foundation.jt;839;objj_executeFile("Foundation/Foundation.j", NO);
{var the_class = objj_allocateClassPair(CPObject, "CSGComponent"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("_selected", "BOOL")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("isSelected"), function $CSGComponent__isSelected(self, _cmd)
{
    return self._selected;
}

,["BOOL"]), new objj_method(sel_getUid("setSelected:"), function $CSGComponent__setSelected_(self, _cmd, newValue)
{
    self._selected = newValue;
}

,["void","BOOL"]), new objj_method(sel_getUid("init"), function $CSGComponent__init(self, _cmd)
{
    self = (objj_getClass("CSGComponent").super_class.method_dtable["init"] || _objj_forward)(self, "init");
    if (self)
    {
        self._selected = NO;
    }
    return self;
}

,["id"])]);
}
p;9;CSGPort.jt;3357;@STATIC;1.0;I;23;Foundation/Foundation.jt;3310;objj_executeFile("Foundation/Foundation.j", NO);
{var the_class = objj_allocateClassPair(CPObject, "CSGPort"),
meta_class = the_class.isa;
var aProtocol = objj_getProtocol("CPCoding");
if (!aProtocol) throw new SyntaxError("*** Could not find definition for protocol \"CPCoding\"");
class_addProtocol(the_class, aProtocol);class_addIvars(the_class, [new objj_ivar("portName", "CPString"), new objj_ivar("isInport", "BOOL"), new objj_ivar("portSize", "CGSize")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("name"), function $CSGPort__name(self, _cmd)
{
    return self.portName;
}

,["CPString"]), new objj_method(sel_getUid("setPortName:"), function $CSGPort__setPortName_(self, _cmd, newValue)
{
    self.portName = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("isInport"), function $CSGPort__isInport(self, _cmd)
{
    return self.isInport;
}

,["BOOL"]), new objj_method(sel_getUid("setIsInport:"), function $CSGPort__setIsInport_(self, _cmd, newValue)
{
    self.isInport = newValue;
}

,["void","BOOL"]), new objj_method(sel_getUid("initWithName:isInport:"), function $CSGPort__initWithName_isInport_(self, _cmd, name, flag)
{
    if (self = (objj_getClass("CSGPort").super_class.method_dtable["init"] || _objj_forward)(self, "init"))
    {
        self.portName = name;
        self.isInport = flag;
        self.portSize = CGSizeMakeZero();
    }
    return self;
}

,["id","CPString","BOOL"]), new objj_method(sel_getUid("initWithCoder:"), function $CSGPort__initWithCoder_(self, _cmd, coder)
{
    self = (objj_getClass("CSGPort").super_class.method_dtable["init"] || _objj_forward)(self, "init");
    if (self)
    {
        self.portName = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "portName"));
        self.isInport = (coder == null ? null : (coder.isa.method_msgSend["decodeBoolForKey:"] || _objj_forward)(coder, "decodeBoolForKey:", "isInport"));
        self.portSize = CGSizeMakeZero();
    }
    return self;
}

,["id","CPCoder"]), new objj_method(sel_getUid("encodeWithCoder:"), function $CSGPort__encodeWithCoder_(self, _cmd, coder)
{
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.portName, "portName"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeBool:forKey:"] || _objj_forward)(coder, "encodeBool:forKey:", self.isInport, "isInport"));
}

,["void","CPCoder"])]);
class_addMethods(meta_class, [new objj_method(sel_getUid("inportWithName:"), function $CSGPort__inportWithName_(self, _cmd, name)
{
    return ((___r1 = (self.isa.method_msgSend["alloc"] || _objj_forward)(self, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithName:isInport:"] || _objj_forward)(___r1, "initWithName:isInport:", name, YES));
    var ___r1;
}

,["id","CPString"]), new objj_method(sel_getUid("outportWithName:"), function $CSGPort__outportWithName_(self, _cmd, name)
{
    return ((___r1 = (self.isa.method_msgSend["alloc"] || _objj_forward)(self, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithName:isInport:"] || _objj_forward)(___r1, "initWithName:isInport:", name, NO));
    var ___r1;
}

,["id","CPString"])]);
}
p;22;CSGProjectController.jt;21298;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;12;CSGProgram.ji;16;CSGProgramView.ji;12;CSGProject.ji;12;CSGBackend.ji;20;CSGDataPersistance.jt;21133;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGProgram.j", YES);objj_executeFile("CSGProgramView.j", YES);objj_executeFile("CSGProject.j", YES);objj_executeFile("CSGBackend.j", YES);objj_executeFile("CSGDataPersistance.j", YES);
{var the_class = objj_allocateClassPair(CPViewController, "CSGProjectController"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("projects", "CPMutableArray"), new objj_ivar("currentProject", "CSGProject"), new objj_ivar("backend", "CSGBackend"), new objj_ivar("openSheet", "CPWindow"), new objj_ivar("projectTable", "CPTableView"), new objj_ivar("availableProjects", "CPArray"), new objj_ivar("tentativeProjectName", "CPString"), new objj_ivar("saveSheet", "CPWindow"), new objj_ivar("saveProjectName", "CPTextField"), new objj_ivar("saveUserName", "CPTextField"), new objj_ivar("savePassword", "CPSecureTextField"), new objj_ivar("programView", "CSGProgramView"), new objj_ivar("untitled_count", "int")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("projects"), function $CSGProjectController__projects(self, _cmd)
{
    return self.projects;
}

,["CPMutableArray"]), new objj_method(sel_getUid("setProjects:"), function $CSGProjectController__setProjects_(self, _cmd, newValue)
{
    self.projects = newValue;
}

,["void","CPMutableArray"]), new objj_method(sel_getUid("currentProject"), function $CSGProjectController__currentProject(self, _cmd)
{
    return self.currentProject;
}

,["CSGProject"]), new objj_method(sel_getUid("setCurrentProject:"), function $CSGProjectController__setCurrentProject_(self, _cmd, newValue)
{
    self.currentProject = newValue;
}

,["void","CSGProject"]), new objj_method(sel_getUid("availableProjects"), function $CSGProjectController__availableProjects(self, _cmd)
{
    return self.availableProjects;
}

,["CPArray"]), new objj_method(sel_getUid("setAvailableProjects:"), function $CSGProjectController__setAvailableProjects_(self, _cmd, newValue)
{
    self.availableProjects = newValue;
}

,["void","CPArray"]), new objj_method(sel_getUid("programView"), function $CSGProjectController__programView(self, _cmd)
{
    return self.programView;
}

,["CSGProgramView"]), new objj_method(sel_getUid("init"), function $CSGProjectController__init(self, _cmd)
{
    self = (objj_getClass("CSGProjectController").super_class.method_dtable["initWithCibName:bundle:externalNameTable:"] || _objj_forward)(self, "initWithCibName:bundle:externalNameTable:", "ProjectView", nil, nil);
    if (self)
    {
        self.untitled_count = 0;
        self.projects = (___r1 = (CPArray.isa.method_msgSend["alloc"] || _objj_forward)(CPArray, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
        self.backend = (CSGBackend.isa.method_msgSend["sharedBackend"] || _objj_forward)(CSGBackend, "sharedBackend");
    }
    return self;
    var ___r1;
}

,["id"]), new objj_method(sel_getUid("acceptsFirstResponder"), function $CSGProjectController__acceptsFirstResponder(self, _cmd)
{
    return YES;
}

,["BOOL"]), new objj_method(sel_getUid("nameForUntitled"), function $CSGProjectController__nameForUntitled(self, _cmd)
{
    var suffix = self.untitled_count ? (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "-%d", self.untitled_count) : "";
    self.untitled_count++;
    return "Untitled" + suffix;
}

,["CPString"]), new objj_method(sel_getUid("setCurrentProject:"), function $CSGProjectController__setCurrentProject_(self, _cmd, project)
{
    if (project == self.currentProject)
    {
        return;
    }
    ((___r1 = self.currentProject), ___r1 == null ? null : (___r1.isa.method_msgSend["deactivate"] || _objj_forward)(___r1, "deactivate"));
    self.currentProject = project;
    ((___r1 = self.currentProject), ___r1 == null ? null : (___r1.isa.method_msgSend["activate"] || _objj_forward)(___r1, "activate"));
    var ___r1;
}

,["void","CSGProject"]), new objj_method(sel_getUid("currentProgram"), function $CSGProjectController__currentProgram(self, _cmd)
{
    return ((___r1 = self.currentProject), ___r1 == null ? null : (___r1.isa.method_msgSend["program"] || _objj_forward)(___r1, "program"));
    var ___r1;
}

,["CSGProgram"]), new objj_method(sel_getUid("projectWithAppID:"), function $CSGProjectController__projectWithAppID_(self, _cmd, app_id)
{
    for (var i = 0; i < self.projects.length; i++)
    {
        var proj = self.projects[i];
        if ((proj == null ? null : (proj.isa.method_msgSend["appID"] || _objj_forward)(proj, "appID")) === app_id)
        {
            return proj;
        }
    }
    return nil;
}

,["CSGProject","CPString"]), new objj_method(sel_getUid("awakeFromCib"), function $CSGProjectController__awakeFromCib(self, _cmd)
{
    if (self.untitled_count > 0)
    {
        CPLog.debug("CSGProjectController::awakeFromCib - been here, done that.");
        return;
    }
    var win = ((___r1 = (CPApp == null ? null : (CPApp.isa.method_msgSend["delegate"] || _objj_forward)(CPApp, "delegate"))), ___r1 == null ? null : (___r1.isa.method_msgSend["theWindow"] || _objj_forward)(___r1, "theWindow"));
    var nextResponder = (win == null ? null : (win.isa.method_msgSend["nextResponder"] || _objj_forward)(win, "nextResponder"));
    (win == null ? null : (win.isa.method_msgSend["setNextResponder:"] || _objj_forward)(win, "setNextResponder:", self));
    (self.isa.method_msgSend["setNextResponder:"] || _objj_forward)(self, "setNextResponder:", nextResponder);
    (self.isa.method_msgSend["addObserver:forKeyPath:options:context:"] || _objj_forward)(self, "addObserver:forKeyPath:options:context:", self.programView, "currentProject", CPKeyValueObservingOptionNew | CPKeyValueObservingOptionOld, nil);
    (self.isa.method_msgSend["addObserver:forKeyPath:options:context:"] || _objj_forward)(self, "addObserver:forKeyPath:options:context:", (CPApp == null ? null : (CPApp.isa.method_msgSend["delegate"] || _objj_forward)(CPApp, "delegate")), "currentProject.appID", CPKeyValueObservingOptionNew, nil);
    var proj = ((___r1 = (CSGProject.isa.method_msgSend["alloc"] || _objj_forward)(CSGProject, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithName:"] || _objj_forward)(___r1, "initWithName:", (self.isa.method_msgSend["nameForUntitled"] || _objj_forward)(self, "nameForUntitled")));
    (self.isa.method_msgSend["setProjects:"] || _objj_forward)(self, "setProjects:", (___r1 = (CPArray.isa.method_msgSend["alloc"] || _objj_forward)(CPArray, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithObjects:count:"] || _objj_forward)(___r1, "initWithObjects:count:", [proj], 1)));
    (self.isa.method_msgSend["setCurrentProject:"] || _objj_forward)(self, "setCurrentProject:", proj);
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("newProject:"), function $CSGProjectController__newProject_(self, _cmd, sender)
{
    var proj = ((___r1 = (CSGProject.isa.method_msgSend["alloc"] || _objj_forward)(CSGProject, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithName:"] || _objj_forward)(___r1, "initWithName:", (self.isa.method_msgSend["nameForUntitled"] || _objj_forward)(self, "nameForUntitled")));
    (self.isa.method_msgSend["willChangeValueForKey:"] || _objj_forward)(self, "willChangeValueForKey:", "projects");
    ((___r1 = self.projects), ___r1 == null ? null : (___r1.isa.method_msgSend["addObject:"] || _objj_forward)(___r1, "addObject:", proj));
    (self.isa.method_msgSend["didChangeValueForKey:"] || _objj_forward)(self, "didChangeValueForKey:", "projects");
    (self.isa.method_msgSend["setCurrentProject:"] || _objj_forward)(self, "setCurrentProject:", proj);
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("closeProject:"), function $CSGProjectController__closeProject_(self, _cmd, sender)
{
    var index = ((___r1 = self.projects), ___r1 == null ? null : (___r1.isa.method_msgSend["indexOfObject:"] || _objj_forward)(___r1, "indexOfObject:", self.currentProject));
    (self.isa.method_msgSend["willChangeValueForKey:"] || _objj_forward)(self, "willChangeValueForKey:", "projects");
    ((___r1 = self.projects), ___r1 == null ? null : (___r1.isa.method_msgSend["removeObjectAtIndex:"] || _objj_forward)(___r1, "removeObjectAtIndex:", index));
    if (self.projects.length === 0)
    {
        var proj = ((___r1 = (CSGProject.isa.method_msgSend["alloc"] || _objj_forward)(CSGProject, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithName:"] || _objj_forward)(___r1, "initWithName:", (self.isa.method_msgSend["nameForUntitled"] || _objj_forward)(self, "nameForUntitled")));
        ((___r1 = self.projects), ___r1 == null ? null : (___r1.isa.method_msgSend["addObject:"] || _objj_forward)(___r1, "addObject:", proj));
    }
    (self.isa.method_msgSend["didChangeValueForKey:"] || _objj_forward)(self, "didChangeValueForKey:", "projects");
    index--;
    index = (index + self.projects.length) % self.projects.length;
    (self.isa.method_msgSend["setCurrentProject:"] || _objj_forward)(self, "setCurrentProject:", ((___r1 = self.projects), ___r1 == null ? null : (___r1.isa.method_msgSend["objectAtIndex:"] || _objj_forward)(___r1, "objectAtIndex:", index)));
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("saveProject:"), function $CSGProjectController__saveProject_(self, _cmd, sender)
{
    var current = (self.isa.method_msgSend["currentProject"] || _objj_forward)(self, "currentProject");
    if ((current == null ? null : (current.isa.method_msgSend["isUntitled"] || _objj_forward)(current, "isUntitled")))
    {
        (self.isa.method_msgSend["saveProjectAs:"] || _objj_forward)(self, "saveProjectAs:", self);
    }
    else
    {
        var db = ((___r1 = (CSGLocalPersistence.isa.method_msgSend["alloc"] || _objj_forward)(CSGLocalPersistence, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
        (db == null ? null : (db.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(db, "setValue:forKey:", current, (current == null ? null : (current.isa.method_msgSend["name"] || _objj_forward)(current, "name"))));
    }
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("revertProjectToSaved:"), function $CSGProjectController__revertProjectToSaved_(self, _cmd, sender)
{
    if (((___r1 = self.currentProject), ___r1 == null ? null : (___r1.isa.method_msgSend["isUntitled"] || _objj_forward)(___r1, "isUntitled")))
    {
        return;
    }
    var index = ((___r1 = self.projects), ___r1 == null ? null : (___r1.isa.method_msgSend["indexOfObject:"] || _objj_forward)(___r1, "indexOfObject:", self.currentProject));
    var db = ((___r1 = (CSGLocalPersistence.isa.method_msgSend["alloc"] || _objj_forward)(CSGLocalPersistence, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
    (db == null ? null : (db.isa.method_msgSend["valueForKey:responseBlock:"] || _objj_forward)(db, "valueForKey:responseBlock:", ((___r1 = self.currentProject), ___r1 == null ? null : (___r1.isa.method_msgSend["name"] || _objj_forward)(___r1, "name")),     function(proj)
    {
        (self.isa.method_msgSend["willChangeValueForKey:"] || _objj_forward)(self, "willChangeValueForKey:", "projects");
        ((___r1 = self.projects), ___r1 == null ? null : (___r1.isa.method_msgSend["replaceObjectAtIndex:withObject:"] || _objj_forward)(___r1, "replaceObjectAtIndex:withObject:", index, proj));
        (self.isa.method_msgSend["didChangeValueForKey:"] || _objj_forward)(self, "didChangeValueForKey:", "projects");
        (self.isa.method_msgSend["setCurrentProject:"] || _objj_forward)(self, "setCurrentProject:", proj);
        var ___r1;
    }));
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("addProject:"), function $CSGProjectController__addProject_(self, _cmd, aProject)
{
    (self.isa.method_msgSend["willChangeValueForKey:"] || _objj_forward)(self, "willChangeValueForKey:", "projects");
    var name = (aProject == null ? null : (aProject.isa.method_msgSend["name"] || _objj_forward)(aProject, "name"));
    var didReplace = NO;
    for (var i = 0; i < self.projects.length; i++)
    {
        var proj = self.projects[i];
        if ((proj == null ? null : (proj.isa.method_msgSend["name"] || _objj_forward)(proj, "name")) === name)
        {
            self.projects[i] = aProject;
            didReplace = YES;
            break;
        }
    }
    if (!didReplace)
    {
        ((___r1 = self.projects), ___r1 == null ? null : (___r1.isa.method_msgSend["addObject:"] || _objj_forward)(___r1, "addObject:", aProject));
    }
    (self.isa.method_msgSend["didChangeValueForKey:"] || _objj_forward)(self, "didChangeValueForKey:", "projects");
    (self.isa.method_msgSend["setCurrentProject:"] || _objj_forward)(self, "setCurrentProject:", aProject);
    var ___r1;
}

,["void","CSGProject"]), new objj_method(sel_getUid("closeSheet:"), function $CSGProjectController__closeSheet_(self, _cmd, sender)
{
    var retCode = (sender == null ? null : (sender.isa.method_msgSend["title"] || _objj_forward)(sender, "title")) === "OK" ? 1 : 0;
    (CPApp == null ? null : (CPApp.isa.method_msgSend["endSheet:returnCode:"] || _objj_forward)(CPApp, "endSheet:returnCode:", (sender == null ? null : (sender.isa.method_msgSend["window"] || _objj_forward)(sender, "window")), retCode));
}

,["void","id"]), new objj_method(sel_getUid("saveProjectAs:"), function $CSGProjectController__saveProjectAs_(self, _cmd, sender)
{
    var db = ((___r1 = (CSGLocalPersistence.isa.method_msgSend["alloc"] || _objj_forward)(CSGLocalPersistence, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
    var win = (CPApp == null ? null : (CPApp.isa.method_msgSend["mainWindow"] || _objj_forward)(CPApp, "mainWindow"));
    if (self.saveSheet === nil)
    {
        var cib = (db == null ? null : (db.isa.method_msgSend["needsAuthentication"] || _objj_forward)(db, "needsAuthentication")) ? "SaveAuthSheet" : "SaveSheet";
        (CPBundle.isa.method_msgSend["loadCibNamed:owner:"] || _objj_forward)(CPBundle, "loadCibNamed:owner:", cib, self);
    }
    ((___r1 = self.saveProjectName), ___r1 == null ? null : (___r1.isa.method_msgSend["setStringValue:"] || _objj_forward)(___r1, "setStringValue:", ((___r2 = self.currentProject), ___r2 == null ? null : (___r2.isa.method_msgSend["name"] || _objj_forward)(___r2, "name"))));
    (CPApp == null ? null : (CPApp.isa.method_msgSend["beginSheet:modalForWindow:modalDelegate:didEndSelector:contextInfo:"] || _objj_forward)(CPApp, "beginSheet:modalForWindow:modalDelegate:didEndSelector:contextInfo:", self.saveSheet, win, self, sel_getUid("didEndSaveSheet:returnCode:contextInfo:"), db));
    var ___r1, ___r2;
}

,["void","id"]), new objj_method(sel_getUid("didEndSaveSheet:returnCode:contextInfo:"), function $CSGProjectController__didEndSaveSheet_returnCode_contextInfo_(self, _cmd, sheet, returnCode, contextInfo)
{
    (sheet == null ? null : (sheet.isa.method_msgSend["orderOut:"] || _objj_forward)(sheet, "orderOut:", self));
    var db = contextInfo;
    if (returnCode == 1)
    {
        var aName = ((___r1 = self.saveProjectName), ___r1 == null ? null : (___r1.isa.method_msgSend["stringValue"] || _objj_forward)(___r1, "stringValue"));
        (self.isa.method_msgSend["willChangeValueForKey:"] || _objj_forward)(self, "willChangeValueForKey:", "projects");
        ((___r1 = self.currentProject), ___r1 == null ? null : (___r1.isa.method_msgSend["setName:"] || _objj_forward)(___r1, "setName:", aName));
        (self.isa.method_msgSend["didChangeValueForKey:"] || _objj_forward)(self, "didChangeValueForKey:", "projects");
        if ((db == null ? null : (db.isa.method_msgSend["needsAuthentication"] || _objj_forward)(db, "needsAuthentication")))
        {
            ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["authenticatePersistanceUser:withPassword:responseBlock:"] || _objj_forward)(___r1, "authenticatePersistanceUser:withPassword:responseBlock:", ((___r2 = self.saveUserName), ___r2 == null ? null : (___r2.isa.method_msgSend["stringValue"] || _objj_forward)(___r2, "stringValue")), ((___r2 = self.savePassword), ___r2 == null ? null : (___r2.isa.method_msgSend["stringValue"] || _objj_forward)(___r2, "stringValue")),             function(token)
            {
                (db == null ? null : (db.isa.method_msgSend["setAuthToken:"] || _objj_forward)(db, "setAuthToken:", token));
                (db == null ? null : (db.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(db, "setValue:forKey:", self.currentProject, aName));
            }));
        }
        else
        {
            (db == null ? null : (db.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(db, "setValue:forKey:", self.currentProject, aName));
        }
    }
    var ___r1, ___r2;
}

,["void","CPWindow","CPInteger","id"]), new objj_method(sel_getUid("loadProject:"), function $CSGProjectController__loadProject_(self, _cmd, sender)
{
    var db = ((___r1 = (CSGLocalPersistence.isa.method_msgSend["alloc"] || _objj_forward)(CSGLocalPersistence, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
    var win = (CPApp == null ? null : (CPApp.isa.method_msgSend["mainWindow"] || _objj_forward)(CPApp, "mainWindow"));
    (self.isa.method_msgSend["setAvailableProjects:"] || _objj_forward)(self, "setAvailableProjects:", []);
    (db == null ? null : (db.isa.method_msgSend["allKeysUsingResponseBlock:"] || _objj_forward)(db, "allKeysUsingResponseBlock:",     function(keys)
    {
        (self.isa.method_msgSend["setAvailableProjects:"] || _objj_forward)(self, "setAvailableProjects:", keys);
    }));
    if (self.openSheet === nil)
    {
        (CPBundle.isa.method_msgSend["loadCibNamed:owner:"] || _objj_forward)(CPBundle, "loadCibNamed:owner:", "OpenSheet", self);
    }
    (CPApp == null ? null : (CPApp.isa.method_msgSend["beginSheet:modalForWindow:modalDelegate:didEndSelector:contextInfo:"] || _objj_forward)(CPApp, "beginSheet:modalForWindow:modalDelegate:didEndSelector:contextInfo:", self.openSheet, win, self, sel_getUid("didEndOpenSheet:returnCode:contextInfo:"), db));
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("didEndOpenSheet:returnCode:contextInfo:"), function $CSGProjectController__didEndOpenSheet_returnCode_contextInfo_(self, _cmd, sheet, returnCode, contextInfo)
{
    (sheet == null ? null : (sheet.isa.method_msgSend["orderOut:"] || _objj_forward)(sheet, "orderOut:", self));
    var db = contextInfo;
    var selectionIndex = ((___r1 = self.projectTable), ___r1 == null ? null : (___r1.isa.method_msgSend["selectedRow"] || _objj_forward)(___r1, "selectedRow"));
    var validSelection = returnCode == 1 && selectionIndex >= 0;
    if (validSelection)
    {
        self.tentativeProjectName = self.availableProjects[selectionIndex];
        (db == null ? null : (db.isa.method_msgSend["valueForKey:responseBlock:"] || _objj_forward)(db, "valueForKey:responseBlock:", self.tentativeProjectName,         function(proj)
        {
            (self.isa.method_msgSend["addProject:"] || _objj_forward)(self, "addProject:", proj);
        }));
    }
    var ___r1;
}

,["void","CPWindow","CPInteger","id"]), new objj_method(sel_getUid("runProject:"), function $CSGProjectController__runProject_(self, _cmd, sender)
{
    ((___r1 = self.currentProject), ___r1 == null ? null : (___r1.isa.method_msgSend["run"] || _objj_forward)(___r1, "run"));
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("stopProject:"), function $CSGProjectController__stopProject_(self, _cmd, sender)
{
    ((___r1 = self.currentProject), ___r1 == null ? null : (___r1.isa.method_msgSend["stop"] || _objj_forward)(___r1, "stop"));
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("stopAll:"), function $CSGProjectController__stopAll_(self, _cmd, sender)
{
    ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["updateAvailableApplicationsUsingBlock:"] || _objj_forward)(___r1, "updateAvailableApplicationsUsingBlock:",     function(applist)
    {
        for (var i = 0; i < applist.length; i++)
        {
            var app_id = applist[i];
            var proj = (self.isa.method_msgSend["projectWithAppID:"] || _objj_forward)(self, "projectWithAppID:", app_id);
            if (proj)
            {
                (proj == null ? null : (proj.isa.method_msgSend["stop"] || _objj_forward)(proj, "stop"));
            }            else
            {
                ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["stopAppWithID:responseBlock:"] || _objj_forward)(___r1, "stopAppWithID:responseBlock:", app_id,                 function()
                {
                    CPLog("Stopping application not started in this session.");
                }));
            }        }        var ___r1;
    }));
    var ___r1;
}

,["void","id"])]);
}
p;12;CSGProgram.jt;10872;@STATIC;1.0;I;23;Foundation/Foundation.ji;15;CSGConnection.jt;10804;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("CSGConnection.j", YES);
{var the_class = objj_allocateClassPair(CPObject, "CSGProgram"),
meta_class = the_class.isa;
var aProtocol = objj_getProtocol("CPCoding");
if (!aProtocol) throw new SyntaxError("*** Could not find definition for protocol \"CPCoding\"");
class_addProtocol(the_class, aProtocol);class_addIvars(the_class, [new objj_ivar("instances", "CPMutableArray"), new objj_ivar("connections", "CPMutableArray"), new objj_ivar("_counter", "int"), new objj_ivar("name", "CPString")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("actors"), function $CSGProgram__actors(self, _cmd)
{
    return self.instances;
}

,["CPMutableArray"]), new objj_method(sel_getUid("name"), function $CSGProgram__name(self, _cmd)
{
    return self.name;
}

,["CPString"]), new objj_method(sel_getUid("setName:"), function $CSGProgram__setName_(self, _cmd, newValue)
{
    self.name = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("init"), function $CSGProgram__init(self, _cmd)
{
    self = (objj_getClass("CSGProgram").super_class.method_dtable["init"] || _objj_forward)(self, "init");
    if (self)
    {
        self.instances = [];
        self.connections = [];
        self._counter = 0;
        var fmt = ((___r1 = (CPDateFormatter.isa.method_msgSend["alloc"] || _objj_forward)(CPDateFormatter, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithDateFormat:allowNaturalLanguage:"] || _objj_forward)(___r1, "initWithDateFormat:allowNaturalLanguage:", "yyMMddHHmmss", NO));
        self.name = (fmt == null ? null : (fmt.isa.method_msgSend["stringFromDate:"] || _objj_forward)(fmt, "stringFromDate:", (CPDate.isa.method_msgSend["date"] || _objj_forward)(CPDate, "date")));
    }
    return self;
    var ___r1;
}

,["id"]), new objj_method(sel_getUid("initWithCoder:"), function $CSGProgram__initWithCoder_(self, _cmd, coder)
{
    self = (objj_getClass("CSGProgram").super_class.method_dtable["init"] || _objj_forward)(self, "init");
    if (self)
    {
        self.instances = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "instances"));
        self.connections = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "connections"));
        self._counter = (coder == null ? null : (coder.isa.method_msgSend["decodeIntForKey:"] || _objj_forward)(coder, "decodeIntForKey:", "counter"));
    }
    return self;
}

,["id","CPCoder"]), new objj_method(sel_getUid("encodeWithCoder:"), function $CSGProgram__encodeWithCoder_(self, _cmd, coder)
{
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.instances, "instances"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.connections, "connections"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeInt:forKey:"] || _objj_forward)(coder, "encodeInt:forKey:", self._counter, "counter"));
}

,["void","CPCoder"]), new objj_method(sel_getUid("addInstance:"), function $CSGProgram__addInstance_(self, _cmd, actor)
{
    (self.isa.method_msgSend["willChangeValueForKey:"] || _objj_forward)(self, "willChangeValueForKey:", "instances");
    var typeParts = ((___r1 = actor.type), ___r1 == null ? null : (___r1.isa.method_msgSend["componentsSeparatedByString:"] || _objj_forward)(___r1, "componentsSeparatedByString:", ".")),
        tmpName = ((___r1 = typeParts[typeParts.length - 1]), ___r1 == null ? null : (___r1.isa.method_msgSend["lowercaseString"] || _objj_forward)(___r1, "lowercaseString"));
    actor.name = (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "%@%d", tmpName, ++self._counter);
    ((___r1 = self.instances), ___r1 == null ? null : (___r1.isa.method_msgSend["insertObject:atIndex:"] || _objj_forward)(___r1, "insertObject:atIndex:", actor, 0));
    (self.isa.method_msgSend["didChangeValueForKey:"] || _objj_forward)(self, "didChangeValueForKey:", "instances");
    var ___r1;
}

,["void","CSGActor"]), new objj_method(sel_getUid("isValidActorName:"), function $CSGProgram__isValidActorName_(self, _cmd, actorName)
{
    var syntax_ok = /^[a-z][a-z0-9_]*$/i.test(actorName);
    if (!syntax_ok)
    {
        return NO;
    }
    for (var i = 0; i < self.instances.length; i++)
    {
        if (actorName === self.instances[i].name)
        {
            return NO;
        }
    }
    return YES;
}

,["BOOL","CPString"]), new objj_method(sel_getUid("addConnectionFrom:fromPort:to:toPort:"), function $CSGProgram__addConnectionFrom_fromPort_to_toPort_(self, _cmd, fromActor, fromPort, toActor, toPort)
{
    if ((fromPort == null ? null : (fromPort.isa.method_msgSend["isInport"] || _objj_forward)(fromPort, "isInport")) === (toPort == null ? null : (toPort.isa.method_msgSend["isInport"] || _objj_forward)(toPort, "isInport")))
    {
        return false;
    }
    var conn;
    if ((fromPort == null ? null : (fromPort.isa.method_msgSend["isInport"] || _objj_forward)(fromPort, "isInport")))
    {
        conn = ((___r1 = (CSGConnection.isa.method_msgSend["alloc"] || _objj_forward)(CSGConnection, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithSrc:srcPort:dst:dstPort:"] || _objj_forward)(___r1, "initWithSrc:srcPort:dst:dstPort:", toActor, toPort, fromActor, fromPort));
    }
    else
    {
        conn = ((___r1 = (CSGConnection.isa.method_msgSend["alloc"] || _objj_forward)(CSGConnection, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithSrc:srcPort:dst:dstPort:"] || _objj_forward)(___r1, "initWithSrc:srcPort:dst:dstPort:", fromActor, fromPort, toActor, toPort));
    }
    for (var i = 0; i < self.connections.length; i++)
    {
        var present = self.connections[i];
        if ((conn == null ? null : (conn.isa.method_msgSend["isEqualToConnection:"] || _objj_forward)(conn, "isEqualToConnection:", present)) || (conn == null ? null : (conn.isa.method_msgSend["hasSameDestinationPortAsConnection:"] || _objj_forward)(conn, "hasSameDestinationPortAsConnection:", present)))
        {
            return false;
        }
    }
    ((___r1 = self.connections), ___r1 == null ? null : (___r1.isa.method_msgSend["addObject:"] || _objj_forward)(___r1, "addObject:", conn));
    return true;
    var ___r1;
}

,["BOOL","CSGActor","CSGPort","CSGActor","CSGPort"]), new objj_method(sel_getUid("connectionForActor:inport:"), function $CSGProgram__connectionForActor_inport_(self, _cmd, actor, port)
{
    for (var i = 0; i < self.connections.length; i++)
    {
        if (((___r1 = self.connections[i]), ___r1 == null ? null : (___r1.isa.method_msgSend["isConnectedToActor:inport:"] || _objj_forward)(___r1, "isConnectedToActor:inport:", actor, port)))
        {
            return self.connections[i];
        }
    }
    return nil;
    var ___r1;
}

,["CSGConnection","CSGActor","CSGPort"]), new objj_method(sel_getUid("connectionsForActor:outport:"), function $CSGProgram__connectionsForActor_outport_(self, _cmd, actor, port)
{
    var conns = (CPMutableArray.isa.method_msgSend["array"] || _objj_forward)(CPMutableArray, "array");
    for (var i = 0; i < self.connections.length; i++)
    {
        if (((___r1 = self.connections[i]), ___r1 == null ? null : (___r1.isa.method_msgSend["isConnectedToActor:outport:"] || _objj_forward)(___r1, "isConnectedToActor:outport:", actor, port)))
        {
            (conns == null ? null : (conns.isa.method_msgSend["addObject:"] || _objj_forward)(conns, "addObject:", self.connections[i]));
        }
    }
    return conns;
    var ___r1;
}

,["CPArray","CSGActor","CSGPort"]), new objj_method(sel_getUid("removeComponent:"), function $CSGProgram__removeComponent_(self, _cmd, comp)
{
    if (comp === nil)
    {
        return;
    }
    if ((comp == null ? null : (comp.isa.method_msgSend["isKindOfClass:"] || _objj_forward)(comp, "isKindOfClass:", (CSGActor == null ? null : (CSGActor.isa.method_msgSend["class"] || _objj_forward)(CSGActor, "class")))))
    {
        var index = self.connections.length;
        while (index--)
        {
            if (((___r1 = self.connections[index]), ___r1 == null ? null : (___r1.isa.method_msgSend["isConnectedToActor:"] || _objj_forward)(___r1, "isConnectedToActor:", comp)))
            {
                ((___r1 = self.connections), ___r1 == null ? null : (___r1.isa.method_msgSend["removeObjectAtIndex:"] || _objj_forward)(___r1, "removeObjectAtIndex:", index));
            }
        }
        (self.isa.method_msgSend["willChangeValueForKey:"] || _objj_forward)(self, "willChangeValueForKey:", "instances");
        ((___r1 = self.instances), ___r1 == null ? null : (___r1.isa.method_msgSend["removeObject:"] || _objj_forward)(___r1, "removeObject:", comp));
        (self.isa.method_msgSend["didChangeValueForKey:"] || _objj_forward)(self, "didChangeValueForKey:", "instances");
    }
    else if ((comp == null ? null : (comp.isa.method_msgSend["isKindOfClass:"] || _objj_forward)(comp, "isKindOfClass:", (CSGConnection.isa.method_msgSend["class"] || _objj_forward)(CSGConnection, "class"))))
    {
        ((___r1 = self.connections), ___r1 == null ? null : (___r1.isa.method_msgSend["removeObject:"] || _objj_forward)(___r1, "removeObject:", comp));
    }
    else
    {
        console.log("Can't remove component", comp);
    }
    var ___r1;
}

,["void","CSGComponent"]), new objj_method(sel_getUid("scriptRepresentation"), function $CSGProgram__scriptRepresentation(self, _cmd)
{
    var reps = (CPMutableArray.isa.method_msgSend["array"] || _objj_forward)(CPMutableArray, "array");
    for (var i = 0; i < self.instances.length; i++)
    {
        (reps == null ? null : (reps.isa.method_msgSend["addObject:"] || _objj_forward)(reps, "addObject:", ((___r1 = self.instances[i]), ___r1 == null ? null : (___r1.isa.method_msgSend["scriptRepresentation"] || _objj_forward)(___r1, "scriptRepresentation"))));
    }
    (reps == null ? null : (reps.isa.method_msgSend["addObject:"] || _objj_forward)(reps, "addObject:", ""));
    for (var i = 0; i < self.connections.length; i++)
    {
        (reps == null ? null : (reps.isa.method_msgSend["addObject:"] || _objj_forward)(reps, "addObject:", ((___r1 = self.connections[i]), ___r1 == null ? null : (___r1.isa.method_msgSend["scriptRepresentation"] || _objj_forward)(___r1, "scriptRepresentation"))));
    }
    var script = (reps == null ? null : (reps.isa.method_msgSend["componentsJoinedByString:"] || _objj_forward)(reps, "componentsJoinedByString:", "\n"));
    return script;
    var ___r1;
}

,["CPString"])]);
}
p;15;CSGConnection.jt;6585;@STATIC;1.0;I;23;Foundation/Foundation.ji;14;CSGComponent.ji;9;CSGPort.jt;6506;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("CSGComponent.j", YES);objj_executeFile("CSGPort.j", YES);
{var the_class = objj_allocateClassPair(CSGComponent, "CSGConnection"),
meta_class = the_class.isa;
var aProtocol = objj_getProtocol("CPCoding");
if (!aProtocol) throw new SyntaxError("*** Could not find definition for protocol \"CPCoding\"");
class_addProtocol(the_class, aProtocol);class_addIvars(the_class, [new objj_ivar("src", "CSGActor"), new objj_ivar("dst", "CSGActor"), new objj_ivar("srcPort", "CSGPort"), new objj_ivar("dstPort", "CSGPort")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("srcActor"), function $CSGConnection__srcActor(self, _cmd)
{
    return self.src;
}

,["CSGActor"]), new objj_method(sel_getUid("setSrc:"), function $CSGConnection__setSrc_(self, _cmd, newValue)
{
    self.src = newValue;
}

,["void","CSGActor"]), new objj_method(sel_getUid("srcPort"), function $CSGConnection__srcPort(self, _cmd)
{
    return self.srcPort;
}

,["CSGPort"]), new objj_method(sel_getUid("setSrcPort:"), function $CSGConnection__setSrcPort_(self, _cmd, newValue)
{
    self.srcPort = newValue;
}

,["void","CSGPort"]), new objj_method(sel_getUid("initWithSrc:srcPort:dst:dstPort:"), function $CSGConnection__initWithSrc_srcPort_dst_dstPort_(self, _cmd, theSrcActor, theSrcPort, theDstActor, theDstPort)
{
    if (self = (objj_getClass("CSGConnection").super_class.method_dtable["init"] || _objj_forward)(self, "init"))
    {
        self.src = theSrcActor;
        self.dst = theDstActor;
        self.srcPort = theSrcPort;
        self.dstPort = theDstPort;
    }
    return self;
}

,["id","CSGActor","CSGPort","CSGActor","CSGPort"]), new objj_method(sel_getUid("initWithCoder:"), function $CSGConnection__initWithCoder_(self, _cmd, coder)
{
    self = (objj_getClass("CSGConnection").super_class.method_dtable["init"] || _objj_forward)(self, "init");
    if (self)
    {
        self.src = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "src"));
        self.dst = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "dst"));
        self.srcPort = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "srcPort"));
        self.dstPort = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "dstPort"));
    }
    return self;
}

,["id","CPCoder"]), new objj_method(sel_getUid("encodeWithCoder:"), function $CSGConnection__encodeWithCoder_(self, _cmd, coder)
{
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.src, "src"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.dst, "dst"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.srcPort, "srcPort"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.dstPort, "dstPort"));
}

,["void","CPCoder"]), new objj_method(sel_getUid("isEqualToConnection:"), function $CSGConnection__isEqualToConnection_(self, _cmd, connection)
{
    if (!connection)
    {
        return NO;
    }
    if (!((___r1 = self.src), ___r1 == null ? null : (___r1.isa.method_msgSend["isEqual:"] || _objj_forward)(___r1, "isEqual:", connection.src)) || !((___r1 = self.dst), ___r1 == null ? null : (___r1.isa.method_msgSend["isEqual:"] || _objj_forward)(___r1, "isEqual:", connection.dst)))
    {
        return NO;
    }
    if (self.srcPort !== connection.srcPort || self.dstPort !== connection.dstPort)
    {
        return NO;
    }
    return YES;
    var ___r1;
}

,["BOOL","CSGConnection"]), new objj_method(sel_getUid("isEqual:"), function $CSGConnection__isEqual_(self, _cmd, object)
{
    if (self === object)
    {
        return YES;
    }
    if (!(object == null ? null : (object.isa.method_msgSend["isKindOfClass:"] || _objj_forward)(object, "isKindOfClass:", (CSGConnection.isa.method_msgSend["class"] || _objj_forward)(CSGConnection, "class"))))
    {
        return NO;
    }
    return (self.isa.method_msgSend["isEqualToConnection:"] || _objj_forward)(self, "isEqualToConnection:", object);
}

,["BOOL","id"]), new objj_method(sel_getUid("hasSameDestinationPortAsConnection:"), function $CSGConnection__hasSameDestinationPortAsConnection_(self, _cmd, conn)
{
    return conn.dst === self.dst && conn.dstPort === self.dstPort;
}

,["BOOL","CSGConnection"]), new objj_method(sel_getUid("isConnectedToActor:"), function $CSGConnection__isConnectedToActor_(self, _cmd, actor)
{
    return self.src === actor || self.dst === actor;
}

,["BOOL","CSGActor"]), new objj_method(sel_getUid("isConnectedToActor:inport:"), function $CSGConnection__isConnectedToActor_inport_(self, _cmd, actor, port)
{
    return self.dst === actor && self.dstPort === port;
}

,["BOOL","CSGActor","CSGPort"]), new objj_method(sel_getUid("isConnectedToActor:outport:"), function $CSGConnection__isConnectedToActor_outport_(self, _cmd, actor, port)
{
    return self.src === actor && self.srcPort === port;
}

,["BOOL","CSGActor","CSGPort"]), new objj_method(sel_getUid("description"), function $CSGConnection__description(self, _cmd)
{
    return (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "%@:%@ -> %@:%@", self.src, self.srcPort, self.dst, self.dstPort);
}

,["CPString"]), new objj_method(sel_getUid("scriptRepresentation"), function $CSGConnection__scriptRepresentation(self, _cmd)
{
    var line = (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "%@.%@ > %@.%@", ((___r1 = self.src), ___r1 == null ? null : (___r1.isa.method_msgSend["name"] || _objj_forward)(___r1, "name")), ((___r1 = self.srcPort), ___r1 == null ? null : (___r1.isa.method_msgSend["name"] || _objj_forward)(___r1, "name")), ((___r1 = self.dst), ___r1 == null ? null : (___r1.isa.method_msgSend["name"] || _objj_forward)(___r1, "name")), ((___r1 = self.dstPort), ___r1 == null ? null : (___r1.isa.method_msgSend["name"] || _objj_forward)(___r1, "name")));
    return line;
    var ___r1;
}

,["CPString"])]);
}
p;16;CSGProgramView.jt;14039;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;14;CSGComponent.ji;10;CSGActor.ji;12;CSGProgram.ji;22;CSGProgram+Rendering.jt;13893;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGComponent.j", YES);objj_executeFile("CSGActor.j", YES);objj_executeFile("CSGProgram.j", YES);objj_executeFile("CSGProgram+Rendering.j", YES);
{var the_class = objj_allocateClassPair(CPView, "CSGProgramView"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("program", "CSGProgram"), new objj_ivar("dragObject", "CSGActor"), new objj_ivar("dragPad", "CPString"), new objj_ivar("selection", "CSGComponent"), new objj_ivar("mouseDraggedAction", "SEL"), new objj_ivar("mouseUpAction", "SEL"), new objj_ivar("dragOffset", "CGPoint"), new objj_ivar("trackingStartLocation", "CGPoint"), new objj_ivar("trackingLocation", "CGPoint")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("selection"), function $CSGProgramView__selection(self, _cmd)
{
    return self.selection;
}

,["CSGComponent"]), new objj_method(sel_getUid("setSelection:"), function $CSGProgramView__setSelection_(self, _cmd, newValue)
{
    self.selection = newValue;
}

,["void","CSGComponent"]), new objj_method(sel_getUid("awakeFromCib"), function $CSGProgramView__awakeFromCib(self, _cmd)
{
    (self.isa.method_msgSend["registerForDraggedTypes:"] || _objj_forward)(self, "registerForDraggedTypes:", [CPStringPboardType]);
    self.mouseDraggedAction = sel_getUid("_nilAction:");
    self.mouseUpAction = sel_getUid("_nilAction:");
}

,["void"]), new objj_method(sel_getUid("drawRect:"), function $CSGProgramView__drawRect_(self, _cmd, dirtyRect)
{
    ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGEditorViewBgColorHEX)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    (CPBezierPath.isa.method_msgSend["fillRect:"] || _objj_forward)(CPBezierPath, "fillRect:", (self.isa.method_msgSend["bounds"] || _objj_forward)(self, "bounds"));
    ((___r1 = self.program), ___r1 == null ? null : (___r1.isa.method_msgSend["renderInBounds:dirtyRect:"] || _objj_forward)(___r1, "renderInBounds:dirtyRect:", (self.isa.method_msgSend["bounds"] || _objj_forward)(self, "bounds"), dirtyRect));
    if (self.dragPad !== nil)
    {
        var path = (CPBezierPath.isa.method_msgSend["bezierPath"] || _objj_forward)(CPBezierPath, "bezierPath");
        (path == null ? null : (path.isa.method_msgSend["moveToPoint:"] || _objj_forward)(path, "moveToPoint:", self.trackingStartLocation));
        (path == null ? null : (path.isa.method_msgSend["lineToPoint:"] || _objj_forward)(path, "lineToPoint:", self.trackingLocation));
        ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGConnectionPendingColorHEX)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
        (path == null ? null : (path.isa.method_msgSend["stroke"] || _objj_forward)(path, "stroke"));
    }
    var ___r1;
}

,["void","CGRect"]), new objj_method(sel_getUid("observeValueForKeyPath:ofObject:change:context:"), function $CSGProgramView__observeValueForKeyPath_ofObject_change_context_(self, _cmd, keyPath, object, change, context)
{
    if (keyPath === "currentProject")
    {
        (self.isa.method_msgSend["setSelection:"] || _objj_forward)(self, "setSelection:", nil);
        var newProject = (change == null ? null : (change.isa.method_msgSend["objectForKey:"] || _objj_forward)(change, "objectForKey:", "CPKeyValueChangeNewKey"));
        self.program = (newProject == null ? null : (newProject.isa.method_msgSend["program"] || _objj_forward)(newProject, "program"));
        (self.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(self, "setNeedsDisplay:", YES);
    }
}

,["void","CPString","id","CPDictionary","id"]), new objj_method(sel_getUid("isFlipped"), function $CSGProgramView__isFlipped(self, _cmd)
{
    return YES;
}

,["BOOL"]), new objj_method(sel_getUid("setSelection:"), function $CSGProgramView__setSelection_(self, _cmd, comp)
{
    if (self.selection !== nil)
    {
        ((___r1 = self.selection), ___r1 == null ? null : (___r1.isa.method_msgSend["setSelected:"] || _objj_forward)(___r1, "setSelected:", NO));
    }
    if (comp !== nil)
    {
        self.selection = comp;
        (comp == null ? null : (comp.isa.method_msgSend["setSelected:"] || _objj_forward)(comp, "setSelected:", YES));
    }
    else
    {
        self.selection = nil;
    }
    var ___r1;
}

,["void","CSGComponent"]), new objj_method(sel_getUid("acceptsFirstResponder"), function $CSGProgramView__acceptsFirstResponder(self, _cmd)
{
    return YES;
}

,["BOOL"]), new objj_method(sel_getUid("keyDown:"), function $CSGProgramView__keyDown_(self, _cmd, event)
{
    var keyCode = (event == null ? null : (event.isa.method_msgSend["keyCode"] || _objj_forward)(event, "keyCode"));
    if (keyCode === CPDeleteForwardKeyCode || keyCode === CPDeleteKeyCode)
    {
        ((___r1 = self.program), ___r1 == null ? null : (___r1.isa.method_msgSend["removeComponent:"] || _objj_forward)(___r1, "removeComponent:", self.selection));
        self.selection = nil;
        (self.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(self, "setNeedsDisplay:", YES);
    }
    var ___r1;
}

,["void","CPEvent"]), new objj_method(sel_getUid("mouseDown:"), function $CSGProgramView__mouseDown_(self, _cmd, event)
{
    var dragStart = (self.isa.method_msgSend["convertPoint:fromView:"] || _objj_forward)(self, "convertPoint:fromView:", (event == null ? null : (event.isa.method_msgSend["locationInWindow"] || _objj_forward)(event, "locationInWindow")), nil);
    self.dragObject = ((___r1 = self.program), ___r1 == null ? null : (___r1.isa.method_msgSend["instanceAtPoint:"] || _objj_forward)(___r1, "instanceAtPoint:", dragStart));
    (self.isa.method_msgSend["setSelection:"] || _objj_forward)(self, "setSelection:", self.dragObject);
    (self.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(self, "setNeedsDisplay:", YES);
    if (self.dragObject === nil)
    {
        return;
    }
    self.dragOffset = CSGSubtractPoints(dragStart, self.dragObject.bounds.origin);
    self.dragPad = ((___r1 = self.dragObject), ___r1 == null ? null : (___r1.isa.method_msgSend["portAtPoint:"] || _objj_forward)(___r1, "portAtPoint:", dragStart));
    if (self.dragPad === nil)
    {
        self.mouseDraggedAction = sel_getUid("_updateDragWithEvent:");
        self.mouseUpAction = sel_getUid("_updateDragWithEvent:");
    }
    else
    {
        self.mouseDraggedAction = sel_getUid("_updateConnectDragWithEvent:");
        self.mouseUpAction = sel_getUid("_finishConnectDragWithEvent:");
    }
    var existingConn = nil;
    if (self.dragPad !== nil && ((___r1 = self.dragPad), ___r1 == null ? null : (___r1.isa.method_msgSend["isInport"] || _objj_forward)(___r1, "isInport")))
    {
        existingConn = ((___r1 = self.program), ___r1 == null ? null : (___r1.isa.method_msgSend["connectionForActor:inport:"] || _objj_forward)(___r1, "connectionForActor:inport:", self.dragObject, self.dragPad));
    }
    if (existingConn !== nil)
    {
        self.dragObject = (existingConn == null ? null : (existingConn.isa.method_msgSend["srcActor"] || _objj_forward)(existingConn, "srcActor"));
        self.dragPad = (existingConn == null ? null : (existingConn.isa.method_msgSend["srcPort"] || _objj_forward)(existingConn, "srcPort"));
        self.trackingStartLocation = ((___r1 = self.dragObject), ___r1 == null ? null : (___r1.isa.method_msgSend["anchorPointForPort:"] || _objj_forward)(___r1, "anchorPointForPort:", self.dragPad));
        self.trackingLocation = dragStart;
        ((___r1 = self.program), ___r1 == null ? null : (___r1.isa.method_msgSend["removeComponent:"] || _objj_forward)(___r1, "removeComponent:", existingConn));
    }
    else
    {
        self.trackingStartLocation = dragStart;
        self.trackingLocation = dragStart;
    }
    var ___r1;
}

,["void","CPEvent"]), new objj_method(sel_getUid("mouseDragged:"), function $CSGProgramView__mouseDragged_(self, _cmd, event)
{
    (self.isa.method_msgSend["autoscroll:"] || _objj_forward)(self, "autoscroll:", event);
    (self.isa.method_msgSend["performSelector:withObject:"] || _objj_forward)(self, "performSelector:withObject:", self.mouseDraggedAction, event);
    (self.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(self, "setNeedsDisplay:", YES);
}

,["void","CPEvent"]), new objj_method(sel_getUid("mouseUp:"), function $CSGProgramView__mouseUp_(self, _cmd, event)
{
    (self.isa.method_msgSend["performSelector:withObject:"] || _objj_forward)(self, "performSelector:withObject:", self.mouseUpAction, event);
    self.mouseUpAction = sel_getUid("_nilAction:");
    self.mouseDraggedAction = sel_getUid("_nilAction:");
    self.dragObject = nil;
    self.dragPad = nil;
    (self.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(self, "setNeedsDisplay:", YES);
}

,["void","CPEvent"]), new objj_method(sel_getUid("constrainPoint:"), function $CSGProgramView__constrainPoint_(self, _cmd, aPoint)
{
    var documentBounds = (self.isa.method_msgSend["bounds"] || _objj_forward)(self, "bounds");
    aPoint.x = MAX(0.0, MIN(aPoint.x, CGRectGetWidth(documentBounds)));
    aPoint.y = MAX(0.0, MIN(aPoint.y, CGRectGetHeight(documentBounds)));
    return aPoint;
}

,["CGPoint","CGPoint"]), new objj_method(sel_getUid("_nilAction:"), function $CSGProgramView___nilAction_(self, _cmd, object)
{
    return;
}

,["void","id"]), new objj_method(sel_getUid("_updateDragWithEvent:"), function $CSGProgramView___updateDragWithEvent_(self, _cmd, event)
{
    var loc = (self.isa.method_msgSend["convertPoint:fromView:"] || _objj_forward)(self, "convertPoint:fromView:", (event == null ? null : (event.isa.method_msgSend["locationInWindow"] || _objj_forward)(event, "locationInWindow")), nil);
    loc = (self.isa.method_msgSend["constrainPoint:"] || _objj_forward)(self, "constrainPoint:", loc);
    self.dragObject.bounds.origin = CSGAddPoints(loc, self.dragOffset);
}

,["void","CPEvent"]), new objj_method(sel_getUid("_updateConnectDragWithEvent:"), function $CSGProgramView___updateConnectDragWithEvent_(self, _cmd, event)
{
    var loc = (self.isa.method_msgSend["convertPoint:fromView:"] || _objj_forward)(self, "convertPoint:fromView:", (event == null ? null : (event.isa.method_msgSend["locationInWindow"] || _objj_forward)(event, "locationInWindow")), nil);
    self.trackingLocation = (self.isa.method_msgSend["constrainPoint:"] || _objj_forward)(self, "constrainPoint:", loc);
}

,["void","CPEvent"]), new objj_method(sel_getUid("_finishConnectDragWithEvent:"), function $CSGProgramView___finishConnectDragWithEvent_(self, _cmd, event)
{
    var dropPoint = (self.isa.method_msgSend["convertPoint:fromView:"] || _objj_forward)(self, "convertPoint:fromView:", (event == null ? null : (event.isa.method_msgSend["locationInWindow"] || _objj_forward)(event, "locationInWindow")), nil),
        dropObject = ((___r1 = self.program), ___r1 == null ? null : (___r1.isa.method_msgSend["instanceAtPoint:"] || _objj_forward)(___r1, "instanceAtPoint:", dropPoint));
    if (dropObject === nil)
    {
        return;
    }
    var dropPad = (dropObject == null ? null : (dropObject.isa.method_msgSend["portAtPoint:"] || _objj_forward)(dropObject, "portAtPoint:", dropPoint));
    if (dropPad === nil)
    {
        return;
    }
    var isValid = ((___r1 = self.program), ___r1 == null ? null : (___r1.isa.method_msgSend["addConnectionFrom:fromPort:to:toPort:"] || _objj_forward)(___r1, "addConnectionFrom:fromPort:to:toPort:", self.dragObject, self.dragPad, dropObject, dropPad));
    if (isValid)
    {
        (self.isa.method_msgSend["setSelection:"] || _objj_forward)(self, "setSelection:", dropObject);
    }
    var ___r1;
}

,["void","CPEvent"]), new objj_method(sel_getUid("prepareForDragOperation:"), function $CSGProgramView__prepareForDragOperation_(self, _cmd, draggingInfo)
{
    return YES;
}

,["BOOL","CPDraggingInfo"]), new objj_method(sel_getUid("performDragOperation:"), function $CSGProgramView__performDragOperation_(self, _cmd, draggingInfo)
{
    var pasteboard = (draggingInfo == null ? null : (draggingInfo.isa.method_msgSend["draggingPasteboard"] || _objj_forward)(draggingInfo, "draggingPasteboard"));
    var item = (pasteboard == null ? null : (pasteboard.isa.method_msgSend["dataForType:"] || _objj_forward)(pasteboard, "dataForType:", CPStringPboardType)),
        loc = (self.isa.method_msgSend["convertPoint:fromView:"] || _objj_forward)(self, "convertPoint:fromView:", (draggingInfo == null ? null : (draggingInfo.isa.method_msgSend["draggingLocation"] || _objj_forward)(draggingInfo, "draggingLocation")), nil),
        actor = ((___r1 = (CSGActor.isa.method_msgSend["alloc"] || _objj_forward)(CSGActor, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithJSObject:"] || _objj_forward)(___r1, "initWithJSObject:", (item == null ? null : (item.isa.method_msgSend["objectFromJSON"] || _objj_forward)(item, "objectFromJSON"))));
    if (actor !== nil)
    {
        ((___r1 = self.program), ___r1 == null ? null : (___r1.isa.method_msgSend["addInstance:"] || _objj_forward)(___r1, "addInstance:", actor));
        (actor == null ? null : (actor.isa.method_msgSend["setOrigin:"] || _objj_forward)(actor, "setOrigin:", loc));
        (self.isa.method_msgSend["setSelection:"] || _objj_forward)(self, "setSelection:", actor);
    }
    else
    {
        console.log("Not adding invalid actor", actor);
    }
    return YES;
    var ___r1;
}

,["BOOL","CPDraggingInfo"]), new objj_method(sel_getUid("concludeDragOperation:"), function $CSGProgramView__concludeDragOperation_(self, _cmd, draggingInfo)
{
    (self.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(self, "setNeedsDisplay:", YES);
}

,["void","CPDraggingInfo"])]);
}
p;22;CSGProgram+Rendering.jt;1862;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;20;CPString+Rendering.ji;12;CSGProgram.ji;20;CSGActor+Rendering.ji;19;CSGPort+Rendering.ji;25;CSGConnection+Rendering.ji;18;CSGGeometryUtils.ji;10;CSGTheme.jt;1636;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CPString+Rendering.j", YES);objj_executeFile("CSGProgram.j", YES);objj_executeFile("CSGActor+Rendering.j", YES);objj_executeFile("CSGPort+Rendering.j", YES);objj_executeFile("CSGConnection+Rendering.j", YES);objj_executeFile("CSGGeometryUtils.j", YES);objj_executeFile("CSGTheme.j", YES);{
var the_class = objj_getClass("CSGProgram")
if(!the_class) throw new SyntaxError("*** Could not find definition for class \"CSGProgram\"");
var meta_class = the_class.isa;class_addMethods(the_class, [new objj_method(sel_getUid("renderInBounds:dirtyRect:"), function $CSGProgram__renderInBounds_dirtyRect_(self, _cmd, bounds, dirtyRect)
{
    for (var i = self.connections.length - 1; i >= 0; i--)
    {
        ((___r1 = self.connections[i]), ___r1 == null ? null : (___r1.isa.method_msgSend["renderWithDirtyRect:"] || _objj_forward)(___r1, "renderWithDirtyRect:", dirtyRect));
    }
    for (var i = self.instances.length - 1; i >= 0; i--)
    {
        ((___r1 = self.instances[i]), ___r1 == null ? null : (___r1.isa.method_msgSend["renderInBounds:dirtyRect:"] || _objj_forward)(___r1, "renderInBounds:dirtyRect:", bounds, dirtyRect));
    }
    var ___r1;
}

,["void","CGRect","CGRect"]), new objj_method(sel_getUid("instanceAtPoint:"), function $CSGProgram__instanceAtPoint_(self, _cmd, point)
{
    for (var i = 0; i < self.instances.length; i++)
    {
        var a = self.instances[i];
        if (CGRectContainsPoint(a.bounds, point))
        {
            return a;
        }
    }
    return nil;
}

,["CSGActor","CGPoint"])]);
}
p;20;CPString+Rendering.jt;2206;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.jt;2139;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);{
var the_class = objj_getClass("CPString")
if(!the_class) throw new SyntaxError("*** Could not find definition for class \"CPString\"");
var meta_class = the_class.isa;class_addMethods(the_class, [new objj_method(sel_getUid("drawAtPoint:withAttributes:"), function $CPString__drawAtPoint_withAttributes_(self, _cmd, point, attributes)
{
    var ctx = ((___r1 = (CPGraphicsContext.isa.method_msgSend["currentContext"] || _objj_forward)(CPGraphicsContext, "currentContext")), ___r1 == null ? null : (___r1.isa.method_msgSend["graphicsPort"] || _objj_forward)(___r1, "graphicsPort"));
    ctx.font = ((___r1 = (CPFont.isa.method_msgSend["systemFontOfSize:"] || _objj_forward)(CPFont, "systemFontOfSize:", 12)), ___r1 == null ? null : (___r1.isa.method_msgSend["cssString"] || _objj_forward)(___r1, "cssString"));
    ctx.fillText(self, point.x, point.y);
    var ___r1;
}

,["void","CSGPoint","CPDictionary"]), new objj_method(sel_getUid("drawInBounds:withAlignment:"), function $CPString__drawInBounds_withAlignment_(self, _cmd, bounds, align)
{
    var x = 0.0;
    var font = (CPFont.isa.method_msgSend["systemFontOfSize:"] || _objj_forward)(CPFont, "systemFontOfSize:", 12);
    if (align !== CPLeftTextAlignment)
    {
        var w = (self.isa.method_msgSend["sizeWithFont:"] || _objj_forward)(self, "sizeWithFont:", font).width;
        if (align === CPCenterTextAlignment)
        {
            x = (bounds.size.width - w) / 2.0;
        }
        else
        {
            x = bounds.size.width - w;
        }
    }
    ((___r1 = (CPColor.isa.method_msgSend["blackColor"] || _objj_forward)(CPColor, "blackColor")), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    var p = CPMakePoint(bounds.origin.x + x, bounds.origin.y + (font == null ? null : (font.isa.method_msgSend["size"] || _objj_forward)(font, "size")));
    (self.isa.method_msgSend["drawAtPoint:withAttributes:"] || _objj_forward)(self, "drawAtPoint:withAttributes:", p, {});
    var ___r1;
}

,["void","CGRect","CPTextAlignment"])]);
}
p;20;CSGActor+Rendering.jt;8356;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;10;CSGActor.ji;10;CSGTheme.ji;18;CSGGeometryUtils.jt;8236;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGActor.j", YES);objj_executeFile("CSGTheme.j", YES);objj_executeFile("CSGGeometryUtils.j", YES);{
var the_class = objj_getClass("CSGActor")
if(!the_class) throw new SyntaxError("*** Could not find definition for class \"CSGActor\"");
var meta_class = the_class.isa;class_addMethods(the_class, [new objj_method(sel_getUid("computeBounds"), function $CSGActor__computeBounds(self, _cmd)
{
    var font = (CPFont.isa.method_msgSend["systemFontOfSize:"] || _objj_forward)(CPFont, "systemFontOfSize:", 12);
    var width_port = 0.0,
        width_hdr,
        rows = Math.max(self.inports.length, self.outports.length) + 2,
        allPorts = self.inports.concat(self.outports);
    for (var i = 0; i < allPorts.length; i++)
    {
        width_port = Math.max(width_port, ((___r1 = allPorts[i]), ___r1 == null ? null : (___r1.isa.method_msgSend["size"] || _objj_forward)(___r1, "size")).width);
    }
    width_hdr = Math.max(((___r1 = self.name), ___r1 == null ? null : (___r1.isa.method_msgSend["sizeWithFont:"] || _objj_forward)(___r1, "sizeWithFont:", font)).width, ((___r1 = self.type), ___r1 == null ? null : (___r1.isa.method_msgSend["sizeWithFont:"] || _objj_forward)(___r1, "sizeWithFont:", font)).width);
    (self.isa.method_msgSend["setSize:"] || _objj_forward)(self, "setSize:", CPMakeSize(Math.max(width_hdr, 2 * width_port + CSGColPadding) + 2 * CSGColPadding, rows * CSGRowHeight));
    self.validBounds = YES;
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("anchorPointForPort:"), function $CSGActor__anchorPointForPort_(self, _cmd, port)
{
    var ports = (port == null ? null : (port.isa.method_msgSend["isInport"] || _objj_forward)(port, "isInport")) ? self.inports : self.outports,
        row = 2;
    for (var i = 0; i < ports.length; i++)
    {
        if (port === ports[i])
        {
            break;
        }
        row++;
    }
    var local = CPMakePoint((port == null ? null : (port.isa.method_msgSend["isInport"] || _objj_forward)(port, "isInport")) ? 0.0 : (self.isa.method_msgSend["size"] || _objj_forward)(self, "size").width, row * CSGRowHeight + CSGRowHeight / 2.0 + CSGPadYOffset);
    return CSGAddPoints((self.isa.method_msgSend["origin"] || _objj_forward)(self, "origin"), local);
}

,["GCPoint","CSGPort"]), new objj_method(sel_getUid("drawStatusIndicator:"), function $CSGActor__drawStatusIndicator_(self, _cmd, rect)
{
    var m = CSGRowHeight / 8.0,
        s = CSGRowHeight / 4.0,
        x = rect.origin.x,
        y = rect.origin.y,
        w = rect.size.width,
        h = rect.size.height,
        r = CPMakeRect(x + w - s - m, y + m, s, s);
    if ((self.isa.method_msgSend["hasValidMandatoryArgs"] || _objj_forward)(self, "hasValidMandatoryArgs"))
    {
        return;
    }
    ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGErrorColorHEX)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    ((___r1 = (CPBezierPath.isa.method_msgSend["bezierPathWithOvalInRect:"] || _objj_forward)(CPBezierPath, "bezierPathWithOvalInRect:", r)), ___r1 == null ? null : (___r1.isa.method_msgSend["fill"] || _objj_forward)(___r1, "fill"));
    var ___r1;
}

,["void","CGRect"]), new objj_method(sel_getUid("renderInBounds:dirtyRect:"), function $CSGActor__renderInBounds_dirtyRect_(self, _cmd, _bounds, dirtyRect)
{
    if (self.validBounds === NO)
    {
        (self.isa.method_msgSend["computeBounds"] || _objj_forward)(self, "computeBounds");
    }
    var hexBackColor,
        hexNameColor,
        hexTypeColor,
        hexFrameColor;
    if ((self.isa.method_msgSend["isComponent"] || _objj_forward)(self, "isComponent"))
    {
        hexBackColor = CSGComponentActorBgColorHEX;
        hexNameColor = CSGComponentActorNameBgColorHEX;
        hexTypeColor = CSGComponentActorTypeBgColorHEX;
        hexFrameColor = CSGComponentActorFrameColorHEX;
    }
    else
    {
        hexBackColor = CSGActorBgColorHEX;
        hexNameColor = CSGActorNameBgColorHEX;
        hexTypeColor = CSGActorTypeBgColorHEX;
        hexFrameColor = CSGActorFrameColorHEX;
    }
    ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", hexBackColor)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    var bgRect = CGRectCreateCopy(self.bounds);
    (CPBezierPath.isa.method_msgSend["fillRect:"] || _objj_forward)(CPBezierPath, "fillRect:", bgRect);
    bgRect.size.height = CSGRowHeight;
    ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", hexNameColor)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    (CPBezierPath.isa.method_msgSend["fillRect:"] || _objj_forward)(CPBezierPath, "fillRect:", bgRect);
    ((___r1 = self.name), ___r1 == null ? null : (___r1.isa.method_msgSend["drawInBounds:withAlignment:"] || _objj_forward)(___r1, "drawInBounds:withAlignment:", bgRect, CPCenterTextAlignment));
    (self.isa.method_msgSend["drawStatusIndicator:"] || _objj_forward)(self, "drawStatusIndicator:", bgRect);
    bgRect.origin.y += CSGRowHeight;
    ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", hexTypeColor)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    (CPBezierPath.isa.method_msgSend["fillRect:"] || _objj_forward)(CPBezierPath, "fillRect:", bgRect);
    ((___r1 = self.type), ___r1 == null ? null : (___r1.isa.method_msgSend["drawInBounds:withAlignment:"] || _objj_forward)(___r1, "drawInBounds:withAlignment:", bgRect, CPCenterTextAlignment));
    var row = 2,
        portCount = Math.max(self.inports.length, self.outports.length);
    for (var i = 0; i < portCount; i++)
    {
        bgRect.origin.y = self.bounds.origin.y + (i + row) * CSGRowHeight;
        if (i < self.inports.length)
        {
            ((___r1 = self.inports[i]), ___r1 == null ? null : (___r1.isa.method_msgSend["renderInBounds:"] || _objj_forward)(___r1, "renderInBounds:", bgRect));
        }
        if (i < self.outports.length)
        {
            ((___r1 = self.outports[i]), ___r1 == null ? null : (___r1.isa.method_msgSend["renderInBounds:"] || _objj_forward)(___r1, "renderInBounds:", bgRect));
        }
    }
    var frameColor = (self.isa.method_msgSend["identifier"] || _objj_forward)(self, "identifier") ? "00FF00" : hexFrameColor;
    if ((self.isa.method_msgSend["isSelected"] || _objj_forward)(self, "isSelected"))
    {
        frameColor = CSGEditorHighlightColorHEX;
    }
    ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", frameColor)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    (CPBezierPath.isa.method_msgSend["strokeRect:"] || _objj_forward)(CPBezierPath, "strokeRect:", self.bounds);
    bgRect.origin.y = self.bounds.origin.y - CSGRowHeight;
    ((___r1 = self.nodeName ? self.nodeName : "---"), ___r1 == null ? null : (___r1.isa.method_msgSend["drawInBounds:withAlignment:"] || _objj_forward)(___r1, "drawInBounds:withAlignment:", bgRect, CPCenterTextAlignment));
    var ___r1;
}

,["void","CGRect","CGRect"]), new objj_method(sel_getUid("portAtPoint:"), function $CSGActor__portAtPoint_(self, _cmd, point)
{
    var pos = CSGSubtractPoints((self.isa.method_msgSend["origin"] || _objj_forward)(self, "origin"), point),
        isOutport = YES,
        row = Math.floor(pos.y / CSGRowHeight - 2);
    if (row < 0)
    {
        return nil;
    }
    if (pos.x >= 0.0 && pos.x <= CSGColPadding)
    {
        isOutport = NO;
    }
    else if (pos.x < (self.isa.method_msgSend["size"] || _objj_forward)(self, "size").width - CSGColPadding || pos.x > (self.isa.method_msgSend["size"] || _objj_forward)(self, "size").width)
    {
        return nil;
    }
    var ports = isOutport ? self.outports : self.inports;
    if (row >= ports.count)
    {
        return nil;
    }
    return ports[row];
}

,["CSGPort","GCPoint"])]);
}
p;10;CSGTheme.jt;1310;@STATIC;1.0;t;1291;CSGErrorColorHEX = "FF0000";
CSGOKColorHEX = "00FF00";
CSGEditorViewBgColorHEX = "FFFFFF";
CSGEditorHighlightColorHEX = "EEA420";
CSGEditorHighlightErrorColorHEX = "FCCFD0";
CSGOutlineViewBgColorHEX = "E4E4E2";
CSGInfoViewBgColorHEX = "E4E4E2";
CSGActorBgColorHEX = "FFFFFF";
CSGActorFrameColorHEX = "091637";
CSGActorNameBgColorHEX = "9ECFE0";
CSGActorTypeBgColorHEX = "FFFFFF";
CSGActorPortColorHEX = "B6B6B6";
CSGComponentActorBgColorHEX = "FFFFFF";
CSGComponentActorFrameColorHEX = "091637";
CSGComponentActorNameBgColorHEX = "FFFFD8";
CSGComponentActorTypeBgColorHEX = "FFFFFF";
CSGConnectionColorHEX = "091637";
CSGConnectionPendingColorHEX = "0994BB";
CSGDefaultColorPalette = ["E16E22", "4F0946", "CF1C21", "EEA420", "68B134", "004C43", "0994BB", "767476", "AAAAAA", "EEEEEE", "C8DFA6", "FDE9BE"];
(CSGRowHeight = 20.0, CSGColPadding = 10.0, CSGPadScale = 0.7, CSGPadYOffset = -2.0, CSGMinControlDist = 80.0, CSGSameActorRowDist = 40.0);
CSGUIConsoleBgColorHEX = "555555";
CSGUIConsoleTextColorHEX = "EEEEEE";
CSGUIDeviceWidth = 120.0;
CSGUIDevicePadding = 10.0;
CSGUIDeviceImageHeight = 64.0;
CSGUIDeviceImageWidth = CSGUIDeviceImageHeight;
CSGUIElementInset = 3.0;
CSGUIConsoleWidth = 300.0;
CSGUIConsoleHeight = 200.0;
CSGUIConsoleFontName = "Courier";
CSGUIConsoleFontSize = 12;
p;18;CSGGeometryUtils.jt;195;@STATIC;1.0;t;177;CSGSubtractPoints = function(p0, p1)
{
    return CPMakePoint(p1.x - p0.x, p1.y - p0.y);
}
CSGAddPoints = function(p0, p1)
{
    return CPMakePoint(p1.x + p0.x, p1.y + p0.y);
}
p;19;CSGPort+Rendering.jt;3034;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;9;CSGPort.ji;10;CSGTheme.jt;2939;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGPort.j", YES);objj_executeFile("CSGTheme.j", YES);{
var the_class = objj_getClass("CSGPort")
if(!the_class) throw new SyntaxError("*** Could not find definition for class \"CSGPort\"");
var meta_class = the_class.isa;class_addMethods(the_class, [new objj_method(sel_getUid("computeSize"), function $CSGPort__computeSize(self, _cmd)
{
    var font = (CPFont.isa.method_msgSend["systemFontOfSize:"] || _objj_forward)(CPFont, "systemFontOfSize:", 12);
    var labelSize = ((___r1 = self.portName), ___r1 == null ? null : (___r1.isa.method_msgSend["sizeWithFont:"] || _objj_forward)(___r1, "sizeWithFont:", font));
    self.portSize = CPMakeSize(labelSize.width + CSGColPadding, CSGRowHeight);
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("size"), function $CSGPort__size(self, _cmd)
{
    if (self.portSize.width == 0)
    {
        (self.isa.method_msgSend["computeSize"] || _objj_forward)(self, "computeSize");
    }
    return self.portSize;
}

,["CGSize"]), new objj_method(sel_getUid("renderPadInBounds:"), function $CSGPort__renderPadInBounds_(self, _cmd, bounds)
{
    var pad = (CPBezierPath.isa.method_msgSend["bezierPath"] || _objj_forward)(CPBezierPath, "bezierPath"),
        h = CSGPadScale * CSGRowHeight,
        w = CSGPadScale * CSGColPadding,
        x = bounds.origin.x + (self.isInport ? 0.0 : bounds.size.width - w),
        y = bounds.origin.y + (CSGRowHeight - h) / 2.0 + CSGPadYOffset;
    (pad == null ? null : (pad.isa.method_msgSend["moveToPoint:"] || _objj_forward)(pad, "moveToPoint:", CPMakePoint(x, y)));
    (pad == null ? null : (pad.isa.method_msgSend["lineToPoint:"] || _objj_forward)(pad, "lineToPoint:", CPMakePoint(x, y + h)));
    (pad == null ? null : (pad.isa.method_msgSend["lineToPoint:"] || _objj_forward)(pad, "lineToPoint:", CPMakePoint(x + w, y + h / 2.0)));
    (pad == null ? null : (pad.isa.method_msgSend["closePath"] || _objj_forward)(pad, "closePath"));
    ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGActorPortColorHEX)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    (pad == null ? null : (pad.isa.method_msgSend["fill"] || _objj_forward)(pad, "fill"));
    var ___r1;
}

,["void","CGRect"]), new objj_method(sel_getUid("renderInBounds:"), function $CSGPort__renderInBounds_(self, _cmd, bounds)
{
    (self.isa.method_msgSend["renderPadInBounds:"] || _objj_forward)(self, "renderPadInBounds:", bounds);
    var insetBounds = CGRectInset(bounds, CSGColPadding, 0);
    ((___r1 = self.portName), ___r1 == null ? null : (___r1.isa.method_msgSend["drawInBounds:withAlignment:"] || _objj_forward)(___r1, "drawInBounds:withAlignment:", insetBounds, self.isInport ? CPLeftTextAlignment : CPRightTextAlignment));
    var ___r1;
}

,["void","CGRect"])]);
}
p;25;CSGConnection+Rendering.jt;2401;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;15;CSGConnection.ji;10;CSGTheme.jt;2299;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGConnection.j", YES);objj_executeFile("CSGTheme.j", YES);{
var the_class = objj_getClass("CSGConnection")
if(!the_class) throw new SyntaxError("*** Could not find definition for class \"CSGConnection\"");
var meta_class = the_class.isa;class_addMethods(the_class, [new objj_method(sel_getUid("renderWithDirtyRect:"), function $CSGConnection__renderWithDirtyRect_(self, _cmd, dirtyRect)
{
    var srcLocation = ((___r1 = self.src), ___r1 == null ? null : (___r1.isa.method_msgSend["anchorPointForPort:"] || _objj_forward)(___r1, "anchorPointForPort:", self.srcPort)),
        dstLocation = ((___r1 = self.dst), ___r1 == null ? null : (___r1.isa.method_msgSend["anchorPointForPort:"] || _objj_forward)(___r1, "anchorPointForPort:", self.dstPort)),
        scrCtrlLocation,
        dstCtrlLocation;
    if ((dstLocation.x - srcLocation.x) / 2.0 < CSGMinControlDist)
    {
        var dy = self.src === self.dst && srcLocation.y - dstLocation.y < 1.0 ? CSGSameActorRowDist : 0.0;
        scrCtrlLocation = CPMakePoint(srcLocation.x + CSGMinControlDist, srcLocation.y - dy);
        dstCtrlLocation = CPMakePoint(dstLocation.x - CSGMinControlDist, dstLocation.y + dy);
    }
    else
    {
        scrCtrlLocation = CPMakePoint((srcLocation.x + dstLocation.x) / 2, srcLocation.y);
        dstCtrlLocation = CPMakePoint((srcLocation.x + dstLocation.x) / 2, dstLocation.y);
    }
    var path = (CPBezierPath.isa.method_msgSend["bezierPath"] || _objj_forward)(CPBezierPath, "bezierPath");
    (path == null ? null : (path.isa.method_msgSend["moveToPoint:"] || _objj_forward)(path, "moveToPoint:", srcLocation));
    (path == null ? null : (path.isa.method_msgSend["curveToPoint:controlPoint1:controlPoint2:"] || _objj_forward)(path, "curveToPoint:controlPoint1:controlPoint2:", dstLocation, scrCtrlLocation, dstCtrlLocation));
    ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGConnectionColorHEX)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    (path == null ? null : (path.isa.method_msgSend["stroke"] || _objj_forward)(path, "stroke"));
    var ___r1;
}

,["void","CGRect"])]);
}
p;12;CSGProject.jt;17772;@STATIC;1.0;I;23;Foundation/Foundation.ji;12;CSGProgram.ji;12;CSGBackend.ji;17;CSGScriptViewer.ji;16;CSGAppUIViewer.ji;18;CSGEventListener.jt;17624;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("CSGProgram.j", YES);objj_executeFile("CSGBackend.j", YES);objj_executeFile("CSGScriptViewer.j", YES);objj_executeFile("CSGAppUIViewer.j", YES);objj_executeFile("CSGEventListener.j", YES);
{var the_class = objj_allocateClassPair(CPObject, "CSGProject"),
meta_class = the_class.isa;
var aProtocol = objj_getProtocol("CPCoding");
if (!aProtocol) throw new SyntaxError("*** Could not find definition for protocol \"CPCoding\"");
class_addProtocol(the_class, aProtocol);class_addIvars(the_class, [new objj_ivar("program", "CSGProgram"), new objj_ivar("name", "CPString"), new objj_ivar("appID", "CPString"), new objj_ivar("isUntitled", "BOOL"), new objj_ivar("showUIView", "BOOL"), new objj_ivar("appUIViewer", "CSGAppUIViewer"), new objj_ivar("eventListener", "CSGEventListener"), new objj_ivar("uiDefinitions", "JSObject"), new objj_ivar("uiTimer", "CPTimer")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("program"), function $CSGProject__program(self, _cmd)
{
    return self.program;
}

,["CSGProgram"]), new objj_method(sel_getUid("setProgram:"), function $CSGProject__setProgram_(self, _cmd, newValue)
{
    self.program = newValue;
}

,["void","CSGProgram"]), new objj_method(sel_getUid("name"), function $CSGProject__name(self, _cmd)
{
    return self.name;
}

,["CPString"]), new objj_method(sel_getUid("setName:"), function $CSGProject__setName_(self, _cmd, newValue)
{
    self.name = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("appID"), function $CSGProject__appID(self, _cmd)
{
    return self.appID;
}

,["CPString"]), new objj_method(sel_getUid("setAppID:"), function $CSGProject__setAppID_(self, _cmd, newValue)
{
    self.appID = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("isUntitled"), function $CSGProject__isUntitled(self, _cmd)
{
    return self.isUntitled;
}

,["BOOL"]), new objj_method(sel_getUid("setIsUntitled:"), function $CSGProject__setIsUntitled_(self, _cmd, newValue)
{
    self.isUntitled = newValue;
}

,["void","BOOL"]), new objj_method(sel_getUid("showUIView"), function $CSGProject__showUIView(self, _cmd)
{
    return self.showUIView;
}

,["BOOL"]), new objj_method(sel_getUid("setShowUIView:"), function $CSGProject__setShowUIView_(self, _cmd, newValue)
{
    self.showUIView = newValue;
}

,["void","BOOL"]), new objj_method(sel_getUid("uiDefinitions"), function $CSGProject__uiDefinitions(self, _cmd)
{
    return self.uiDefinitions;
}

,["JSObject"]), new objj_method(sel_getUid("setUiDefinitions:"), function $CSGProject__setUiDefinitions_(self, _cmd, newValue)
{
    self.uiDefinitions = newValue;
}

,["void","JSObject"]), new objj_method(sel_getUid("initWithName:"), function $CSGProject__initWithName_(self, _cmd, projectName)
{
    if (self = (objj_getClass("CSGProject").super_class.method_dtable["init"] || _objj_forward)(self, "init"))
    {
        self.name = projectName;
        self.program = ((___r1 = (CSGProgram.isa.method_msgSend["alloc"] || _objj_forward)(CSGProgram, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
        self.appID = nil;
        self.isUntitled = YES;
        self.uiDefinitions = {};
        (self == null ? null : (self.isa.method_msgSend["setShowUIView:"] || _objj_forward)(self, "setShowUIView:", YES));
    }
    return self;
    var ___r1;
}

,["id","CPString"]), new objj_method(sel_getUid("initWithCoder:"), function $CSGProject__initWithCoder_(self, _cmd, coder)
{
    self = (objj_getClass("CSGProject").super_class.method_dtable["initWithName:"] || _objj_forward)(self, "initWithName:", "_DUMMY_");
    if (self)
    {
        self.program = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "program"));
        self.name = (coder == null ? null : (coder.isa.method_msgSend["decodeObjectForKey:"] || _objj_forward)(coder, "decodeObjectForKey:", "name"));
        self.isUntitled = (coder == null ? null : (coder.isa.method_msgSend["decodeBoolForKey:"] || _objj_forward)(coder, "decodeBoolForKey:", "isUntitled"));
        self.appID = nil;
    }
    return self;
}

,["id","CPCoder"]), new objj_method(sel_getUid("encodeWithCoder:"), function $CSGProject__encodeWithCoder_(self, _cmd, coder)
{
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.program, "program"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeObject:forKey:"] || _objj_forward)(coder, "encodeObject:forKey:", self.name, "name"));
    (coder == null ? null : (coder.isa.method_msgSend["encodeBool:forKey:"] || _objj_forward)(coder, "encodeBool:forKey:", self.isUntitled, "isUntitled"));
}

,["void","CPCoder"]), new objj_method(sel_getUid("setErrors:andWarnings:"), function $CSGProject__setErrors_andWarnings_(self, _cmd, errors, warnings)
{
    errors.forEach(    function(error, i, list)
    {
        list[i] = i + 1 + " : " + error.reason;
    });
    warnings.forEach(    function(warning, i, list)
    {
        list[i] = i + 1 + " : " + warning.reason;
    });
    var errorViewer = ((___r1 = (CSGScriptViewer.isa.method_msgSend["alloc"] || _objj_forward)(CSGScriptViewer, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
    var errorText = (errors == null ? null : (errors.isa.method_msgSend["componentsJoinedByString:"] || _objj_forward)(errors, "componentsJoinedByString:", "\n"));
    var warningText = (warnings == null ? null : (warnings.isa.method_msgSend["componentsJoinedByString:"] || _objj_forward)(warnings, "componentsJoinedByString:", "\n"));
    var text = ((___r1 = ["Errors:", errorText, "", "Warnings:", warningText]), ___r1 == null ? null : (___r1.isa.method_msgSend["componentsJoinedByString:"] || _objj_forward)(___r1, "componentsJoinedByString:", "\n"));
    (errorViewer == null ? null : (errorViewer.isa.method_msgSend["setTitle:"] || _objj_forward)(errorViewer, "setTitle:", "Errors and Warnings"));
    (errorViewer == null ? null : (errorViewer.isa.method_msgSend["setScript:"] || _objj_forward)(errorViewer, "setScript:", text));
    (errorViewer == null ? null : (errorViewer.isa.method_msgSend["setReleasedWhenClosed:"] || _objj_forward)(errorViewer, "setReleasedWhenClosed:", YES));
    var ___r1;
}

,["void","id","id"]), new objj_method(sel_getUid("isRunning"), function $CSGProject__isRunning(self, _cmd)
{
    return self.appID !== nil;
}

,["BOOL"]), new objj_method(sel_getUid("run"), function $CSGProject__run(self, _cmd)
{
    if ((self.isa.method_msgSend["isRunning"] || _objj_forward)(self, "isRunning"))
    {
        return;
    }
    var backend = (CSGBackend.isa.method_msgSend["sharedBackend"] || _objj_forward)(CSGBackend, "sharedBackend");
    var script = ((___r1 = self.program), ___r1 == null ? null : (___r1.isa.method_msgSend["scriptRepresentation"] || _objj_forward)(___r1, "scriptRepresentation"));
    (backend == null ? null : (backend.isa.method_msgSend["deployScript:withName:responseBlock:"] || _objj_forward)(backend, "deployScript:withName:responseBlock:", script, self.name,     function(response)
    {
        var app_id = response.application_id;
        if (app_id === undefined)
        {
            (self.isa.method_msgSend["setErrors:andWarnings:"] || _objj_forward)(self, "setErrors:andWarnings:", response.errors, response.warnings);
        }        else
        {
            (backend == null ? null : (backend.isa.method_msgSend["infoForAppID:usingBlock:"] || _objj_forward)(backend, "infoForAppID:usingBlock:", app_id,             function(info)
            {
                (self.isa.method_msgSend["setRuntimeInfo:"] || _objj_forward)(self, "setRuntimeInfo:", info);
                (self.isa.method_msgSend["setAppID:"] || _objj_forward)(self, "setAppID:", app_id);
                (self.isa.method_msgSend["startUI"] || _objj_forward)(self, "startUI");
            }));
        }    }));
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("stop"), function $CSGProject__stop(self, _cmd)
{
    if (!(self.isa.method_msgSend["isRunning"] || _objj_forward)(self, "isRunning"))
    {
        return;
    }
    var backend = (CSGBackend.isa.method_msgSend["sharedBackend"] || _objj_forward)(CSGBackend, "sharedBackend");
    (backend == null ? null : (backend.isa.method_msgSend["stopAppWithID:responseBlock:"] || _objj_forward)(backend, "stopAppWithID:responseBlock:", self.appID,     function()
    {
        (self.isa.method_msgSend["stopUI"] || _objj_forward)(self, "stopUI");
        ((___r1 = ((___r2 = self.program), ___r2 == null ? null : (___r2.isa.method_msgSend["actors"] || _objj_forward)(___r2, "actors"))), ___r1 == null ? null : (___r1.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(___r1, "setValue:forKey:", nil, "identifier"));
        ((___r1 = ((___r2 = self.program), ___r2 == null ? null : (___r2.isa.method_msgSend["actors"] || _objj_forward)(___r2, "actors"))), ___r1 == null ? null : (___r1.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(___r1, "setValue:forKey:", nil, "nodeName"));
        (self.isa.method_msgSend["setAppID:"] || _objj_forward)(self, "setAppID:", nil);
        var ___r1, ___r2;
    }));
}

,["void"]), new objj_method(sel_getUid("startUI"), function $CSGProject__startUI(self, _cmd)
{
    var backend = (CSGBackend.isa.method_msgSend["sharedBackend"] || _objj_forward)(CSGBackend, "sharedBackend");
    (backend == null ? null : (backend.isa.method_msgSend["getUIDefinitions:responseBlock:"] || _objj_forward)(backend, "getUIDefinitions:responseBlock:", self.appID,     function(defs)
    {
        self.uiDefinitions = defs;
        if (self.uiDefinitions && (self.isa.method_msgSend["hasUIActors"] || _objj_forward)(self, "hasUIActors"))
        {
            self.appUIViewer = ((___r1 = (CSGAppUIViewer.isa.method_msgSend["alloc"] || _objj_forward)(CSGAppUIViewer, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithProject:"] || _objj_forward)(___r1, "initWithProject:", self));
            (self.isa.method_msgSend["addUIEventListener"] || _objj_forward)(self, "addUIEventListener");
            (self.isa.method_msgSend["showUI"] || _objj_forward)(self, "showUI");
        }        var ___r1;
    }));
}

,["void"]), new objj_method(sel_getUid("addUIEventListener"), function $CSGProject__addUIEventListener(self, _cmd)
{
    var HAS_NGINX_REWRITE = NO;
    var host = ((___r1 = (CSGHostConfig.isa.method_msgSend["sharedHostConfig"] || _objj_forward)(CSGHostConfig, "sharedHostConfig")), ___r1 == null ? null : (___r1.isa.method_msgSend["calvinHost"] || _objj_forward)(___r1, "calvinHost"));
    var containerID = ((___r1 = (CSGHostConfig.isa.method_msgSend["sharedHostConfig"] || _objj_forward)(CSGHostConfig, "sharedHostConfig")), ___r1 == null ? null : (___r1.isa.method_msgSend["containerID"] || _objj_forward)(___r1, "containerID"));
    var url = "";
    if (containerID !== "")
    {
        if (HAS_NGINX_REWRITE)
        {
            url = "http://" + host + ":7777/" + containerID + "/client_id/" + self.appID;
        }
        else
        {
            url = "http://" + host + ":5000/event_stream/" + containerID + "/client_id/" + self.appID;
        }
    }
    else
    {
        url = "http://" + host + ":7777/client_id/" + self.appID;
    }
    console.log("Adding eventlistener:", url);
    self.eventListener = ((___r1 = (CSGEventListener.isa.method_msgSend["alloc"] || _objj_forward)(CSGEventListener, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithURL:eventType:dataFormat:"] || _objj_forward)(___r1, "initWithURL:eventType:dataFormat:", url, "message", CSGJSONStringDataFormat));
    ((___r1 = self.eventListener), ___r1 == null ? null : (___r1.isa.method_msgSend["setDelegate:"] || _objj_forward)(___r1, "setDelegate:", self.appUIViewer));
    ((___r1 = self.eventListener), ___r1 == null ? null : (___r1.isa.method_msgSend["startListening"] || _objj_forward)(___r1, "startListening"));
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("stopUI"), function $CSGProject__stopUI(self, _cmd)
{
    (self.isa.method_msgSend["hideUI"] || _objj_forward)(self, "hideUI");
    ((___r1 = self.eventListener), ___r1 == null ? null : (___r1.isa.method_msgSend["stopListening"] || _objj_forward)(___r1, "stopListening"));
    ((___r1 = self.appUIViewer), ___r1 == null ? null : (___r1.isa.method_msgSend["close"] || _objj_forward)(___r1, "close"));
    self.uiDefinitions = {};
    self.appUIViewer = nil;
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("hasUIActors"), function $CSGProject__hasUIActors(self, _cmd)
{
    return (self.isa.method_msgSend["uiActors"] || _objj_forward)(self, "uiActors").length > 0;
}

,["BOOL"]), new objj_method(sel_getUid("uiActors"), function $CSGProject__uiActors(self, _cmd)
{
    var ui_actors = [];
    var actors = ((___r1 = self.program), ___r1 == null ? null : (___r1.isa.method_msgSend["actors"] || _objj_forward)(___r1, "actors"));
    for (var i = 0; i < actors.length; i++)
    {
        var actor = actors[i];
        if (self.uiDefinitions[actor.type])
        {
            ui_actors.push(actor);
        }
    }
    return ui_actors;
    var ___r1;
}

,["CPArray"]), new objj_method(sel_getUid("startUITimer"), function $CSGProject__startUITimer(self, _cmd)
{
    if (!self.uiTimer || !((___r1 = self.uiTimer), ___r1 == null ? null : (___r1.isa.method_msgSend["isValid"] || _objj_forward)(___r1, "isValid")))
    {
        self.uiTimer = (CPTimer.isa.method_msgSend["scheduledTimerWithTimeInterval:callback:repeats:"] || _objj_forward)(CPTimer, "scheduledTimerWithTimeInterval:callback:repeats:", 1,         function()
        {
            (self.isa.method_msgSend["updateUIVisibility"] || _objj_forward)(self, "updateUIVisibility");
        }, YES);
    }
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("stopUITimer"), function $CSGProject__stopUITimer(self, _cmd)
{
    if (self.uiTimer && ((___r1 = self.uiTimer), ___r1 == null ? null : (___r1.isa.method_msgSend["isValid"] || _objj_forward)(___r1, "isValid")))
    {
        ((___r1 = self.uiTimer), ___r1 == null ? null : (___r1.isa.method_msgSend["invalidate"] || _objj_forward)(___r1, "invalidate"));
    }
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("updateUIVisibility"), function $CSGProject__updateUIVisibility(self, _cmd)
{
    ((___r1 = (CSGBackend.isa.method_msgSend["sharedBackend"] || _objj_forward)(CSGBackend, "sharedBackend")), ___r1 == null ? null : (___r1.isa.method_msgSend["actorsOnUIRuntime:"] || _objj_forward)(___r1, "actorsOnUIRuntime:",     function(list)
    {
        ((___r1 = self.appUIViewer), ___r1 == null ? null : (___r1.isa.method_msgSend["updateVisibility:"] || _objj_forward)(___r1, "updateVisibility:", list));
        var ___r1;
    }));
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("setRuntimeInfo:"), function $CSGProject__setRuntimeInfo_(self, _cmd, rti)
{
    if (!rti)
    {
        return;
    }
    var actor_ids = rti.actors;
    var namespace = rti.ns;
    var name_map = (CPDictionary.isa.method_msgSend["dictionaryWithJSObject:"] || _objj_forward)(CPDictionary, "dictionaryWithJSObject:", rti.actors_name_map);
    var actors = ((___r1 = self.program), ___r1 == null ? null : (___r1.isa.method_msgSend["actors"] || _objj_forward)(___r1, "actors"));
    for (var i = 0; i < actors.length; i++)
    {
        var actor = actors[i];
        var qualified_name = namespace + ":" + actor.name;
        var id = (name_map == null ? null : (name_map.isa.method_msgSend["allKeysForObject:"] || _objj_forward)(name_map, "allKeysForObject:", qualified_name))[0];
        (actor == null ? null : (actor.isa.method_msgSend["setIdentifier:"] || _objj_forward)(actor, "setIdentifier:", id));
    }
    var ___r1;
}

,["void","JSObject"]), new objj_method(sel_getUid("setShowUIView:"), function $CSGProject__setShowUIView_(self, _cmd, flag)
{
    if (flag === self.showUIView)
    {
        return;
    }
    self.showUIView = flag;
    if (self.showUIView)
    {
        (self.isa.method_msgSend["showUI"] || _objj_forward)(self, "showUI");
    }
    else
    {
        (self.isa.method_msgSend["hideUI"] || _objj_forward)(self, "hideUI");
    }
}

,["void","BOOL"]), new objj_method(sel_getUid("showUI"), function $CSGProject__showUI(self, _cmd)
{
    if (self.appUIViewer && self.showUIView)
    {
        (self.isa.method_msgSend["startUITimer"] || _objj_forward)(self, "startUITimer");
        ((___r1 = self.appUIViewer), ___r1 == null ? null : (___r1.isa.method_msgSend["showWindow:"] || _objj_forward)(___r1, "showWindow:", self));
    }
    var ___r1;
}

,["void"]), new objj_method(sel_getUid("hideUI"), function $CSGProject__hideUI(self, _cmd)
{
    if (self.appUIViewer)
    {
        ((___r1 = ((___r2 = self.appUIViewer), ___r2 == null ? null : (___r2.isa.method_msgSend["window"] || _objj_forward)(___r2, "window"))), ___r1 == null ? null : (___r1.isa.method_msgSend["orderOut:"] || _objj_forward)(___r1, "orderOut:", self));
        (self.isa.method_msgSend["stopUITimer"] || _objj_forward)(self, "stopUITimer");
    }
    var ___r1, ___r2;
}

,["void"]), new objj_method(sel_getUid("activate"), function $CSGProject__activate(self, _cmd)
{
    (self.isa.method_msgSend["showUI"] || _objj_forward)(self, "showUI");
}

,["void"]), new objj_method(sel_getUid("deactivate"), function $CSGProject__deactivate(self, _cmd)
{
    (self.isa.method_msgSend["hideUI"] || _objj_forward)(self, "hideUI");
}

,["void"])]);
}
p;17;CSGScriptViewer.jt;1739;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.jt;1672;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);
{var the_class = objj_allocateClassPair(CPWindowController, "CSGScriptViewer"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("scriptView", "CPTextView")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("init"), function $CSGScriptViewer__init(self, _cmd)
{
    self = (objj_getClass("CSGScriptViewer").super_class.method_dtable["initWithWindowCibName:"] || _objj_forward)(self, "initWithWindowCibName:", "ScriptViewer");
    if (self)
    {
    }
    return self;
}

,["id"]), new objj_method(sel_getUid("setReleasedWhenClosed:"), function $CSGScriptViewer__setReleasedWhenClosed_(self, _cmd, flag)
{
    console.log("FIXME: [[self window] setReleasedWhenClosed:flag];");
}

,["void","BOOL"]), new objj_method(sel_getUid("setTitle:"), function $CSGScriptViewer__setTitle_(self, _cmd, title)
{
    ((___r1 = (self.isa.method_msgSend["window"] || _objj_forward)(self, "window")), ___r1 == null ? null : (___r1.isa.method_msgSend["setTitle:"] || _objj_forward)(___r1, "setTitle:", title));
    var ___r1;
}

,["void","CPString"]), new objj_method(sel_getUid("setScript:"), function $CSGScriptViewer__setScript_(self, _cmd, script)
{
    ((___r1 = (self.isa.method_msgSend["window"] || _objj_forward)(self, "window")), ___r1 == null ? null : (___r1.isa.method_msgSend["orderFront:"] || _objj_forward)(___r1, "orderFront:", self));
    ((___r1 = self.scriptView), ___r1 == null ? null : (___r1.isa.method_msgSend["setString:"] || _objj_forward)(___r1, "setString:", script));
    var ___r1;
}

,["void","CPString"])]);
}
p;16;CSGAppUIViewer.jt;4862;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;14;CSGAppUIView.ji;12;CSGBackend.ji;18;CSGEventListener.jt;4736;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGAppUIView.j", YES);objj_executeFile("CSGBackend.j", YES);objj_executeFile("CSGEventListener.j", YES);
{var the_class = objj_allocateClassPair(CPWindowController, "CSGAppUIViewer"),
meta_class = the_class.isa;
var aProtocol = objj_getProtocol("CSGEventListening");
if (!aProtocol) throw new SyntaxError("*** Could not find definition for protocol \"CSGEventListening\"");
class_addProtocol(the_class, aProtocol);class_addIvars(the_class, [new objj_ivar("project", "CSGProject"), new objj_ivar("appUIView", "CSGAppUIView")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("initWithProject:"), function $CSGAppUIViewer__initWithProject_(self, _cmd, aProject)
{
    self = (objj_getClass("CSGAppUIViewer").super_class.method_dtable["initWithWindowCibName:"] || _objj_forward)(self, "initWithWindowCibName:", "AppUIViewer");
    if (self)
    {
        self.project = aProject;
        ((___r1 = (self == null ? null : (self.isa.method_msgSend["window"] || _objj_forward)(self, "window"))), ___r1 == null ? null : (___r1.isa.method_msgSend["setTitle:"] || _objj_forward)(___r1, "setTitle:", "Device Simulation"));
        ((___r1 = self.appUIView), ___r1 == null ? null : (___r1.isa.method_msgSend["addActors:definitions:"] || _objj_forward)(___r1, "addActors:definitions:", ((___r2 = self.project), ___r2 == null ? null : (___r2.isa.method_msgSend["uiActors"] || _objj_forward)(___r2, "uiActors")), ((___r2 = self.project), ___r2 == null ? null : (___r2.isa.method_msgSend["uiDefinitions"] || _objj_forward)(___r2, "uiDefinitions"))));
    }
    return self;
    var ___r1, ___r2;
}

,["id","CSGProject"]), new objj_method(sel_getUid("updateVisibility:"), function $CSGAppUIViewer__updateVisibility_(self, _cmd, actorsOnRuntime)
{
    ((___r1 = self.appUIView), ___r1 == null ? null : (___r1.isa.method_msgSend["updateVisibility:"] || _objj_forward)(___r1, "updateVisibility:", actorsOnRuntime));
    var ___r1;
}

,["void","CPArray"]), new objj_method(sel_getUid("uiAction:"), function $CSGAppUIViewer__uiAction_(self, _cmd, sender)
{
    var data = nil;
    switch((sender == null ? null : (sender.isa.method_msgSend["class"] || _objj_forward)(sender, "class"))) {
        case CPButton:
        case CSGButton:
            data = (sender == null ? null : (sender.isa.method_msgSend["state"] || _objj_forward)(sender, "state"));
            break;
        case CPSlider:
            data = (sender == null ? null : (sender.isa.method_msgSend["floatValue"] || _objj_forward)(sender, "floatValue"));
            break;
default:
            console.log("FIXME: get value", sender);
            break;
    }
    if (data !== nil)
    {
        (self.isa.method_msgSend["eventFor:withData:"] || _objj_forward)(self, "eventFor:withData:", sender, data);
    }
}

,["void","id"]), new objj_method(sel_getUid("eventFor:withData:"), function $CSGAppUIViewer__eventFor_withData_(self, _cmd, control, data)
{
    var actor_id = ((___r1 = (control == null ? null : (control.isa.method_msgSend["superview"] || _objj_forward)(control, "superview"))), ___r1 == null ? null : (___r1.isa.method_msgSend["actor"] || _objj_forward)(___r1, "actor")).identifier;
    var backend = (CSGBackend.isa.method_msgSend["sharedBackend"] || _objj_forward)(CSGBackend, "sharedBackend");
    (backend == null ? null : (backend.isa.method_msgSend["generateEventForActor:withData:"] || _objj_forward)(backend, "generateEventForActor:withData:", actor_id, data));
    var ___r1;
}

,["void","id","JSObject"]), new objj_method(sel_getUid("uiSetAction:"), function $CSGAppUIViewer__uiSetAction_(self, _cmd, sender)
{
    (self.isa.method_msgSend["eventFor:withData:"] || _objj_forward)(self, "eventFor:withData:", sender, 1);
}

,["void","id"]), new objj_method(sel_getUid("uiResetAction:"), function $CSGAppUIViewer__uiResetAction_(self, _cmd, sender)
{
    (self.isa.method_msgSend["eventFor:withData:"] || _objj_forward)(self, "eventFor:withData:", sender, 0);
}

,["void","id"]), new objj_method(sel_getUid("eventWithData:sender:"), function $CSGAppUIViewer__eventWithData_sender_(self, _cmd, data, sender)
{
    var actors = ((___r1 = self.project.program), ___r1 == null ? null : (___r1.isa.method_msgSend["actors"] || _objj_forward)(___r1, "actors"));
    for (var i = 0; i < actors.length; i++)
    {
        var actor = actors[i];
        if (data.client_id == actor.identifier)
        {
            (actor == null ? null : (actor.isa.method_msgSend["setUiState:"] || _objj_forward)(actor, "setUiState:", data.state));
            break;
        }
    }
    var ___r1;
}

,["void","id","CSGEventListener"])]);
}
p;14;CSGAppUIView.jt;2420;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;16;CSGActorUIView.jt;2332;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGActorUIView.j", YES);
{var the_class = objj_allocateClassPair(CPView, "CSGAppUIView"),
meta_class = the_class.isa;objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("addActors:definitions:"), function $CSGAppUIView__addActors_definitions_(self, _cmd, actors, defs)
{
    var delta = 10;
    for (var i = 0; i < actors.length; i++)
    {
        var actor = actors[i];
        var config = defs[actor.type];
        var origin = CGPointMake(delta, delta);
        delta += 20;
        var new_ui = ((___r1 = (CSGActorUIView.isa.method_msgSend["alloc"] || _objj_forward)(CSGActorUIView, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithActor:config:origin:"] || _objj_forward)(___r1, "initWithActor:config:origin:", actor, config, origin));
        (self.isa.method_msgSend["addSubview:"] || _objj_forward)(self, "addSubview:", new_ui);
    }
    (self.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(self, "setNeedsDisplay:", YES);
    var ___r1;
}

,["void","CPArray","JSObject"]), new objj_method(sel_getUid("updateVisibility:"), function $CSGAppUIView__updateVisibility_(self, _cmd, actorsOnRuntime)
{
    var actorUIViews = (self.isa.method_msgSend["subviews"] || _objj_forward)(self, "subviews");
    for (var i = 0; i < actorUIViews.length; i++)
    {
        var actorUIView = actorUIViews[i];
        (actorUIView == null ? null : (actorUIView.isa.method_msgSend["updateVisibility:"] || _objj_forward)(actorUIView, "updateVisibility:", actorsOnRuntime));
    }
}

,["void","CPArray"]), new objj_method(sel_getUid("drawRect:"), function $CSGAppUIView__drawRect_(self, _cmd, dirtyRect)
{
    ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGEditorViewBgColorHEX)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    (CPBezierPath.isa.method_msgSend["fillRect:"] || _objj_forward)(CPBezierPath, "fillRect:", (self.isa.method_msgSend["bounds"] || _objj_forward)(self, "bounds"));
    var ___r1;
}

,["void","CGRect"]), new objj_method(sel_getUid("isFlipped"), function $CSGAppUIView__isFlipped(self, _cmd)
{
    return YES;
}

,["BOOL"])]);
}
p;16;CSGActorUIView.jt;25501;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;10;CSGTheme.jt;25418;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGTheme.j", YES);{
var the_class = objj_getClass("CPTextView")
if(!the_class) throw new SyntaxError("*** Could not find definition for class \"CPTextView\"");
var meta_class = the_class.isa;class_addMethods(the_class, [new objj_method(sel_getUid("appendText:"), function $CPTextView__appendText_(self, _cmd, aString)
{
    var isAttributed = (aString == null ? null : (aString.isa.method_msgSend["isKindOfClass:"] || _objj_forward)(aString, "isKindOfClass:", CPAttributedString)),
        string = isAttributed ? (aString == null ? null : (aString.isa.method_msgSend["string"] || _objj_forward)(aString, "string")) : aString;
    (self.isa.method_msgSend["willChangeValueForKey:"] || _objj_forward)(self, "willChangeValueForKey:", "objectValue");
    ((___r1 = self._textStorage), ___r1 == null ? null : (___r1.isa.method_msgSend["replaceCharactersInRange:withAttributedString:"] || _objj_forward)(___r1, "replaceCharactersInRange:withAttributedString:", CPMakeRangeCopy(self._selectionRange), aString));
    (self.isa.method_msgSend["didChangeValueForKey:"] || _objj_forward)(self, "didChangeValueForKey:", "objectValue");
    (self.isa.method_msgSend["_continuouslyReverseSetBinding"] || _objj_forward)(self, "_continuouslyReverseSetBinding");
    var selectionRange = CPMakeRange(((___r1 = (self.isa.method_msgSend["string"] || _objj_forward)(self, "string")), ___r1 == null ? null : (___r1.isa.method_msgSend["length"] || _objj_forward)(___r1, "length")), 0);
    (self.isa.method_msgSend["_setSelectedRange:affinity:stillSelecting:overwriteTypingAttributes:"] || _objj_forward)(self, "_setSelectedRange:affinity:stillSelecting:overwriteTypingAttributes:", selectionRange, 0, NO, NO);
    self._startTrackingLocation = self._selectionRange.location;
    (self.isa.method_msgSend["didChangeText"] || _objj_forward)(self, "didChangeText");
    ((___r1 = self._layoutManager), ___r1 == null ? null : (___r1.isa.method_msgSend["_validateLayoutAndGlyphs"] || _objj_forward)(___r1, "_validateLayoutAndGlyphs"));
    (self.isa.method_msgSend["sizeToFit"] || _objj_forward)(self, "sizeToFit");
    (self.isa.method_msgSend["scrollRangeToVisible:"] || _objj_forward)(self, "scrollRangeToVisible:", self._selectionRange);
    self._stickyXLocation = MAX(0, self._caret._rect.origin.x - 1);
    var ___r1;
}

,["void","CPAttributedString"])]);
}

{var the_class = objj_allocateClassPair(CPButton, "CSGButton"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("mouseDownAction", "SEL")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("mouseDownAction"), function $CSGButton__mouseDownAction(self, _cmd)
{
    return self.mouseDownAction;
}

,["SEL"]), new objj_method(sel_getUid("setMouseDownAction:"), function $CSGButton__setMouseDownAction_(self, _cmd, newValue)
{
    self.mouseDownAction = newValue;
}

,["void","SEL"]), new objj_method(sel_getUid("mouseDown:"), function $CSGButton__mouseDown_(self, _cmd, anEvent)
{
    if ((self.isa.method_msgSend["mouseDownAction"] || _objj_forward)(self, "mouseDownAction"))
    {
        (CPApp == null ? null : (CPApp.isa.method_msgSend["sendAction:to:from:"] || _objj_forward)(CPApp, "sendAction:to:from:", (self.isa.method_msgSend["mouseDownAction"] || _objj_forward)(self, "mouseDownAction"), (self.isa.method_msgSend["target"] || _objj_forward)(self, "target"), self));
    }
    (objj_getClass("CSGButton").super_class.method_dtable["mouseDown:"] || _objj_forward)(self, "mouseDown:", anEvent);
}

,["void","CPEvent"])]);
}

{var the_class = objj_allocateClassPair(CPTextField, "CSGBuzzer"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("sound", "JSObject")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("sound"), function $CSGBuzzer__sound(self, _cmd)
{
    return self.sound;
}

,["JSObject"]), new objj_method(sel_getUid("setSound:"), function $CSGBuzzer__setSound_(self, _cmd, newValue)
{
    self.sound = newValue;
}

,["void","JSObject"]), new objj_method(sel_getUid("initWithFrame:"), function $CSGBuzzer__initWithFrame_(self, _cmd, aFrame)
{
    self = (objj_getClass("CSGBuzzer").super_class.method_dtable["initWithFrame:"] || _objj_forward)(self, "initWithFrame:", aFrame);
    if (self)
    {
        self.sound = new webkitAudioContext();
        var oscillator = self.sound.createOscillator();
        console.log(self.sound, oscillator);
        oscillator.type = 'square';
        oscillator.frequency.value = 440;
        oscillator.connect(self.sound.destination);
        oscillator.start();
        if (self.sound)
        {
            self.sound.suspend();
        }
    }
    return self;
}

,["id","CGRect"]), new objj_method(sel_getUid("setObjectValue:"), function $CSGBuzzer__setObjectValue_(self, _cmd, obj)
{
    console.log();
    var volume = obj || 0;
    if (volume === 0)
    {
        if (self.sound)
        {
            self.sound.suspend();
        }
    }
    else
    {
        if (self.sound)
        {
            self.sound.resume();
        }
    }
    (objj_getClass("CSGBuzzer").super_class.method_dtable["setObjectValue:"] || _objj_forward)(self, "setObjectValue:", obj);
}

,["void","id"])]);
}

{var the_class = objj_allocateClassPair(CPView, "CSGActorUIView"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("actor", "CSGActor"), new objj_ivar("imageView", "CPImageView"), new objj_ivar("defaultImage", "CPImage"), new objj_ivar("alternateImage", "CPImage"), new objj_ivar("dragLocation", "CGPoint"), new objj_ivar("layout", "JSObject"), new objj_ivar("_console_attrs", "CPDictionary")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("actor"), function $CSGActorUIView__actor(self, _cmd)
{
    return self.actor;
}

,["CSGActor"]), new objj_method(sel_getUid("setActor:"), function $CSGActorUIView__setActor_(self, _cmd, newValue)
{
    self.actor = newValue;
}

,["void","CSGActor"]), new objj_method(sel_getUid("initWithActor:config:origin:"), function $CSGActorUIView__initWithActor_config_origin_(self, _cmd, anActor, config, origin)
{
    self = (objj_getClass("CSGActorUIView").super_class.method_dtable["initWithFrame:"] || _objj_forward)(self, "initWithFrame:", CGRectMakeZero());
    if (self)
    {
        self.actor = anActor;
        self._console_attrs = (___r1 = (CPDictionary.isa.method_msgSend["alloc"] || _objj_forward)(CPDictionary, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithObjects:forKeys:"] || _objj_forward)(___r1, "initWithObjects:forKeys:", [(CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGUIConsoleTextColorHEX), (CPFont.isa.method_msgSend["fontWithName:size:"] || _objj_forward)(CPFont, "fontWithName:size:", CSGUIConsoleFontName, CSGUIConsoleFontSize)], [CPForegroundColorAttributeName, CPFontAttributeName]));
        self.layout = (CSGActorUIView.isa.method_msgSend["layout:"] || _objj_forward)(CSGActorUIView, "layout:", config);
        (self == null ? null : (self.isa.method_msgSend["setFrameSize:"] || _objj_forward)(self, "setFrameSize:", self.layout.frame.size));
        (self == null ? null : (self.isa.method_msgSend["setFrameOrigin:"] || _objj_forward)(self, "setFrameOrigin:", origin));
        (self == null ? null : (self.isa.method_msgSend["setup:"] || _objj_forward)(self, "setup:", config));
    }
    return self;
    var ___r1;
}

,["id","CSGActor","JSObject","CGPoint"]), new objj_method(sel_getUid("setup:"), function $CSGActorUIView__setup_(self, _cmd, config)
{
    var label = ((___r1 = (CPTextField.isa.method_msgSend["alloc"] || _objj_forward)(CPTextField, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithFrame:"] || _objj_forward)(___r1, "initWithFrame:", self.layout.name_frame));
    (label == null ? null : (label.isa.method_msgSend["setEditable:"] || _objj_forward)(label, "setEditable:", NO));
    (label == null ? null : (label.isa.method_msgSend["setAlignment:"] || _objj_forward)(label, "setAlignment:", CPCenterTextAlignment));
    (label == null ? null : (label.isa.method_msgSend["bind:toObject:withKeyPath:options:"] || _objj_forward)(label, "bind:toObject:withKeyPath:options:", CPValueBinding, self.actor, "name", nil));
    (self.isa.method_msgSend["addSubview:"] || _objj_forward)(self, "addSubview:", label);
    (self.isa.method_msgSend["_loadImages:"] || _objj_forward)(self, "_loadImages:", config);
    self.imageView = ((___r1 = (CPImageView.isa.method_msgSend["alloc"] || _objj_forward)(CPImageView, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithFrame:"] || _objj_forward)(___r1, "initWithFrame:", self.layout.image_frame));
    ((___r1 = self.imageView), ___r1 == null ? null : (___r1.isa.method_msgSend["setImageScaling:"] || _objj_forward)(___r1, "setImageScaling:", CPImageScaleProportionallyDown));
    ((___r1 = self.imageView), ___r1 == null ? null : (___r1.isa.method_msgSend["setImage:"] || _objj_forward)(___r1, "setImage:", self.defaultImage));
    (self.isa.method_msgSend["addSubview:"] || _objj_forward)(self, "addSubview:", self.imageView);
    var control = (self.isa.method_msgSend["_physicalControl:"] || _objj_forward)(self, "_physicalControl:", config.control);
    (self.isa.method_msgSend["addSubview:"] || _objj_forward)(self, "addSubview:", control);
    var ___r1;
}

,["void","JSObject"]), new objj_method(sel_getUid("_loadImages:"), function $CSGActorUIView___loadImages_(self, _cmd, config)
{
    var imageName = "Resources/" + config.image + ".png";
    self.defaultImage = ((___r1 = (CPImage.isa.method_msgSend["alloc"] || _objj_forward)(CPImage, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithContentsOfFile:"] || _objj_forward)(___r1, "initWithContentsOfFile:", imageName));
    imageName = "Resources/" + config.image + "_alt.png";
    self.alternateImage = ((___r1 = (CPImage.isa.method_msgSend["alloc"] || _objj_forward)(CPImage, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initByReferencingFile:size:"] || _objj_forward)(___r1, "initByReferencingFile:size:", imageName, CGSizeMake(-1, -1)));
    ((___r1 = self.alternateImage), ___r1 == null ? null : (___r1.isa.method_msgSend["setDelegate:"] || _objj_forward)(___r1, "setDelegate:", self));
    ((___r1 = self.alternateImage), ___r1 == null ? null : (___r1.isa.method_msgSend["load"] || _objj_forward)(___r1, "load"));
    var ___r1;
}

,["void","JSObject"]), new objj_method(sel_getUid("imageDidError:"), function $CSGActorUIView__imageDidError_(self, _cmd, image)
{
    if (image == self.alternateImage)
    {
        self.alternateImage = nil;
    }
}

,["void","CPImage"]), new objj_method(sel_getUid("_physicalControl:"), function $CSGActorUIView___physicalControl_(self, _cmd, cConfig)
{
    var control = nil;
    if (cConfig.sensor)
    {
        control = (self.isa.method_msgSend["_physicalSensor:"] || _objj_forward)(self, "_physicalSensor:", cConfig);
    }
    else
    {
        control = (self.isa.method_msgSend["_physicalActuator:"] || _objj_forward)(self, "_physicalActuator:", cConfig);
    }
    return control;
}

,["id","JSObject"]), new objj_method(sel_getUid("_physicalSensor:"), function $CSGActorUIView___physicalSensor_(self, _cmd, cConfig)
{
    var control;
    if (cConfig.type === "boolean")
    {
        control = ((___r1 = (CSGButton.isa.method_msgSend["alloc"] || _objj_forward)(CSGButton, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithFrame:"] || _objj_forward)(___r1, "initWithFrame:", self.layout.control_frame));
        (control == null ? null : (control.isa.method_msgSend["setTarget:"] || _objj_forward)(control, "setTarget:", nil));
        if (cConfig.behaviour === "momentary")
        {
            (control == null ? null : (control.isa.method_msgSend["setButtonType:"] || _objj_forward)(control, "setButtonType:", CPMomentaryPushInButton));
            (control == null ? null : (control.isa.method_msgSend["setState:"] || _objj_forward)(control, "setState:", cConfig['default'] ? 0 : 1));
            (control == null ? null : (control.isa.method_msgSend["setMouseDownAction:"] || _objj_forward)(control, "setMouseDownAction:", sel_getUid("uiSetAction:")));
            (control == null ? null : (control.isa.method_msgSend["setAction:"] || _objj_forward)(control, "setAction:", sel_getUid("uiResetAction:")));
        }
        else
        {
            (control == null ? null : (control.isa.method_msgSend["setButtonType:"] || _objj_forward)(control, "setButtonType:", CPPushOnPushOffButton));
            (control == null ? null : (control.isa.method_msgSend["setState:"] || _objj_forward)(control, "setState:", cConfig['default'] ? 1 : 0));
            (control == null ? null : (control.isa.method_msgSend["setAction:"] || _objj_forward)(control, "setAction:", sel_getUid("uiAction:")));
        }
    }
    else
    {
        control = ((___r1 = (CPSlider.isa.method_msgSend["alloc"] || _objj_forward)(CPSlider, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithFrame:"] || _objj_forward)(___r1, "initWithFrame:", self.layout.control_frame));
        (control == null ? null : (control.isa.method_msgSend["setTarget:"] || _objj_forward)(control, "setTarget:", nil));
        (control == null ? null : (control.isa.method_msgSend["setAction:"] || _objj_forward)(control, "setAction:", sel_getUid("uiAction:")));
        (control == null ? null : (control.isa.method_msgSend["setMaxValue:"] || _objj_forward)(control, "setMaxValue:", cConfig.max));
        (control == null ? null : (control.isa.method_msgSend["setMinValue:"] || _objj_forward)(control, "setMinValue:", cConfig.min));
        (control == null ? null : (control.isa.method_msgSend["setContinuous:"] || _objj_forward)(control, "setContinuous:", NO));
        (control == null ? null : (control.isa.method_msgSend["setObjectValue:"] || _objj_forward)(control, "setObjectValue:", cConfig['default']));
    }
    return control;
    var ___r1;
}

,["id","JSObject"]), new objj_method(sel_getUid("_physicalActuator:"), function $CSGActorUIView___physicalActuator_(self, _cmd, cConfig)
{
    var control;
    if (cConfig.type == "console")
    {
        var scrollview = ((___r1 = (CPScrollView.isa.method_msgSend["alloc"] || _objj_forward)(CPScrollView, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithFrame:"] || _objj_forward)(___r1, "initWithFrame:", self.layout.control_frame));
        (scrollview == null ? null : (scrollview.isa.method_msgSend["setHasVerticalScroller:"] || _objj_forward)(scrollview, "setHasVerticalScroller:", YES));
        (scrollview == null ? null : (scrollview.isa.method_msgSend["setHasHorizontalScroller:"] || _objj_forward)(scrollview, "setHasHorizontalScroller:", NO));
        (scrollview == null ? null : (scrollview.isa.method_msgSend["setAutohidesScrollers:"] || _objj_forward)(scrollview, "setAutohidesScrollers:", YES));
        (scrollview == null ? null : (scrollview.isa.method_msgSend["setAutoresizingMask:"] || _objj_forward)(scrollview, "setAutoresizingMask:", CPViewWidthSizable | CPViewHeightSizable));
        control = ((___r1 = (CPTextView.isa.method_msgSend["alloc"] || _objj_forward)(CPTextView, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithFrame:"] || _objj_forward)(___r1, "initWithFrame:", (scrollview == null ? null : (scrollview.isa.method_msgSend["bounds"] || _objj_forward)(scrollview, "bounds"))));
        (control == null ? null : (control.isa.method_msgSend["setAutoresizingMask:"] || _objj_forward)(control, "setAutoresizingMask:", CPViewWidthSizable | CPViewHeightSizable));
        (control == null ? null : (control.isa.method_msgSend["setEditable:"] || _objj_forward)(control, "setEditable:", NO));
        (control == null ? null : (control.isa.method_msgSend["setBackgroundColor:"] || _objj_forward)(control, "setBackgroundColor:", (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGUIConsoleBgColorHEX)));
        (scrollview == null ? null : (scrollview.isa.method_msgSend["setDocumentView:"] || _objj_forward)(scrollview, "setDocumentView:", control));
        ((___r1 = self.actor), ___r1 == null ? null : (___r1.isa.method_msgSend["addObserver:forKeyPath:options:context:"] || _objj_forward)(___r1, "addObserver:forKeyPath:options:context:", self, "uiState", CPKeyValueChangeSetting, scrollview));
        ((___r1 = self.actor), ___r1 == null ? null : (___r1.isa.method_msgSend["setUiState:"] || _objj_forward)(___r1, "setUiState:", ""));
        control = scrollview;
    }
    else if (cConfig.behaviour === "audio")
    {
        control = ((___r1 = (CSGBuzzer.isa.method_msgSend["alloc"] || _objj_forward)(CSGBuzzer, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithFrame:"] || _objj_forward)(___r1, "initWithFrame:", self.layout.control_frame));
        (control == null ? null : (control.isa.method_msgSend["setEditable:"] || _objj_forward)(control, "setEditable:", NO));
        (control == null ? null : (control.isa.method_msgSend["setAlignment:"] || _objj_forward)(control, "setAlignment:", CPCenterTextAlignment));
        (control == null ? null : (control.isa.method_msgSend["bind:toObject:withKeyPath:options:"] || _objj_forward)(control, "bind:toObject:withKeyPath:options:", CPValueBinding, self.actor, "uiState", nil));
        ((___r1 = self.actor), ___r1 == null ? null : (___r1.isa.method_msgSend["setUiState:"] || _objj_forward)(___r1, "setUiState:", cConfig['default'] || 0));
    }
    else
    {
        control = ((___r1 = (CPTextField.isa.method_msgSend["alloc"] || _objj_forward)(CPTextField, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithFrame:"] || _objj_forward)(___r1, "initWithFrame:", self.layout.control_frame));
        (control == null ? null : (control.isa.method_msgSend["setEditable:"] || _objj_forward)(control, "setEditable:", NO));
        (control == null ? null : (control.isa.method_msgSend["setAlignment:"] || _objj_forward)(control, "setAlignment:", CPCenterTextAlignment));
        (control == null ? null : (control.isa.method_msgSend["bind:toObject:withKeyPath:options:"] || _objj_forward)(control, "bind:toObject:withKeyPath:options:", CPValueBinding, self.actor, "uiState", nil));
        if (cConfig.type === "boolean" || cConfig.type === "int")
        {
            ((___r1 = self.actor), ___r1 == null ? null : (___r1.isa.method_msgSend["addObserver:forKeyPath:options:context:"] || _objj_forward)(___r1, "addObserver:forKeyPath:options:context:", self, "uiState", CPKeyValueChangeSetting, nil));
        }
        ((___r1 = self.actor), ___r1 == null ? null : (___r1.isa.method_msgSend["setUiState:"] || _objj_forward)(___r1, "setUiState:", cConfig['default'] || 0));
    }
    return control;
    var ___r1;
}

,["id","JSObject"]), new objj_method(sel_getUid("observeValueForKeyPath:ofObject:change:context:"), function $CSGActorUIView__observeValueForKeyPath_ofObject_change_context_(self, _cmd, keyPath, object, change, context)
{
    if (context)
    {
        var text = ((___r1 = (CPAttributedString.isa.method_msgSend["alloc"] || _objj_forward)(CPAttributedString, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithString:attributes:"] || _objj_forward)(___r1, "initWithString:attributes:", "" + object.uiState, self._console_attrs));
        ((___r1 = (context == null ? null : (context.isa.method_msgSend["documentView"] || _objj_forward)(context, "documentView"))), ___r1 == null ? null : (___r1.isa.method_msgSend["appendText:"] || _objj_forward)(___r1, "appendText:", text));
        return;
    }
    if (self.alternateImage === nil)
    {
        return;
    }
    ((___r1 = self.imageView), ___r1 == null ? null : (___r1.isa.method_msgSend["setImage:"] || _objj_forward)(___r1, "setImage:", ((___r2 = object.uiState), ___r2 == null ? null : (___r2.isa.method_msgSend["boolValue"] || _objj_forward)(___r2, "boolValue")) ? self.alternateImage : self.defaultImage));
    var ___r1, ___r2;
}

,["void","CPString","id","CPDictionary","id"]), new objj_method(sel_getUid("updateVisibility:"), function $CSGActorUIView__updateVisibility_(self, _cmd, actorsOnRuntime)
{
    var hidden = YES;
    if (actorsOnRuntime)
    {
        for (var i = 0; i < actorsOnRuntime.length; i++)
        {
            if (self.actor.identifier === actorsOnRuntime[i])
            {
                hidden = NO;
                break;
            }
        }
    }
    (self.isa.method_msgSend["setHidden:"] || _objj_forward)(self, "setHidden:", hidden);
}

,["void","CPArray"]), new objj_method(sel_getUid("mouseDown:"), function $CSGActorUIView__mouseDown_(self, _cmd, anEvent)
{
    self.dragLocation = (anEvent == null ? null : (anEvent.isa.method_msgSend["locationInWindow"] || _objj_forward)(anEvent, "locationInWindow"));
}

,["void","CPEvent"]), new objj_method(sel_getUid("mouseDragged:"), function $CSGActorUIView__mouseDragged_(self, _cmd, anEvent)
{
    var location = (anEvent == null ? null : (anEvent.isa.method_msgSend["locationInWindow"] || _objj_forward)(anEvent, "locationInWindow")),
        origin = (self.isa.method_msgSend["frame"] || _objj_forward)(self, "frame").origin;
    if (self.dragLocation == nil)
    {
        self.dragLocation = location;
    }
    (self.isa.method_msgSend["setFrameOrigin:"] || _objj_forward)(self, "setFrameOrigin:", CGPointMake(origin.x + location.x - self.dragLocation.x, origin.y + location.y - self.dragLocation.y));
    self.dragLocation = location;
}

,["void","CPEvent"]), new objj_method(sel_getUid("mouseUp:"), function $CSGActorUIView__mouseUp_(self, _cmd, anEvent)
{
    var aPoint = (anEvent == null ? null : (anEvent.isa.method_msgSend["locationInWindow"] || _objj_forward)(anEvent, "locationInWindow")).origin;
    (self.isa.method_msgSend["setFrameOrigin:"] || _objj_forward)(self, "setFrameOrigin:", aPoint);
}

,["void","CPEvent"]), new objj_method(sel_getUid("drawRect:"), function $CSGActorUIView__drawRect_(self, _cmd, aRect)
{
    ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGEditorViewBgColorHEX)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    (CPBezierPath.isa.method_msgSend["fillRect:"] || _objj_forward)(CPBezierPath, "fillRect:", (self.isa.method_msgSend["bounds"] || _objj_forward)(self, "bounds"));
    ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGActorNameBgColorHEX)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    (CPBezierPath.isa.method_msgSend["fillRect:"] || _objj_forward)(CPBezierPath, "fillRect:", self.layout.title_frame);
    if (((___r1 = self.actor), ___r1 == null ? null : (___r1.isa.method_msgSend["isSelected"] || _objj_forward)(___r1, "isSelected")))
    {
        ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGEditorHighlightColorHEX)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    }
    else
    {
        ((___r1 = (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGComponentActorFrameColorHEX)), ___r1 == null ? null : (___r1.isa.method_msgSend["set"] || _objj_forward)(___r1, "set"));
    }
    (CPBezierPath.isa.method_msgSend["strokeRect:"] || _objj_forward)(CPBezierPath, "strokeRect:", (self.isa.method_msgSend["bounds"] || _objj_forward)(self, "bounds"));
    var ___r1;
}

,["void","CPRect"])]);
class_addMethods(meta_class, [new objj_method(sel_getUid("layout:"), function $CSGActorUIView__layout_(self, _cmd, config)
{
    var layout = {};
    switch(config.control.type) {
        case "console":
            layout.title_frame = CGRectMake(0, 0, CSGUIConsoleWidth, CSGRowHeight);
            layout.name_frame = CGRectInset(CGRectCreateCopy(layout.title_frame), CSGUIElementInset, CSGUIElementInset);
            layout.image_frame = CGRectMakeZero();
            layout.control_frame = CGRectMake(0, CSGRowHeight, CSGUIConsoleWidth, CSGUIConsoleHeight);
            layout.control_frame = CGRectInset(layout.control_frame, CSGUIElementInset, CSGUIElementInset);
            layout.frame = CGRectMake(0, 0, CSGUIConsoleWidth, CSGRowHeight + CSGUIConsoleHeight);
            break;
default:
            layout.title_frame = CGRectMake(0, 0, CSGUIDeviceWidth, CSGRowHeight);
            layout.name_frame = CGRectInset(CGRectCreateCopy(layout.title_frame), CSGUIElementInset, CSGUIElementInset);
            layout.image_frame = CGRectMake((CSGUIDeviceWidth - CSGUIDeviceImageWidth) / 2.0, CSGRowHeight + CSGUIDevicePadding, CSGUIDeviceImageWidth, CSGUIDeviceImageHeight);
            layout.control_frame = CGRectMake(0, CSGRowHeight + CSGUIDevicePadding * 2.0 + CSGUIDeviceImageHeight, CSGUIDeviceWidth, CSGRowHeight);
            layout.control_frame = CGRectInset(layout.control_frame, CSGUIDevicePadding, 0);
            layout.frame = CGRectMake(0, 0, CSGUIDeviceWidth, CSGRowHeight * 2.0 + CSGUIDevicePadding * 3.0 + CSGUIDeviceImageHeight);
            break;
    }
    return layout;
}

,["JSObject","JSObject"])]);
}
p;18;CSGEventListener.jt;4684;@STATIC;1.0;I;23;Foundation/Foundation.jt;4637;objj_executeFile("Foundation/Foundation.j", NO);{var the_typedef = objj_allocateTypeDef("CSGEventDataFormat");
objj_registerTypeDef(the_typedef);
}CSGInvalidDataFormat = 0;
CSGRawDataFormat = 1;
CSGJSONStringDataFormat = 2;
CSGJSONDataFormat = 3;
{var the_protocol = objj_allocateProtocol("CSGEventListening");
objj_registerProtocol(the_protocol);
protocol_addMethodDescriptions(the_protocol, [new objj_method(sel_getUid("eventWithData:sender:"), Nil
,["void","id","CSGEventListener"])], true, true);
}
{var the_class = objj_allocateClassPair(CPObject, "CSGEventListener"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("dataFormat", "CSGEventDataFormat"), new objj_ivar("eventName", "CPString"), new objj_ivar("delegate", "id"), new objj_ivar("eventSource", "Object"), new objj_ivar("dataConverter", "Function"), new objj_ivar("listener", "Function")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("dataFormat"), function $CSGEventListener__dataFormat(self, _cmd)
{
    return self.dataFormat;
}

,["CSGEventDataFormat"]), new objj_method(sel_getUid("setDataFormat:"), function $CSGEventListener__setDataFormat_(self, _cmd, newValue)
{
    self.dataFormat = newValue;
}

,["void","CSGEventDataFormat"]), new objj_method(sel_getUid("eventType"), function $CSGEventListener__eventType(self, _cmd)
{
    return self.eventName;
}

,["CPString"]), new objj_method(sel_getUid("setEventName:"), function $CSGEventListener__setEventName_(self, _cmd, newValue)
{
    self.eventName = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("delegate"), function $CSGEventListener__delegate(self, _cmd)
{
    return self.delegate;
}

,["id"]), new objj_method(sel_getUid("setDelegate:"), function $CSGEventListener__setDelegate_(self, _cmd, newValue)
{
    self.delegate = newValue;
}

,["void","id"]), new objj_method(sel_getUid("initWithURL:eventType:dataFormat:"), function $CSGEventListener__initWithURL_eventType_dataFormat_(self, _cmd, anURL, eventType, fmt)
{
    if (self = (objj_getClass("CSGEventListener").super_class.method_dtable["init"] || _objj_forward)(self, "init"))
    {
        self.eventSource = new EventSource(anURL);
        self.eventName = eventType;
        (self == null ? null : (self.isa.method_msgSend["_setDataFormat:"] || _objj_forward)(self, "_setDataFormat:", fmt));
        self.eventSource.onerror =         function(e)
        {
            console.log("EventSource failed ", self);
        };
    }
    return self;
}

,["id","CPURL","CPString","CSGEventDataFormat"]), new objj_method(sel_getUid("_setDataFormat:"), function $CSGEventListener___setDataFormat_(self, _cmd, fmt)
{
    switch(fmt) {
        case CSGRawDataFormat:
            self.dataFormat = fmt;
            self.dataConverter =             function(x)
            {
                return x;
            };
            break;
        case CSGJSONStringDataFormat:
            self.dataFormat = fmt;
            self.dataConverter = JSON.parse;
            break;
default:
            self.dataFormat = CSGInvalidDataFormat;
            self.dataConverter =             function(x)
            {
                return x;
            };
            break;
    }
}

,["void","CSGEventDataFormat"]), new objj_method(sel_getUid("isListening"), function $CSGEventListener__isListening(self, _cmd)
{
    return self.listener != nil;
}

,["BOOL"]), new objj_method(sel_getUid("startListening"), function $CSGEventListener__startListening(self, _cmd)
{
    if (self.listener)
    {
        return;
    }
    self.listener =     function(evt)
    {
        if (self.delegate)
        {
            ((___r1 = self.delegate), ___r1 == null ? null : (___r1.isa.method_msgSend["eventWithData:sender:"] || _objj_forward)(___r1, "eventWithData:sender:", self.dataConverter(evt.data), self));
            ((___r1 = (CPRunLoop.isa.method_msgSend["currentRunLoop"] || _objj_forward)(CPRunLoop, "currentRunLoop")), ___r1 == null ? null : (___r1.isa.method_msgSend["limitDateForMode:"] || _objj_forward)(___r1, "limitDateForMode:", CPDefaultRunLoopMode));
        }        else
        {
            console.log("No delegate, dropping event:", evt);
        }        var ___r1;
    };
    self.eventSource.addEventListener(self.eventName, self.listener, false);
}

,["void"]), new objj_method(sel_getUid("stopListening"), function $CSGEventListener__stopListening(self, _cmd)
{
    if (!self.listener)
    {
        return;
    }
    self.eventSource.removeEventListener(self.eventName, self.listener, false);
    self.eventSource.close();
    self.listener = nil;
}

,["void"])]);
}
p;20;CSGDataPersistance.jt;7474;@STATIC;1.0;I;23;Foundation/Foundation.ji;12;CSGBackend.jt;7410;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("CSGBackend.j", YES);{var the_protocol = objj_allocateProtocol("CSGPersistance");
objj_registerProtocol(the_protocol);
protocol_addMethodDescriptions(the_protocol, [new objj_method(sel_getUid("needsAuthentication"), Nil
,["BOOL"]), new objj_method(sel_getUid("setValue:forKey:"), Nil
,["void","id","CPString"]), new objj_method(sel_getUid("valueForKey:responseBlock:"), Nil
,["void","CPString","Function"]), new objj_method(sel_getUid("allKeysUsingResponseBlock:"), Nil
,["void","Function"]), new objj_method(sel_getUid("deleteValueForKey:"), Nil
,["void","CPString"])], true, true);
}
{var the_class = objj_allocateClassPair(CPObject, "CSGBasePersistence"),
meta_class = the_class.isa;
var aProtocol = objj_getProtocol("CSGPersistance");
if (!aProtocol) throw new SyntaxError("*** Could not find definition for protocol \"CSGPersistance\"");
class_addProtocol(the_class, aProtocol);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("init"), function $CSGBasePersistence__init(self, _cmd)
{
    return (objj_getClass("CSGBasePersistence").super_class.method_dtable["init"] || _objj_forward)(self, "init");
}

,["id"]), new objj_method(sel_getUid("needsAuthentication"), function $CSGBasePersistence__needsAuthentication(self, _cmd)
{
    return NO;
}

,["BOOL"]), new objj_method(sel_getUid("setValue:forKey:"), function $CSGBasePersistence__setValue_forKey_(self, _cmd, value, key)
{
}

,["void","id","CPString"]), new objj_method(sel_getUid("valueForKey:responseBlock:"), function $CSGBasePersistence__valueForKey_responseBlock_(self, _cmd, key, responseBlock)
{
    responseBlock(nil);
}

,["void","CPString","Function"]), new objj_method(sel_getUid("allKeysUsingResponseBlock:"), function $CSGBasePersistence__allKeysUsingResponseBlock_(self, _cmd, responseBlock)
{
    responseBlock([]);
}

,["void","Function"]), new objj_method(sel_getUid("deleteValueForKey:"), function $CSGBasePersistence__deleteValueForKey_(self, _cmd, key)
{
}

,["void","CPString"])]);
}

{var the_class = objj_allocateClassPair(CSGBasePersistence, "CSGLocalPersistence"),
meta_class = the_class.isa;objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("init"), function $CSGLocalPersistence__init(self, _cmd)
{
    if (self = (objj_getClass("CSGLocalPersistence").super_class.method_dtable["init"] || _objj_forward)(self, "init"))
    {
        try {
            var x = '__storage_test__';
            window.localStorage.setItem(x, x);
            window.localStorage.removeItem(x);
        }
        catch(e) {
            CPLogAlert("\nHTML5 local storage not available.\nSaving and loading will be disabled.");
            return ((___r1 = (CSGBasePersistence.isa.method_msgSend["alloc"] || _objj_forward)(CSGBasePersistence, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
            var ___r1;
        }
    }
    return self;
}

,["id"]), new objj_method(sel_getUid("needsAuthentication"), function $CSGLocalPersistence__needsAuthentication(self, _cmd)
{
    return NO;
}

,["BOOL"]), new objj_method(sel_getUid("setValue:forKey:"), function $CSGLocalPersistence__setValue_forKey_(self, _cmd, value, key)
{
    var dataString = ((___r1 = (CPKeyedArchiver.isa.method_msgSend["archivedDataWithRootObject:"] || _objj_forward)(CPKeyedArchiver, "archivedDataWithRootObject:", value)), ___r1 == null ? null : (___r1.isa.method_msgSend["rawString"] || _objj_forward)(___r1, "rawString"));
    window.localStorage.setItem(key, dataString);
    var ___r1;
}

,["void","id","CPString"]), new objj_method(sel_getUid("valueForKey:responseBlock:"), function $CSGLocalPersistence__valueForKey_responseBlock_(self, _cmd, key, responseBlock)
{
    var dataString = window.localStorage.getItem(key);
    var value = dataString !== null ? (CPKeyedUnarchiver.isa.method_msgSend["unarchiveObjectWithData:"] || _objj_forward)(CPKeyedUnarchiver, "unarchiveObjectWithData:", (CPData.isa.method_msgSend["dataWithRawString:"] || _objj_forward)(CPData, "dataWithRawString:", dataString)) : nil;
    responseBlock(value);
}

,["void","CPString","Function"]), new objj_method(sel_getUid("allKeysUsingResponseBlock:"), function $CSGLocalPersistence__allKeysUsingResponseBlock_(self, _cmd, responseBlock)
{
    var n = window.localStorage.length;
    var keys = [];
    for (var i = 0; i < n; i++)
    {
        keys[i] = window.localStorage.key(i);
    }
    responseBlock(keys);
}

,["void","Function"]), new objj_method(sel_getUid("deleteValueForKey:"), function $CSGLocalPersistence__deleteValueForKey_(self, _cmd, key)
{
    window.localStorage.removeItem(key);
}

,["void","CPString"])]);
}

{var the_class = objj_allocateClassPair(CPObject, "CSGRemotePersistence"),
meta_class = the_class.isa;
var aProtocol = objj_getProtocol("CSGPersistance");
if (!aProtocol) throw new SyntaxError("*** Could not find definition for protocol \"CSGPersistance\"");
class_addProtocol(the_class, aProtocol);class_addIvars(the_class, [new objj_ivar("backend", "CSGBackend"), new objj_ivar("authToken", "CPString")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("authToken"), function $CSGRemotePersistence__authToken(self, _cmd)
{
    return self.authToken;
}

,["CPString"]), new objj_method(sel_getUid("setAuthToken:"), function $CSGRemotePersistence__setAuthToken_(self, _cmd, newValue)
{
    self.authToken = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("init"), function $CSGRemotePersistence__init(self, _cmd)
{
    if (self = (objj_getClass("CSGRemotePersistence").super_class.method_dtable["init"] || _objj_forward)(self, "init"))
    {
        self.backend = (CSGBackend.isa.method_msgSend["sharedBackend"] || _objj_forward)(CSGBackend, "sharedBackend");
        self.authToken = nil;
    }
    return self;
}

,["id"]), new objj_method(sel_getUid("needsAuthentication"), function $CSGRemotePersistence__needsAuthentication(self, _cmd)
{
    return YES;
}

,["BOOL"]), new objj_method(sel_getUid("setValue:forKey:"), function $CSGRemotePersistence__setValue_forKey_(self, _cmd, value, key)
{
    ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["storeValue:forKey:authToken:"] || _objj_forward)(___r1, "storeValue:forKey:authToken:", value, key, self.authToken));
    var ___r1;
}

,["void","id","CPString"]), new objj_method(sel_getUid("valueForKey:responseBlock:"), function $CSGRemotePersistence__valueForKey_responseBlock_(self, _cmd, key, responseBlock)
{
    ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["fetchValueForKey:responseBlock:"] || _objj_forward)(___r1, "fetchValueForKey:responseBlock:", key, responseBlock));
    var ___r1;
}

,["void","CPString","Function"]), new objj_method(sel_getUid("allKeysUsingResponseBlock:"), function $CSGRemotePersistence__allKeysUsingResponseBlock_(self, _cmd, responseBlock)
{
    ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["fetchAllKeysUsingResponseBlock:"] || _objj_forward)(___r1, "fetchAllKeysUsingResponseBlock:", responseBlock));
    var ___r1;
}

,["void","Function"]), new objj_method(sel_getUid("deleteValueForKey:"), function $CSGRemotePersistence__deleteValueForKey_(self, _cmd, key)
{
    CPLog("Not implemented");
}

,["void","CPString"])]);
}
p;14;CSGInspector.jt;11188;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;14;CSGComponent.ji;10;CSGActor.ji;15;CSGConnection.ji;10;CSGTheme.jt;11051;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGComponent.j", YES);objj_executeFile("CSGActor.j", YES);objj_executeFile("CSGConnection.j", YES);objj_executeFile("CSGTheme.j", YES);
{var the_class = objj_allocateClassPair(CPViewController, "CSGInspector"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("component", "CSGComponent"), new objj_ivar("delegate", "id"), new objj_ivar("keys", "CPArray"), new objj_ivar("optKeys", "CPArray"), new objj_ivar("mandatoryCount", "CPInteger"), new objj_ivar("totalCount", "CPInteger"), new objj_ivar("docs", "CPString"), new objj_ivar("panelNameField", "CPTextField"), new objj_ivar("panelTypeField", "CPTextField"), new objj_ivar("panelTableView", "CPTableView")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("docs"), function $CSGInspector__docs(self, _cmd)
{
    return self.docs;
}

,["CPString"]), new objj_method(sel_getUid("setDocs:"), function $CSGInspector__setDocs_(self, _cmd, newValue)
{
    self.docs = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("initWithDelegate:"), function $CSGInspector__initWithDelegate_(self, _cmd, inspectorDelegate)
{
    self = (objj_getClass("CSGInspector").super_class.method_dtable["initWithCibName:bundle:externalNameTable:"] || _objj_forward)(self, "initWithCibName:bundle:externalNameTable:", "InspectorView", nil, nil);
    if (self)
    {
        self.delegate = inspectorDelegate;
        ((___r1 = (self == null ? null : (self.isa.method_msgSend["view"] || _objj_forward)(self, "view"))), ___r1 == null ? null : (___r1.isa.method_msgSend["setHidden:"] || _objj_forward)(___r1, "setHidden:", YES));
        self.docs = "";
    }
    return self;
    var ___r1;
}

,["id","id"]), new objj_method(sel_getUid("observeValueForKeyPath:ofObject:change:context:"), function $CSGInspector__observeValueForKeyPath_ofObject_change_context_(self, _cmd, keyPath, object, change, context)
{
    var newSel = (change == null ? null : (change.isa.method_msgSend["objectForKey:"] || _objj_forward)(change, "objectForKey:", "CPKeyValueChangeNewKey"));
    (self.isa.method_msgSend["setComponent:"] || _objj_forward)(self, "setComponent:", newSel);
}

,["void","CPString","id","CPDictionary","id"]), new objj_method(sel_getUid("setComponent:"), function $CSGInspector__setComponent_(self, _cmd, comp)
{
    self.component = comp;
    if ((comp == null ? null : (comp.isa.method_msgSend["isKindOfClass:"] || _objj_forward)(comp, "isKindOfClass:", (CSGActor.isa.method_msgSend["class"] || _objj_forward)(CSGActor, "class"))))
    {
        ((___r1 = (self.isa.method_msgSend["view"] || _objj_forward)(self, "view")), ___r1 == null ? null : (___r1.isa.method_msgSend["setHidden:"] || _objj_forward)(___r1, "setHidden:", NO));
        ((___r1 = self.panelNameField), ___r1 == null ? null : (___r1.isa.method_msgSend["setStringValue:"] || _objj_forward)(___r1, "setStringValue:", comp.name));
        ((___r1 = self.panelTypeField), ___r1 == null ? null : (___r1.isa.method_msgSend["setStringValue:"] || _objj_forward)(___r1, "setStringValue:", comp.type));
        (self.isa.method_msgSend["setDocs:"] || _objj_forward)(self, "setDocs:", comp.docs);
        self.keys = ((___r1 = ((___r2 = comp.mandatoryArgs), ___r2 == null ? null : (___r2.isa.method_msgSend["allKeys"] || _objj_forward)(___r2, "allKeys"))), ___r1 == null ? null : (___r1.isa.method_msgSend["sortedArrayUsingSelector:"] || _objj_forward)(___r1, "sortedArrayUsingSelector:", sel_getUid("caseInsensitiveCompare:")));
        self.optKeys = ((___r1 = ((___r2 = comp.optionalArgs), ___r2 == null ? null : (___r2.isa.method_msgSend["allKeys"] || _objj_forward)(___r2, "allKeys"))), ___r1 == null ? null : (___r1.isa.method_msgSend["sortedArrayUsingSelector:"] || _objj_forward)(___r1, "sortedArrayUsingSelector:", sel_getUid("caseInsensitiveCompare:")));
        self.mandatoryCount = ((___r1 = self.keys), ___r1 == null ? null : (___r1.isa.method_msgSend["count"] || _objj_forward)(___r1, "count"));
        self.totalCount = self.mandatoryCount + ((___r1 = self.optKeys), ___r1 == null ? null : (___r1.isa.method_msgSend["count"] || _objj_forward)(___r1, "count"));
    }
    else
    {
        self.totalCount = 0;
        ((___r1 = (self.isa.method_msgSend["view"] || _objj_forward)(self, "view")), ___r1 == null ? null : (___r1.isa.method_msgSend["setHidden:"] || _objj_forward)(___r1, "setHidden:", YES));
        (self.isa.method_msgSend["setDocs:"] || _objj_forward)(self, "setDocs:", "");
    }
    ((___r1 = self.panelTableView), ___r1 == null ? null : (___r1.isa.method_msgSend["reloadData"] || _objj_forward)(___r1, "reloadData"));
    var ___r1, ___r2;
}

,["void","CGSComponent"]), new objj_method(sel_getUid("updateName:"), function $CSGInspector__updateName_(self, _cmd, sender)
{
    if (self.component === nil || !((___r1 = self.component), ___r1 == null ? null : (___r1.isa.method_msgSend["isKindOfClass:"] || _objj_forward)(___r1, "isKindOfClass:", (CSGActor.isa.method_msgSend["class"] || _objj_forward)(CSGActor, "class"))))
    {
        console.log("ERROR: updateName BAD COMPONENT", self.component, sender);
        return;
    }
    if (((___r1 = self.delegate), ___r1 == null ? null : (___r1.isa.method_msgSend["shouldSetName:forActor:"] || _objj_forward)(___r1, "shouldSetName:forActor:", (sender == null ? null : (sender.isa.method_msgSend["stringValue"] || _objj_forward)(sender, "stringValue")), self.component)))
    {
        ((___r1 = self.component), ___r1 == null ? null : (___r1.isa.method_msgSend["setName:"] || _objj_forward)(___r1, "setName:", (sender == null ? null : (sender.isa.method_msgSend["stringValue"] || _objj_forward)(sender, "stringValue"))));
        ((___r1 = self.delegate), ___r1 == null ? null : (___r1.isa.method_msgSend["refreshViewForActor:"] || _objj_forward)(___r1, "refreshViewForActor:", self.component));
    }
    else
    {
        (sender == null ? null : (sender.isa.method_msgSend["setStringValue:"] || _objj_forward)(sender, "setStringValue:", ((___r1 = self.component), ___r1 == null ? null : (___r1.isa.method_msgSend["name"] || _objj_forward)(___r1, "name"))));
    }
    var ___r1;
}

,["void","id"]), new objj_method(sel_getUid("controlTextDidEndEditing:"), function $CSGInspector__controlTextDidEndEditing_(self, _cmd, aNotification)
{
    var row = ((___r1 = self.panelTableView), ___r1 == null ? null : (___r1.isa.method_msgSend["selectedRow"] || _objj_forward)(___r1, "selectedRow"));
    if (row < 0)
    {
        return;
    }
    var textField = (aNotification == null ? null : (aNotification.isa.method_msgSend["object"] || _objj_forward)(aNotification, "object"));
    var value = (textField == null ? null : (textField.isa.method_msgSend["stringValue"] || _objj_forward)(textField, "stringValue"));
    if (row < self.mandatoryCount)
    {
        var key = self.keys[row];
        ((___r1 = self.component), ___r1 == null ? null : (___r1.isa.method_msgSend["setMandatoryValue:forKey:"] || _objj_forward)(___r1, "setMandatoryValue:forKey:", value, key));
    }
    else
    {
        var key = self.optKeys[row - self.mandatoryCount];
        ((___r1 = self.component), ___r1 == null ? null : (___r1.isa.method_msgSend["setOptionalValue:forKey:"] || _objj_forward)(___r1, "setOptionalValue:forKey:", value, key));
    }
    (self.isa.method_msgSend["_updateTextField:atRow:forKey:"] || _objj_forward)(self, "_updateTextField:atRow:forKey:", textField, row, key);
    ((___r1 = self.delegate), ___r1 == null ? null : (___r1.isa.method_msgSend["refreshViewForActor:"] || _objj_forward)(___r1, "refreshViewForActor:", self.component));
    var ___r1;
}

,["void","CPNotification"]), new objj_method(sel_getUid("_updateTextField:atRow:forKey:"), function $CSGInspector___updateTextField_atRow_forKey_(self, _cmd, textField, row, key)
{
    var bgColors = ((___r1 = self.panelTableView), ___r1 == null ? null : (___r1.isa.method_msgSend["alternatingRowBackgroundColors"] || _objj_forward)(___r1, "alternatingRowBackgroundColors"));
    var valid = ((___r1 = self.component.argOK), ___r1 == null ? null : (___r1.isa.method_msgSend["valueForKey:"] || _objj_forward)(___r1, "valueForKey:", key));
    var bgColor = valid ? bgColors[row % 2] : (CPColor.isa.method_msgSend["colorWithHexString:"] || _objj_forward)(CPColor, "colorWithHexString:", CSGEditorHighlightErrorColorHEX);
    (textField == null ? null : (textField.isa.method_msgSend["setBackgroundColor:"] || _objj_forward)(textField, "setBackgroundColor:", bgColor));
    (textField == null ? null : (textField.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(textField, "setNeedsDisplay:", YES));
    var ___r1;
}

,["void","CPTextField","CPInteger","CPString"]), new objj_method(sel_getUid("numberOfRowsInTableView:"), function $CSGInspector__numberOfRowsInTableView_(self, _cmd, tv)
{
    return self.totalCount;
}

,["CPInteger","CPTableView"]), new objj_method(sel_getUid("tableView:viewForTableColumn:row:"), function $CSGInspector__tableView_viewForTableColumn_row_(self, _cmd, table, tableColumn, row)
{
    var key,
        displayKey,
        value,
        colId = tableColumn._identifier;
    if (row < self.mandatoryCount)
    {
        key = self.keys[row];
        displayKey = key;
        value = ((___r1 = self.component.mandatoryArgs), ___r1 == null ? null : (___r1.isa.method_msgSend["objectForKey:"] || _objj_forward)(___r1, "objectForKey:", key));
    }
    else
    {
        key = self.optKeys[row - self.mandatoryCount];
        value = ((___r1 = self.component.optionalArgs), ___r1 == null ? null : (___r1.isa.method_msgSend["objectForKey:"] || _objj_forward)(___r1, "objectForKey:", key));
        displayKey = (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "(%@)", key);
    }
    var textField = (table == null ? null : (table.isa.method_msgSend["makeViewWithIdentifier:owner:"] || _objj_forward)(table, "makeViewWithIdentifier:owner:", colId, self));
    if ((colId == null ? null : (colId.isa.method_msgSend["isEqualToString:"] || _objj_forward)(colId, "isEqualToString:", "args")))
    {
        (textField == null ? null : (textField.isa.method_msgSend["setStringValue:"] || _objj_forward)(textField, "setStringValue:", displayKey));
    }
    else if ((colId == null ? null : (colId.isa.method_msgSend["isEqualToString:"] || _objj_forward)(colId, "isEqualToString:", "vals")))
    {
        (textField == null ? null : (textField.isa.method_msgSend["setStringValue:"] || _objj_forward)(textField, "setStringValue:", value));
        (self.isa.method_msgSend["_updateTextField:atRow:forKey:"] || _objj_forward)(self, "_updateTextField:atRow:forKey:", textField, row, key);
    }
    else
    {
        (textField == null ? null : (textField.isa.method_msgSend["setStringValue:"] || _objj_forward)(textField, "setStringValue:", "ERROR"));
    }
    return textField;
    var ___r1;
}

,["CPView","CPTableView","CPTableColumn","CPInteger"])]);
}
p;21;CSGRuntimeInspector.jt;10928;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;14;CSGComponent.ji;10;CSGActor.ji;15;CSGConnection.ji;12;CSGBackend.jt;10789;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGComponent.j", YES);objj_executeFile("CSGActor.j", YES);objj_executeFile("CSGConnection.j", YES);objj_executeFile("CSGBackend.j", YES);
{var the_class = objj_allocateClassPair(CPViewController, "CSGRuntimeInspector"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("component", "CSGComponent"), new objj_ivar("ports", "CPArray"), new objj_ivar("panelNameField", "CPTextField"), new objj_ivar("panelTypeField", "CPTextField"), new objj_ivar("runtimeDict", "CPMutableDictionary"), new objj_ivar("runtimeList", "CPArray"), new objj_ivar("backend", "CSGBackend")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("ports"), function $CSGRuntimeInspector__ports(self, _cmd)
{
    return self.ports;
}

,["CPArray"]), new objj_method(sel_getUid("setPorts:"), function $CSGRuntimeInspector__setPorts_(self, _cmd, newValue)
{
    self.ports = newValue;
}

,["void","CPArray"]), new objj_method(sel_getUid("init"), function $CSGRuntimeInspector__init(self, _cmd)
{
    self = (objj_getClass("CSGRuntimeInspector").super_class.method_dtable["initWithCibName:bundle:externalNameTable:"] || _objj_forward)(self, "initWithCibName:bundle:externalNameTable:", "RuntimeInspectorView", nil, nil);
    if (self)
    {
        self.backend = (CSGBackend.isa.method_msgSend["sharedBackend"] || _objj_forward)(CSGBackend, "sharedBackend");
        ((___r1 = (self == null ? null : (self.isa.method_msgSend["view"] || _objj_forward)(self, "view"))), ___r1 == null ? null : (___r1.isa.method_msgSend["setHidden:"] || _objj_forward)(___r1, "setHidden:", YES));
        self.runtimeList = [];
        self.runtimeDict = (___r1 = (CPDictionary.isa.method_msgSend["alloc"] || _objj_forward)(CPDictionary, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
        ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["getRuntimeInfoResponseBlock:"] || _objj_forward)(___r1, "getRuntimeInfoResponseBlock:",         function(dict)
        {
            (self == null ? null : (self.isa.method_msgSend["setRuntimeDict:"] || _objj_forward)(self, "setRuntimeDict:", dict));
        }));
    }
    return self;
    var ___r1;
}

,["id"]), new objj_method(sel_getUid("setRuntimeDict:"), function $CSGRuntimeInspector__setRuntimeDict_(self, _cmd, dict)
{
    var names = (dict == null ? null : (dict.isa.method_msgSend["allKeys"] || _objj_forward)(dict, "allKeys"));
    names.sort();
    self.runtimeDict = dict;
    (self.isa.method_msgSend["setRuntimeList:"] || _objj_forward)(self, "setRuntimeList:", names);
}

,["void","id"]), new objj_method(sel_getUid("runtimeDict"), function $CSGRuntimeInspector__runtimeDict(self, _cmd)
{
    return self.runtimeDict;
}

,["CPDictionary"]), new objj_method(sel_getUid("setRuntimeList:"), function $CSGRuntimeInspector__setRuntimeList_(self, _cmd, list)
{
    self.runtimeList = list;
}

,["void","id"]), new objj_method(sel_getUid("runtimeList"), function $CSGRuntimeInspector__runtimeList(self, _cmd)
{
    return self.runtimeList;
}

,["CPArray"]), new objj_method(sel_getUid("observeValueForKeyPath:ofObject:change:context:"), function $CSGRuntimeInspector__observeValueForKeyPath_ofObject_change_context_(self, _cmd, keyPath, object, change, context)
{
    var newSel = (change == null ? null : (change.isa.method_msgSend["objectForKey:"] || _objj_forward)(change, "objectForKey:", "CPKeyValueChangeNewKey"));
    (self.isa.method_msgSend["setComponent:"] || _objj_forward)(self, "setComponent:", newSel);
    ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["getRuntimeInfoResponseBlock:"] || _objj_forward)(___r1, "getRuntimeInfoResponseBlock:",     function(dict)
    {
        (self.isa.method_msgSend["setRuntimeDict:"] || _objj_forward)(self, "setRuntimeDict:", dict);
    }));
    var ___r1;
}

,["void","CPString","id","CPDictionary","id"]), new objj_method(sel_getUid("setComponent:"), function $CSGRuntimeInspector__setComponent_(self, _cmd, comp)
{
    self.component = comp;
    if ((comp == null ? null : (comp.isa.method_msgSend["isKindOfClass:"] || _objj_forward)(comp, "isKindOfClass:", (CSGActor.isa.method_msgSend["class"] || _objj_forward)(CSGActor, "class"))))
    {
        ((___r1 = (self.isa.method_msgSend["view"] || _objj_forward)(self, "view")), ___r1 == null ? null : (___r1.isa.method_msgSend["setHidden:"] || _objj_forward)(___r1, "setHidden:", NO));
        ((___r1 = self.panelNameField), ___r1 == null ? null : (___r1.isa.method_msgSend["setStringValue:"] || _objj_forward)(___r1, "setStringValue:", comp.name));
        ((___r1 = self.panelTypeField), ___r1 == null ? null : (___r1.isa.method_msgSend["setStringValue:"] || _objj_forward)(___r1, "setStringValue:", comp.type));
        ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["infoForActorID:withResponseBlock:"] || _objj_forward)(___r1, "infoForActorID:withResponseBlock:", (comp == null ? null : (comp.isa.method_msgSend["identifier"] || _objj_forward)(comp, "identifier")),         function(info)
        {
            (self.isa.method_msgSend["setActorInfo:"] || _objj_forward)(self, "setActorInfo:", info);
        }));
    }
    else
    {
        ((___r1 = (self.isa.method_msgSend["view"] || _objj_forward)(self, "view")), ___r1 == null ? null : (___r1.isa.method_msgSend["setHidden:"] || _objj_forward)(___r1, "setHidden:", YES));
    }
    var ___r1;
}

,["void","CGSComponent"]), new objj_method(sel_getUid("setActorInfo:"), function $CSGRuntimeInspector__setActorInfo_(self, _cmd, info)
{
    if (info.is_shadow === undefined)
    {
        ((___r1 = self.component), ___r1 == null ? null : (___r1.isa.method_msgSend["setStatus:"] || _objj_forward)(___r1, "setStatus:", "Undefined"));
    }
    else
    {
        ((___r1 = self.component), ___r1 == null ? null : (___r1.isa.method_msgSend["setStatus:"] || _objj_forward)(___r1, "setStatus:", info.is_shadow ? "Shadow" : "Running"));
    }
    var tmpPorts = [];
    var inports = info.inports;
    for (var i = 0; i < inports.length; i++)
    {
        var port = (CPMutableDictionary.isa.method_msgSend["dictionaryWithJSObject:"] || _objj_forward)(CPMutableDictionary, "dictionaryWithJSObject:", inports[i]);
        (port == null ? null : (port.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(port, "setValue:forKey:", "in", "direction"));
        (port == null ? null : (port.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(port, "setValue:forKey:", 0, "tokenCount"));
        (tmpPorts == null ? null : (tmpPorts.isa.method_msgSend["addObject:"] || _objj_forward)(tmpPorts, "addObject:", port));
        var port_id = (port == null ? null : (port.isa.method_msgSend["valueForKey:"] || _objj_forward)(port, "valueForKey:", "id"));
        ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["infoForNode:actor:port:responseBlock:"] || _objj_forward)(___r1, "infoForNode:actor:port:responseBlock:", info.node_id, ((___r2 = self.component), ___r2 == null ? null : (___r2.isa.method_msgSend["identifier"] || _objj_forward)(___r2, "identifier")), port_id,         function(info)
        {
            (self.isa.method_msgSend["setPort:info:"] || _objj_forward)(self, "setPort:info:", port_id, info);
        }));
    }
    var outports = info.outports;
    for (var i = 0; i < outports.length; i++)
    {
        var port = (CPMutableDictionary.isa.method_msgSend["dictionaryWithJSObject:"] || _objj_forward)(CPMutableDictionary, "dictionaryWithJSObject:", outports[i]);
        (port == null ? null : (port.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(port, "setValue:forKey:", "out", "direction"));
        (port == null ? null : (port.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(port, "setValue:forKey:", 0, "tokenCount"));
        (tmpPorts == null ? null : (tmpPorts.isa.method_msgSend["addObject:"] || _objj_forward)(tmpPorts, "addObject:", port));
        var port_id = (port == null ? null : (port.isa.method_msgSend["valueForKey:"] || _objj_forward)(port, "valueForKey:", "id"));
        ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["infoForNode:actor:port:responseBlock:"] || _objj_forward)(___r1, "infoForNode:actor:port:responseBlock:", info.node_id, ((___r2 = self.component), ___r2 == null ? null : (___r2.isa.method_msgSend["identifier"] || _objj_forward)(___r2, "identifier")), port_id,         function(info)
        {
            (self.isa.method_msgSend["setPort:info:"] || _objj_forward)(self, "setPort:info:", port_id, info);
        }));
    }
    (self.isa.method_msgSend["setPorts:"] || _objj_forward)(self, "setPorts:", tmpPorts);
    var ___r1, ___r2;
}

,["void","JSObject"]), new objj_method(sel_getUid("setPort:info:"), function $CSGRuntimeInspector__setPort_info_(self, _cmd, portID, info)
{
    (self.isa.method_msgSend["willChangeValueForKey:"] || _objj_forward)(self, "willChangeValueForKey:", "ports");
    var wpos = info.write_pos;
    var rpos_object = info.read_pos;
    var rpos_list = [];
    for (var property in rpos_object)
    {
        if (rpos_object.hasOwnProperty(property))
        {
            (rpos_list == null ? null : (rpos_list.isa.method_msgSend["addObject:"] || _objj_forward)(rpos_list, "addObject:", rpos_object[property]));
        }
    }
    var rpos = Math.min.apply(null, rpos_list);
    for (var i = 0; i < self.ports.length; i++)
    {
        var port = self.ports[i];
        if ((port == null ? null : (port.isa.method_msgSend["valueForKey:"] || _objj_forward)(port, "valueForKey:", "id")) === portID)
        {
            (port == null ? null : (port.isa.method_msgSend["setValue:forKey:"] || _objj_forward)(port, "setValue:forKey:", wpos - rpos, "tokenCount"));
            break;
        }
    }
    (self.isa.method_msgSend["didChangeValueForKey:"] || _objj_forward)(self, "didChangeValueForKey:", "ports");
}

,["void","CPString","JSObject"]), new objj_method(sel_getUid("migrate:"), function $CSGRuntimeInspector__migrate_(self, _cmd, sender)
{
    var selection = ((___r1 = (sender == null ? null : (sender.isa.method_msgSend["selectedItem"] || _objj_forward)(sender, "selectedItem"))), ___r1 == null ? null : (___r1.isa.method_msgSend["title"] || _objj_forward)(___r1, "title"));
    var rtID = ((___r1 = self.runtimeDict), ___r1 == null ? null : (___r1.isa.method_msgSend["valueForKey:"] || _objj_forward)(___r1, "valueForKey:", selection));
    ((___r1 = self.backend), ___r1 == null ? null : (___r1.isa.method_msgSend["migrateActor:toNode:"] || _objj_forward)(___r1, "migrateActor:toNode:", self.component, rtID));
    var ___r1;
}

,["void","id"])]);
}
p;26;CSGCapabilitiesInspector.jt;6031;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.ji;12;CSGBackend.jt;5947;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);objj_executeFile("CSGBackend.j", YES);
{var the_class = objj_allocateClassPair(CPViewController, "CSGCapabilitiesInspector"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("rtSelect", "CPPopUpButton"), new objj_ivar("runtimeNames", "CPMutableArray"), new objj_ivar("capabilities", "CPMutableArray"), new objj_ivar("url", "CPTextField"), new objj_ivar("runtimeCapabilities", "CPDictionary")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("runtimeNames"), function $CSGCapabilitiesInspector__runtimeNames(self, _cmd)
{
    return self.runtimeNames;
}

,["CPMutableArray"]), new objj_method(sel_getUid("setRuntimeNames:"), function $CSGCapabilitiesInspector__setRuntimeNames_(self, _cmd, newValue)
{
    self.runtimeNames = newValue;
}

,["void","CPMutableArray"]), new objj_method(sel_getUid("capabilities"), function $CSGCapabilitiesInspector__capabilities(self, _cmd)
{
    return self.capabilities;
}

,["CPMutableArray"]), new objj_method(sel_getUid("setCapabilities:"), function $CSGCapabilitiesInspector__setCapabilities_(self, _cmd, newValue)
{
    self.capabilities = newValue;
}

,["void","CPMutableArray"]), new objj_method(sel_getUid("runtimeCapabilities"), function $CSGCapabilitiesInspector__runtimeCapabilities(self, _cmd)
{
    return self.runtimeCapabilities;
}

,["CPDictionary"]), new objj_method(sel_getUid("setRuntimeCapabilities:"), function $CSGCapabilitiesInspector__setRuntimeCapabilities_(self, _cmd, newValue)
{
    self.runtimeCapabilities = newValue;
}

,["void","CPDictionary"]), new objj_method(sel_getUid("init"), function $CSGCapabilitiesInspector__init(self, _cmd)
{
    self = (objj_getClass("CSGCapabilitiesInspector").super_class.method_dtable["initWithCibName:bundle:externalNameTable:"] || _objj_forward)(self, "initWithCibName:bundle:externalNameTable:", "CapabilitiesView", nil, nil);
    if (self)
    {
        self.runtimeNames = [];
        self.url = "";
        self.runtimeCapabilities = (___r1 = (CPDictionary.isa.method_msgSend["alloc"] || _objj_forward)(CPDictionary, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["init"] || _objj_forward)(___r1, "init"));
        self.capabilities = (___r1 = (CPArray.isa.method_msgSend["alloc"] || _objj_forward)(CPArray, "alloc"), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithObjects:count:"] || _objj_forward)(___r1, "initWithObjects:count:", ["loading..."], 1));
    }
    return self;
    var ___r1;
}

,["id"]), new objj_method(sel_getUid("awakeFromCib"), function $CSGCapabilitiesInspector__awakeFromCib(self, _cmd)
{
    (self.isa.method_msgSend["reload"] || _objj_forward)(self, "reload");
}

,["void"]), new objj_method(sel_getUid("reload"), function $CSGCapabilitiesInspector__reload(self, _cmd)
{
    var backend = (CSGBackend.isa.method_msgSend["sharedBackend"] || _objj_forward)(CSGBackend, "sharedBackend");
    (backend == null ? null : (backend.isa.method_msgSend["getRuntimeCapabilitiesResponseBlock:"] || _objj_forward)(backend, "getRuntimeCapabilitiesResponseBlock:",     function(caps)
    {
        (self.isa.method_msgSend["setRuntimeCapabilities:"] || _objj_forward)(self, "setRuntimeCapabilities:", caps);
    }));
}

,["void"]), new objj_method(sel_getUid("updateDetail:"), function $CSGCapabilitiesInspector__updateDetail_(self, _cmd, sender)
{
    var key = ((___r1 = ((___r2 = self.rtSelect), ___r2 == null ? null : (___r2.isa.method_msgSend["selectedItem"] || _objj_forward)(___r2, "selectedItem"))), ___r1 == null ? null : (___r1.isa.method_msgSend["title"] || _objj_forward)(___r1, "title"));
    if (!((___r1 = self.runtimeCapabilities), ___r1 == null ? null : (___r1.isa.method_msgSend["containsKey:"] || _objj_forward)(___r1, "containsKey:", key)))
    {
        setTimeout(        function()
        {
            (self.isa.method_msgSend["updateDetail:"] || _objj_forward)(self, "updateDetail:", self);
        }, 2000);
        return;
    }
    var info = ((___r1 = self.runtimeCapabilities), ___r1 == null ? null : (___r1.isa.method_msgSend["valueForKey:"] || _objj_forward)(___r1, "valueForKey:", key));
    ((___r1 = self.url), ___r1 == null ? null : (___r1.isa.method_msgSend["setStringValue:"] || _objj_forward)(___r1, "setStringValue:", (info == null ? null : (info.isa.method_msgSend["valueForKey:"] || _objj_forward)(info, "valueForKey:", "url"))));
    var capList = (info == null ? null : (info.isa.method_msgSend["valueForKey:"] || _objj_forward)(info, "valueForKey:", "capabilities"));
    if (!capList)
    {
        return;
    }
    capList.forEach(    function(cap, i, list)
    {
        list[i] = cap.replace(/^calvinsys\./, "");
    });
    (self.isa.method_msgSend["setCapabilities:"] || _objj_forward)(self, "setCapabilities:", capList.sort());
    if (self.capabilities.length == 0)
    {
        setTimeout(        function()
        {
            (self.isa.method_msgSend["updateDetail:"] || _objj_forward)(self, "updateDetail:", self);
        }, 2000);
    }
    var ___r1, ___r2;
}

,["void","id"]), new objj_method(sel_getUid("setRuntimeCapabilities:"), function $CSGCapabilitiesInspector__setRuntimeCapabilities_(self, _cmd, dict)
{
    self.runtimeCapabilities = (dict == null ? null : (dict.isa.method_msgSend["copy"] || _objj_forward)(dict, "copy"));
    var names = (dict == null ? null : (dict.isa.method_msgSend["allKeys"] || _objj_forward)(dict, "allKeys"));
    names.sort();
    (self.isa.method_msgSend["setRuntimeNames:"] || _objj_forward)(self, "setRuntimeNames:", names);
    (self.isa.method_msgSend["updateDetail:"] || _objj_forward)(self, "updateDetail:", self);
}

,["void","CPDictionary"]), new objj_method(sel_getUid("refresh:"), function $CSGCapabilitiesInspector__refresh_(self, _cmd, sender)
{
    (self.isa.method_msgSend["reload"] || _objj_forward)(self, "reload");
}

,["void","id"])]);
}
p;15;CSGHelpViewer.jt;1602;@STATIC;1.0;I;23;Foundation/Foundation.jI;15;AppKit/AppKit.jt;1535;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("AppKit/AppKit.j", NO);
{var the_class = objj_allocateClassPair(CPWindowController, "CSGHelpViewer"),
meta_class = the_class.isa;class_addIvars(the_class, [new objj_ivar("webView", "CPWebView"), new objj_ivar("helpURL", "CPURL")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("init"), function $CSGHelpViewer__init(self, _cmd)
{
    self = (objj_getClass("CSGHelpViewer").super_class.method_dtable["initWithWindowCibName:"] || _objj_forward)(self, "initWithWindowCibName:", "HelpViewer");
    if (self)
    {
        self.helpURL = ((___r1 = (CPURL.isa.method_msgSend["alloc"] || _objj_forward)(CPURL, "alloc")), ___r1 == null ? null : (___r1.isa.method_msgSend["initWithString:"] || _objj_forward)(___r1, "initWithString:", "help/help.html"));
    }
    return self;
    var ___r1;
}

,["id"]), new objj_method(sel_getUid("showHelp"), function $CSGHelpViewer__showHelp(self, _cmd)
{
    ((___r1 = (self.isa.method_msgSend["window"] || _objj_forward)(self, "window")), ___r1 == null ? null : (___r1.isa.method_msgSend["orderFront:"] || _objj_forward)(___r1, "orderFront:", self));
    ((___r1 = self.webView), ___r1 == null ? null : (___r1.isa.method_msgSend["setMainFrameURL:"] || _objj_forward)(___r1, "setMainFrameURL:", self.helpURL));
    ((___r1 = self.webView), ___r1 == null ? null : (___r1.isa.method_msgSend["setNeedsDisplay:"] || _objj_forward)(___r1, "setNeedsDisplay:", YES));
    var ___r1;
}

,["void"])]);
}
p;12;CSGConsole.jt;3463;@STATIC;1.0;I;23;Foundation/Foundation.ji;18;CSGEventListener.ji;15;CSGHostConfig.jt;3373;objj_executeFile("Foundation/Foundation.j", NO);objj_executeFile("CSGEventListener.j", YES);objj_executeFile("CSGHostConfig.j", YES);
{var the_class = objj_allocateClassPair(CPObject, "CSGConsole"),
meta_class = the_class.isa;
var aProtocol = objj_getProtocol("CSGEventListening");
if (!aProtocol) throw new SyntaxError("*** Could not find definition for protocol \"CSGEventListening\"");
class_addProtocol(the_class, aProtocol);class_addIvars(the_class, [new objj_ivar("consoleBase", "CPString"), new objj_ivar("maxItems", "int"), new objj_ivar("items", "CPMutableArray"), new objj_ivar("listener", "CSGEventListener")]);objj_registerClassPair(the_class);
class_addMethods(the_class, [new objj_method(sel_getUid("consoleBase"), function $CSGConsole__consoleBase(self, _cmd)
{
    return self.consoleBase;
}

,["CPString"]), new objj_method(sel_getUid("setConsoleBase:"), function $CSGConsole__setConsoleBase_(self, _cmd, newValue)
{
    self.consoleBase = newValue;
}

,["void","CPString"]), new objj_method(sel_getUid("maxItems"), function $CSGConsole__maxItems(self, _cmd)
{
    return self.maxItems;
}

,["int"]), new objj_method(sel_getUid("setMaxItems:"), function $CSGConsole__setMaxItems_(self, _cmd, newValue)
{
    self.maxItems = newValue;
}

,["void","int"]), new objj_method(sel_getUid("items"), function $CSGConsole__items(self, _cmd)
{
    return self.items;
}

,["CPMutableArray"]), new objj_method(sel_getUid("setItems:"), function $CSGConsole__setItems_(self, _cmd, newValue)
{
    self.items = newValue;
}

,["void","CPMutableArray"]), new objj_method(sel_getUid("init"), function $CSGConsole__init(self, _cmd)
{
    self = (objj_getClass("CSGConsole").super_class.method_dtable["init"] || _objj_forward)(self, "init");
    if (self)
    {
        var config = (CSGHostConfig.isa.method_msgSend["sharedHostConfig"] || _objj_forward)(CSGHostConfig, "sharedHostConfig");
        (self == null ? null : (self.isa.method_msgSend["setItems:"] || _objj_forward)(self, "setItems:", []));
        (self == null ? null : (self.isa.method_msgSend["setConsoleBase:"] || _objj_forward)(self, "setConsoleBase:", (CPString.isa.method_msgSend["stringWithFormat:"] || _objj_forward)(CPString, "stringWithFormat:", "http://%@:%d", (config == null ? null : (config.isa.method_msgSend["valueForKey:"] || _objj_forward)(config, "valueForKey:", CSGConsoleHostKey)), (config == null ? null : (config.isa.method_msgSend["valueForKey:"] || _objj_forward)(config, "valueForKey:", CSGConsolePortKey)))));
        self.maxItems = 100;
    }
    return self;
}

,["id"]), new objj_method(sel_getUid("eventWithData:sender:"), function $CSGConsole__eventWithData_sender_(self, _cmd, data, sender)
{
    (self.isa.method_msgSend["willChangeValueForKey:"] || _objj_forward)(self, "willChangeValueForKey:", "items");
    if (self.items.length == self.maxItems)
    {
        self.items.shift();
    }
    self.items.push((JSON.parse(data)).msg);
    (self.isa.method_msgSend["didChangeValueForKey:"] || _objj_forward)(self, "didChangeValueForKey:", "items");
}

,["void","id","CSGEventListener"]), new objj_method(sel_getUid("setMaxItems:"), function $CSGConsole__setMaxItems_(self, _cmd, n)
{
    if (n < self.maxItems)
    {
        (self.isa.method_msgSend["setItems:"] || _objj_forward)(self, "setItems:", self.items.slice(-n));
    }
    self.maxItems = n;
}

,["void","int"])]);
}
