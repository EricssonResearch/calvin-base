port_property_data = {
    'routing': {
        'doc': """Routing decides how tokens are routed out or in of a port """,
        'type': 'category',
        'values': {
            'fanout': {
                'doc': """The default routing of all tokens to all peers""",
                'direction': "out"
            },
            'round-robin': {
                'doc': """Route each tokens to one peer in a round-robin schedule""",
                'direction': "out"
            },
            'random': {
                'doc': """Route each tokens to one peer in a random schedule""",
                'direction': "out"
            },
            'collect-unordered': {
                'doc': """
                    Collect tokens from multiple peers, actions see
                    them individually in without order between peers
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
        }
    },
    'queue_length': {
        'doc': """Specifies the minimum number of tokens that the queue can hold.""",
        'type': 'scalar',
        'direction': 'inout'
    },
    'nbr_peers': {
        'doc': """
                Automatically set based on connections in calvinscript. When
                not using calvinscript needs to set it on ports with multiple
                connections at least for inports.
                """,
        'type': 'scalar',
        'direction': 'inout'
    },
    'tag': {
        'doc': """Specifies a tag on e.g. an outport that can be retrived with certain inport routing properties""",
        'type': 'string',
        'direction': 'inout'
    },
    'test1': {
        'doc': """
                This is a property used only for tests, needed to pass syntax checking.
                """,
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
    },
    'test2': {
        'doc': """
                This is a property used only for tests, needed to pass syntax checking.
                """,
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
        }
    }
}

