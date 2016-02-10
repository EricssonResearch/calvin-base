var connect_uri;        // control uri of runtime
var peers = [];         // runtimes
var applications = [];  // applications
var actors = [];        // actors
var ports = [];         // actor ports
var graph = new dagreD3.graphlib.Graph({compound:true})
            .setGraph({
                rankdir: "LR"
            })
            .setDefaultEdgeLabel(function() { return {}; });
var render = new dagreD3.render();
var svg = d3.select("#applicationGraph").append("svg");
svg.attr("width", document.getElementById("applicationGraph").width);
svg.attr("height", document.getElementById("applicationGraph").height);
var svgGroup = svg.append("g");
var graphTimer = null;

function addActorToGraph(actor)
{
    if (document.getElementById("chkDrawApplication").checked) {
        if (graphTimer) {
            clearTimeout(graphTimer);
        }

        var color = d3.scale.category20();
        for (var index in peers) {
            if (peers[index].id == actor.peer_id) {
                graph.setNode(peers[index].id, {
                    label: peers[index].name,
                    clusterLabelPos: 'top',
                    style: 'fill: LightGrey'
                });
            }
        }

        if (actor.is_shadow) {
            graph.setNode(actor.id, {label: actor.name, style: 'fill: Tomato'});
        } else {
            graph.setNode(actor.id, {label: actor.name, style: 'fill: White'});
        }
        graph.setParent(actor.id, actor.peer_id);

        graphTimer = setTimeout(updateGraph, 1000);
    }
}

function addPortToGraph(port)
{
    if (document.getElementById("chkDrawApplication").checked && document.getElementById("chkDrawConnections").checked) {
        if (graphTimer) {
            clearTimeout(graphTimer);
        }

        if (port.direction == "out") {
            var peer_index;
            for (peer_index in port.peers) {
                var peer_port = findPort(port.peers[peer_index][1]);
                if (peer_port) {
                    if (graphTimer) {
                        clearTimeout(graphTimer);
                    }
                    if(document.getElementById("chkShowPortNames").checked) {
                        graph.setEdge(port.actor_id, peer_port.actor_id, {label: port.name + " > " + peer_port.name});
                    } else {
                        graph.setEdge(port.actor_id, peer_port.actor_id);
                    }
                }
            }
        } else if(port.direction == "in") {
            if (port.peer) {
                var peer_port = findPort(port.peer[1]);
                if (peer_port) {
                    var peer_actor = findActor(peer_port.actor_id);
                    if (peer_actor) {
                        if(document.getElementById("chkShowPortNames").checked) {
                            graph.setEdge(peer_port.actor_id, port.actor_id, {label: peer_port.name + " > " + port.name});
                        } else {
                            graph.setEdge(peer_port.actor_id, port.actor_id);
                        }
                    }
                }
            }
        }
        graphTimer = setTimeout(updateGraph, 1000);
    }
}

function updateGraph()
{
    graph.nodes().forEach(function(v) {
      var node = graph.node(v);
      // Round the corners of the nodes
      node.rx = node.ry = 5;
    });

    svg
        .call(d3.behavior.zoom().on("zoom", function() {
            var ev = d3.event;
            svg.select("g")
                .attr("transform", "translate(" + ev.translate + ") scale(" + ev.scale + ")");
        }));

    // Run the renderer. This is what draws the final graph.
    render(d3.select("svg g"), graph);
}

// Clear application graph
function clearApplicationGraph() {
    document.getElementById("applicationGraph").innerHTML = "";

    graph = new dagreD3.graphlib.Graph({compound:true})
                .setGraph({
                    rankdir: "LR"
                })
                .setDefaultEdgeLabel(function() { return {}; });
    render = new dagreD3.render();
    svg = d3.select("#applicationGraph").append("svg");
    svg.attr("width", document.getElementById("applicationGraph").width);
    svg.attr("height", document.getElementById("applicationGraph").height);
    svgGroup = svg.append("g");
}

// Runtime object constructor function
function runtimeObject(id)
{
    this.id = id;
    this.actors = [];
    this.source = null;
    this.peers = [];
}

// Return runtime object from id
function findRuntime(id)
{
    var index;
    for (index in peers) {
        if (peers[index].id == id) {
            return peers[index];
        }
    }
}

// Application object constructor function
function applicationObject(id)
{
    this.id = id;
    this.actors = [];
}

// Return application object
function findApplication(id)
{
    var index;
    for (index in applications) {
        if (applications[index].id == id) {
            return applications[index];
        }
    }
}

// Actor object constructor function
function actorObject(id)
{
    this.id = id;
    this.inports = [];
    this.outports = [];
}

// Return actor from id
function findActor(id)
{
    var index;
    for (index in actors) {
        if (actors[index].id == id) {
            return actors[index];
        }
    }
}

// Port object constructor function
function portObject(id)
{
    this.id = id;
}

// Return port from id
function findPort(id)
{
    var index;
    for (index in ports) {
        if (ports[index].id == id) {
            return ports[index];
        }
    }
}

// Helper to clear table
function clearTable(tableRef)
{
    for(var i = 0; i < tableRef.rows.length;) {
       tableRef.deleteRow(i);
    }
}

// Helper to clear combobox
function clearCombo(selectbox)
{
    for(var i = 0; i < selectbox.options.length;) {
        selectbox.remove(i);
    }
}

