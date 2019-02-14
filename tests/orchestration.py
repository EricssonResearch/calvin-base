import subprocess
import shlex
import socket
import time

import yaml
import requests


def _start_process(cmd):
    if isinstance(cmd, basestring):
        cmd = shlex.split(cmd)
    process = subprocess.Popen(cmd)
    return process
        

class Process(object):
    """docstring for Process"""
    
    # Define the (immutable) properties exposed by the process
    info_exports = []
        
    def __init__(self, config):
        super(Process, self).__init__()
        self.config = config
        self.config["uri"] = "http://{host}:{port}".format(**config)
        self.proc_handle = self.start_process()
        self.wait_for_ack()
            
    def info(self):
        return {k:self.config[k] for k in self.info_exports}
    
    def cmd(self):
        raise NotImplementedError("Subclass must override.")
        
    def start_process(self):
        return _start_process(self.cmd())
    
    def stop_process(self):
        if not self.proc_handle: return
        self.proc_handle.kill()
        self.proc_handle.communicate()
        self.proc_handle.wait()  
        
    def wait_for_ack(self):
        return True      
            
            

class ActorstoreProcess(Process):
    """docstring for ActorstorProcess"""
    
    info_exports = ["name", "uri", "type"]
            
    def cmd(self):
        return "csactorstore --host {host} --port {port}".format(**self.config)   
        
        
class RegistryProcess(Process):
    """docstring for RegistryProcess"""
    
    info_exports = ["name", "uri", "type"]
    
    def cmd(self):
        return "csregistry --host {host} --port {port}".format(**self.config)    
        
        
class RuntimeProcess(Process):
    """docstring for RuntimeProcess"""
    
    # FIXME: Pass service config as arguments, not env vars
    # FIXME: Wait for runtime to report node_id
    
    info_exports = ["name", "uri", "rt2rt", "registry", "actorstore", "node_id"]
    
    def __init__(self, config):
        super(RuntimeProcess, self).__init__(config)
        self.config["rt2rt"] = "calvinip://{host}:{rt2rt_port}".format(**config)
        self.config["node_id"] = ""
        
    def cmd(self):
        return "csruntime --host {host} -p {rt2rt_port} -c {port}".format(**self.config)
        
    def wait_for_ack(self):
        req = self.config["uri"]+"/id"
        for i in range(10):
            try:
                r = requests.get(req)
            except requests.exceptions.ConnectionError:
                time.sleep(0.5)    
                continue
            if r.status_code == 200:
                data = r.json()
                self.config["node_id"] = data['id']
                return True
        else:
            return False
              
        
        
        
factories = {
    'REGISTRY': RegistryProcess,
    'ACTORSTORE': ActorstoreProcess,
    'RUNTIME': RuntimeProcess
}

def factory(entity):
    class_ = factories[entity['class']]
    return class_(entity) 

    
def _random_ports(n):
    """
    Return free port number.
    """
    def _free_socket():
        free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        free_socket.bind(('localhost', 0))
        free_socket.listen(5)
        return free_socket
    
    sockets = [_free_socket() for i in range(n)]
      
    ports = [s.getsockname()[1] for s in sockets]
    for s in sockets:
        s.close()
    return ports


class SystemManager(object):
    """Read a system config file (JSON, YAML) and set up a system accordingly."""
    def __init__(self, system_config):
        super(SystemManager, self).__init__()
        self._system = [] #[factory(entity) for entity in system_config]
        self.prepare_port_numbers(system_config)
        self.process_config(system_config)
        self.wait_for_system()
        
    def wait_for_system(self):
        for s in self._system:
            if not s.wait_for_ack():
                print "TIMEOUT for ", s.info()
        
    def prepare_port_numbers(self, system_config):
        # Prepare range of port numbers
        port_count = 0
        for entity in system_config:
            if not 'port' in entity: 
                port_count += 1
            if entity['class'] == 'RUNTIME' and not 'rt2rt_port' in entity:
                port_count += 1
        self.port_numbers = _random_ports(port_count) 

    def process_config(self, system_config):
        for entity in system_config:
            self._system.append(self.process_entity(entity))
    
    def process_entity(self, entity):
        entity.setdefault('host', 'localhost')
        if not 'port' in entity:
            entity['port'] = self.port_numbers.pop(0)
        if entity['class'] == 'RUNTIME':
            if not 'rt2rt_port' in entity:
                entity['rt2rt_port'] = self.port_numbers.pop(0)
            # RUNTIME => expand actorstore and registry
            # Must be previously started => in _system
            self.expand_registry(entity)
            self.expand_actorstore(entity)
        return factory(entity)

    def expand_registry(self, entity):
        reg = entity['registry']
        if not reg.startswith('$'):
            return
        reg_name = reg[1:]
        info = self.info[reg_name]
        if 'rt2rt' in info:
            # Runtime acting as proxy for registry
            entity['registry'] = {'uri': info['rt2rt'], 'type': 'PROXY'}                
        else:
            entity['registry'] = { 'uri': info['uri'], 'type': info['type']}

    def expand_actorstore(self, entity):
        reg = entity['actorstore']
        if not reg.startswith('$'):
            return            
        reg_name = reg[1:]
        info = self.info[reg_name]
        entity['actorstore'] = { 'uri': info['uri'], 'type': info['type']}
        
    @property
    def info(self):
        """Return a dict with immutable properties from each process wrapper"""
        return {item.pop('name'):item for item in (s.info() for s in self._system)}
    
    def teardown(self):
        """Tear down the system."""
        for item in reversed(self._system):
            item.stop_process()
            
        
if __name__ == '__main__':
    from pprint import pprint
    with open('/Users/eperspe/Source/calvin-base/tests/SystemYAML.yaml') as fp:
        system_config = yaml.load(fp)
        
    s = SystemManager(system_config)
    print "STARTED"
    pprint(s.info)
    
    s.teardown()       