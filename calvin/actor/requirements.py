
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import dynops
import calvin.utilities.calvinresponse as response
from calvin.runtime.south.plugins.async import async

_log = get_logger(__name__)


class ActorRequirements(object):
    def __init__(self, node, am, requirements, actor_id):
        self.node = node
        self.am = am
        self.requirements = requirements
        self.actor_id = actor_id

    def _no_actor(self, callback):
        # Can only migrate actors from our node
        _log.analyze(self.node.id, "+ NO ACTOR", {'actor_id': self.actor_id})
        if callback:
            callback(status=response.CalvinResponse(False))

    def _no_requirements(self, callback):
        # requirements need to be list
        _log.analyze(self.node.id, "+ NO REQ LIST", {'actor_id': self.actor_id})
        if callback:
            callback(status=response.CalvinResponse(response.BAD_REQUEST))

    def fulfill(self, actors, extend, move, callback):
        if self.actor_id not in actors:
            return self._no_actor(callback)
        if not isinstance(self.requirements, (list, tuple)):
            return self._no_requirements(callback)

        actor = actors[self.actor_id]
        actor._collect_placement_counter = 0
        actor._collect_placement_last_value = 0
        actor._collect_placement_cb = None
        actor.requirements_add(self.requirements, extend)
        node_iter = self.node.app_manager.actor_requirements(None, self.actor_id)
        possible_placements = set([])
        done = [False]
        node_iter.set_cb(self._update_requirements_placements, node_iter, possible_placements,
                         move=move, cb=callback, done=done)
        _log.analyze(self.node.id, "+ CALL CB", {'actor_id': self.actor_id, 'node_iter': str(node_iter)})

        # Must call it since the triggers might already have released before cb set
        self._update_requirements_placements(node_iter, possible_placements, move=move, cb=callback, done=done)
        _log.analyze(self.node.id, "+ END", {'actor_id': self.actor_id, 'node_iter': str(node_iter)})

    def _pause_iteration(self, actor, node_iter, possible_placements, done, move, cb):
        _log.analyze(self.node.id, "+ PAUSED",
                     {'counter': actor._collect_placement_counter,
                      'last_value': actor._collect_placement_last_value,
                      'diff': actor._collect_placement_counter - actor._collect_placement_last_value})
        # FIXME the dynops should be self triggering, but is not...
        # This is a temporary fix by keep trying
        delay = 0.0 if actor._collect_placement_counter > actor._collect_placement_last_value + 100 else 0.2
        actor._collect_placement_counter += 1
        actor._collect_placement_cb = async.DelayedCall(delay, self._update_requirements_placements,
                                                        node_iter, possible_placements, done=done,
                                                        move=move, cb=cb)

    def _stop_iteration(self, possible_placements, done, move, cb):
        # all possible actor placements derived
        _log.analyze(self.node.id, "+ ALL", {})
        done[0] = True
        if move and len(possible_placements) > 1:
            possible_placements.discard(self.node.id)
        if not possible_placements:
            if cb:
                cb(status=response.CalvinResponse(False))
            return
        if self.node.id in possible_placements:
            # Actor could stay, then do that
            if cb:
                cb(status=response.CalvinResponse(True))
            return
        # TODO do a better selection between possible nodes
        self.am.migrate(self.actor_id, possible_placements.pop(), callback=cb)
        _log.analyze(self.node.id, "+ END", {})

    def _update_requirements_placements(self, node_iter, possible_placements, done, move=False, cb=None):
        _log.analyze(self.node.id, "+ BEGIN", {}, tb=True)
        actor = self.am.actors[self.actor_id]
        if actor._collect_placement_cb:
            actor._collect_placement_cb.cancel()
            actor._collect_placement_cb = None
        if done[0]:
            return
        try:
            while True:
                _log.analyze(self.node.id, "+ ITER", {})
                node_id = node_iter.next()
                possible_placements.add(node_id)
        except dynops.PauseIteration:
            return self._pause_iteration(actor, node_iter, possible_placements, done, move, cb)
        except StopIteration:
            return self._stop_iteration(possible_placements, done, move, cb)
        except:
            _log.exception("actor/requirements:_update_requirements_placements")
