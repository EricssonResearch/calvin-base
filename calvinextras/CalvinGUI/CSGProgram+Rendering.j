@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>
@import "CPString+Rendering.j"

@import "CSGProgram.j"
@import "CSGActor+Rendering.j"
@import "CSGPort+Rendering.j"
@import "CSGConnection+Rendering.j"
@import "CSGGeometryUtils.j"
@import "CSGTheme.j"


@implementation CSGProgram (Rendering)

- (void)renderInBounds:(CGRect)bounds dirtyRect:(CGRect)dirtyRect
{
    for (var i=connections.length-1; i>=0; i--) {
        [connections[i] renderWithDirtyRect:dirtyRect];
    }

    for (var i=instances.length-1; i>=0; i--) {
        [instances[i] renderInBounds:bounds dirtyRect:dirtyRect];
    }
}

- (CSGActor)instanceAtPoint:(CGPoint)point
{
    for (var i=0; i<instances.length; i++) {
        var a = instances[i];
        if (CGRectContainsPoint(a.bounds, point)) {
            return a;
        }
    }
    return nil;
}


@end
