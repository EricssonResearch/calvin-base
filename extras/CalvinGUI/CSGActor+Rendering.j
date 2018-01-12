@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@import "CSGActor.j"
@import "CSGTheme.j"
@import "CSGGeometryUtils.j"

@class CSGPort;


@implementation CSGActor (Rendering)

- (void)computeBounds
{
    var font = [CPFont systemFontOfSize:12];
    var width_port = 0.0,
        width_hdr,
        rows = Math.max(inports.length, outports.length) + 2,
        allPorts = inports.concat(outports);

    for (var i=0; i<allPorts.length; i++) {
        width_port = Math.max(width_port, [allPorts[i] size].width);
    }

    width_hdr = Math.max([name sizeWithFont:font].width, [type sizeWithFont:font].width);
    [self setSize:CPMakeSize(Math.max(width_hdr, 2*width_port + CSGColPadding) + 2*CSGColPadding, rows*CSGRowHeight)];
    validBounds = YES;
}

- (GCPoint)anchorPointForPort:(CSGPort)port
{
    var ports = [port isInport] ? inports : outports,
        row = 2;
    for (var i=0; i<ports.length; i++) {
        if (port === ports[i]) {
            break;
        }
        row++;
    }
    var local = CPMakePoint([port isInport] ? 0.0 : [self size].width, row * CSGRowHeight + CSGRowHeight/2.0 + CSGPadYOffset);
    return CSGAddPoints([self origin], local);  // Global position
}

- (void)drawStatusIndicator:(CGRect)rect
{
    // Draw indicator in upper right corner of rect,
    // use CSGRowHeight for sizing.
    var m = CSGRowHeight/8.0, // margin
        s = CSGRowHeight/4.0, // bounding rect side
        x = rect.origin.x,
        y = rect.origin.y,
        w = rect.size.width,
        h = rect.size.height,
        r = CPMakeRect(x+w-s-m, y+m, s, s);


    if ([self hasValidMandatoryArgs]){
        return;
    }
    // var color = [self hasValidMandatoryArgs]?CSGOKColorHEX:CSGErrorColorHEX;
    // [[CPColor colorWithHexString:color] set];
    [[CPColor colorWithHexString:CSGErrorColorHEX] set];
    [[CPBezierPath bezierPathWithOvalInRect:r] fill];
}

- (void)renderInBounds:(CGRect)_bounds dirtyRect:(CGRect)dirtyRect
{
    if (validBounds === NO) {
        [self computeBounds];
    }
    // Render components visually different from primitive actors
    var hexBackColor, hexNameColor, hexTypeColor, hexFrameColor;
    if ([self isComponent]) {
        hexBackColor  = CSGComponentActorBgColorHEX;
        hexNameColor  = CSGComponentActorNameBgColorHEX;
        hexTypeColor  = CSGComponentActorTypeBgColorHEX;
        hexFrameColor = CSGComponentActorFrameColorHEX;
    } else {
        hexBackColor  = CSGActorBgColorHEX;
        hexNameColor  = CSGActorNameBgColorHEX;
        hexTypeColor  = CSGActorTypeBgColorHEX;
        hexFrameColor = CSGActorFrameColorHEX;
    }

    // Layout machinery
    // Can't use normal procedures since transforming the coordinate system isn't supported(?)
    // Must offset all drawing by bounds.origin manually. Sigh.

    // Object background
    [[CPColor colorWithHexString:hexBackColor] set];
    var bgRect = CGRectCreateCopy(bounds);
    [CPBezierPath fillRect:bgRect];

    // Header
    bgRect.size.height = CSGRowHeight;
    [[CPColor colorWithHexString:hexNameColor] set];
    [CPBezierPath fillRect:bgRect];
    [name drawInBounds:bgRect withAlignment:CPCenterTextAlignment];
    // Header status indicator
    [self drawStatusIndicator:bgRect];
    bgRect.origin.y += CSGRowHeight;
    [[CPColor colorWithHexString:hexTypeColor] set];
    [CPBezierPath fillRect:bgRect];
    [type drawInBounds:bgRect withAlignment:CPCenterTextAlignment];

    // Ports
    var row = 2,
        portCount = Math.max(inports.length, outports.length);
    for (var i=0; i<portCount; i++) {
        bgRect.origin.y = bounds.origin.y + (i + row)*CSGRowHeight;
        if (i<inports.length) {
            [inports[i] renderInBounds:bgRect];
        }
        if (i<outports.length) {
            [outports[i] renderInBounds:bgRect];
        }
    }

    // Frame
    var frameColor = [self identifier]?@"00FF00":hexFrameColor; // [self identifier] => running
    if ([self isSelected]) {
        // Selection takes preceedence over running/not running
        frameColor = CSGEditorHighlightColorHEX;
    }
    [[CPColor colorWithHexString:frameColor] set];
    [CPBezierPath strokeRect:bounds];

    // Nodename
    bgRect.origin.y = bounds.origin.y - CSGRowHeight;
    [nodeName?nodeName:"---" drawInBounds:bgRect withAlignment:CPCenterTextAlignment];
}

- (CSGPort)portAtPoint:(GCPoint)point
{
    var pos = CSGSubtractPoints([self origin], point),
        isOutport = YES,
        row = Math.floor(pos.y / CSGRowHeight - 2);
    if (row < 0) {
        return nil;
    }
    if (pos.x >= 0.0 && pos.x <= CSGColPadding) {
        isOutport = NO;
    } else if (pos.x < ([self size].width - CSGColPadding) || pos.x > [self size].width) {
        return nil;
    }
    var ports = isOutport ? outports : inports;
    if (row >= ports.count) {
        return nil;
    }
    return ports[row];
}

@end