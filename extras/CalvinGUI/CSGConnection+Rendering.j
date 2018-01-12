@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@import "CSGConnection.j"
@import "CSGTheme.j"


@implementation CSGConnection (Rendering)

- (void)renderWithDirtyRect:(CGRect)dirtyRect
{
    var srcLocation = [src anchorPointForPort:srcPort],
        dstLocation = [dst anchorPointForPort:dstPort],
        scrCtrlLocation,
        dstCtrlLocation;

    if ((dstLocation.x - srcLocation.x)/2.0 < CSGMinControlDist) {
        // Same row in same component needs extra care
        var dy = (src === dst && (srcLocation.y - dstLocation.y) < 1.0) ? CSGSameActorRowDist : 0.0;
        scrCtrlLocation = CPMakePoint(srcLocation.x + CSGMinControlDist, srcLocation.y - dy);
        dstCtrlLocation = CPMakePoint(dstLocation.x - CSGMinControlDist, dstLocation.y + dy);
    } else {
        scrCtrlLocation = CPMakePoint((srcLocation.x + dstLocation.x)/2, srcLocation.y);
        dstCtrlLocation = CPMakePoint((srcLocation.x + dstLocation.x)/2, dstLocation.y);
    }

    var path = [CPBezierPath bezierPath];
    [path moveToPoint:srcLocation];
    [path curveToPoint:dstLocation controlPoint1:scrCtrlLocation controlPoint2:dstCtrlLocation];
    [[CPColor colorWithHexString:CSGConnectionColorHEX] set];
    [path stroke];
}

@end
