@import <Foundation/Foundation.j>

@implementation CSGPort : CPObject <CPCoding>
{
    CPString portName @accessors(getter=name);
    BOOL isInport @accessors(getter=isInport);
    CGSize portSize;
}

+ (id)inportWithName:(CPString)name
{
    return [[self alloc] initWithName:name isInport:YES];
}

+ (id)outportWithName:(CPString)name
{
    return [[self alloc] initWithName:name isInport:NO];
}

- (id)initWithName:(CPString)name isInport:(BOOL)flag
{
  if(self = [super init])
  {
      portName = name;
      isInport = flag;
      portSize = CGSizeMakeZero();
  }
  return self;
}

//
// Implement CPCoding protocol for serialization
//
- (id)initWithCoder:(CPCoder)coder
{
    self = [super init];
    if (self) {
        portName = [coder decodeObjectForKey:@"portName"];
        isInport = [coder decodeBoolForKey:@"isInport"];
        portSize = CGSizeMakeZero();
    }
    return self;
}

- (void)encodeWithCoder:(CPCoder)coder
{
    [coder encodeObject:portName forKey:@"portName"];
    [coder encodeBool:isInport forKey:@"isInport"];
}

@end