// Helper to sort combobox
function sortCombo(selectbox)
{
    $(selectbox).html($(selectbox).children('option').sort(function (x, y) {
        return $(x).text().toUpperCase() < $(y).text().toUpperCase() ? -1 : 1;
    }));
    $(selectbox).get(0).selectedIndex = 0;
};

// Busy spinner
var opts = {
    lines: 11, // The number of lines to draw
    length: 15, // The length of each line
    width: 10, // The line thickness
    radius: 30, // The radius of the inner circle
    corners: 1, // Corner roundness (0..1)
    rotate: 0, // The rotation offset
    direction: 1, // 1: clockwise, -1: counterclockwise
    color: '#000', // #rgb or #rrggbb
    speed: 0.6, // Rounds per second
    trail: 60, // Afterglow percentage
    shadow: false, // Whether to render a shadow
    hwaccel: false, // Whether to use hardware acceleration
    className: 'spinner', // The CSS class to assign to the spinner
    zIndex: 2e9, // The z-index (defaults to 2000000000)
    top: 'auto', // Top position relative to parent in px
    left: 'auto' // Left position relative to parent in px
};
var spinner = new Spinner(opts);
var spinner_div = $('#spinner').get(0);
var spinCount = 0;

// Start spinner
function startSpin()
{
    if (spinCount == 0) {
        spinner.spin(spinner_div);
    }
    spinCount = spinCount + 1;
}

// Stop spinner
function stopSpin()
{
    spinCount = spinCount - 1;
    if (spinCount == 0) {
        spinner.stop();
    }
}

// Helper to get cookie
function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i=0; i<ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1);
        if (c.indexOf(name) == 0) return c.substring(name.length,c.length);
    }
    return "";
}

// Reset data, show connectDialog and get information from selected runtime
function connect()
{
    peers = [];
    applications = [];
    actors = [];
    ports = [];

    var tableRef = document.getElementById("peersTable");
    for(var i = 1; i < tableRef.rows.length;) {
       tableRef.deleteRow(i);
    }

    var uri = getCookie("calvin_uri");
    var index_search = getCookie("calvin_indexsearch");

    document.getElementById("connect_uri").value = uri;
    document.getElementById("index_search").value = index_search;

    $("#connectDialog").modal({
        modal: true,
        show: true,
    });
}

function connectHandler() {
    connect_uri = $("#connect_uri").val();
    index_search = $("#index_search").val();
    document.cookie="calvin_uri=" + connect_uri;
    document.cookie="calvin_indexsearch=" + index_search;
    getPeerID();
    if (index_search) {
        getPeersFromIndex(index_search);
    }
    $("#connectDialog").modal('hide');
}

// Get id of peer with uri "uri"
function getPeerID()
{
    var url = connect_uri + '/id';
    console.log("getPeerID - url: " + url);
    $.ajax({
        timeout: 20000,
        beforeSend: function() {
            startSpin();
        },
        complete: function() {
            stopSpin();
        },
        dataType: 'json',
        url: url,
        type: 'GET',
        success: function(data) {
            if (data) {
                console.log("getPeerID - Response: " + JSON.stringify(data));
                getPeer(data.id, true);
            } else {
                console.log("getPeerID - Empty response");
            }
        },
        error: function() {
            alert("Failed to get node id, url: " + url);
        }
    });
}

// Get peers from index "index"
function getPeersFromIndex(index)
{
    var url = connect_uri + '/index/' + index;
    console.log("getPeersFromIndex - url: " + url);
    $.ajax({
        timeout: 10000,
        beforeSend: function() {
            startSpin();
        },
        complete: function() {
            stopSpin();
        },
        dataType: 'json',
        url: url,
        type: 'GET',
        success: function(data) {
            if (data) {
                console.log("getPeersFromIndex response: " + JSON.stringify(data));
                var index;
                for (index in data.result) {
                    if (!findRuntime(data.result[index])) {
                        getPeer(data.result[index]);
                    }
                }
            } else {
                console.log("getPeersFromIndex - Empty response");
            }
        },
        error: function() {
            alert("Failed to get peers from index, url: " + url);
        }
    });
}

// Get connected peers
function getPeers(peer)
{
    var url = peer.control_uri + '/nodes';
    console.log("getPeers - url: " + url);
    $.ajax({
        peer: peer,
        timeout: 20000,
        beforeSend: function() {
            startSpin();
        },
        complete: function() {
            stopSpin();
        },
        dataType: 'json',
        url: url,
        type: 'GET',
        success: function(data) {
            if (data) {
                console.log("getPeers response: " + JSON.stringify(data));
                this.peer.peers = data;
                var index;
                for (index in data) {
                    if (!findRuntime(data[index])) {
                        getPeer(data[index]);
                    }
                }
            } else {
                console.log("getPeers - Empty response");
            }
        },
        error: function() {
            alert("Failed to get peers, url: " + url);
        }
    });
}

