from calvin.common import metadata_proxy as mdproxy
from calvinservices.csparser import visualize
from calvin.common.docgen import DocumentationStore         




class ToolSupport(object):
    """docstring for ToolSupport"""
    def __init__(self, actorstore_uri='local'):
        super(ToolSupport, self).__init__()
        self.store = mdproxy.ActorMetadataProxy(actorstore_uri)
    #
    # Scripting
    #
    def visualize_script(self, script):
        dot, it = visualize.visualize_script(self.store.get_metadata, script)
        return dot, it
    
    def visualize_deployment(self, script):
        dot, it = visualize.visualize_deployment(self.store.get_metadata, script)
        return dot, it
        
    def visualize_component(self, script, component_name):
        dot, it = visualize.visualize_component(self.store.get_metadata, script, component_name)
        return dot, it
   
    def help_for_actor(self, actor):
        pass
        # store = DocumentationStore(args.actorstore_uri)
        # if args.format == 'raw':
        #     print(store.help_raw(args.what))
        # else:
        #     compact = bool(args.format == 'compact')
        #     print(store.help(args.what, compact=compact, formatting=args.prettyprinter))

    def syntax_check(self, script):
        pass
    
    def compile(self, script):
        pass
    
    def completion(self, script):
        pass

    #
    # Actor development
    #
    def help_for_calvinsys(self, calvinsys):
        pass
        # store = DocumentationStore(args.actorstore_uri)
        # if args.format == 'raw':
        #     print(store.help_raw(args.what))
        # else:
        #     compact = bool(args.format == 'compact')
        #     print(store.help(args.what, compact=compact, formatting=args.prettyprinter))
    
    def help_for_calvinlib(self, calvinlib):
        pass
        
    def test_actor():
        pass    
        
    #
    # System Management
    #
    def system_setup(self):
        pass
    
    def system_list():
        pass 
    
    def system_teardown():
        pass 

    #
    # App Management
    #        
    def app_deploy(self, system, script):
        pass
        
    def app_list(self, system):
        pass
        
    def app_terminate(self, system, name):
        pass
    
    
        