import json
import hashlib

    

def signature(metadata):
    signature = {
        u'actor_type': unicode("{ns}.{name}".format(**metadata)),
        u'inports': sorted([unicode(port['name']) for port in metadata['ports'] if port['direction'] == 'in']),
        u'outports': sorted([unicode(port['name']) for port in metadata['ports'] if port['direction'] == 'out'])
    }
    data = json.dumps(signature, separators=(',', ':'), sort_keys=True)
    return hashlib.sha256(data).hexdigest()
