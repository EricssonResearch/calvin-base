@import <Foundation/Foundation.j>

@implementation CSGComponent : CPObject
{
    BOOL _selected @accessors(getter=isSelected, setter=setSelected);
}

-(id)init
{
    self = [super init];
    if (self) {
        _selected = NO;
    }
    return self;
}

@end