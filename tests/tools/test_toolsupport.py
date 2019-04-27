import pytest

from tools import toolsupport

script = """
component Filter() in -> out {
    id : std.Identity(dump=false)

    .in > id.token
    id.token > .out
}

src : flow.Init(data=1)
filt : Filter()
snk : io.Print()

voidport > src.in
src.out > filt.in
filt.out > snk.token
"""

ts = toolsupport.ToolSupport('local')

def test_sanity():
    assert ts

def test_visualize():
    # TODO: It's possible to unit test visualization by using the following pattern 
    # dot, it = ts.visualize_script("src : flow.Init(data=1)")
    dot, it = ts.visualize_script(script)
    assert it.error_count == 0
    dot, it = ts.visualize_deployment(script)    
    assert it.error_count == 0
    dot, it = ts.visualize_component(script, 'Filter')    
    print(dot)
    assert it.error_count == 0
    
def test_compile():
    deployable, it = ts.compile(script)
    assert it.error_count == 0
    it = ts.syntax_check(script)
    assert it.error_count == 0


    
    
    
    
    
    