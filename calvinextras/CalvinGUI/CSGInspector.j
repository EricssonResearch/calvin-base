@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@import "CSGComponent.j"
@import "CSGActor.j"
@import "CSGConnection.j"
@import "CSGTheme.j"

@implementation CSGInspector : CPViewController
{
    CSGComponent component; // Component to inspect.
    id delegate; // FIXME: Make formal protocol

    // Data source
    CPArray keys;
    CPArray optKeys;
    CPInteger mandatoryCount;
    CPInteger totalCount;
    // Doc text
    CPString docs @accessors();
    // Inspector view items
    @outlet CPTextField panelNameField;
    @outlet CPTextField panelTypeField;
    @outlet CPTableView panelTableView;
}

- (id)initWithDelegate:(id)inspectorDelegate
{
    // self = [super initWithWindowCibName:"InspectorView"];
    self = [super initWithCibName:"InspectorView" bundle:nil externalNameTable:nil];
    if (self) {
        self.delegate = inspectorDelegate;
        [[self view] setHidden:YES];
        docs = "";
    }
    return self;
}

- (void)observeValueForKeyPath:(CPString)keyPath
                      ofObject:(id)object
                        change:(CPDictionary)change
                       context:(id)context
{
    var newSel = [change objectForKey:"CPKeyValueChangeNewKey"];
    [self setComponent:newSel];
}

- (void)setComponent:(CGSComponent)comp
{
    self.component = comp;
    if ([comp isKindOfClass:[CSGActor class]]) {
        // console.log("actor identifier", [comp identifier]);
        [[self view] setHidden:NO];
        [panelNameField setStringValue:comp.name];
        [panelTypeField setStringValue:comp.type];
        [self setDocs:comp.docs];
        // Setup info for data source
        // Sort dictionary keys once
        keys = [[comp.mandatoryArgs allKeys] sortedArrayUsingSelector: @selector(caseInsensitiveCompare:)];
        optKeys = [[comp.optionalArgs allKeys] sortedArrayUsingSelector: @selector(caseInsensitiveCompare:)];
        mandatoryCount = [keys count];
        totalCount = mandatoryCount + [optKeys count];
    } else {
        totalCount = 0;
        [[self view] setHidden:YES];
        [self setDocs:""];
    }
    [panelTableView reloadData];
}

//
// Actions
//
- (@action)updateName:(id)sender
{
    if (component === nil || ![component isKindOfClass:[CSGActor class]]) {
        console.log("ERROR: updateName BAD COMPONENT", component, sender);
        return;
    }
    if ([delegate shouldSetName:[sender stringValue] forActor:component]) {
        [component setName:[sender stringValue]];
        [delegate refreshViewForActor:component];
    } else {
        [sender setStringValue:[component name]];
    }
}

- (void)controlTextDidEndEditing:(CPNotification)aNotification
{
    var row = [panelTableView selectedRow];
    if (row < 0) {
        return;
    }
    var textField = [aNotification object];
    var value = [textField stringValue];
    if (row < mandatoryCount) {
        var key = keys[row];
        [component setMandatoryValue:value forKey:key];
    } else {
        var key = optKeys[row - mandatoryCount];
        [component setOptionalValue:value forKey:key];
    }
    [self _updateTextField:textField atRow:row forKey:key];
    [delegate refreshViewForActor:component];
}

- (void)_updateTextField:(CPTextField)textField atRow:(CPInteger)row forKey:(CPString)key
{
    var bgColors = [panelTableView alternatingRowBackgroundColors];
    var valid = [component.argOK valueForKey:key];
    var bgColor = (valid) ? bgColors[row % 2] : [CPColor colorWithHexString:CSGEditorHighlightErrorColorHEX];
    [textField setBackgroundColor:bgColor];
    [textField setNeedsDisplay:YES];
}
//
// Table data source and delegate methods
//
- (CPInteger)numberOfRowsInTableView:(CPTableView)tv
{
    return totalCount;
}

- (CPView)tableView:(CPTableView)table viewForTableColumn:(CPTableColumn)tableColumn row:(CPInteger)row
{
    var key,
        displayKey,
        value,
        colId = tableColumn._identifier;
    if (row < mandatoryCount) {
        key = keys[row];
        displayKey = key;
        value = [component.mandatoryArgs objectForKey:key];
    } else {
        key = optKeys[row - mandatoryCount];
        value = [component.optionalArgs objectForKey:key];
        // Reformat key for display
        displayKey = [CPString stringWithFormat:"(%@)", key];
    }

    var textField = [table makeViewWithIdentifier:colId owner:self];
    if ([colId isEqualToString:@"args"]) {
        [textField setStringValue:displayKey];
    } else if ([colId isEqualToString:@"vals"]) {
        [textField setStringValue:value];
        [self _updateTextField:textField atRow:row forKey:key];
    } else {
        [textField setStringValue:"ERROR"]; // This should not happen
    }

    return textField;
}

@end