// Get runtime information from runtime with id "id"
function getPeer(id)
{
    var url = connect_uri + '/node/' + id;
    console.log("getPeer - url: " + url);
    $.ajax({
        timeout: 20000,
        beforeSend: function() {
            startSpin();
        },
        complete: function() {
            stopSpin();
        },
        dataType: 'json',
        url: url,
        type: 'GET',
        success: function(data) {
            if (data) {
                console.log("getPeer response: " + JSON.stringify(data));
                if (!findRuntime(id)) {
                    var peer = new runtimeObject(id);
                    peer.uri = data.uri;
                    peer.control_uri = data.control_uri;
                    peer.attributes = data.attributes;
                    if (peer.attributes.indexed_public) {
                        for (attribute in peer.attributes.indexed_public) {
                            if (peer.attributes.indexed_public[attribute].indexOf("node_name") != -1) {
                                var res = peer.attributes.indexed_public[attribute].split("/");
                                peer.name = res[res.length - 1];
                            }
                        }
                    }
                    if (!peer.name) {
                        peer.name = id;
                    }
                    peers[peers.length] = peer;
                    showPeer(peer);
                    getPeers(peer);
                }
            } else {
                console.log("getPeer - Empty response");
            }
        },
        error: function() {
            alert("Failed to get peer, url: " + url);
        }
    });
}

// Get applications from all runtimes
function getApplications()
{
    console.log("getApplications");
    clearTable(document.getElementById("applicationsTable"));
    clearTable(document.getElementById("actorsTable"));
    clearTable(document.getElementById("actorPortsTable"));
    clearTable(document.getElementById("actorPortFifoTable"));
    clearCombo(document.getElementById("actorSelector"));
    clearCombo(document.getElementById("portSelector"));
    var applicationSelector = document.getElementById("applicationSelector")
    clearCombo(applicationSelector);
    clearCombo(traceApplicationSelector);
    applicationSelector.options.add(new Option(""));
    traceApplicationSelector.options.add(new Option("All"));
    clearApplicationGraph();
    applications = [];
    actors = [];
    var index;
    for (index in peers) {
        url = peers[index].control_uri + '/applications';
        $.ajax({
            uri: peers[index].control_uri,
            timeout: 20000,
            beforeSend: function() {
                startSpin();
            },
            complete: function() {
                stopSpin();
            },
            dataType: 'json',
            url: url,
            type: 'GET',
            success: function(data) {
                if (data) {
                    console.log("getApplications - Response: " + JSON.stringify(data));
                    var index_application;
                    for (index_application in data) {
                        getApplication(this.uri, data[index_application]);
                    }
                } else {
                    console.log("getApplication - Empty result");
                }
            },
            error: function() {
                alert("Failed to get applications, url: " + url);
            }
        });
    }
}

// Get application with id "id"
function getApplication(uri, id)
{
    var url = uri + '/application/' + id;
    console.log("getApplication - url: " + url);
    $.ajax({
        uri: uri,
        timeout: 20000,
        beforeSend: function() {
            startSpin();
        },
        complete: function() {
            stopSpin();
        },
        dataType: 'json',
        url: url,
        type: 'GET',
        success: function(data) {
            if (data) {
                console.log("getApplication - Response: " + JSON.stringify(data));
                var application = findApplication(id);
                if (!application) {
                    application = new applicationObject(id);
                    applications[applications.length] = application;
                }
                application.name = data.name;
                application.actors = data.actors;
                application.control_uri = this.uri;
                var applicationSelector = document.getElementById("applicationSelector");
                var optionApplication = new Option(application.name);
                optionApplication.id =  application.id;
                applicationSelector.options.add(optionApplication);
                sortCombo(applicationSelector);

                applicationSelector = document.getElementById("traceApplicationSelector");
                optionApplication = new Option(application.name);
                optionApplication.id =  application.id;
                applicationSelector.options.add(optionApplication);
                sortCombo(applicationSelector);
            } else {
                console.log("getApplication - Empty response");
            }
        },
        error: function() {
            alert("Failed to get application, url: " + url);
        }
    });
}

// Get actor with id "id"
function getActor(id, show)
{
    var url = connect_uri + '/actor/' + id;
    console.log("getActor - url: " + url)
    $.ajax({
        timeout: 20000,
        beforeSend: function() {
            startSpin();
        },
        complete: function() {
            stopSpin();
        },
        dataType: 'json',
        url: url,
        type: 'GET',
        success: function(data) {
            if (data) {
                console.log("getActor - Response: " + JSON.stringify(data));
                var actor = findActor(id);
                if (!actor) {
                    actor = new actorObject(id);
                    actors[actors.length] = actor;
                }
                actor.id = id;
                actor.name = data.name;
                actor.type = data.type;
                actor.peer_id = data.node_id;
                actor.inports = [];
                actor.is_shadow = data.is_shadow;
                var index;
                for (index in data.inports) {
                    actor.inports[actor.inports.length] = data.inports[index].id;
                    getPort(id, data.inports[index].id);
                }
                actor.outports = [];
                for (index in data.outports) {
                    actor.outports[actor.outports.length] = data.outports[index].id;
                    getPort(id, data.outports[index].id);
                }

                if (show) {
                    showActor();
                } else {
                    var actorSelector = document.getElementById("actorSelector");
                    var optionActor = new Option(actor.name);
                    optionActor.id =  actor.id;
                    actorSelector.options.add(optionActor);
                    sortCombo(actorSelector);
                    addActorToGraph(actor);
                }
            } else {
                console.log("getActor - Empty response");
            }
        },
        error: function() {
            alert("Failed to get actor, url: " + url);
        }
    });
}

