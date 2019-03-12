import pytest


def _assert_tagged_set(control_api, rt_uri, sink_ids):
    """
    Helper function to handle cases where the default 
    _assert_expectation function is not sufficient.
    Is used in place of expected value in testlist.
    """
    n_values = 20
    for sink_id in sink_ids:
        for retry in range(10):
            status, actual = control_api.get_actor_report(rt_uri, sink_id)
            assert status == 200
            if len(actual) >= n_values:
                break
                
        pairs = [x.split('-') for x in actual]
        tags = {p[0] for p in pairs}
        values = sorted([int(p[1]) for p in pairs])
        assert values[:n_values] == list(range(1, n_values+1))
        assert tags == set(["tag1", "tag2", "tag3"])


testlist = [
    (
        'test_destroy_app_with_localactors',
        r"""
            src : std.Counter()
            snk : test.Sink(store_tokens=1, quiet=1, active=true)
            src.integer > snk.token
        """,
        ['snk'],
        [list(range(1, 11))],
    ),
    (
        'test_output capture',
        r"""
            src : std.Counter()
            ity : std.Identity(dump=false)
            snk : test.Sink(store_tokens=1, quiet=1, active=true)
            src.integer > ity.token
            ity.token > snk.token
        """,
        ['snk'],
        [list(range(1, 11))],
    ),
    (
        'test_fanout',
        r"""
            src : std.Counter()
            snk1 : test.Sink(store_tokens=1, quiet=1, active=true)
            snk2 : test.Sink(store_tokens=1, quiet=1, active=true)
            src.integer > snk1.token
            src.integer > snk2.token
        """,
        ['snk1', 'snk2'],
        [list(range(1, 11))]*2,
    ),
    (
        'test_fanout_from_component_inports',
        r"""
            component Foo() in -> a, b{
              a : std.Identity(dump=false)
              b : std.Identity(dump=false)
              .in >  a.token
              .in > b.token
              a.token > .a
              b.token > .b
            }
            snk2 : test.Sink(store_tokens=1, quiet=1, active=true)
            snk1 : test.Sink(store_tokens=1, quiet=1, active=true)
            foo : Foo()
            req : std.Counter()
            req.integer > foo.in
            foo.a > snk1.token
            foo.b > snk2.token
        """,
        ['snk1', 'snk2'],
        [list(range(1, 11))]*2,
    ),
    (
        'test_map_alternate',
        r"""
            snk : test.Sink(store_tokens=1, quiet=1, active=true)
            input: std.Counter()
            alt: flow.Alternate(order=[&out1.out, &out2.out, &out3.out])
            out1 : text.PrefixString(prefix="tag-1:")
            out2 : text.PrefixString(prefix="tag-2:")
            out3 : text.PrefixString(prefix="tag-3:")
            input.integer > out1.in
            input.integer > out2.in
            input.integer > out3.in
            out1.out > alt.token
            out2.out > alt.token
            out3.out > alt.token
            alt.token > snk.token
        """,
        ['snk'],
        [[
            "tag-1:1",
            "tag-2:1",
            "tag-3:1",
            "tag-1:2",
            "tag-2:2",
            "tag-3:2",
            "tag-1:3",
            "tag-2:3",
            "tag-3:3",
            "tag-1:4",
            "tag-2:4",
            "tag-3:4"
        ]],
    ),
    (
        'test_map_dealternate',
        r"""
            snk : test.Sink(store_tokens=1, quiet=1, active=true)
            input: std.Counter()
            switch: flow.Dealternate(order=[&out3.in, &out1.in, &out2.in])
            out1 : text.PrefixString(prefix="tag-1:")
            out2 : text.PrefixString(prefix="tag-2:")
            out3 : text.PrefixString(prefix="tag-3:")
            collect : flow.Alternate(order=[&out1.out, &out2.out, &out3.out])
            input.integer > switch.token
            switch.token > out1.in
            switch.token > out2.in
            switch.token > out3.in
            out1.out > collect.token
            out2.out > collect.token
            out3.out > collect.token
            collect.token > snk.token
        """,
        ['snk'],
        [[
            "tag-1:2",
            "tag-2:3",
            "tag-3:1",
            "tag-1:5",
            "tag-2:6",
            "tag-3:4",
            "tag-1:8",
            "tag-2:9",
            "tag-3:7"
        ]]
    ),
    (
        'test_map_dispatch_dict',
        r"""
            snk : test.Sink(store_tokens=1, quiet=1, active=true)
            dd : flow.DispatchDict(mapping={"t1": &tag1.in, "t2": &tag2.in, "t3": &tag3.in})
            tag1: text.PrefixString(prefix="tag-1:")
            tag2: text.PrefixString(prefix="tag-2:")
            tag3: text.PrefixString(prefix="tag-3:")
            coll : flow.Alternate(order=[&tag1.out, &tag2.out, &tag3.out])
            {"t1": 1, "t2": 2, "t3": 3} > dd.dict
            dd.token > tag1.in
            dd.token > tag2.in
            dd.token > tag3.in
            dd.default > voidport
            tag1.out > coll.token
            tag2.out > coll.token
            tag3.out > coll.token
            coll.token > snk.token
        """,
        ['snk'],
        [[
            "tag-1:1",
            "tag-2:2",
            "tag-3:3",
            "tag-1:1",
            "tag-2:2",
            "tag-3:3",
            "tag-1:1",
            "tag-2:2",
            "tag-3:3",
        ]],
    ),
    (
        'test_map_collect_complete_dict',
        """
            snk : test.Sink(store_tokens=1, quiet=1, active=true)
            dd : flow.DispatchDict(mapping={"t1": &tag1.in, "t2": &tag2.in, "t3": &tag3.in})
            tag1: text.PrefixString(prefix="tag-1:")
            tag2: text.PrefixString(prefix="tag-2:")
            tag3: text.PrefixString(prefix="tag-3:")
            cd : flow.CollectCompleteDict(mapping={"t1": &tag2.out, "t2": &tag3.out, "t3": &tag1.out})
            {"t1": 1, "t2": 2, "t3": 3} > dd.dict
            dd.token > tag1.in
            dd.token > tag2.in
            dd.token > tag3.in
            dd.default > voidport
            tag1.out > cd.token
            tag2.out > cd.token
            tag3.out > cd.token
            cd.dict > snk.token
        """,
        ['snk'],
        [[{'t2': 'tag-3:3', 't3': 'tag-1:1', 't1': 'tag-2:2'}]*10],
    ),
    (
        'test_map_dispatch_collect',
        r"""
            snk : test.Sink(store_tokens=1, quiet=1, active=true)
            input: std.Counter()
            disp : flow.Dispatch()
            coll : flow.Collect()
            tag1: text.PrefixString(prefix="tag1-")
            tag2: text.PrefixString(prefix="tag2-")
            tag3: text.PrefixString(prefix="tag3-")
            input.integer > disp.token
            disp.token > tag1.in
            disp.token > tag2.in
            disp.token > tag3.in
            tag1.out > coll.token
            tag2.out > coll.token
            tag3.out > coll.token
            coll.token > snk.token
        """,
        ['snk'],
        _assert_tagged_set,        
    )
]

