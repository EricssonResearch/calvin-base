

function CSGSubtractPoints(p0, p1) {
    return CPMakePoint(p1.x-p0.x, p1.y-p0.y);
}

function CSGAddPoints(p0, p1) {
    return CPMakePoint(p1.x+p0.x, p1.y+p0.y);
}