// Get port with id "port_id" on actor "actor_id" and draw application
function getPort(actor_id, port_id)
{
    var url = connect_uri + '/actor/' + actor_id + '/port/' + port_id;
    console.log("getPort - url: " + url);
    $.ajax({
        timeout: 20000,
        beforeSend: function() {
            startSpin();
        },
        complete: function() {
            stopSpin();
        },
        dataType: 'json',
        url: url,
        type: 'GET',
        success: function(data) {
            if (data) {
                console.log("getPort - Response: " + JSON.stringify(data));
                var port = new portObject(port_id);
                port.actor_id = data.actor_id;
                port.direction = data.direction;
                port.name = data.name;
                port.connected = data.connected;
                port.peer_id = data.node_id;
                port.peers = []
                if (port.direction == "out") {
                    var index;
                    for (index in data.peers) {
                        port.peers[port.peers.length] = data.peers[index];
                    }
                }
                if (port.direction == "in") {
                    port.peer = data.peer;
                }
                ports[ports.length] = port;

                addPortToGraph(port);
            } else {
                console.log("getPort - Empty response");
            }
        },
        error: function() {
            alert("Failed to get port, url: " + url);
        }
    });
}

// Get state of port with id "port_id"
function getPortState(port_id)
{
    var port = findPort(port_id);
    if (port) {
        var actor = findActor(port.actor_id);
        if (actor) {
            var runtime = findRuntime(actor.peer_id);
            if (runtime) {
                var url = runtime.control_uri + '/actor/' + port.actor_id + '/port/' + port_id + "/state";
                console.log("getPort - url: " + url);
                $.ajax({
                    timeout: 20000,
                    beforeSend: function() {
                        startSpin();
                    },
                    complete: function() {
                        stopSpin();
                    },
                    dataType: 'json',
                    url: url,
                    type: 'GET',
                    success: function(data) {
                        if (data) {
                            console.log("getPortState - Response: " + JSON.stringify(data));
                            var tableRef = document.getElementById('actorPortFifoTable');
                            clearTable(tableRef);

                            var fifos = data.fifo;
                            for (fifo in fifos) {
                                var fifo = fifos[fifo];
                                AddTableItem(tableRef, document.createTextNode(fifo.type), document.createTextNode(JSON.stringify(fifo.data)));
                            }
                        } else {
                            console.log("getPortState - Empty response");
                        }
                    },
                    error: function() {
                        alert("Failed to get port state, url: " + url);
                    }
                });
            }
        }
    }
}

// Helper for adding a table row with elements
function AddTableItem(tableRef, element1, element2, element3, element4, element5, element6)
{
    var row = tableRef.insertRow();
    if (element1) {
        var cell = row.insertCell(0);
        cell.appendChild(element1);
    }

    if (element2) {
        var cell = row.insertCell(1);
        cell.appendChild(element2);
    }

    if (element3) {
        var cell = row.insertCell(2);
        cell.appendChild(element3);
    }

    if (element4) {
        var cell = row.insertCell(3);
        cell.appendChild(element4);
    }

    if (element5) {
        var cell = row.insertCell(4);
        cell.appendChild(element5);
    }

    if (element6) {
        var cell = row.insertCell(5);
        cell.appendChild(element6);
    }

    return row;
}

// Add "peer" to peersTable
function showPeer(peer)
{
    var tableRef = document.getElementById('peersTable');

    var btnDestroy = document.createElement('input');
    btnDestroy.type = 'button';
    btnDestroy.className = "btn btn-danger btn-xs";
    btnDestroy.id = peer.id;
    btnDestroy.value = 'Destroy';
    btnDestroy.setAttribute("onclick", "destroyPeer(this.id)");

    var btnDeploy = document.createElement('input');
    btnDeploy.type = 'button';
    btnDeploy.className = "btn btn-primary btn-xs";
    btnDeploy.id = peer.id;
    btnDeploy.value = 'Deploy...';
    btnDeploy.setAttribute("onclick", "showDeployApplication(this.id)");

    var row = AddTableItem(tableRef, document.createTextNode(peer.id), document.createTextNode(peer.name), document.createTextNode(peer.uri), document.createTextNode(peer.control_uri), btnDestroy, btnDeploy);
    row.id = peer.id;
    row.setAttribute("onclick", "showPeerAttributes(this.id); showPeerConnections(this.id); $(this).toggleClass(\"active\"); $(this).siblings().removeClass(\"active\");");
}

// Update peerTable with attributes from runtime with id "peer_id"
function showPeerAttributes(peer_id)
{
    var peer = findRuntime(peer_id);
    if (peer) {
        var tableRef = document.getElementById('peerTable');
        clearTable(tableRef);
        if (peer.attributes.indexed_public) {
            for (attribute in peer.attributes.indexed_public) {
                AddTableItem(tableRef, document.createTextNode("Indexed public"), document.createTextNode(peer.attributes.indexed_public[attribute]));
            }
        }

        if (peer.attributes.public) {
            for (attribute in peer.attributes.public) {
                AddTableItem(tableRef, document.createTextNode("Public"), document.createTextNode(peer.attributes.public[attribute]));
            }
        }
    }
}

