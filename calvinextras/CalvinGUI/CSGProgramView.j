@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@import "CSGComponent.j"
@import "CSGActor.j"
@import "CSGProgram.j"
@import "CSGProgram+Rendering.j"

@implementation CSGProgramView : CPView
{
   CSGProgram program;
   CSGActor dragObject;
   CPString dragPad;
   CSGComponent selection @accessors;

   SEL mouseDraggedAction;
   SEL mouseUpAction;

   CGPoint dragOffset;
   CGPoint trackingStartLocation;
   CGPoint trackingLocation;
}

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

- (void)awakeFromCib
{
    [self registerForDraggedTypes:[CPStringPboardType]];
    mouseDraggedAction = @selector(_nilAction:);
    mouseUpAction = @selector(_nilAction:);
    // [self setScaleSize:CGSizeMake(0.5, 0.5)];
}

- (void)drawRect:(CGRect)dirtyRect
{
    [[CPColor colorWithHexString:CSGEditorViewBgColorHEX] set];
    [CPBezierPath fillRect:[self bounds]];

    [program renderInBounds:[self bounds] dirtyRect:dirtyRect];

    if (dragPad !== nil) {
        // Transient connection line
        var path = [CPBezierPath bezierPath];
        [path moveToPoint:trackingStartLocation];
        [path lineToPoint:trackingLocation];
        [[CPColor colorWithHexString:CSGConnectionPendingColorHEX] set];
        [path stroke];
    }
}

// Observe changes in certain variables to keep different parts synchronized
- (void)observeValueForKeyPath:(CPString)keyPath
                      ofObject:(id)object
                        change:(CPDictionary)change
                       context:(id)context
{
    if (keyPath === @"currentProject") {
        // Program was changed
        [self setSelection:nil];
        var newProject = [change objectForKey:"CPKeyValueChangeNewKey"];
        program = [newProject program];
        [self setNeedsDisplay:YES];
    }
}


- (BOOL)isFlipped
{
    return YES;
}

//
// Helper methods
//

- (void)setSelection:(CSGComponent)comp
{
    if (selection !== nil) {
        [selection setSelected:NO];
    }
    if (comp !== nil) {
        selection = comp;
        [comp setSelected:YES];
        // FIXME: View ordering
        // [program makeFront:new];
    } else {
        selection = nil;
    }
}

//
// Manipulating components
//

// Inform the responder chain that we handle key presses here
- (BOOL)acceptsFirstResponder
{
    return YES;
}

- (void)keyDown:(CPEvent)event
{
    var keyCode = [event keyCode];
    if (keyCode === CPDeleteForwardKeyCode || keyCode === CPDeleteKeyCode) {
        [program removeComponent:selection];
        selection = nil;
        [self setNeedsDisplay:YES];
   }
}

- (void)mouseDown:(CPEvent)event
{
    var dragStart = [self convertPoint:[event locationInWindow] fromView:nil];
    dragObject = [program instanceAtPoint:dragStart];
    [self setSelection:dragObject];
    [self setNeedsDisplay:YES];
    // FIXME: Change cursor
    // [[CPCursor closedHandCursor] push];
    if (dragObject === nil) {
        return;
    }
    dragOffset = CSGSubtractPoints(dragStart, dragObject.bounds.origin)
    dragPad = [dragObject portAtPoint:dragStart];

    // Set actions to perform based on whether user is moving actor or connecting ports
    if (dragPad === nil) {
        mouseDraggedAction = @selector(_updateDragWithEvent:);
        mouseUpAction = @selector(_updateDragWithEvent:);
    } else {
        mouseDraggedAction = @selector(_updateConnectDragWithEvent:);
        mouseUpAction = @selector(_finishConnectDragWithEvent:);
    }

    // If dragPad is an inport AND there is already a connection,
    // simulate "in drag" from other end to change or drop connection
    var existingConn = nil;
    if (dragPad !== nil && [dragPad isInport]) {
        existingConn = [program connectionForActor:dragObject inport:dragPad];
    }
    if (existingConn !== nil) {
        dragObject = [existingConn srcActor];
        dragPad = [existingConn srcPort];
        trackingStartLocation = [dragObject anchorPointForPort:dragPad];
        trackingLocation = dragStart;
        [program removeComponent:existingConn];
    } else {
        trackingStartLocation = dragStart;
        trackingLocation = dragStart;
    }
}

