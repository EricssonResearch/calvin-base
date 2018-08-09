# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from calvin.utilities import dynops
from calvin.utilities import calvinlogger
from calvin.runtime.north.plugins.requirements import req_operations
import calvin.requests.calvinresponse as response
from calvin.runtime.south.async import async

_log = calvinlogger.get_logger(__name__)

class ReqMatch(object):
    """ ReqMatch Do requirement matching for an actor.
        node: the node
        callback: takes arguments possible_placements (set) and status (CalvinResponse)
        replace_infinite: when the possible placement would be InfinteElement replace it with all known node ids
    """
    def __init__(self, node, callback=None, replace_infinite=False):
        super(ReqMatch, self).__init__()
        self.node = node
        self.callback = callback
        self.replace_infinite = replace_infinite

    def match_for_actor(self, actor_id):
        """ Helper function for matching locally found actors """
        if actor_id not in self.node.am.actors:
            # Can only migrate actors from our node
            _log.analyze(self.node.id, "+ NO ACTOR", {'actor_id': actor_id})
            if callable(self.callback):
                self.callback(status=response.CalvinResponse(False), possible_placements=set([]))
            return
        actor = self.node.am.actors[actor_id]
        return self.match(
                    requirements=actor.requirements_get(),
                    actor_id=actor_id,
                    component_ids=actor.component_members())

    def match_actor_registry(self, actor_id):
        """ Helper function to first fetch requirements from registry """
        # TODO no component level handling currently
        def _got_requirements(key, value):
            if response.isnotfailresponse(value):
                try:
                    self.match(value, actor_id)
                except:
                    if callable(self.callback):
                        self.callback(status=response.CalvinResponse(response.BAD_REQUEST), possible_placements=set([]))
            else:
                if callable(self.callback):
                    self.callback(status=value, possible_placements=set([]))
        if actor_id in self.node.am.actors:
            # Don't waste time if local
            return self.match_for_actor(actor_id)
        else:
            self.node.storage.get_actor_requirements(actor_id, cb=_got_requirements)

    def match(self, requirements, actor_id=None, component_ids=None):
        """ Match the list of requirements either from a local actor or on behalf of
            another runtime.
            callback is called with the possible placement set and status,
            i.e. callback(status=CalvinResponse(), possible_placments=set([...]))
            status can be OK, BAD_REQUEST, SERVER_ERROR

            actor_id and component_ids are used when calling the requirement operations only,
            they are required by some of the req operations.
        """
        if not isinstance(requirements, (list, tuple)):
            # Requirements need to be list
            _log.analyze(self.node.id, "+ NO REQ LIST", {'reqs': requirements})
            if callable(self.callback):
                self.callback(status=response.CalvinResponse(response.BAD_REQUEST), possible_placements=set([]))
            return
        self.requirements = requirements
        self.actor_id = actor_id
        self.component_ids = component_ids
        self._collect_placement_counter = 0
        self._collect_placement_last_value = 0
        self._collect_placement_cb = None
        self.node_iter = self._build_match()
        self.possible_placements = set([])
        self.done = False
        self.node_iter.set_cb(self._collect_placements)
        _log.analyze(self.node.id, "+ CALL CB", {'actor_id': self.actor_id, 'node_iter': str(self.node_iter)})
        # Must call it since the triggers might already have released before cb set
        self._collect_placements()
        _log.analyze(self.node.id, "+ END", {'actor_id': self.actor_id, 'node_iter': str(self.node_iter)})

    def _build_match(self):
        intersection_iters = []
        difference_iters = []
        for req in self.requirements:
            if req['op']=='union_group':
                # Special operation that first forms a union of a requirement's list response set
                # To allow alternative requirements options
                intersection_iters.append(self._build_union_match(req=req).set_name("SActor" + self.actor_id))
            else:
                try:
                    _log.analyze(self.node.id, "+ REQ OP", {'op': req['op'], 'kwargs': req['kwargs']})
                    it = req_operations[req['op']].req_op(self.node,
                                            actor_id=self.actor_id,
                                            component=self.component_ids,
                                            **req['kwargs']).set_name(req['op']+",SActor" + self.actor_id)
                    if req['type']=='+':
                        intersection_iters.append(it)
                    elif req['type']=='-':
                        difference_iters.append(it)
                    else:
                        _log.error("actor_requirements unknown req type %s for %s!!!" % (req['type'], self.actor_id),
                                   exc_info=True)
                except:
                    _log.error("actor_requirements one req failed for %s!!!" % self.actor_id, exc_info=True)
                    # FIXME how to handle failed requirements, now we drop it
        return_iter = dynops.Intersection(*intersection_iters).set_name("SActor" + self.actor_id)
        if difference_iters:
            return_iter = dynops.Difference(return_iter, *difference_iters).set_name("SActor" + self.actor_id)
        return return_iter

    def _build_union_match(self, req):
        union_iters = []
        for union_req in req['requirements']:
            try:
                union_iters.append(req_operations[union_req['op']].req_op(self.node,
                                        actor_id=self.actor_id,
                                        component=self.component_ids,
                                        **union_req['kwargs']).set_name(union_req['op'] + ",UActor" + self.actor_id))
            except:
                _log.error("union_requirements one req failed for %s!!!" % self.actor_id, exc_info=True)
        return dynops.Union(*union_iters)

    def _collect_placements(self):
        _log.analyze(self.node.id, "+ BEGIN", {}, tb=True)
        if self._collect_placement_cb:
            self._collect_placement_cb.cancel()
            self._collect_placement_cb = None
        if self.done:
            return
        try:
            while True:
                _log.analyze(self.node.id, "+ ITER", {})
                node_id = self.node_iter.next()
                self.possible_placements.add(node_id)
        except dynops.PauseIteration:
            _log.analyze(self.node.id, "+ PAUSED",
                    {'counter': self._collect_placement_counter,
                     'last_value': self._collect_placement_last_value,
                     'diff': self._collect_placement_counter - self._collect_placement_last_value})
            # FIXME the dynops should be self triggering, but is not...
            # This is a temporary fix by keep trying
            delay = 0.0 if self._collect_placement_counter > self._collect_placement_last_value + 100 else 0.2
            self._collect_placement_counter += 1
            self._collect_placement_cb = async.DelayedCall(delay, self._collect_placements)
            return
        except StopIteration:
            # All possible actor placements derived
            _log.analyze(self.node.id, "+ ALL", {})
            self.done = True
            if self.replace_infinite:
                # Replace Infinte Element with all known real ids
                if any([isinstance(node_id, dynops.InfiniteElement) for node_id in self.possible_placements]):
                    try:
                        replace_ids = self.node.network._links.keys() + [self.node.id]
                    except:
                        replace_ids = [self.node.id]
                    self.possible_placements = set(replace_ids)
            if callable(self.callback):
                status = response.CalvinResponse(True if self.possible_placements else False)
                self.callback(possible_placements=self.possible_placements, status=status)
                return
            _log.analyze(self.node.id, "+ END", {})
        except:
            _log.exception("ReqMatch:_collect_placements")