// Update connectionsTable with attributes from runtime with id "peer_id"
function showPeerConnections(peer_id)
{
    var runtime = findRuntime(peer_id);
    if (runtime) {
        var tableRef = document.getElementById('connectionsTable');
        clearTable(tableRef);
        if (runtime.peers) {
            for (connection in runtime.peers) {
                var peer = findRuntime(runtime.peers[connection]);
                if (peer) {
                    AddTableItem(tableRef, document.createTextNode(peer.name));
                } else {
                    AddTableItem(tableRef, document.createTextNode(runtime.peers[connection]));
                }
            }
        }
    }
}

// Add "application" to applicationsTable
function showApplication()
{
    var selectedIndex = document.getElementById("applicationSelector").selectedIndex;
    var selectOptions = document.getElementById("applicationSelector").options;
    var applicationID = selectOptions[selectedIndex].id;
    var tableRef = document.getElementById('applicationsTable');
    clearTable(tableRef);
    var actorSelector = document.getElementById('actorSelector')
    clearCombo(actorSelector);
    actorSelector.options.add(new Option(""));
    clearTable(document.getElementById('actorsTable'));
    clearTable(document.getElementById("actorPortsTable"));
    clearTable(document.getElementById("actorPortFifoTable"));
    clearCombo(document.getElementById("portSelector"));
    clearApplicationGraph();
    stopGraphEvents();

    var application = findApplication(applicationID);
    if (application) {
        //Name
        AddTableItem(tableRef, document.createTextNode("Name"), document.createTextNode(application.name));

        // ID
        AddTableItem(tableRef, document.createTextNode("ID"), document.createTextNode(application.id));

        // Destroy
        var btnDestroy = document.createElement('input');
        btnDestroy.type = 'button';
        btnDestroy.className = "btn btn-danger btn-xs";
        btnDestroy.id = application.id;
        btnDestroy.value = 'Destroy';
        btnDestroy.setAttribute("onclick", "destroyApplication(this.id)");
        AddTableItem(tableRef, document.createTextNode("Destroy"), btnDestroy);

        var index;
        for (index in application.actors) {
            getActor(application.actors[index], false);
        }
        startGraphEvents(application);
    }
}

// Update selected actor
function updateSelectedActor()
{
    var selectedIndex = document.getElementById("actorSelector").selectedIndex;
    var selectOptions = document.getElementById("actorSelector").options;
    var actorID = selectOptions[selectedIndex].id;
    if (actorID) {
        getActor(actorID, true);
    }
}

// Add "actor" to actorsTable
function showActor()
{
    var selectedIndex = document.getElementById("actorSelector").selectedIndex;
    var selectOptions = document.getElementById("actorSelector").options;
    var actorID = selectOptions[selectedIndex].id;

    var tableRef = document.getElementById('actorsTable');
    clearTable(tableRef);
    clearCombo(document.getElementById("portSelector"));
    clearTable(document.getElementById("actorPortsTable"));
    clearTable(document.getElementById("actorPortFifoTable"));

    var actor = findActor(actorID);
    if (actor) {
        //Name
        AddTableItem(tableRef, document.createTextNode("Name"), document.createTextNode(actor.name));

        // ID
        AddTableItem(tableRef, document.createTextNode("ID"), document.createTextNode(actor.id));

        // Actor type
        AddTableItem(tableRef, document.createTextNode("Type"), document.createTextNode(actor.type));

        // ID
        var runtime = findRuntime(actor.peer_id);
        AddTableItem(tableRef, document.createTextNode("Runtime"), document.createTextNode(runtime.name));

        // Shadow
        AddTableItem(tableRef, document.createTextNode("Shadow"), document.createTextNode(actor.is_shadow));

        // Migrate
        var selectNode = document.createElement("select");
        selectNode.id = "selectRuntime";
        var index;
        for (index in peers) {
            if (peers[index].id != actor.peer_id) {
                var optionPeer = new Option(peers[index].name);
                optionPeer.id = peers[index].id;
                selectNode.options.add(optionPeer);
                sortCombo(selectNode);
            }
        }
        var btnMigrate = document.createElement('input');
        btnMigrate.type = 'button';
        btnMigrate.className = "btn btn-primary btn-xs";
        btnMigrate.id = actor.id;
        btnMigrate.value = 'Migrate';
        btnMigrate.setAttribute("onclick", "migrate(this.id)");
        AddTableItem(tableRef, selectNode, btnMigrate);

        // Add ports
        var portSelector = document.getElementById("portSelector");
        clearCombo(portSelector);
        portSelector.options.add(new Option(""));

        var index;
        for (index in actor.inports) {
            var port = findPort(actor.inports[index]);
            if (port) {
                var optionPort = new Option(port.name);
                optionPort.id =  port.id;
                portSelector.options.add(optionPort);
                sortCombo(portSelector);
            }
        }
        for (index in actor.outports) {
            var port = findPort(actor.outports[index]);
            if (port) {
                var optionPort = new Option(port.name);
                optionPort.id =  port.id;
                portSelector.options.add(optionPort);
                sortCombo(portSelector);
            }
        }
    }
}

