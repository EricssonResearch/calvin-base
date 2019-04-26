# from tools.toolsupport import visualize
from calvin.common import metadata_proxy as mdproxy
from calvin.common.docgen import DocumentationStore         
from calvinservices.csparser.parser import calvin_parse
from calvinservices.csparser.codegen import CodeGen
from calvinservices.csparser.dscodegen import DSCodeGen

class ToolSupport(object):
    """docstring for ToolSupport"""
    def __init__(self, actorstore_uri='local'):
        super(ToolSupport, self).__init__()
        self.store = mdproxy.ActorMetadataProxy(actorstore_uri)


    def _calvin_cg(self, source_text, app_name):
        ast_root, issuetracker = calvin_parse(source_text)
        cg = CodeGen(ast_root, app_name, self.store)
        return cg, issuetracker

    # FIXME: [PP] Change calvin_ to calvinscript_
    def calvin_codegen(self, source_text, app_name):
        """
        Generate application code from script, return deployable and issuetracker.

        Parameter app_name is required to provide a namespace for the application.
        """
        cg, issuetracker = self._calvin_cg(source_text, app_name)
        cg.generate_code(issuetracker)
        return cg.app_info, issuetracker

    def calvin_dscodegen(self, source_text, app_name):
        """
        Generate deployment info from script, return deploy_info and issuetracker.

        Parameter app_name is required to provide a namespace for the application.
        """
        ast_root, issuetracker = calvin_parse(source_text)
        cg = DSCodeGen(ast_root, app_name)
        cg.generate_code(issuetracker)
        return cg.deploy_info, issuetracker


    def calvin_astgen(self, source_text, app_name):
        """
        Generate AST from script, return processed AST and issuetracker.

        Parameter app_name is required to provide a namespace for the application.
        """
        cg, issuetracker = self._calvin_cg(source_text, app_name)
        cg.phase1(issuetracker)
        cg.phase2(issuetracker)
        return cg.root, issuetracker


    def calvin_components(self, source_text, names=None):
        """
        Generate AST from script, return requested components and issuetracker.

        If there are errors during AST processing, no components will be returned.
        Optional parameter names is a list of components to extract, if present (or None)
        return all components found in script.
        """
        cg, issuetracker = self._calvin_cg(source_text, '')
        cg.phase1(issuetracker)

        if issuetracker.error_count:
            return [], issuetracker

        if names:
            comps = []
            for name in names:
                # NB. query returns a list
                comp = query(cg.root, kind=ast.Component, attributes={'name':name}, maxdepth=1)
                if not comp:
                    reason = "Component '{}' not found".format(name)
                    issuetracker.add_error(reason, cg.root)
                else:
                    comps.extend(comp)
        else:
            comps = query(cg.root, kind=ast.Component, maxdepth=1)

        return comps, issuetracker


    #
    # Scripting
    #
    def visualize_script(self, script):
        dot, it = visualize.visualize_script(self.store, script)
        return dot, it
    
    def visualize_deployment(self, script):
        dot, it = visualize.visualize_deployment(self.store, script)
        return dot, it
        
    def visualize_component(self, script, component_name):
        dot, it = visualize.visualize_component(self.store, script, component_name)
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
    
    
        