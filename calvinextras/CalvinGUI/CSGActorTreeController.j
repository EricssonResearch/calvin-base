@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@import "CSGBackend.j"
@import "CSGActorTreeNode.j"

/* FIXME:
 * Track selection (for bindings to info view)
 * Support dragging source protocol
 * Support getting item for path (e.g. path = "std.Counter")
 */

@implementation CSGActorTreeController : CPViewController
{
    @outlet CPOutlineView outlineView @accessors();
    @outlet CPProgressIndicator spinner @accessors();
    CSGActorTreeNode selectedItem @accessors();
    CSGBackend backend;
    CSGActorTreeNode root;
    int outstanding;
}

- (id)init
{
    self = [super initWithCibName:"ActorView" bundle:nil externalNameTable:nil];
    if (self) {
        backend = [CSGBackend sharedBackend];
        root = [[CSGActorTreeNode alloc] initWithData:@""];
        outstanding = 0;
    }
    return self;
}

- (void)awakeFromCib
{
    [spinner stopAnimation:self];
    [self reload];
}

- (void)reload
{
    root = [[CSGActorTreeNode alloc] initWithData:@""];
    outstanding = 0;
    [self getDataForNode:root];
}

- (void)_beginUpdate
{
    if (outstanding === 0) {
        [spinner startAnimation:self];
    }
    outstanding += 1;
}

- (void)_completeUpdate
{
    outstanding -= 1;
    if (outstanding === 0) {
        [spinner stopAnimation:self];
        [outlineView reloadData];
    }
}

- (void)_createChildren:(CPArray)children forNode:(CSGActorTreeNode)node isLeaf:(BOOL)leaf
{
    for (var i=0; i<children.length; i++) {
        var newNode = [[CSGActorTreeNode alloc] initWithData:children[i]];
        [newNode setIsLeaf:leaf];
        [node addChild:newNode];
        if ([newNode isLeaf]) {
            [self getDataForNode:newNode];
        }
    }
}

- (void)getDataForNode:(CSGActorTreeNode)node
{
    [self _beginUpdate];
    [backend docFor:node.path responseBlock:function(body) {
        [self updateNode:node withData:body];
    }]
}

- (void)updateNode:(CSGActorTreeNode)node withData:(JSObject)data
{
    if (data.actors === undefined && data.modules === undefined && data.type === undefined) {
        console.log("skipping", data);
        // Catch old-style components
        [self _completeUpdate];
        return;
    }
    [node setInfo:data];
    if (!data.hasOwnProperty('type')) {
        [self _createChildren:data.modules.sort() forNode:node isLeaf:NO];
        [self _createChildren:data.actors.sort() forNode:node isLeaf:YES];
    }
    [self _completeUpdate];
}

//
// Actor outline Data Source methods
//
- (int)outlineView:(CPOutlineView)outlineView numberOfChildrenOfItem:(id)item
{
    if (item === nil) {
        item = root;
    }
    if (item !== root && [item count] === 0) {
        // An expandable item had zero children => load them
        [self getDataForNode:item];
    }
    return [item count];
}

- (BOOL)outlineView:(CPOutlineView)outlineView isItemExpandable:(id)item
{
    return ![item isLeaf];
}

- (id)outlineView:(CPOutlineView)outlineView child:(int)index ofItem:(id)item
{
    if (item === nil) {
        item = root;
    }
    return [item childAtIndex:index];
}

- (id)outlineView:(CPOutlineView)outlineView objectValueForTableColumn:(CPTableColumn)tableColumn byItem:(id)item
{
    return item;
}

//
// Actor outline delegate methods
//
- (BOOL)outlineView:(CPOutlineView)outlineView shouldEditTableColumn:(CPTableColumn)tableColumn item:(id)item
{
    return NO;
}

// Update documentation view when actor selection changes
- (void)outlineViewSelectionDidChange:(CPNotification)notification
{
    var ov = [notification object];
    var si = [ov itemAtRow:[ov selectedRow]];
    [self setSelectedItem:si];
}

//
// Actor outline Drag support
//
- (BOOL)outlineView:(CPOutlineView)outlineView writeItems:(CPArray)items toPasteboard:(CPPasteboard)pboard
{
    var item = items[0];
    // No dragging unless this is an actor (leaf node)
    if (![item isLeaf]) {
        return NO;
    }
    if ([pboard availableTypeFromArray:[CPStringPboardType]] === nil) {
        [pboard declareTypes:[CPStringPboardType] owner:self];
    }
    // [pboard clearContents];
    [pboard setData:[CPString JSONFromObject:item.info] forType:CPStringPboardType];
    return YES;
}

@end