// update actorPortsTable
function showPort()
{
    var selectedIndex = document.getElementById("portSelector").selectedIndex;
    var selectOptions = document.getElementById("portSelector").options;
    var portID = selectOptions[selectedIndex].id;

    var tableRef = document.getElementById("actorPortsTable");
    clearTable(tableRef);
    clearTable(document.getElementById("actorPortFifoTable"));

    var port = findPort(portID);
    if (port) {
        // Port name
        AddTableItem(tableRef, document.createTextNode("Name"), document.createTextNode(port.name));

        // Port id
        AddTableItem(tableRef, document.createTextNode("ID"), document.createTextNode(port.id));

        // Direction
        AddTableItem(tableRef, document.createTextNode("Direction"), document.createTextNode(port.direction));

        // Connected
        AddTableItem(tableRef, document.createTextNode("Connected"), document.createTextNode(port.connected));

        // Get fifo
        var btnFifo = document.createElement('input');
        btnFifo.type = 'button';
        btnFifo.className = "btn btn-primary btn-xs";
        btnFifo.id = port.id;
        btnFifo.value = 'Get fifo...';
        btnFifo.setAttribute("onclick", "getPortState(this.id)");
        AddTableItem(tableRef, document.createTextNode("Fifo"), btnFifo);
    }
}

// Migrate actor with "actor_id" to selected runtime in combobox in actorsTable
function migrate(actor_id)
{
    var combo = document.getElementById('selectRuntime');
    var peer_id = combo.options[combo.selectedIndex].id;
    var actor = findActor(actor_id);
    if (actor) {
        var node = findRuntime(actor.peer_id);
        if (node) {
            var url = node.control_uri + '/actor/' + actor.id + '/migrate';
            var data = JSON.stringify({'peer_node_id': peer_id});
            console.log("migrate - url: " + url + " data: " + data);
            $.ajax({
                timeout: 5000,
                beforeSend: function() {
                    startSpin();
                },
                complete: function() {
                    stopSpin();
                },
                url: url,
                type: 'POST',
                data: data,
                success: function() {
                    getActor(actor_id, true);
                },
                error: function() {
                    console.log("Failed to migrate");
                }
            });
        } else {
            console.log("migrate - No node with id: " + actor.peer_id);
        }
    }
}

// Destroy application with "application_id"
function destroyApplication(application_id)
{
    var application = findApplication(application_id);
    if (application) {
        var url = application.control_uri + '/application/' + application_id
        console.log("destroyApplication url: " + url)
        $.ajax({
            timeout: 20000,
            beforeSend: function() {
                startSpin();
            },
            complete: function() {
                stopSpin();
            },
            url: url,
            type: 'DELETE',
            success: function() {
                getApplications();
            },
            error: function() {
                alert("Failed to destroy application");
            }
        });
    } else {
        console.log("destroyApplication - No application with id: " + application_id);
    }
}

// Destroy runtime with id "peer_id"
function destroyPeer(peer_id)
{
    var peer = findRuntime(peer_id);
    if (peer) {
        var url = peer.control_uri + '/node';
        console.log("destroyPeer url: " + url);

        if (peer.source != null) {
            peer.source.removeEventListener("message", eventHandler, false);
        }

        $.ajax({
            timeout: 20000,
            beforeSend: function() {
                startSpin();
            },
            complete: function() {
                stopSpin();
            },
            url: url,
            type: 'DELETE',
            success: function() {
                var tableRef = document.getElementById('peersTable');
                for (var x = 0; x < tableRef.rows.length; x++) {
                    if (tableRef.rows[x].cells[0].innerHTML == peer_id) {
                        tableRef.deleteRow(x);
                        return;
                    }
                }
            },
            error: function() {
                alert("Failed to destroy peer");
            }
        });
    } else {
        console.log("destroyPeer - No peer with id: " + peer_id);
    }
}

// Enable/disable draw connections checkbox
function toggleDrawConnections()
{
    if (document.getElementById("chkDrawApplication").checked) {
        document.getElementById("chkDrawConnections").disabled = false;
        document.getElementById("chkShowPortNames").disabled = false;
    } else {
        document.getElementById("chkDrawConnections").disabled = true;
        document.getElementById("chkShowPortNames").disabled = true;
    }
}

// Enable/disable action result checkbox
function toggleActionResult()
{
    if (document.getElementById("chkTraceActorFiring").checked) {
        document.getElementById("chkTraceActorFiringActionResult").disabled = false;
    } else {
        document.getElementById("chkTraceActorFiringActionResult").disabled = true;
    }
}

// Show trace dialog
function startLog()
{
    getApplications();
    $("#traceDialog").modal({
        modal: true,
        show: true,
        width: 300,
        height: 300,
    });
}

