
import os
import subprocess
import shlex
import shutil
import socket
import json
import time

import requests


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
        req = self.sysdef["uri"] + self.ack_path
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
        cmd = "csruntime --host {host} -p {rt2rt_port} -c {port}".format(**self.sysdef)
        opt1 = ' --registry "{registry}"'.format(**self.sysdef) if 'registry' in self.sysdef else ""
        opt2 = ' --name "{name}"'.format(**self.sysdef)
        conf = ' --config-file "{}"'.format(self.runtime_config_file)
        attrs = self._attributes_option()
        debug = ' -l DEBUG'
        return cmd + opt1 + opt2 + conf + attrs # + debug

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
    """Read a system config file (JSON, YAML), set up a system accordingly."""

    def __init__(self, system_config, tmp_dir, start=True):
        super(SystemManager, self).__init__()
        # Prepare a range of port numbers, use maximum number
        # of potentially undefined ports:
        self.port_numbers = _random_ports(2 * len(system_config))
        self._system = []
        self.process_config(system_config, tmp_dir)
        # print "System startup sequence:"
        # print "------------------------"
        # for s in self._system:
        #     print s
        # print "------------------------"
        if not start:
            return
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
        for s in self._system:
            s.wait_for_ack()
            if not s.ack_status:
                print("TIMEOUT for ", s.info())

    def process_config(self, system_config, tmp_dir):
        for entity in system_config:
            self._system.append(self.process_entity(entity, tmp_dir))

    def process_entity(self, entity, tmp_dir):
        self.expand(entity, 'registry')
        self.expand(entity, 'actorstore')
        return factory(entity, self.port_numbers, tmp_dir)

    def expand(self, entity, entry):
        value = entity.get(entry, "")
        if not isinstance(value, str) or not value.startswith('$'):
            return
        info = self.info[value[1:]]
        if 'rt2rt' in info:
            # Runtime acting as proxy for registry/actorstore
            entity[entry] = {'uri': '{}'.format(info['rt2rt']), 'type': 'proxy'}
        else:
            entity[entry] = {'uri': '{}'.format(info['uri']), 'type': info['type']}

    @property
    def info(self):
        """Return a dict with immutable properties from each process wrapper"""
        return {
            item.pop('name'): item
            for item in (s.info() for s in self._system)
        }

    def teardown(self):
        """Tear down the system."""
        for item in reversed(self._system):
            item.stop_process()

