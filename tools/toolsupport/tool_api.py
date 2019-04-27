from calvin.common import metadata_proxy as mdproxy
from calvin.common.docgen import DocumentationStore         
from calvinservices.csparser import parser, codegen, dscodegen, visitor, astnode
from . import visualize2 as visualize


class ToolSupport(object):
    """docstring for ToolSupport"""
    def __init__(self, actorstore_uri):
        super(ToolSupport, self).__init__()
        self.store = mdproxy.ActorMetadataProxy(actorstore_uri)

    #
    # Script parsing
    #
    def _calvin_cg(self, source_text, app_name):
        ast_root, issuetracker = parser.calvin_parse(source_text)
        cg = codegen.CodeGen(ast_root, app_name, self.store)
        return cg, issuetracker

    def calvin_codegen(self, source_text, app_name='script'):
        """
        Generate application code from script, return deployable and issuetracker.

        Parameter app_name is required to provide a namespace for the application.
        """
        cg, issuetracker = self._calvin_cg(source_text, app_name)
        cg.generate_code(issuetracker)
        return cg.app_info, issuetracker

    def calvin_dscodegen(self, source_text, app_name='script'):
        """
        Generate deployment info from script, return deploy_info and issuetracker.

        Parameter app_name is required to provide a namespace for the application.
        """
        ast_root, issuetracker = parser.calvin_parse(source_text)
        cg = dscodegen.DSCodeGen(ast_root, app_name)
        cg.generate_code(issuetracker)
        return cg.deploy_info, issuetracker

    def calvin_astgen(self, source_text, app_name='script'):
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
        Optional parameter names is a list of components to extract, if not present (or None)
        return all components found in script.
        """
        cg, issuetracker = self._calvin_cg(source_text, '')
        cg.phase1(issuetracker)

        if issuetracker.error_count:
            return [], issuetracker

        # FIXME: Speed up by getting query once and then filter result if names given
        if names:
            comps = []
            for name in names:
                # NB. query returns a list
                comp = visitor.query(cg.root, kind=astnode.Component, attributes={'name':name}, maxdepth=1)
                if not comp:
                    reason = "Component '{}' not found".format(name)
                    issuetracker.add_error(reason, cg.root)
                else:
                    comps.extend(comp)
        else:
            comps = visitor.query(cg.root, kind=astnode.Component, maxdepth=1)

        return comps, issuetracker

    def compile(self, source_text):
        app_info, issuetracker = self.calvin_codegen(source_text)
        deploy_info, issuetracker2 = self.calvin_dscodegen(source_text)
        issuetracker.merge(issuetracker2)
        deployable = {
            'app_info': app_info,
            'app_info_signature': None,
            'deploy_info': deploy_info
        }
        return (deployable, issuetracker)
        
    def syntax_check(self, source_text):
        _, issuetracker = self.compile(source_text)
        return issuetracker
        
    #
    # Script visualization
    #  
    def visualize_script(self, source_text):
       """Process source_text and return graphviz (dot) source representing application."""
       # Here we need the unprocessed tree ...
       ir, issuetracker = parser.calvin_parse(source_text)
       # ... but expand portlists to simplify rendering
       rw = codegen.PortlistRewrite(issuetracker)
       rw.visit(ir)
       r = visualize.DotRenderer(self.store)
       dot_source = r.render(ir)
       return dot_source, issuetracker

    def visualize_deployment(self, source_text):
        # Here we need the processed tree
        ast_root, issuetracker = self.calvin_astgen(source_text, 'visualizer')
        r = visualize.DotRenderer(self.store)
        dot_source = r.render(ast_root)
        return dot_source, issuetracker

    def visualize_component(self, source_text, name):
        comp_defs, issuetracker = self.calvin_components(source_text, names=[name])
        print(comp_defs)
        r = visualize.DotRenderer(self.store)
        dot_source = r.render(comp_defs[0])
        return dot_source, issuetracker
   
    #
    # Help
    #
    def help_for_actor(self, actor):
        pass
        # store = DocumentationStore(args.actorstore_uri)
        # if args.format == 'raw':
        #     print(store.help_raw(args.what))
        # else:
        #     compact = bool(args.format == 'compact')
        #     print(store.help(args.what, compact=compact, formatting=args.prettyprinter))

    
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
    
    
        