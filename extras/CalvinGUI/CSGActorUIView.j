/*
 *  CSGActorUIView.j
 *  EACalvin
 *
 *  Created by Per Persson on 2017-05-17.
 *  Copyright Ericsson AB 2017. All rights reserved.
*/

@import <Foundation/Foundation.j>
@import <AppKit/AppKit.j>
@import "CSGTheme.j"


@implementation CPTextView (CPAttributedStringAdditions)

- (void)appendText:(CPAttributedString)aString
{
    var isAttributed = [aString isKindOfClass:CPAttributedString],
        string = isAttributed ? [aString string]:aString;

    [self willChangeValueForKey:@"objectValue"];
    [_textStorage replaceCharactersInRange:CPMakeRangeCopy(_selectionRange) withAttributedString:aString];
    [self didChangeValueForKey:@"objectValue"];
    [self _continuouslyReverseSetBinding];

    var selectionRange = CPMakeRange([[self string] length], 0);
    [self _setSelectedRange:selectionRange affinity:0 stillSelecting:NO overwriteTypingAttributes:NO];
    _startTrackingLocation = _selectionRange.location;

    [self didChangeText];
    [_layoutManager _validateLayoutAndGlyphs];
    [self sizeToFit];
    [self scrollRangeToVisible:_selectionRange];
    _stickyXLocation = MAX(0, _caret._rect.origin.x - 1);
}

@end


@implementation CSGButton : CPButton
{
    SEL mouseDownAction @accessors;
}

- (void)mouseDown:(CPEvent)anEvent
{
    if ([self mouseDownAction]) {
        [CPApp sendAction:[self mouseDownAction] to:[self target] from:self];
    }
    [super mouseDown:anEvent];
}
@end



@implementation CSGBuzzer : CPTextField
{
    JSObject sound @accessors;
}

- (id)initWithFrame:(CGRect)aFrame
{
    self = [super initWithFrame:aFrame];
    if (self) {
        sound = new webkitAudioContext();
        var oscillator = sound.createOscillator();
        console.log(sound, oscillator);
        oscillator.type = 'square';
        oscillator.frequency.value = 440;
        oscillator.connect(sound.destination);
        oscillator.start();
        if (sound) {
            sound.suspend()
        }
    }
    return self;
}


- (void)setObjectValue:(id)obj
{
    console.log();
    var volume = obj || 0;
    if (volume === 0) {
        if (sound) {
            sound.suspend()
        }
    } else {
        if (sound) {
            sound.resume()
        }
    }
    [super setObjectValue:obj];
}

@end

@implementation CSGActorUIView : CPView
{
    CSGActor actor @accessors();

    CPImageView imageView;
    CPImage defaultImage;
    CPImage alternateImage;

    CGPoint dragLocation;
    JSObject layout;
    CPDictionary _console_attrs;
}

+ (JSObject)layout:(JSObject)config
{
    var layout = {};
    switch (config.control.type) {
    case "console":
        layout.title_frame = CGRectMake(0, 0, CSGUIConsoleWidth, CSGRowHeight);
        layout.name_frame = CGRectInset(CGRectCreateCopy(layout.title_frame), CSGUIElementInset, CSGUIElementInset);
        layout.image_frame = CGRectMakeZero();
        layout.control_frame = CGRectMake(0, CSGRowHeight, CSGUIConsoleWidth, CSGUIConsoleHeight);
        layout.control_frame = CGRectInset(layout.control_frame, CSGUIElementInset, CSGUIElementInset);
        layout.frame = CGRectMake(0, 0, CSGUIConsoleWidth, CSGRowHeight + CSGUIConsoleHeight);
        break;
    default:
        layout.title_frame = CGRectMake(0, 0, CSGUIDeviceWidth, CSGRowHeight);
        layout.name_frame = CGRectInset(CGRectCreateCopy(layout.title_frame), CSGUIElementInset, CSGUIElementInset);
        layout.image_frame = CGRectMake((CSGUIDeviceWidth - CSGUIDeviceImageWidth)/2.0, CSGRowHeight + CSGUIDevicePadding, CSGUIDeviceImageWidth, CSGUIDeviceImageHeight);
        layout.control_frame = CGRectMake(0, CSGRowHeight + CSGUIDevicePadding*2.0 + CSGUIDeviceImageHeight, CSGUIDeviceWidth, CSGRowHeight);
        layout.control_frame = CGRectInset(layout.control_frame, CSGUIDevicePadding, 0);
        layout.frame = CGRectMake(0, 0, CSGUIDeviceWidth, CSGRowHeight*2.0 + CSGUIDevicePadding*3.0 + CSGUIDeviceImageHeight);
        break;
    }
    return layout;
}

