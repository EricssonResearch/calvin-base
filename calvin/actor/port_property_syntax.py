port_property_data = {
    'name': {
        'doc': """Calvin-base supported port properties""",
        'type': 'name',
        'capability_type': "name",
        'value': "runtime.base.1",
        'user-level': False
    },
    'routing': {
        'doc': """Routing decides how tokens are routed out or in of a port.""",
        'user-level': True,
        'type': 'category',
        'capability_type': "category",
        'values': {
            'default': {
                'doc': """The default routing of all tokens to all peers.""",
                'direction': "out"
            },
            'fanout': {
                'doc': """The default routing of all tokens to all peers with specific name.""",
                'direction': "out"
            },
            'round-robin': {
                'doc': """Route each tokens to one peer in a round-robin schedule.""",
                'direction': "out"
            },
            'random': {
                'doc': """Route each tokens to one peer in a random schedule.""",
                'direction': "out"
            },
            'balanced': {
                'doc': """Route each tokens to one peer based on queue length.""",
                'direction': "out"
            },
            'dispatch-ordered': {
                'doc': """
                    Dispatch tokens to multiple peers (TESTING).
                    """,
                'direction': "out",
                'multipeer': True
            },
            'dispatch-mapped': {
                'doc': """
                    Dispatch tokens to multiple peers (TESTING).
                    """,
                'direction': "out",
                'multipeer': True
            },
            'collect-unordered': {
                'doc': """
                    Collect tokens from multiple peers, actions see
                    them individually in without order between peers.
                    """,
                'direction': "in",
                'multipeer': True
            },
            'collect-tagged': {
                'doc': """
                    Collect tokens from multiple peers, actions see
                    them individually as {<tag>: token}. Use property tag on
                    a connected outport otherwise tag defaults to port id.
                    """,
                'direction': "in",
                'multipeer': True
            },
            'collect-all-tagged': {
                'doc': """
                    Collect tokens from multiple peers, actions see
                    them all as one token {<tag1>: <token1>, ... <tagN>: <tokenN>}.
                    Use property tag on a connected outport otherwise tag defaults to port id.
                    """,
                'direction': "in",
                'multipeer': True
            },
            'collect-any-tagged': {
                'doc': """
                    Collect tokens from multiple peers, actions see
                    them as one token {<tag1>: <token1>, ... <tagN>: <tokenN>}. The collected
                    token is available when any of the peers have delivered tokens.
                    Use property tag on a connected outport otherwise tag defaults to port id.
                    """,
                'direction': "in",
                'multipeer': True
            },
        }
    },
    'queue_length': {
        'doc': """Specifies the minimum number of tokens that the queue can hold.""",
        'user-level': True,
        'type': 'scalar',
        'direction': 'inout',
        'capability_type': "ignore"
    },
    'nbr_peers': {
        'doc': """
                Automatically set based on connections in calvinscript. When
                not using calvinscript needs to set it on ports with multiple
                connections at least for inports.
                """,
        'user-level': False,
        'type': 'scalar',
        'direction': 'inout',
        'capability_type': "func",
        'capability_func': lambda n: "one" if n==1 else "many",
        'capability_categories': ["one", "many"]  # This node support these
    },
    'tag': {
        'doc': """Specifies a tag on e.g. an outport that can be retrived with certain inport routing properties.""",
        'user-level': True,
        'type': 'string',
        'direction': 'inout',
        'capability_type': "propertyname"
    },
    'test1': {
        'doc': """
                This is a property used only for tests, needed to pass syntax checking.
                """,
        'user-level': False,
        'type': 'category',
        'values': {
            'dummy': {
                'direction': 'inout'
            },
            'dummy1': {
                'direction': 'inout'
            },
            'dummy2': {
                'direction': 'inout'
            },
            'dummyx': {
                'direction': 'inout'
            },
            'dummyy': {
                'direction': 'inout'
            },
            'dummyz': {
                'direction': 'inout'
            },
            'dummyi': {
                'direction': 'inout'
            },
        },
        'capability_type': "ignore"
    },
    'test2': {
        'doc': """
                This is a property used only for tests, needed to pass syntax checking.
                """,
        'user-level': False,
        'type': 'category',
        'values': {
            'dummy': {
                'direction': 'inout'
            },
            'dummy1': {
                'direction': 'inout'
            },
            'dummy2': {
                'direction': 'inout'
            },
            'dummyx': {
                'direction': 'inout'
            },
            'dummyy': {
                'direction': 'inout'
            },
            'dummyz': {
                'direction': 'inout'
            },
            'dummyi': {
                'direction': 'inout'
            }
        },
        'capability_type': "ignore"
    }
}

