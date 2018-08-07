@import <Foundation/Foundation.j>
@import "CSGActor.j"

@implementation CSGActorTreeNode : CPObject
{
    CPString data @accessors(readonly);
    CPString path @accessors();
    JSObject info @accessors();
    CPString documentation @accessors();
    BOOL isLeaf @accessors();
    CPMutableArray children;

}

- (id)initWithData:(CPString)string
{
    if (self = [super init]) {
        children = @[];
        data = string;
        path = string;
        documentation = string;
        isLeaf = NO;
    }
    return self;
}

- (CPString)description
{
    return [CPString stringWithFormat:"TreeNode%@(%@)", isLeaf?"Leaf":"", path];
}

- (void)addChild:(CSGActorTreeNode)child
{
    if (data !== "") {
        [child setPath:data + "." + child.data];
    }
    [children addObject:child];
}

- (CSGActorTreeNode)childAtIndex:(int)index
{
    return [children objectAtIndex:index];
}

- (int)count
{
    return [children count];
}

- (void)setInfo:(JSObject)actorInfo
{
    info = actorInfo;
    [self setDocumentation:CSGActorDocsFromJSONRep(actorInfo)];
}

@end

