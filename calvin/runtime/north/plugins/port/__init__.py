from calvin.utilities.utils import enum
# Only TEMPORARY, TERMINATE and EXHAUST are used on highest level in actor and port manager
# TEMPORARY is used during migration
# TERMINATE is used for dereplication without preserving tokens
# EXHAUST is used for dereplication while preserving tokens
# The different exhaust disconnects are based on a higher level exhaust value
# EXHAUST and EXHAUST_PEER are used at actor port, endpoint and connection level
# EXHAUST_INPORT, EXHAUST_OUTPORT, EXHAUST_PEER_SEND, EXHAUST_PEER_RECV are used at queue level
DISCONNECT = enum('TEMPORARY', 'TERMINATE', 'EXHAUST', 'EXHAUST_PEER',
                  'EXHAUST_INPORT', 'EXHAUST_OUTPORT', 'EXHAUST_PEER_RECV', 'EXHAUST_PEER_SEND')