system_config = r"""
- class: ACTORSTORE
  name: actorstore
  port: 4999
  type: REST
- class: RUNTIME
  name: runtime
  actorstore: $actorstore
  registry: 
    type: local
    uri: null
"""

@pytest.fixture(scope='module', params=testlist)
def deploy_application(request, system_setup, deploy_app, destroy_app):
    """Deploy applications from set of scrips and test output"""
    rt_uri = system_setup['runtime']['uri']
    actorstore_uri = system_setup['actorstore']['uri']
    # expects can be a function
    name, script, sinks, expects = request.param
    if type(expects) in (list, tuple):
        assert len(sinks) == len(expects)
    app_info = deploy_app(rt_uri, script, name, actorstore_uri)
    actor_map = app_info['actor_map']
    sink_ids = [actor_map[name + ':' + sink] for sink in sinks]

    yield (rt_uri, sink_ids, expects)

    # Clean-up section
    destroy_app(rt_uri, app_info)


def _assert_expectation(control_api, rt_uri, sink_ids, expects):
    """Compare the aoutput from sinks to values in expects"""
    for sink_id, expected in zip(sink_ids, expects):
        for retry in range(10):
            status, actual = control_api.get_actor_report(rt_uri, sink_id)
            assert status == 200
            if len(actual) >= len(expected):
                break
        assert len(actual) >= len(expected)
        assert actual[:len(expected)] == expected

    
def test_actual_output(deploy_application, control_api):
    rt_uri, sink_ids, expects = deploy_application
    if type(expects) in (list, tuple):
        _assert_expectation(control_api, rt_uri, sink_ids, expects)
    else:
        # expects is a function that knows how to determine success/failure
        expects(control_api, rt_uri, sink_ids)    


# The tests to perform here are the ones that cannot be caught by either compiler tests or actor unit tests
# Examples include: deploy, destroy, fan-out, fan-in, port routing
# They should be repeated in a multi-runtime test in combination with migration


# @pytest.mark.xfail
# def testMapComponentPort(self):
#     script = r"""
#     component Dummy() in -> out {
#         identity : std.Identity()
#         .in > identity.token
#         identity.token > .out
#     }
#     snk : test.Sink(store_tokens=1, quiet=1)
#     dummy : Dummy()
#     cdict : flow.CollectCompleteDict(mapping={"dummy":&dummy.out})
#     1 > dummy.in
#     dummy.out > cdict.token
#     cdict.dict > snk.token
#     """
#     actual = self._run_test(script, 10)
#     expected = [{u'dummy': 1}]*len(actual)
#     self.assert_lists_equal(expected, actual)
#
#
# @pytest.mark.xfail
# def testMapComponentInternalPort(self):
#     script = r"""
#     component Dummy() in -> out {
#         # Works with &foo.token or "foo.token" if constant has label :foo
#         cdict : flow.CollectCompleteDict(mapping={"dummy":&.in})
#
#         .in > cdict.token
#         cdict.dict > .out
#     }
#     snk : test.Sink(store_tokens=1, quiet=1)
#     dummy : Dummy()
#     1 > dummy.in
#     dummy.out > snk.token
#     """
#     actual = self._run_test(script, 10)
#     expected = [{u'dummy': 1}]*len(actual)
#     self.assert_lists_equal(expected, actual)
#