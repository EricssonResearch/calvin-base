import os
import subprocess
import shlex
import shutil
import socket
import json
import time

import requests

from calvin.common.calvinconfig import CalvinConfig

def _start_process(cmd):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    process = subprocess.Popen(cmd)
    return process


class Process(object):
    """docstring for Process"""

    # Define the (immutable) properties exposed by the process
    info_exports = []
    # Define the path to use in wait_for_ack
    ack_path = ""

    def __init__(self, sysdef, port_numbers, tmp_dir):
        super(Process, self).__init__()
        self.sysdef = sysdef
        self.sysdef.setdefault('host', '127.0.0.1')
        self.sysdef.setdefault('port', port_numbers.pop(0))
        self.sysdef["uri"] = "http://{host}:{port}".format(**self.sysdef)
        self.proc_handle = None
        self.ack_status = False

    def info(self):
        return {k: self.sysdef[k] for k in self.info_exports if k in self.sysdef}

    def cmd(self):
        raise NotImplementedError("Subclass must override.")

    def __repr__(self):
        return self.cmd()

    def start_process(self):
        self.proc_handle = _start_process(self.cmd())

    def stop_process(self):
        if not self.proc_handle: return
        self.proc_handle.kill()
        self.proc_handle.communicate()
        self.proc_handle.wait()

    def ack_ok_action(self, response):
        pass

    def wait_for_ack(self):
        req = self.sysdef["uri"]
        if not req:
            # We don't have a way of talking the system... (e.g. using control proxy)
            # FIXME: Add "ping" on rt2rt port.
            self.ack_status = True
            return
        req = req + self.ack_path
        for i in range(20):
            try:
                r = requests.get(req)
            except requests.exceptions.ConnectionError:
                time.sleep(0.25)
                continue
            if r.status_code == 200:
                self.ack_ok_action(r)
                self.ack_status = True
                return
        self.ack_status = False



class ActorstoreProcess(Process):
    """docstring for ActorstorProcess"""

    info_exports = ["name", "uri", "type"]
    ack_path = "/actors/"

    def cmd(self):
        return "csactorstore --host {host} --port {port}".format(**self.sysdef)


class RegistryProcess(Process):
    """docstring for RegistryProcess"""

    info_exports = ["name", "uri", "type"]
    ack_path = "/dumpstorage"

    def cmd(self):
        return "csregistry --host {host} --port {port}".format(**self.sysdef)


class RuntimeProcess(Process):
    """docstring for RuntimeProcess"""

    # FIXME: Pass actor store config as arguments

    info_exports = ["name", "uri", "rt2rt", "node_id", "actorstore", "registry"]
    ack_path = "/id"

    def __init__(self, sysdef, port_numbers, tmp_dir):
        super(RuntimeProcess, self).__init__(sysdef, port_numbers, tmp_dir)
        self._prepare_rt_config_file(tmp_dir)
        self.sysdef.setdefault('rt2rt_port', port_numbers.pop(0))
        self.sysdef["rt2rt"] = "calvinip://{host}:{rt2rt_port}".format(**self.sysdef)
        if 'control_proxy' in self.sysdef:
            self.sysdef['uri'] = None # self.sysdef['control_proxy']['uri']
        self.sysdef["node_id"] = ""
        

    def _prepare_rt_config_file(self, tmp_dir):
        default_config_file = os.path.join(tmp_dir, 'default.conf')
        runtime_config_file = os.path.join(tmp_dir, '{name}.conf'.format(**self.sysdef))
        self.runtime_config_file = runtime_config_file
        if 'config' not in self.sysdef:
            shutil.copyfile(default_config_file, runtime_config_file)
            return
        print(self.sysdef)
        # load config, patch, and write
        with open(default_config_file, 'r') as fp:
            conf = json.load(fp)
        for key, value in self.sysdef['config'].items():
            conf[key].update(value)
        with open(runtime_config_file, 'w') as fp:
            json.dump(conf, fp)

    def _attributes_option(self):
        attrs = self.sysdef.get("attributes")
        if not attrs:
            return ""
        if isinstance(attrs, str):
            # Assume file reference
            return ' --attr-file {}'.format(attrs)
        # Convert attrs to JSON
        return ' --attr "{}"'.format(attrs)

    def cmd(self):
        # print("sysdef", self.sysdef)
        cmd = 'csruntime --host {host} -p {rt2rt_port}'.format(**self.sysdef)
        ctrl_fmt = ' --control_proxy {control_proxy[uri]}' if 'control_proxy' in self.sysdef else ' -c {port}'
        ctrl = ctrl_fmt.format(**self.sysdef)
        store = ' --actorstore {actorstore[uri]}'.format(**self.sysdef) if 'actorstore' in self.sysdef else ''
        opt1 = ' --registry "{registry}"'.format(**self.sysdef) if 'registry' in self.sysdef else ''
        opt2 = ' --name "{name}"'.format(**self.sysdef)
        conf = ' --config-file "{}"'.format(self.runtime_config_file)
        attrs = self._attributes_option()
        debug = ' -l DEBUG'
        return cmd + ctrl + store + opt1 + opt2 + conf + attrs # + debug

    def ack_ok_action(self, response):
        data = response.json()
        self.sysdef["node_id"] = data['id']