function startTrace() {
    var actors = [];
    var events = [];
    var selectedIndex = document.getElementById("traceApplicationSelector").selectedIndex;
    if (selectedIndex != 0) {
        var selectOptions = document.getElementById("traceApplicationSelector").options;
        var application_id = selectOptions[selectedIndex].id;
        var application = findApplication(application_id);
        if (application) {
            actors = application.actors;
        }
    }

    if (document.getElementById("chkTraceActorFiring").checked) {
        events.push("actor_firing");
    }
    if (document.getElementById("chkTraceActorFiringActionResult").checked) {
        events.push("action_result");
    }
    if (document.getElementById("chkTraceActorNew").checked) {
        events.push("actor_new");
    }
    if (document.getElementById("chkTraceActorDestroy").checked) {
        events.push("actor_destroy");
    }
    if (document.getElementById("chkTraceActorMigrate").checked) {
        events.push("actor_migrate");
    }
    if (document.getElementById("chkTraceApplicationNew").checked) {
        events.push("application_new");
    }
    if (document.getElementById("chkTraceApplicationDestroy").checked) {
        events.push("application_destroy");
    }

    $("#traceDialog").modal('hide');
    for (var index in peers) {
        if (peers[index].source) {
            alert("Trace already started on runtime" + peers[index].id);
        } else {
            var url = peers[index].control_uri + '/log';
            var data = JSON.stringify({'actors': actors, 'events': events});
            console.log("startLog - url: " + url + " data: " + data);
            $.ajax({
                peer: peers[index],
                timeout: 20000,
                beforeSend: function() {
                    startSpin();
                },
                complete: function() {
                    stopSpin();
                },
                url: url,
                type: 'POST',
                data: data,
                success: function(data) {
                    if(data) {
                        console.log("startLog - data: " + JSON.stringify(data));
                        this.peer.user_id = data.user_id;
                        this.peer.source = new EventSource(this.peer.control_uri + '/log/' + this.peer.user_id);
                        this.peer.source.addEventListener("message", eventHandler, false);
                    } else {
                        console.log("startLog - Empty response");
                    }
                },
                error: function() {
                    console.log("startLog - Failed, url: " + url);
                }
            });
        }
    }
}

// Stop trace
function stopLog()
{
    for (var index in peers) {
        var url = peers[index].control_uri + '/log/' + peers[index].user_id;
        console.log("stopLog url: " + url);
        $.ajax({
            timeout: 20000,
            beforeSend: function() {
                startSpin();
            },
            complete: function() {
                stopSpin();
            },
            url: url,
            type: 'DELETE',
            success: function() {
            },
            error: function() {
                alert("stopLog - Failed, url: " + url);
            }
        });
        if (peers[index].source) {
            peers[index].source.removeEventListener("message", eventHandler, false);
            peers[index].source.close();
            peers[index].source = null;
        }
    }
}

// Clear log table
function clearLog() {
    var tableRef = document.getElementById('logTable');
    for(var i = 1; i < tableRef.rows.length;) {
       tableRef.deleteRow(i);
    }
}

// Event handler for log data
function eventHandler(event)
{
    var trace_size = $("#trace_size").val();
    var data = JSON.parse(event.data);
    var tableRef = document.getElementById('logTable');
    if (tableRef.rows.length > trace_size) {
        tableRef.deleteRow(tableRef.rows.length -1);
    }
    var newRow = tableRef.insertRow(1);
    var cell0 = newRow.insertCell(0);
    var cell1 = newRow.insertCell(1);
    var cell2 = newRow.insertCell(2);
    var cell3 = newRow.insertCell(3);
    var cell4 = newRow.insertCell(4);
    var cell5 = newRow.insertCell(5);
    var cell6 = newRow.insertCell(6);
    var cell7 = newRow.insertCell(7);
    var cell8 = newRow.insertCell(8);

    cell0.appendChild(document.createTextNode(new Date().toISOString())); // Clocks not synchronized, use clients time
    cell1.appendChild(document.createTextNode(data.node_id));
    cell2.appendChild(document.createTextNode(data.type));
    if (data.type == "actor_fire") {
        var actor_name = "";
        var actor = findActor(data.actor_id);
        if (actor) {
            actor_name = actor.name;
        }
        cell3.appendChild(document.createTextNode(data.actor_id));
        cell4.appendChild(document.createTextNode(actor_name));
        cell5.appendChild(document.createTextNode(data.action_method));
        cell6.appendChild(document.createTextNode(data.consumed));
        cell7.appendChild(document.createTextNode(data.produced));
        if (data.action_result) {
            cell8.appendChild(document.createTextNode(data.action_result));
        }
    } else if(data.type == "actor_new") {
        var actor = findActor(data.actor);
        if (!actor) {
            actor = new actorObject(data.actor);
            actors[actors.length] = actor;
        }
        actor.id = data.actor_id;
        actor.name = data.actor_name;
        actor.type = data.actor_type;
        actor.is_shadow = data.is_shadow;
        cell3.appendChild(document.createTextNode(actor.id));
        cell4.appendChild(document.createTextNode(actor.name));
        cell5.appendChild(document.createTextNode(actor.type));
        cell6.appendChild(document.createTextNode(actor.is_shadow));
    } else if(data.type == "actor_destroy") {
        var actor_name = "";
        var actor = findActor(data.actor_id);
        if (actor) {
            actor_name = actor.name;
        }
        cell3.appendChild(document.createTextNode(data.actor_id));
        cell4.appendChild(document.createTextNode(actor_name));
    } else if(data.type == "actor_migrate") {
        var actor_name = "";
        var actor = findActor(data.actor_id);
        if (actor) {
            actor_name = actor.name;
        }
        cell3.appendChild(document.createTextNode(data.actor_id));
        cell4.appendChild(document.createTextNode(actor_name));
        cell5.appendChild(document.createTextNode(data.dest_node_id));
    } else if(data.type == "application_new") {
        cell3.appendChild(document.createTextNode(data.application_id));
        cell4.appendChild(document.createTextNode(data.application_name));
    } else if(data.type == "application_destroy") {
        cell3.appendChild(document.createTextNode(data.application_id));
    } else {
        console.log("eventHandler - Unknown event type:" + data.type);
    }
}

