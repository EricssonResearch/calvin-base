import os
import os.path
import importlib
import inspect
import json

class CalvinSysDoc(object):
    def __init__(self):
        data = ""
        for dirpath, dirnames, filenames in os.walk("calvin/runtime/south/calvinsys"):
            for filename in filenames:
                if filename.endswith('.py'):
                    filename = filename[:-3]
                    try:
                        pymodule = importlib.import_module(self.rel_path_to_namespace(os.path.join(dirpath, filename)))
                        if pymodule is not None:
                            pyclass = getattr(pymodule, filename)
                            if not pyclass:
                                continue
                            if hasattr(pyclass, 'init_schema'):
                                data += "### " + pyclass.__doc__.lstrip() + "\n"
                                data += "### init(args)\n#### args:\n```\n" + json.dumps(pyclass.init_schema, indent=4, separators=(',', ': ')) + "```\n\n"
                            if hasattr(pyclass, 'can_read_schema'):
                                data += "### can_read()\n#### Returns:\n```\n" + json.dumps(pyclass.can_read_schema, indent=4, separators=(',', ': ')) + "```\n\n"
                            if hasattr(pyclass, 'read_schema'):
                                data += "### read()\n#### Returns:\n```\n" + json.dumps(pyclass.read_schema, indent=4, separators=(',', ': ')) + "```\n\n"
                            if hasattr(pyclass, 'can_write_schema'):
                                data += "### can_write()\n#### Returns:\n```\n" + json.dumps(pyclass.can_write_schema, indent=4, separators=(',', ': ')) + "```\n\n"
                            if hasattr(pyclass, 'write_schema'):
                                data += "### write(args)\n#### args:\n```\n" + json.dumps(pyclass.write_schema, indent=4, separators=(',', ': ')) + "```\n\n"
                    except Exception:
                        pass
        print data

    def rel_path_to_namespace(self, rel_path):
        return '.'.join([x for x in rel_path.split('/')]).strip('.')


if __name__ == '__main__':
    obj = CalvinSysDoc()
