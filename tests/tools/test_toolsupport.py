import pytest

from tools import toolsupport

def test_sanity():
    ts = toolsupport.ToolSupport()
    assert ts

def test_visualize():
    script = """
    component Filter(param) in -> out {
        id : std.Identity()
    
        .in > id.token
        id.token > .out
    }

    src : flow.Init(data=1)
    filt : Filter(param=1)
    snk : io.Print()

    voidport > src.in
    src.out > filt.in
    filt.out > snk.token
    """

    ts = toolsupport.ToolSupport()
    dot, it = ts.visualize_script(script)
    assert it.error_count == 0
    # dot, it = ts.visualize_deployment(script)
    # assert dot == None
    # assert it.error_count == 0
    
    
    
    
    
    # def visualize_deployment(self, script):
    #     dot, it = visualize.visualize_deployment(self.store.get_metadata, script)
    #     return dot, it
    #
    # def visualize_component(self, script, component_name):
    #     dot, it = visualize.visualize_component(self.store.get_metadata, script, component_name)
    #     return dot, it
    
    
    
    
    