// Start event stream for graph
function startGraphEvents(application)
{
    var events = ["actor_new"];
    var actors = application.actors;
    for (var index in peers) {
        if (peers[index].graph_source) {
            alert("Graph trace already started on runtime" + peers[index].name);
        } else {
            var url = peers[index].control_uri + '/log';
            var data = JSON.stringify({'actors': actors, 'events': events});
            console.log("startGraphEvents - url: " + url + " data: " + data);
            $.ajax({
                peer: peers[index],
                timeout: 5000,
                beforeSend: function() {
                    startSpin();
                },
                complete: function() {
                    stopSpin();
                },
                url: url,
                type: 'POST',
                data: data,
                success: function(data) {
                    if(data) {
                        console.log("startGraphEvents - data: " + JSON.stringify(data));
                        this.peer.graph_user_id = data.user_id;
                        this.peer.graph_source = new EventSource(this.peer.control_uri + '/log/' + data.user_id);
                        this.peer.graph_source.addEventListener("message", graphEventHandler, false);
                    } else {
                        console.log("startGraphEvents - Empty response");
                    }
                },
                error: function() {
                    console.log("startGraphEvents - Failed, url: " + url);
                }
            });
        }
    }
}

// Stop event stream for graph
function stopGraphEvents()
{
    for (var index in peers) {
        if (peers[index].graph_source && peers[index].graph_user_id) {
            var url = peers[index].control_uri + '/log/' + peers[index].graph_user_id;
            console.log("stopGraphEvents url: " + url);
            $.ajax({
                timeout: 5000,
                beforeSend: function() {
                    startSpin();
                },
                complete: function() {
                    stopSpin();
                },
                url: url,
                type: 'DELETE',
                success: function() {
                },
                error: function() {
                    alert("stopGraphEvents - Failed, url: " + url);
                }
            });

            peers[index].graph_source.removeEventListener("message", graphEventHandler, false);
            peers[index].graph_source.close();
            peers[index].graph_source = null;
        }
    }
}

// Event handler for log data
function graphEventHandler(event)
{
    console.log("graphEventHandler" + event.data);
    var data = JSON.parse(event.data);
    if(data.type == "actor_new") {
        var actor = findActor(data.actor_id);
        if (actor) {
            actor.peer_id = data.node_id;
            actor.is_shadow = data.is_shadow;
            addActorToGraph(actor);
        }
    } else {
        console.log("graphEventHandler - Unknown event type:" + data.type);
    }
}

// Show dialog for deploying application on "peer_id"
function showDeployApplication(peer_id)
{
    var peer = findRuntime(peer_id);
    if (peer) {
        $("#deployDialog").modal({
            modal: true,
            width: 800,
            height: 800,
        });
        $("#deployDialog").modal.peer = peer;
        $("#deployDialog").modal({
            show: true,
        });
    }
}

function deployHandler() {
    var peer = $("#deployDialog").modal.peer;
    var script = $("#deploy_script").val();
    var name = $("#script_name").val();
    var reqs = $("#migrate_reqs").val();
    deployApplication(peer.control_uri, script, reqs, name);
    $("#deployDialog").modal('close');
}

// Deploy application with "script" and "name" to runtime with "uri"
function deployApplication(uri, script, reqs, name)
{
    var url = uri + '/deploy';
    var data;
    if (reqs) {
        var requirements = JSON.parse(reqs);
        data = JSON.stringify({'script': script, 'deploy_info': requirements, 'name': name});
    } else {
        data = JSON.stringify({'script': script, 'name': name});
    }
    console.log("deployApplication url: " + url + " data: " + data);
    $.ajax({
        timeout: 20000,
        beforeSend: function() {
            startSpin();
        },
        complete: function() {
            stopSpin();
        },
        url: url,
        type: 'POST',
        data: data,
        success: function(data) {
            console.log("deployApplication - Success");
        },
        error: function() {
            alert("Failed to deploy application, url: " + url + " data: " + data);
        }
    });
}

jQuery(document).ready(function() {
    connect();

    // handle file select in deploy app
    var fileInputDeploy = document.getElementById('fileInputDeploy');
    var fileDisplayDeploy = document.getElementById('deploy_script');
    fileInputDeploy.addEventListener('change', function(e) {
        var file = fileInputDeploy.files[0];
        var reader = new FileReader();
        document.getElementById('script_name').value = file.name.split(".")[0];

        reader.onload = function(e) {
            fileDisplayDeploy.innerHTML = e.target.result;
        }

        reader.readAsText(file);
    });

    // handle file select in migrate application
    var fileInputMigrate = document.getElementById('fileInputMigrateApplication');
    var fileDisplayMigrate = document.getElementById('migrate_reqs');
    fileInputMigrate.addEventListener('change', function(e) {
        var file = fileInputMigrate.files[0];
        var reader = new FileReader();

        reader.onload = function(e) {
            fileDisplayMigrate.innerHTML = e.target.result;
        }

        reader.readAsText(file);
    });

    // handle tabbed view
    jQuery('.tabs .tab-links a').on('click', function(e)  {
        var currentAttrValue = jQuery(this).attr('href');

        if (currentAttrValue == "#tabApplications") {
            getApplications();
        } else {
            stopGraphEvents();
        }

        // Show/Hide Tabs
        jQuery('.tabs ' + currentAttrValue).show().siblings().hide();

        // Change/remove current tab to active
        jQuery(this).parent('li').addClass('active').siblings().removeClass('active');

        e.preventDefault();
    });
});
