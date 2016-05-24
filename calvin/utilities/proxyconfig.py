from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

# {"VendorID": {"VendorName": <VendorName>, "products": {"<ProductID>": {"ProductName": "<ProductName>", "capabilities": [<capability>]}}}}
proxy_devices = {
	"0x1":
	{
		"VendorName": "Ericsson",
		"products":
		{
			"0x1":
			{
				"ProductName": "uCalvin",
				"capabilities": ["calvinsys.events.timer"]
			}
		}
	}
}

def set_proxy_config(vid, pid, node_id, storage):
	"""
	Set node configuration of node with id node_id with information from proxy_devices
	with vid and pid
	TODO: Add command to remove config
	"""
	status = False
	try:
		if vid in proxy_devices:
		    if pid in proxy_devices[vid]['products']:
		        for c in proxy_devices[vid]['products'][pid]['capabilities']:
		            storage.add_index(['node', 'capabilities', c], node_id, root_prefix_level=3)
		        status = True
	except:
		_log.error("Failed to configure proxy node")
	return status