factories = {
    'REGISTRY': RegistryProcess,
    'ACTORSTORE': ActorstoreProcess,
    'RUNTIME': RuntimeProcess
}


def factory(entity, port_numbers, tmp_dir):
    class_ = factories[entity['class']]
    return class_(entity, port_numbers, tmp_dir)


def _random_ports(n):
    """
    Return free port numbers.
    """

    def _free_socket():
        free_socket = socket.socket()
        free_socket.bind(('localhost', 0))
        free_socket.listen(5)
        return free_socket

    sockets = [_free_socket() for i in range(n)]

    ports = [s.getsockname()[1] for s in sockets]
    for s in sockets:
        s.close()
    return ports


class SystemManager(object):
    """
    Given a system_config, set up a system accordingly on the test machine (127.0.0.1).
    
    'system_config' is a data structure, typically defined in a YAML file, that 
    contain entries describing nodes in the system, and their relation.
    
    'tmp_dir' is the working directory to use (optional).
    
    'start' is a boolean indicating wether or not to actully deploy the system (defaults to True) 
    
    'verbose' is a boolean indicating wether or not to print the csruntime commands issued (defaults to True)
    
    
    system_config
    =============
    To refer to the URI of a certain node, it is possible (and recommended) to use the notion
    $<node name>, e.g. $actorstore will equal http://127.0.0.1:4999 if the actor store service
    is named 'actorstore' and is started with default properties.  
    
    Each node must have properties 'class', and 'name':

        - class is one of: REGISTRY, ACTORSTORE, RUNTIME (capitals required)
        - name is any string as log as it doesn't start with '$'
    
    Besides the mandatory properties, the optional properties of each class are listed below:
    
    
    REGISTRY
    --------
    port: Port number to start service on (defaults to random free port)
    type: Currently only REST is available (defaults to REST)
    
    
    ACTORSTORE
    ----------
    port: Port number to start service on (defaults to random free port)
    type: Currently only REST is available (defaults to REST)
    
    
    RUNTIME
    -------
    port: Port for control API (defaults to random free port)
    control_proxy : rt2rt URI of a runtime node acting as control API proxy (defaults to null). N.B. Overrides 'port'  
    rt2rt_port: Port for runtime-to-runtime communication (defaults to random free port)
    actorstore: URI of actorstore to use, typically '$actorstore' (defaults to http://127.0.0.1:4999)
    registry: URI of registry to use, often '$registry', 
              but could also refer to a RUNTIME, e.g. '$rt1', in which case rt1 will act as
              proxy for the registry. Additionally, a full spec can also be given as a dictionary:
              {"uri": <uri>, "type": "REST"}.
              Defaults to  {"uri": null, "type": "local"} from calvin.conf file
    config: A dictionary of config properties to override (relative to the default config)
    attributes: A dictionary of node attributes
    
    
    Example
    -------
    
    The following is an example of a system with an actor store, a registry, and two runtimes.
    The first runtime has reconfigured the log.info calvinsys module to write to stdout, and the
    second runtime has a set of attributes, and is using the first runtime as proxy for the registry.
    
    - class: REGISTRY
      name: registry
      port: 4998
      type: REST
    - class: ACTORSTORE
      name: actorstore
      port: 4999
      type: REST
    - class: RUNTIME
      name: testNode1
      actorstore: $actorstore
      registry: $registry
      config:
        calvinsys:
            log.info:
              attributes:
                level: info
              module:
                term.StandardOut
    - class: RUNTIME
      name: testNode2
      actorstore: $actorstore
      registry: $testNode1
      attributes:
        indexed_public:
          address:
            country: SE
            locality: testCity
            street: testStreet
            streetNumber: 1
          node_name:
            organization: org.testexample    
    """

    def __init__(self, system_config, tmp_dir=None, start=True, verbose=True):
        super(SystemManager, self).__init__()
        # Prepare a range of port numbers, use maximum number
        # of potentially undefined ports:
        self.port_numbers = _random_ports(2 * len(system_config))
        self._system = []
        self.workdir = self.prepare_workdir(tmp_dir)
        self.process_config(system_config)
        if verbose:
            self.print_commands()
        if start:
            self.start()

    def prepare_workdir(self, tmp_dir):
        if tmp_dir == None:
            tmp_dir = tempfile.mkdtemp()
        default_config_path = os.path.join(tmp_dir, 'default.conf') 
        cc = CalvinConfig()
        cc.write_default_config(default_config_path)
        return tmp_dir


    @property
    def info(self):
        """
        Return a dict with (immutable) system properties. 
        
        Use 'name' property as key for lookup of node info.
        
        For each node it contains the properties declared in the corresponding class' 'info_exports' variable.
        For ACTORSTORE and REGISTRY they are 'uri', and 'type'.
        For RUNTIME they are 'uri', 'rt2rt', 'node_id', 'actorstore', and 'registry', where the value of 
        'uri' can be None if it doesn't have a control API.
        """
        return { item.pop('name'): item for item in (s.info() for s in self._system) }
        
    def print_commands(self):
        print("System startup sequence:")
        print("------------------------")
        for s in self._system:
            print(s)
        print("------------------------")
            
    def start(self):
        try:
            self.start_system()
            self.wait_for_system()
        except Exception as err:
            self.teardown()
            self._system = []
            raise err              

    def start_system(self):
        for s in self._system:
            s.start_process()

    def wait_for_system(self):
        """Wait for all of the nodes to be up and running"""
        for s in self._system:
            s.wait_for_ack()
            if not s.ack_status:
                sys_info = s.info()
                raise TimeoutError("TIMEOUT for {}".format(sys_info['name']))

    def process_config(self, system_config):
        for entity in system_config:
            self._system.append(self.process_entity(entity))

    def process_entity(self, entity):
        # Check if entity has property X defined by a $ref. If so, replace it with the expansion of $ref 
        self.expand(entity, 'registry')
        self.expand(entity, 'actorstore')
        self.expand(entity, 'control_proxy')
        # Create in instance of the class representing this entity (RUNTIME, ACTORSTORE, or REGISTRY)
        return factory(entity, self.port_numbers, self.workdir)

    def expand(self, entity, entry):
        value = entity.get(entry, "")
        if not isinstance(value, str) or not value.startswith('$'):
            return
        # Expand the reference    
        ref_name = value[1:]
        info = self.info[ref_name]
        # Only RUNTIME have rt2rt prop
        ref_is_runtime = 'rt2rt' in info
        if ref_is_runtime:
            # Assume runtime is acting as proxy for registry/actorstore, use the rt2rt URI
            entity[entry] = {'uri': '{}'.format(info['rt2rt']), 'type': 'proxy'}
        else:
            # Use normal URI
            entity[entry] = {'uri': '{}'.format(info['uri']), 'type': info['type']}

    def teardown(self):
        """Tear down the system."""
        for item in reversed(self._system):
            item.stop_process()