- (void)mouseDragged: (CPEvent)event
{
    // FIXME: Constrain to view bounds
    [self autoscroll:event];
    [self performSelector:mouseDraggedAction withObject:event];
    [self setNeedsDisplay:YES];
}

- (void)mouseUp:(CPEvent)event
{
    // FIXME: move actor to head of list
    // FIXME: Change cursor
    // [[CPCursor currentCursor] pop];
    [self performSelector:mouseUpAction withObject:event];
    // Clear the actions
    mouseUpAction = @selector(_nilAction:);
    mouseDraggedAction = @selector(_nilAction:);
    dragObject = nil;
    dragPad = nil;
    [self setNeedsDisplay:YES];
}

- (CGPoint)constrainPoint:(CGPoint)aPoint
{
    var documentBounds = [self bounds];
    aPoint.x = MAX(0.0, MIN(aPoint.x, CGRectGetWidth(documentBounds)));
    aPoint.y = MAX(0.0, MIN(aPoint.y, CGRectGetHeight(documentBounds)));

    return aPoint;
}

// - (CGPoint)constrainPoint:(CGPoint)aPoint usingItemBounds:(CGRect)itemBounds
// {
//     var documentBounds = [self bounds];
//     aPoint.x = MAX(0.0, MIN(aPoint.x, MAX(CGRectGetWidth(documentBounds) - CGRectGetWidth(itemBounds), 0.0)));
//     aPoint.y = MAX(0.0, MIN(aPoint.y, MAX(CGRectGetHeight(documentBounds) - CGRectGetHeight(itemBounds), 0.0)));
//     return aPoint;
// }

- (void)_nilAction:(id)object
{
    return;
}

- (void)_updateDragWithEvent:(CPEvent)event
{
    var loc = [self convertPoint:[event locationInWindow] fromView: nil];
    loc = [self constrainPoint:loc];
    dragObject.bounds.origin = CSGAddPoints(loc, dragOffset);
}

- (void)_updateConnectDragWithEvent:(CPEvent)event
{
    var loc = [self convertPoint:[event locationInWindow] fromView: nil];
    trackingLocation = [self constrainPoint:loc];
}

- (void)_finishConnectDragWithEvent:(CPEvent)event
{
    var dropPoint = [self convertPoint:[event locationInWindow] fromView: nil],
        dropObject = [program instanceAtPoint:dropPoint];
    if (dropObject === nil) {
        return;
    }
    var dropPad = [dropObject portAtPoint:dropPoint];
    if (dropPad === nil) {
            return;
    }
    var isValid = [program addConnectionFrom:dragObject fromPort:dragPad to:dropObject toPort:dropPad];
    if (isValid) {
        [self setSelection:dropObject];
    }
}

//
// Component drop
//
- (BOOL)prepareForDragOperation:(CPDraggingInfo)draggingInfo
{
    return YES;
}

- (BOOL)performDragOperation:(CPDraggingInfo)draggingInfo
{
    var pasteboard = [draggingInfo draggingPasteboard];
    // if(![pasteboard availableTypeFromArray:[CPStringPboardType]])
    //     return NO;
    var item = [pasteboard dataForType:CPStringPboardType],
        loc = [self convertPoint:[draggingInfo draggingLocation] fromView: nil],
        actor = [[CSGActor alloc] initWithJSObject:[item objectFromJSON]];
    if (actor !== nil) {
        [program addInstance:actor];
        [actor setOrigin:loc];
        [self setSelection:actor];
    } else {
        console.log("Not adding invalid actor", actor);
    }
    return YES;
}

- (void)concludeDragOperation:(CPDraggingInfo)draggingInfo
{
   [self setNeedsDisplay:YES];
}
@end