@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>

@import "CSGActorUIView.j"

@implementation CSGAppUIView : CPView
{
}

- (void)addActors:(CPArray)actors definitions:(JSObject)defs
{
    var delta = 10;
    for (var i=0; i<actors.length; i++) {
        var actor = actors[i];
        var config = defs[actor.type];
        var origin = CGPointMake(delta, delta);
        delta += 20;
        var new_ui = [[CSGActorUIView alloc] initWithActor:actor config:config origin:origin];
        [self addSubview:new_ui];
    }
    [self setNeedsDisplay:YES];
}

- (void)updateVisibility:(CPArray)actorsOnRuntime
{
    var actorUIViews = [self subviews];
    for (var i=0; i<actorUIViews.length; i++) {
        var actorUIView = actorUIViews[i];
        [actorUIView updateVisibility:actorsOnRuntime];
    }
}

- (void)drawRect:(CGRect)dirtyRect
{
    [[CPColor colorWithHexString:CSGEditorViewBgColorHEX] set];
    // [[CPColor redColor] set];
    [CPBezierPath fillRect:[self bounds]];
}

- (BOOL)isFlipped
{
    return YES;
}

@end
