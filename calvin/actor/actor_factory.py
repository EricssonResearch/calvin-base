
from calvin.actorstore.store import ActorStore
from calvin.utilities.calvinlogger import get_logger
from calvin.actor.actor import ShadowActor

_log = get_logger(__name__)


class ActorFactory(object):
    def __init__(self, node):
        self.node = node

    def create_actor(self, actor_type, state=None, args={}, signature=None, app_id=None):
        try:
            if state:
                a = self._create_from_state(actor_type, state, app_id)
            else:
                a = self._create_new(actor_type, args, app_id)
        except Exception as e:
            _log.exception("Actor creation failed")
            raise(e)

        # Store the actor signature to enable GlobalStore lookup
        a.signature_set(signature)
        self.node.storage.add_actor(a, self.node.id, app_id)

        return a

    def _new_actor(self, actor_type, app_id, actor_id=None):
        """Return a 'bare' actor of actor_type, raises an exception on failure."""
        (found, is_primitive, class_) = ActorStore().lookup(actor_type)
        if not found:
            # Here assume a primtive actor, now become shadow actor
            _log.analyze(self.node.id, "+ NOT FOUND CREATE SHADOW ACTOR", {'class': class_})
            found = True
            is_primitive = True
            class_ = ShadowActor
        if not found or not is_primitive:
            _log.error("Requested actor %s is not available" % (actor_type))
            raise Exception("ERROR_NOT_FOUND")
        try:
            # Create a 'bare' instance of the actor
            a = class_(actor_type, actor_id=actor_id, app_id=app_id)
        except Exception as e:
            _log.exception("")
            _log.error("The actor %s(%s) can't be instantiated." % (actor_type, class_.__init__))
            raise(e)
        try:
            a._calvinsys = self.node.calvinsys()
            a.check_requirements()
        except Exception as e:
            _log.analyze(self.node.id, "+ FAILED REQS CREATE SHADOW ACTOR", {'class': class_})
            a = ShadowActor(actor_type, actor_id=actor_id, app_id=app_id)
            a._calvinsys = self.node.calvinsys()
        return a

    def _create_new(self, actor_type, args, app_id):
        """Return an initialized actor in PENDING state, raises an exception on failure."""
        try:
            a = self._new_actor(actor_type, app_id)
            # Now that required APIs are attached we can call init() which may use the APIs
            human_readable_name = args.pop('name', '')
            a.name = human_readable_name
            self.node.pm.add_ports_of_actor(a)
            a.init(**args)
            a.setup_complete()
        except Exception as e:
            _log.exception(e)
            raise(e)
        return a

    def _create_from_state(self, actor_type, state, app_id):
        """Return a restored actor in PENDING state, raises an exception on failure."""
        try:
            _log.analyze(self.node.id, "+", state)
            a = self._new_actor(actor_type, app_id, actor_id=state['id'])
            if '_shadow_args' in state:
                # We were a shadow, do a full init
                args = state.pop('_shadow_args')
                state['_managed'].remove('_shadow_args')
                a.init(**args)
                # If still shadow don't call did_migrate
                did_migrate = isinstance(a, ShadowActor)
            else:
                did_migrate = True
            # Always do a set_state for the port's state
            a.set_state(state)
            self.node.pm.add_ports_of_actor(a)
            if did_migrate:
                a.did_migrate()
            a.setup_complete()
        except Exception as e:
            raise(e)
        return a