- (id)initWithActor:(CSGActor)anActor config:(JSObject)config origin:(CGPoint)origin
{
    self = [super initWithFrame:CGRectMakeZero()];
    if (self) {
        actor = anActor;
        _console_attrs = @{
            CPForegroundColorAttributeName:[CPColor colorWithHexString:CSGUIConsoleTextColorHEX],
            CPFontAttributeName:[CPFont fontWithName:CSGUIConsoleFontName size:CSGUIConsoleFontSize]
        };
        self.layout = [CSGActorUIView layout:config];
        [self setFrameSize:self.layout.frame.size];
        [self setFrameOrigin:origin];
        [self setup:config];
    }
    return self;
}


- (void)setup:(JSObject)config
{
    var label = [[CPTextField alloc] initWithFrame:self.layout.name_frame];
    [label setEditable:NO];
    [label setAlignment:CPCenterTextAlignment];
    // Bind the label value to the actual name since it can be changed by user.
    [label bind:CPValueBinding toObject:actor withKeyPath:"name" options:nil];
    [self addSubview:label];

    [self _loadImages:config];
    imageView = [[CPImageView alloc] initWithFrame:self.layout.image_frame];
    [imageView setImageScaling:CPImageScaleProportionallyDown];
    [imageView setImage:defaultImage];
    [self addSubview:imageView];

    var control = [self _physicalControl:config.control];
    [self addSubview:control];
}

- (void)_loadImages:(JSObject)config
{
    var imageName = "Resources/" + config.image + ".png";
    defaultImage = [[CPImage alloc] initWithContentsOfFile:imageName];
    imageName = "Resources/" + config.image + "_alt.png";
    alternateImage = [[CPImage alloc] initByReferencingFile:imageName size:CGSizeMake(-1, -1)];
    [alternateImage setDelegate:self];
    [alternateImage load]; // Force loading
}


// CPImage delegate method
- (void)imageDidError:(CPImage)image
{
    if (image == alternateImage) {
        alternateImage = nil;
    }
}


- (id)_physicalControl:(JSObject)cConfig
{
    var control = nil;
    if (cConfig.sensor) {
        control = [self _physicalSensor:cConfig];
    } else {
        control = [self _physicalActuator:cConfig];
    }
    return control;
}

- (id)_physicalSensor:(JSObject)cConfig
{
    var control;
        if (cConfig.type === "boolean") {
        control = [[CSGButton alloc] initWithFrame:layout.control_frame];
        [control setTarget:nil];
        if (cConfig.behaviour === "momentary") {
            // Momentary: CPMomentaryPushInButton, CPMomentaryPushButton, CPMomentaryLight, CPMomentaryChangeButton
            [control setButtonType:CPMomentaryPushInButton];
            [control setState:cConfig['default']?0:1];
            [control setMouseDownAction:@selector(uiSetAction:)];
            [control setAction:@selector(uiResetAction:)];
        } else {
            // Topggling: CPPushOnPushOffButton, CPOnOffButton, CPToggleButton
            [control setButtonType:CPPushOnPushOffButton];
            [control setState:cConfig['default']?1:0];
            [control setAction:@selector(uiAction:)];
        }
    } else {
        control = [[CPSlider alloc] initWithFrame:layout.control_frame];
        [control setTarget:nil];
        [control setAction:@selector(uiAction:)];

        [control setMaxValue:cConfig.max];
        [control setMinValue:cConfig.min];
        [control setContinuous:NO];
        [control setObjectValue:cConfig['default']];
    }

    return control;
}

