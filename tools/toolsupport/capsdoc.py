#
# Generate calvinsys and calvinlib documentation 
#
import os
import json
import importlib
import inspect # import cleandoc, getargs

from calvin.common import calvinconfig
_conf = calvinconfig.get()


class CapsDoc(object):
    """Base class for CalvinSysDoc and CalvinLibDoc"""
    
    def __init__(self):
        super(CapsDoc, self).__init__()
        basepath = os.path.dirname(os.path.realpath(__file__))
        self.basepath = os.path.abspath(os.path.join(basepath, '../..')) 
        self.mapping = None
        self.data = None
    
    def rel_path_to_namespace(self, rel_path):
        rel_path = rel_path[len(self.basepath):]
        return '.'.join([x for x in rel_path.split('/')]).strip('.')
    
    def all_modules(self, pathlist, excludelist):
        for path in pathlist:
            libroot = os.path.join(self.basepath, path)  
            for dirpath, dirnames, filenames in os.walk(libroot):
                for filename in filenames:
                    if not filename.endswith('.py'):
                        continue
                    if filename in excludelist:
                        continue              
                    filename, _ = os.path.splitext(filename)
                    modpath = self.rel_path_to_namespace(os.path.join(dirpath, filename))
                    yield (modpath, filename)
        
    
    def parse_modules(self, pathlist, excludelist=None):
        objects = {}
        excludelist = ['__init__.py'] + (excludelist or [])
        for modpath, filename in self.all_modules(pathlist, excludelist):
            try:
                pymodule = importlib.import_module(modpath)
                if pymodule is not None:
                    pyclass = getattr(pymodule, filename)
                    if not pyclass:
                        continue
                    doc_obj = self.parse_class(pyclass)
                    key = self.transform_key(modpath)
                    objects[key] = doc_obj     
            except Exception as e:
                # print("Error: {}".format(e))
                pass
                    
        return objects
        
    def parse_class(self, pyclass):
        doc_obj = {
            'documentation': inspect.cleandoc(pyclass.__doc__).split('\n'),
        }
        for attr in dir(pyclass):
            if not attr.endswith('_schema'):
                continue
            raw_schema = getattr(pyclass, attr)
            doc_obj[attr[:-len("_schema")]] = {
                'documentation': inspect.cleandoc(raw_schema.get('description', "Undocumented")).split('\n'),
                'args': {k:v['type'] for k, v in raw_schema.get('properties', {}).items()}
            }
        return doc_obj

    def get_metadata(self, what):
        if not what:
            md = self.get_root_metadata()
        elif what in self.definitions:
            md = self.get_leaf_metadata(what)
        else:
            md = self.get_partial_metadata(what)
        print("metadata", json.dumps(md, indent=4))    
        if md is not None:
            return md
        # Error condition

    def get_root_metadata(self):
        modules = sorted(set([m.split('.')[0] for m in self.definitions.keys()]))
        return self._module_data(self.rootname, modules)

    def get_partial_metadata(self, what):
        # Find all paths that match what.xxx.yyy.zzz; filter out xxx
        modules = sorted(set([m[len(what)+1:].split('.', 1)[0] for m in self.definitions.keys() if m.startswith(what+'.')]))
        if not modules:
            return None # No match
        return self._module_data(what, modules)
        
    def _module_data(self, what, modules):
        return {
            'type': 'module', 
            'name': what,
            'items': [{'name':k, 'documentation':['Submodule']} for k in modules],
            'documentation': ['Submodules of {}'.format(what)], 
        }
                    
    def transform_key(self, modpath):
        raise Exception("Subclass must override transform_key")
    
    def get_leaf_metadata(self, what):
        raise Exception("Must be implemented by subclass")
        
        
        
        
        
class CalvinSysDriverDoc(CapsDoc):
    """docstring for CalvinSysDoc"""
    
    def __init__(self):
        super(CalvinSysDriverDoc, self).__init__()
        calvinsys_paths = _conf.get(None, 'calvinsys_paths') or []
        excludelist = ['calvinsys_doc.py', 'base_calvinsys_object.py']
        self.data = self.parse_modules(calvinsys_paths, excludelist)
        # print(json.dumps(self.data, indent=4))

    @property
    def rootname(self):
        return "CalvinSys driver"
    
    @property
    def definitions(self):
        return self.data
    
    def transform_key(self, modpath):
        _, key = modpath.split('.calvinsys.', 1)        
        return key                
                
    def get_leaf_metadata(self, what):
        impl = self.data[what]
        return {
            'type': 'driver', 
            'name': what,
            'attributes': impl['init']['args'],
            'api': impl,
            'documentation': impl['documentation'],
        }
        

class CalvinSysCapsDoc(CalvinSysDriverDoc):
    """docstring for CalvinSysDoc"""
    
    def __init__(self):
        super(CalvinSysCapsDoc, self).__init__()
        self.mapping = _conf.get_section('calvinsys')
        # print(json.dumps(self.mapping, indent=4))

    @property
    def rootname(self):
        return "CalvinSys mapping"

    @property
    def definitions(self):
        return self.mapping

    def get_leaf_metadata(self, what):
        this = self.definitions[what]
        impl = self.data.get(this['module'], {})
        # print(json.dumps(impl, indent=4))
        return {
            'type': 'capability', 
            'name': what,
            'mapping': {
                'name': this['module'],
                'attributes': this['attributes'],
                'api': impl,
            },
            'documentation': [],
        }


        
class CalvinLibImplDoc(CapsDoc):
    def __init__(self):
        super(CalvinLibImplDoc, self).__init__()
        calvinlib_paths = ['calvin/runtime/south/calvinlib']
        excludelist = ['calvinlib_doc.py', 'base_calvinlib_object.py']
        self.data = self.parse_modules(calvinlib_paths, excludelist)
        # print(json.dumps(self.data, indent=4))
        
    @property
    def rootname(self):
        return "CalvinLib implementation"
    
    @property
    def definitions(self):
        return self.data

    def transform_key(self, modpath):
        _, key = modpath.split('.calvinlib.', 1)        
        return key                
            
    def get_leaf_metadata(self, what):
        data = self.data.get(what)
        return {
            'type': 'module', 
            'name': what,
            'items': [{'name':k, 'documentation':v['documentation']} for k, v in data.items() if k is not 'documentation'],
            'documentation': data['documentation'], 
        }

        
class CalvinLibCapsDoc(CalvinLibImplDoc):
    def __init__(self):
        super(CalvinLibCapsDoc, self).__init__()
        self.mapping = _conf.get_section('calvinlib')
        
    @property
    def rootname(self):
        return "CalvinLib mapping"
    
    @property
    def definitions(self):
        return self.mapping

    def get_leaf_metadata(self, what):
        this = self.definitions[what]
        impl = self.data.get(this['module'], {})
        # print(json.dumps(impl, indent=4))
        print(this)
        print(impl)
        return {
            'type': 'libapi', 
            'name': what,
            'mapping': {
                'name': this['module'],
                'attributes': {},
                'api': {k:v['documentation'] for k,v in impl.items() if k not in ['documentation', 'init']},
            },
            'documentation': [],
        }
