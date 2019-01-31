The table below show the current API usage by the following components: CalvinGUI, CSWeb, cscontrol, csruntime, and utilites.nodecontrol.py

CalvinGUI, CSWeb, and cscontrol basically need the same set of functionality (which makes sense, since they are all used to deploy apps and monitor state).
The big question mark is the registry API; we need to expose a common interface to the registry regardless of the backend implementation, and the preferred way would be to 
only expose the "get_accessors" in class Storage. However, both CalvinGUI, CSWeb and cscontrol seem to require _reads_ from the indexed database.

Actually, we should consider making CalvinGUI, CSWeb and cscontrol equal in terms of features.


| API group        | Operation                                                | Helper               | GUI | CSWEB | CSCTRL | CSRT | NDCTRL | COMMENT                           |
|------------------|----------------------------------------------------------|----------------------|-----|-------|--------|------|--------|-----------------------------------|
| registry_api     | GET "/node/" + nodeID                                    | .get_node            |  X  |   X   |   X    |      |   X    | Accessor: storage.get_node        |
| registry_api     | GET "/actor/" + actorID                                  | .get_actor           |  X  |   X   |   X    |      |        | Accessor: storage.get_actor       |
| registry_api     | GET "/application/" + appID                              | .get_application     |     |   X   |   X    |      |        | Accessor: storage.get_application |
| registry_api     | GET /actor/' + actor_id + '/port/' + port_id             |                      |     |   X   |        |      |        | Accessor: storage.get_port        |
| registry_api     | GET "/index/"                                            | .get_index           |     |   X   |   X    |      |        |                                   |
| registry_api     | GET /index/replicas/actors/                              |                      |     |   X   |        |      |        |                                   |
| registry_api     | GET "/index/node/attribute/node_name"                    |                      |  X  |       |        |      |        |                                   |
|                  |                                                          |                      |     |       |        |      |        |                                   |
| application_api  | POST "/actor/" + actorID + "/migrate"                    | .migrate             |  X  |   X   |   X    |      |        |                                   |
| application_api  | POST "/actor/" + actorID + "/replicate"                  |                      |     |   X   |        |      |        |                                   |
| application_api  | GET "/actor/" + actorID + "/port/" + portID + "/state"   |                      |  X  |   X   |        |      |        |                                   |
| application_api  | GET "/actors"                                            | .get_actors          |  X  |       |   X    |      |        |                                   |
| application_api  | DELETE "/application/" + appID                           | .delete_application  |  X  |   X   |   X    |      |        |                                   |
| application_api  | POST "/application/" + appID + "/migrate"                | .migrate_app_use_req |  X  |   X   |   X    |      |        |                                   |
| application_api  | GET "/applications"                                      | .get_applications    |  X  |   X   |   X    |      |        |                                   |
| application_api  | POST "/deploy"                                           | .deploy              |  X  |   X   |   X    |      |        |                                   |
| application_api  | DELETE "/actor/" + actorID                               | .delete_actor        |     |       |   X    |      |        | Deprecated, remove                |
|                  |                                                          |                      |     |       |        |      |        |                                   |
| runtime_api      | GET "/capabilities"                                      |                      |  X  |   X   |        |      |        |                                   |
| runtime_api      | GET /id                                                  | .get_node_id         |     |   X   |   X    |      |   X    |                                   |
| runtime_api      | GET /nodes                                               | .get_nodes           |     |   X   |   X    |      |        |                                   |
| runtime_api      | DELETE /node/ + method                                   | .quit                |     |   X   |   X    |      |        |                                   |
| runtime_api      | POST /peer_setup                                         | .peer_setup          |     |       |   X    |      |        |                                   |
|                  |                                                          |                      |     |       |        |      |        |                                   |
| uicalvinsys_api  | POST "/uicalvinsys"                                      |                      |  X  |       |        |      |        |                                   |
| uicalvinsys_api  | GET "/uicalvinsys/" + appID                              |                      |  X  |       |        |      |        |                                   |
|                  |                                                          |                      |     |       |        |      |        |                                   |
| proxyhandler_api | GET "/proxy/ + peerID + /capabilities"                   |                      |     |   X   |        |      |        |                                   |
| proxyhandler_api | DELETE /proxy/ + peerID + / + method                     |                      |     |   X   |        |      |        |                                   |
|                  |                                                          |                      |     |       |        |      |        |                                   |
| logging_api      | POST /log                                                |                      |     |   X   |        |      |        | What about GET /log?              |
| logging_api      | logging_api DELETE /log/ + peerID                        |                      |     |   X   |        |      |        |                                   |
|                  |                                                          |                      |     |       |        |      |        |                                   |
| security_api     | POST /certificate_authority/certificate_signing_request  |.sign_csr_request     |     |       |        |  X   |        | Most of security API is unused?   |
|                  |                                                          |                      |     |       |        |      |        |                                   |