- (id)_physicalActuator:(JSObject)cConfig
{
    var control;
    if (cConfig.type == "console") {
        var scrollview = [[CPScrollView alloc] initWithFrame:layout.control_frame];
        [scrollview setHasVerticalScroller:YES];
        [scrollview setHasHorizontalScroller:NO];
        [scrollview setAutohidesScrollers:YES];
        [scrollview setAutoresizingMask:CPViewWidthSizable | CPViewHeightSizable];

        control = [[CPTextView alloc] initWithFrame:[scrollview bounds]];
        [control setAutoresizingMask:CPViewWidthSizable | CPViewHeightSizable];
        [control setEditable:NO];
        [control setBackgroundColor:[CPColor colorWithHexString:CSGUIConsoleBgColorHEX]];

        [scrollview setDocumentView:control];

        [actor addObserver:self forKeyPath:"uiState" options:CPKeyValueChangeSetting context:scrollview]; // FIXME: Pass scrollview?
        [actor setUiState:""];

        // return the scrollview
        control = scrollview;
    } else if (cConfig.behaviour === "audio") {
        control = [[CSGBuzzer alloc] initWithFrame:layout.control_frame];
        [control setEditable:NO];
        [control setAlignment:CPCenterTextAlignment];
        [control bind:CPValueBinding toObject:actor withKeyPath:"uiState" options:nil];
        [actor setUiState:cConfig['default'] || 0];
    } else {
        control = [[CPTextField alloc] initWithFrame:layout.control_frame];
        [control setEditable:NO];
        [control setAlignment:CPCenterTextAlignment];
        [control bind:CPValueBinding toObject:actor withKeyPath:"uiState" options:nil];
        if (cConfig.type === "boolean" || cConfig.type === "int") {
            [actor addObserver:self forKeyPath:"uiState" options:CPKeyValueChangeSetting context:nil];
        }
        [actor setUiState:cConfig['default'] || 0];
    }
    return control;
}


- (void)observeValueForKeyPath:(CPString)keyPath
                      ofObject:(id)object
                        change:(CPDictionary)change
                       context:(id)context
{
    if (context) {
        var text = [[CPAttributedString alloc] initWithString:""+object.uiState attributes:_console_attrs];
        [[context documentView] appendText:text];
        return;
    }
    if (alternateImage === nil) {
        return;
    }
    [imageView setImage:[object.uiState boolValue]?alternateImage:defaultImage];
}

- (void)updateVisibility:(CPArray)actorsOnRuntime
{
    var hidden = YES;
    if (actorsOnRuntime) {
        for (var i=0; i<actorsOnRuntime.length; i++) {
            if (actor.identifier === actorsOnRuntime[i]) {
                hidden = NO;
                break;
            }
        }
    }
    [self setHidden:hidden];
}

//
// Standard view methods
//
- (void)mouseDown:(CPEvent)anEvent
{
    dragLocation = [anEvent locationInWindow];
}

- (void)mouseDragged:(CPEvent)anEvent
{
    var location = [anEvent locationInWindow],
        origin = [self frame].origin;
    // Sometimes mouseDragged is called before mouseDown?
    if (dragLocation == nil) {
        dragLocation = location;
    }
    [self setFrameOrigin:CGPointMake(origin.x + location.x - dragLocation.x, origin.y + location.y - dragLocation.y)];
    dragLocation = location;
}

- (void)mouseUp:(CPEvent)anEvent
{
    var aPoint = [anEvent locationInWindow].origin;
    [self setFrameOrigin:aPoint];
}

- (void)drawRect:(CPRect)aRect {
    [[CPColor colorWithHexString:CSGEditorViewBgColorHEX] set];
    [CPBezierPath fillRect:[self bounds]];
    [[CPColor colorWithHexString:CSGActorNameBgColorHEX] set];
    [CPBezierPath fillRect:self.layout.title_frame];
    if ([actor isSelected]) {
        [[CPColor colorWithHexString:CSGEditorHighlightColorHEX] set];
    } else {
        [[CPColor colorWithHexString:CSGComponentActorFrameColorHEX] set];
    }
    [CPBezierPath strokeRect:[self bounds]];

    // [[CPColor colorWithHexString:"FF0000"] set];
    // [CPBezierPath strokeRect:self.layout.title_frame];
    // [CPBezierPath strokeRect:self.layout.name_frame];
    // [CPBezierPath strokeRect:self.layout.image_frame];
    // [CPBezierPath strokeRect:self.layout.control_frame];
    // [CPBezierPath strokeRect:self.layout.frame];
}

@end

