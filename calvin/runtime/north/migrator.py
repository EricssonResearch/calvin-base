
from calvin.utilities.calvin_callback import CalvinCB
import calvin.utilities.calvinresponse as response


class Migrator(object):
    def __init__(self, node, am):
        self.node = node
        self.am = am

    def _abort(self, callback, value):
        if callback:
            callback(status=response.CalvinResponse(value))
        return

    def migrate_actor(self, actor_id, node_id, callback=None):
        """Migrates an actor actor_id to peer node node_id"""
        if actor_id not in self.am.actors:
            # Can only migrate actors from our node
            return self._abort(callback, False)
        if node_id == self.node.id:
            # No need to migrate to ourself
            return self._abort(callback, True)

        actor = self.am.actors[actor_id]
        actor._migrating_to = node_id
        actor.will_migrate()
        actor_type = actor._type
        ports = actor.connections(self.node.id)
        # Disconnect ports and continue in _migrate_disconnect
        self.node.pm.disconnect(callback=CalvinCB(self._migrate_disconnected,
                                                  actor=actor,
                                                  actor_type=actor_type,
                                                  ports=ports,
                                                  node_id=node_id,
                                                  callback=callback),
                                actor_id=actor_id)
        self.node.control.log_actor_migrate(actor_id, node_id)

    def _migrate_disconnected(self, actor, actor_type, ports, node_id, status, callback=None, **state):
        """ Actor disconnected, continue migration """
        if status:
            state = actor.state()
            self.am.destroy(actor.id)
            self.node.proto.actor_new(node_id, callback, actor_type, state, ports)
        elif callback:  # FIXME handle errors!!!
            callback(status=status)
