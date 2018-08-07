@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@import "CSGPort.j"
@import "CSGTheme.j"

@implementation CSGPort (Rendering)

// Private
- (void)computeSize
{
    var font = [CPFont systemFontOfSize:12];
    var labelSize = [portName sizeWithFont:font];
    portSize = CPMakeSize(labelSize.width + CSGColPadding, CSGRowHeight);
}

- (CGSize)size
{
    if (portSize.width == 0) {
        [self computeSize];
    }
    return portSize;
}

- (void)renderPadInBounds:(CGRect)bounds
{
    var pad = [CPBezierPath bezierPath],
        h = CSGPadScale * CSGRowHeight,
        w = CSGPadScale * CSGColPadding,
        x = bounds.origin.x + (isInport ? 0.0 : bounds.size.width - w),
        y = bounds.origin.y + (CSGRowHeight - h)/2.0 + CSGPadYOffset;
    [pad moveToPoint:CPMakePoint(x,y)];
    [pad lineToPoint:CPMakePoint(x, y + h)];
    [pad lineToPoint:CPMakePoint(x + w, y + h/2.0)];
    [pad closePath];
    [[CPColor colorWithHexString:CSGActorPortColorHEX] set];
    [pad fill];
}

- (void)renderInBounds:(CGRect)bounds
{
  [self renderPadInBounds:bounds];
  var insetBounds = CGRectInset(bounds, CSGColPadding, 0);
  [portName drawInBounds:insetBounds withAlignment:isInport?CPLeftTextAlignment:CPRightTextAlignment]
}
@end