# Constrained node port property support
constrained_port_property_data = {
    'name': {
        'doc': """Calvin-constrained supported port properties""",
        'type': 'name',
        'capability_type': "name",
        'value': "runtime.constrained.1",
        'user-level': False
    },
    'routing': {
        'doc': """Routing decides how tokens are routed out or in of a port """,
        'user-level': True,
        'type': 'category',
        'capability_type': "category",
        'values': {
            'default': {
                'doc': """The default routing of all tokens to all peers""",
                'direction': "out"
            },
            'fanout': {
                'doc': """The default routing of all tokens to all peers with specific name""",
                'direction': "out"
            },
        }
    },
    'queue_length': {
        'doc': """Specifies the minimum number of tokens that the queue can hold.""",
        'user-level': True,
        'type': 'scalar',
        'direction': 'inout',
        'capability_type': "ignore"
    },
    'nbr_peers': {
        'doc': """
                Automatically set based on connections in calvinscript. When
                not using calvinscript needs to set it on ports with multiple
                connections at least for inports.
                """,
        'user-level': False,
        'type': 'scalar',
        'direction': 'inout',
        'capability_type': "func",
        'capability_func': lambda n: "one" if n==1 else "many",
        'capability_categories': ["one"]  # Constrained node support these
    },
}

port_property_sets = {
    "all": port_property_data,
    "runtime.base.1": port_property_data,
    "runtime.constrained.1": constrained_port_property_data
    }

def list_port_property_capabilities(which="runtime.base.1"):
    """ List a runtime's supported port properties """
    data = port_property_sets[which]
    property_capabilities = []
    # list all of the details as well as the collective name of the properties
    for propertyname, value in data.items():
        if value['capability_type'] == "ignore":
            continue
        if value['capability_type'] == "category":
            for category in value["values"]:
                property_capabilities.append(propertyname + "." + category)
        elif value['capability_type'] == "propertyname":
            property_capabilities.append(propertyname)
        elif value['capability_type'] == "name":
            property_capabilities.append(value["value"])
        elif value['capability_type'] == "func":
            for category in value['capability_categories']:
                property_capabilities.append(propertyname + "." + category)
    return ["portproperty." + p for p in property_capabilities]

def get_port_property_capabilities(properties):
    property_capabilities = set([])
    for key, values in properties.items():
        if isinstance(values, (list, tuple)):
            value = values[0]
        else:
            value = values
        if key not in port_property_data.keys():
            # This should not happen so just ignore it
            continue
        ppdata = port_property_sets['all'][key]
        if ppdata['capability_type'] == "ignore":
            continue
        if ppdata['capability_type'] == "category":
            property_capabilities.add(key + "." + value)
        elif ppdata['capability_type'] == "propertyname":
            property_capabilities.add(key)
        elif ppdata['capability_type'] == "func":
            category = ppdata['capability_func'](value)
            property_capabilities.add(key + "." + category)
    return set(["portproperty." + p for p in property_capabilities])

def get_port_property_runtime(properties, prepend=True):
    runtimes = []
    for rt, ppdata in port_property_sets.items():
        if rt == "all":
            continue
        available = set(list_port_property_capabilities(which=rt))
        if properties.issubset(available):
            runtimes.append(rt)
    if prepend:
        runtimes = ["portproperty." + rt for rt in runtimes]
    return runtimes

def generate_port_dir_doc(type_, direction):
    if direction == "in":
        return "The " + type_ + " can be applied on in-ports.\n"
    elif direction == "out":
        return "The " + type_ + " can be applied on out-ports.\n"
    elif direction == "inout":
        return "The " + type_ + " can be applied on both in- and out-ports.\n"
    else:
        return "The direction of the port the " + type_ + " can be applied on is decided by the arguments.\n"

def generate_doc():
    p = "# Port Properties \n"
    p += """This page list the port properties that can be specified in a Calvinscript.\n"""
    s = ""
    for pp, value in port_property_sets['all'].items():
        if not value["user-level"]:
            continue
        p += "* `" + pp + "`\n"
        s += "## " + pp + "\n"
        s += value["doc"] + "\n"
        direction = value.get("direction", "unknown")
        s += generate_port_dir_doc("property", direction)
        s += "Argument type is " + value.get("type", "unknown") + ".\n"
        s += "\n    <actor-instance>.<port-name>[in/out](" + pp + "=<" + value.get("type", "unknown") + ">)\n"
        s += "\n"
        if value.get("type", "unknown") != "category":
            continue
        for name, data in value.get("values", {}).items():
            s += "* `\"" + name + "\"`: " + data.get("doc", "") + " "
            s += generate_port_dir_doc("argument", data.get("direction", "unknown")) + "\n"
    return p + "\n" + s

if __name__ == '__main__':
    print generate_doc()