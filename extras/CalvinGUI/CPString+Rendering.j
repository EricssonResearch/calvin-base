@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@implementation CPString (Rendering)

//=============================================================================
// Category on CPString providing -drawAtPoint:withAttributes:
// FIXME: attributes are currently unused
//        cache font information
//=============================================================================
- (void)drawAtPoint:(CSGPoint)point withAttributes:(CPDictionary)attributes
{
    var ctx = [[CPGraphicsContext currentContext] graphicsPort];
    ctx.font = [[CPFont systemFontOfSize:12] cssString];
    ctx.fillText(self, point.x, point.y);
}

- (void)drawInBounds:(CGRect)bounds withAlignment:(CPTextAlignment)align
{
    var x = 0.0;
    var font = [CPFont systemFontOfSize:12];
    if (align !== CPLeftTextAlignment) {
        var w = [self sizeWithFont:font].width;
        if (align === CPCenterTextAlignment) {
            x = (bounds.size.width - w)/2.0;
        } else { // CPRightTextAlignment
            x = bounds.size.width - w;
        }
    }
    [[CPColor blackColor] set]; // FIXME: Remove when debugged
    var p = CPMakePoint(bounds.origin.x + x, bounds.origin.y + [font size]);
    [self drawAtPoint:p withAttributes:{}];
}

@end
