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
var svgGroup = svg.append("g");
var graphTimer = null;
var color = d3.scale.category20();

var findNode = function (nodes, id)
{
    for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].id === id)
            return nodes[i];
    }
}

function drawConnections()
{
    var nodes = [];
    var links = [];

    document.getElementById("connectionsGraph").innerHTML = "";

    var width = 800,
        height = 600;

    var svg_con = d3.select("#connectionsGraph").append("svg")
        .attr("width", width)
        .attr("height", height);

    var force = d3.layout.force()
        .charge(-120)
        .linkDistance(100)
        .size([width, height]);

    var index_peer;
    for (index_peer in peers) {
        var source = {id:peers[index_peer].id, name:peers[index_peer].node_name.name};
        nodes.push(source);
    }

    for (index_peer in peers) {
        var source = findNode(nodes, peers[index_peer].id);
        if (source) {
            var index_connection;
            for (index_connection in peers[index_peer].peers) {
                var dest = findNode(nodes, peers[index_peer].peers[index_connection]);
                if (dest) {
                    links.push({source:source, target:dest});
                }
            }
        }
    }

    force
        .nodes(nodes)
        .links(links)
        .start();

    var link = svg_con.selectAll(".link")
            .data(force.links())
        .enter().append("line")
            .attr("class", "link")
            .style("stroke-width", function(d) { return 2; });

    var gnodes = svg_con.selectAll('g.gnode')
        .data(nodes)
        .enter()
        .append('g')
        .classed('gnode', true);

    var node = gnodes.append("circle")
        .attr("class", "node")
        .attr("r", 10)
        .style("fill", function(d) { return color("#aec7e8"); })
        .call(force.drag);

    var labels = gnodes.append("text")
        .attr("x", 10)
        .attr("y", ".31em")
        .style("font-size", "15px")
        .text(function(d) { return d.name; });

    force.on("tick", function() {
        link.attr("x1", function(d) { return d.source.x; })
            .attr("y1", function(d) { return d.source.y; })
            .attr("x2", function(d) { return d.target.x; })
            .attr("y2", function(d) { return d.target.y; });

        gnodes.attr("transform", function(d) {
            return 'translate(' + [d.x, d.y] + ')';
        });
    });
};

// Show dialog for setting requirements
function showMessage(message)
{
    $("#show_message_body").html(message);
    $("#messageDialog").modal({
        modal: true,
        show: true
    });
}

function showAlert(message, type, delay)
{
    var alert = $('<div class="alert alert-' + type + ' fade in">')
        .append(
            $('<button type="button" class="close" data-dismiss="alert">')
            .append("&times;")
        )
        .append(message);

    $("#alerts-container").prepend(alert);

    if (delay) {
        window.setTimeout(function() { alert.alert("close") }, delay);
    }
}

function showError(message)
{
    showAlert(message, "danger", 10000);
}

function showSuccess(message)
{
    showAlert(message, "success", 5000);
}

function showInfo(message)
{
    showAlert(message, "info", 5000);
}

function addActorToGraph(actor)
{
    if (document.getElementById("chkDrawApplication").checked) {
        if (graphTimer) {
            clearTimeout(graphTimer);
        }

        for (var index in peers) {
            if (peers[index].id == actor.peer_id) {
                graph.setNode(peers[index].id, {
                    label: peers[index].node_name.name,
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

function removeActorFromGraph(actor)
{
    if (document.getElementById("chkDrawApplication").checked) {
        if (graphTimer) {
            clearTimeout(graphTimer);
        }

        graph.removeNode(actor.id);

        graphTimer = setTimeout(updateGraph, 1000);
    }
}

function addPortToGraph(port)
{
    if (document.getElementById("chkDrawApplication").checked && document.getElementById("chkDrawConnections").checked) {
        if (graphTimer) {
            clearTimeout(graphTimer);
        }

        var peer_index = 0;
        for (peer_index in port.peers) {
            var peer_port = findPort(port.peers[peer_index][1]);
            if (peer_port) {
                if (graphTimer) {
                    clearTimeout(graphTimer);
                }
                if (port.direction == "out") {
                    if(document.getElementById("chkShowPortNames").checked) {
                        graph.setEdge(port.actor_id, peer_port.actor_id, {label: port.name + " > " + peer_port.name});
                    } else {
                        graph.setEdge(port.actor_id, peer_port.actor_id);
                    }
                } else {
                    if(document.getElementById("chkShowPortNames").checked) {
                        graph.setEdge(peer_port.actor_id, port.actor_id, {label: peer_port.name + " > " + port.name});
                    } else {
                        graph.setEdge(peer_port.actor_id, port.actor_id);
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

    svg.attr("width", 1000);
    svg.attr("height", 600);
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
    svg.attr("width", 1000);
    svg.attr("height", 600);
}

// Runtime object constructor function
function runtimeObject(id)
{
    this.id = id;
    this.actors = [];
    this.source = null;
    this.peers = [];
    this.node_name = {};
    this.address = {};
    this.owner = {};
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

function popRuntime(id)
{
    var index;
    for (index in peers) {
        if (peers[index].id == id) {
            return peers.splice(index, 1)[0];
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

// Return actor from id and remove it
function popActor(id)
{
    var index;
    for (index in actors) {
        if (actors[index].id == id) {
            return actors.splice(index, 1)[0];
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
    for (var index in peers) {
        if (peers[index].source) {
            peers[index].source.removeEventListener("message", eventHandler, false);
            peers[index].source.close();
        }

        if (peers[index].graph_source && peers[index].graph_user_id) {
            peers[index].graph_source.removeEventListener("message", graphEventHandler, false);
            peers[index].graph_source.close();
        }
    }

    clearLog();

    peers = [];
    applications = [];
    actors = [];
    ports = [];

    var tableRef = document.getElementById("peersTable");
    for(var i = 1; i < tableRef.rows.length;) {
       tableRef.deleteRow(i);
    }

    var uri = getCookie("calvin_uri");

    document.getElementById("connect_uri").value = uri;

    $("#connectDialog").modal({
        modal: true,
        show: true,
    });
}

function connectHandler()
{
    connect_uri = $("#connect_uri").val();
    document.cookie="calvin_uri=" + connect_uri;
    getPeerID();
    if ($('#chk_get_all_runtimes').is(':checked')) {
        getPeersFromIndex("/node/attribute/node_name");
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
            showError("Failed to get node id, url: " + url);
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
            console.log("Failed to get peers from index, url: " + url);
        }
    });
}

// Get connected peers
function getPeers(peer)
{
    if (peer.control_uris) {
        var url = peer.control_uris[0] + '/nodes';
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
                console.log("Failed to get peers, url: " + url);
            }
        });
    }
}

function updatePeers()
{
    for (var index in peers) {
        getPeer(peers[index].id);
    }
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
                var peer = findRuntime(id);
                if (!peer) {
                    peer = new runtimeObject(id);
                    peers[peers.length] = peer;
                }
                if (data.uris) {
                    peer.uris = data.uris;
                } else {
                    peer.uris = "";
                }
                if (data.control_uris) {
                    peer.control_uris = data.control_uris;
                } else {
                    peer.control_uris = "";
                }
                if (data.proxy) {
                    peer.proxy = data.proxy;
                } else {
                    peer.proxy = "";
                }
                if (data.sleeping) {
                    peer.sleeping = data.sleeping;
                } else {
                    peer.sleeping = false;
                }
                peer.attributes = data.attributes;
                if (peer.attributes.indexed_public) {
                    for (attribute in peer.attributes.indexed_public) {
                        if (peer.attributes.indexed_public[attribute].indexOf("node_name") != -1) {
                            var res = peer.attributes.indexed_public[attribute].split("/");
                            if (res.length > 4) {
                                if (res[res.length - 5])
                                    peer.node_name.organization = res[res.length - 5];
                                if (res[res.length - 4])
                                    peer.node_name.organizationalUnit = res[res.length - 4];
                                if (res[res.length - 3])
                                    peer.node_name.purpose = res[res.length - 3];
                                if (res[res.length - 2])
                                    peer.node_name.group = res[res.length - 2];
                                if (res[res.length - 1])
                                    peer.node_name.name = res[res.length - 1];
                            }
                        } else if (peer.attributes.indexed_public[attribute].indexOf("address") != -1) {
                            var res = peer.attributes.indexed_public[attribute].split("/");
                            if (res.length > 4) {
                                if (res[res.length - 8])
                                    peer.address.country = res[res.length - 8];
                                if (res[res.length - 7])
                                    peer.address.stateOrProvince = res[res.length - 7];
                                if (res[res.length - 6])
                                    peer.address.locality = res[res.length - 6];
                                if (res[res.length - 5])
                                    peer.address.street = res[res.length - 5];
                                if (res[res.length - 4])
                                    peer.address.streetNumber = res[res.length - 4];
                                if (res[res.length - 3])
                                    peer.address.building = res[res.length - 3];
                                if (res[res.length - 2])
                                    peer.address.floor = res[res.length - 2];
                                if (res[res.length - 1])
                                    peer.address.room = res[res.length - 1];
                            }
                        } if (peer.attributes.indexed_public[attribute].indexOf("owner") != -1) {
                            var res = peer.attributes.indexed_public[attribute].split("/");
                            if (res.length > 4) {
                                if (res[res.length - 4])
                                    peer.owner.organization = res[res.length - 4];
                                if (res[res.length - 3])
                                    peer.owner.organizationalUnit = res[res.length - 3];
                                if (res[res.length - 2])
                                    peer.owner.role = res[res.length - 2];
                                if (res[res.length - 1])
                                    peer.owner.personOrGroup = res[res.length - 1];
                            }
                        }
                    }
                }
                if (!peer.node_name.name) {
                    peer.node_name.name = id;
                }
                showPeer(peer);
                getPeers(peer);
            } else {
                console.log("getPeer - Empty response");
            }
        },
        error: function() {
            // If we don't find the runtime in storage remove it
            popRuntime(id)
            var tableRef = document.getElementById('peersTable');
            for (var x = 0; x < tableRef.rows.length; x++) {
                if (tableRef.rows[x].cells[0].innerHTML == id) {
                    tableRef.deleteRow(x);
                    break;
                }
            }
            showInfo("Ignore unfound peer, id: " + id);
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
        if (peers[index].control_uris) {
            url = peers[index].control_uris[0] + '/applications';
            $.ajax({
                uri: peers[index].control_uris[0],
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
                    // Remove the peer that we failed to contact
                    popRuntime(peers[index].id)
                    console.log("Failed to get applications, url: " + url);
                }
            });
        }
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
            showError("Failed to get application, url: " + url);
        }
    });
}

// Get actor with id "id"
function getActor(id, show, replicas, retries)
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
                if (replicas && "replication_master_id" in data && data.replication_master_id == actor.id) {
                    actor.master = true
                    actor.replication_id = data.replication_id
                    getReplicas(data.replication_id)
                } else {
                    actor.master = false
                }
            } else {
                console.log("getActor - Empty response");
            }
        },
        error: function() {
            showError("Failed to get actor, url: " + url);
            if (retries > 0) {
                getActor(id, show, replicas, retries - 1)
            }
        }
    });
}

// Get replicas for replication with id "id"
function getReplicas(id)
{
    var url = connect_uri + '/index/replicas/actors/' + id + '?root_prefix_level=3';
    console.log("getReplicas - url: " + url)
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
                console.log("getReplicas - Response: " + JSON.stringify(data));
                var index
                for (index in data.result) {
                    var actor_id = data.result[index]
                    getActor(actor_id, false, false, 0)
                }
            } else {
                console.log("getReplicas - Empty response");
            }
        },
        error: function() {
            showInfo("Failed to get replicas, url: " + url);
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
                port.name = data.name;
                port.connected = data.connected;
                port.peer_id = data.node_id;
                port.peers = []
                port.direction = data.properties.direction;
                var index = 0;
                for (index in data.peers) {
                    port.peers[port.peers.length] = data.peers[index];
                }
                port.routing = data.properties.routing;
                ports[ports.length] = port;

                addPortToGraph(port);
            } else {
                console.log("getPort - Empty response");
            }
        },
        error: function() {
            showError("Failed to get port, url: " + url);
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
            if (runtime && runtime.control_uris) {
                var url = runtime.control_uris[0] + '/actor/' + port.actor_id + '/port/' + port_id + "/state";
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
                        showError("Failed to get port state, url: " + url);
                    }
                });
            }
        }
    }
}

// Helper for adding a table row with elements
function AddTableItem(tableRef, element1, element2, element3, element4, element5, element6, element7, element8, element9, element10)
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

    if (element7) {
        var cell = row.insertCell(6);
        cell.appendChild(element7);
    }

    if (element8) {
        var cell = row.insertCell(7);
        cell.appendChild(element8);
    }

    if (element9) {
        var cell = row.insertCell(8);
        cell.appendChild(element9);
    }

    if (element10) {
        var cell = row.insertCell(9);
        cell.appendChild(element10);
    }

    return row;
}

function set_input(input, value)
{
    if (!value || value == undefined) {
        input.value = "";
    } else {
        input.value = value;
    }
}

function showRuntimeConfig(peer_id)
{
    var peer = findRuntime(peer_id);
    if (peer) {
        set_input(document.getElementById("conf_name_organization"), peer.node_name.organization);
        set_input(document.getElementById("conf_name_organizationalUnit"), peer.node_name.organizationalUnit);
        set_input(document.getElementById("conf_name_purpose"), peer.node_name.purpose);
        set_input(document.getElementById("conf_name_group"), peer.node_name.group);
        set_input(document.getElementById("conf_name_name"), peer.node_name.name);
        set_input(document.getElementById("conf_address_country"), peer.address.country);
        set_input(document.getElementById("conf_address_stateOrProvince"), peer.address.stateOrProvince);
        set_input(document.getElementById("conf_address_locality"), peer.address.locality);
        set_input(document.getElementById("conf_address_street"), peer.address.street);
        set_input(document.getElementById("conf_address_streetNumber"), peer.address.streetNumber);
        set_input(document.getElementById("conf_address_building"), peer.address.building);
        set_input(document.getElementById("conf_address_floor"), peer.address.floor);
        set_input(document.getElementById("conf_address_room"), peer.address.room);
        set_input(document.getElementById("conf_owner_organization"), peer.owner.organization);
        set_input(document.getElementById("conf_owner_organizationalUnit"), peer.owner.organizationalUnit);
        set_input(document.getElementById("conf_owner_role"), peer.owner.role);
        set_input(document.getElementById("conf_owner_personOrGroup"), peer.owner.personOrGroup);
        $("#configDialog").modal.peer = peer;
        $("#configDialog").modal({
            modal: true,
            show: true
        });
    }
}

function update_attribute_from_input(attribute, input)
{
    if (input.val() == undefined || input.val().length == 0) {
        if (attribute) {
            console.log(attribute);
            attribute = "";
            console.log(attribute);
        }
    } else {
        attribute = input.val();
    }

    return attribute;
}

function setRuntimeConfig()
{
    $("#configDialog").modal('hide');
    var peer = $("#configDialog").modal.peer;
    peer.node_name.organization = update_attribute_from_input(peer.node_name.organization, $("#conf_name_organization"));
    peer.node_name.organizationalUnit = update_attribute_from_input(peer.node_name.organizationalUnit, $("#conf_name_organizationalUnit"));
    peer.node_name.purpose = update_attribute_from_input(peer.node_name.purpose, $("#conf_name_purpose"));
    peer.node_name.group = update_attribute_from_input(peer.node_name.group, $("#conf_name_group"));
    peer.node_name.name = update_attribute_from_input(peer.node_name.name, $("#conf_name_name"));
    peer.address.country = update_attribute_from_input(peer.address.country, $("#conf_address_country"));
    peer.address.stateOrProvince = update_attribute_from_input(peer.address.organizationalUnit, $("#conf_address_stateOrProvince"));
    peer.address.locality = update_attribute_from_input(peer.address.locality, $("#conf_address_locality"));
    peer.address.street = update_attribute_from_input(peer.address.street, $("#conf_address_street"));
    peer.address.streetNumber = update_attribute_from_input(peer.address.streetNumber, $("#conf_address_streetNumber"));
    peer.address.building = update_attribute_from_input(peer.address.building, $("#conf_address_building"));
    peer.address.floor = update_attribute_from_input(peer.address.floor, $("#conf_address_floor"));
    peer.address.room = update_attribute_from_input(peer.address.room, $("#conf_address_room"));
    peer.owner.organization = update_attribute_from_input(peer.owner.organization, $("#conf_owner_organization"));
    peer.owner.organizationalUnit = update_attribute_from_input(peer.owner.organizationalUnit, $("#conf_owner_organizationalUnit"));
    peer.owner.role = update_attribute_from_input(peer.owner.role, $("#conf_owner_role"));
    peer.owner.personOrGroup = update_attribute_from_input(peer.owner.personOrGroup, $("#conf_owner_personOrGroup"));

    var url;
    if (peer.control_uris) {
        url = peer.control_uris[0] + '/node/' + peer.id + '/attributes/indexed_public';
    } else {
        url = connect_uri + '/node/' + peer.id + '/attributes/indexed_public';
    }

    var data = {};
    if (!$.isEmptyObject(peer.node_name))
        data['node_name'] = peer.node_name;
    if (!$.isEmptyObject(peer.address) > 0)
        data['address'] = peer.address;
    if (!$.isEmptyObject(peer.owner) > 0)
        data['owner'] = peer.owner;
    data = JSON.stringify(data);
    console.log("set runtime config - url: " + url + " data: " + data);
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
            showSuccess("Runtime " + peer.id + " updated");
            var tableRef = document.getElementById('peersTable');
            for (var x = 0; x < tableRef.rows.length; x++) {
                if (tableRef.rows[x].cells[0].innerHTML == peer.id) {
                    tableRef.rows[x].cells[1].innerHTML = peer.node_name.name;
                    return;
                }
            }
        },
        error: function() {
            showError("Failed to update runtime " + peer.id);
        }
    });
}

// Add "peer" to peersTable
function showPeer(peer)
{
    var row;
    var tableRef = document.getElementById('peersTable');

    for (var x = 0; x < tableRef.rows.length; x++) {
        if (tableRef.rows[x].cells[0].innerHTML == peer.id) {
            tableRef.rows[x].cells[1] = peer.node_name.name;
            return;
        }
    }

    var btnConfigure = document.createElement('input');
    btnConfigure.type = 'button';
    btnConfigure.className = "btn btn-primary btn-xs";
    btnConfigure.id = peer.id;
    btnConfigure.value = 'Configure...';
    btnConfigure.setAttribute("onclick", "showRuntimeConfig(this.id)");

    if (peer.control_uris) {
        var btnDestroy = document.createElement('input');
        btnDestroy.type = 'button';
        btnDestroy.className = "btn btn-danger btn-xs";
        btnDestroy.id = peer.id;
        btnDestroy.value = 'Destroy';
        btnDestroy.setAttribute("onclick", "destroyPeer(this.id)");

        var btnAbolish = document.createElement('input');
        btnAbolish.type = 'button';
        btnAbolish.className = "btn btn-danger btn-xs";
        btnAbolish.id = peer.id;
        btnAbolish.value = 'Abolish';
        btnAbolish.setAttribute("onclick", "destroyPeerByMethod(this.id, 'migrate')");

        var btnDeploy = document.createElement('input');
        btnDeploy.type = 'button';
        btnDeploy.className = "btn btn-primary btn-xs";
        btnDeploy.id = peer.id;
        btnDeploy.value = 'Deploy...';
        btnDeploy.setAttribute("onclick", "showDeployApplication(this.id)");

        row = AddTableItem(tableRef,
            document.createTextNode(peer.id),
            document.createTextNode(peer.node_name.name),
            document.createTextNode(peer.uris),
            document.createTextNode(peer.control_uris),
            document.createTextNode(peer.proxy),
            document.createTextNode(peer.sleeping),
            btnConfigure,
            btnDestroy,
            btnAbolish,
            btnDeploy);
    } else {
        row = AddTableItem(tableRef,
            document.createTextNode(peer.id),
            document.createTextNode(peer.node_name.name),
            document.createTextNode(peer.uris),
            document.createTextNode(peer.control_uris),
            document.createTextNode(peer.proxy),
            document.createTextNode(peer.sleeping),
            btnConfigure);
    }

    row.id = peer.id;
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

        // Set requirements
        var btnSetRequirements = document.createElement('input');
        btnSetRequirements.type = 'button';
        btnSetRequirements.className = "btn btn-primary btn-xs";
        btnSetRequirements.id = application.id;
        btnSetRequirements.value = 'Set requirements...';
        btnSetRequirements.setAttribute("onclick", "showSetRequirements(this.id)");
        AddTableItem(tableRef, document.createTextNode("Set requirements"), btnSetRequirements);

        var index;
        for (index in application.actors) {
            getActor(application.actors[index], false, true, 0);
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
        getActor(actorID, true, false, 0);
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
        AddTableItem(tableRef, document.createTextNode("Runtime"), document.createTextNode(runtime.node_name.name));

        // Shadow
        AddTableItem(tableRef, document.createTextNode("Shadow"), document.createTextNode(actor.is_shadow));

        // Migrate
        var selectNode = document.createElement("select");
        selectNode.id = "selectRuntime";
        var index;
        for (index in peers) {
            if (peers[index].id != actor.peer_id) {
                var optionPeer = new Option(peers[index].node_name.name);
                optionPeer.id = peers[index].id;
                selectNode.options.add(optionPeer);
                sortCombo(selectNode);
            } else {
                var optionPeer = new Option("Same");
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

        // FIXME now during testing we have manual control over replication, this will be removed later
        var btnReplicate = document.createElement('input');
        btnReplicate.type = 'button';
        btnReplicate.className = "btn btn-primary btn-xs";
        btnReplicate.id = actor.id;
        btnReplicate.value = 'Replicate';
        btnReplicate.setAttribute("onclick", "replicate(this.id)");

        // FIXME now during testing we have manual control over dereplication, this will be removed later
        var btnDereplicate = document.createElement('input');
        btnDereplicate.type = 'button';
        btnDereplicate.className = "btn btn-primary btn-xs";
        btnDereplicate.id = actor.id;
        btnDereplicate.value = 'Dereplicate';
        btnDereplicate.setAttribute("onclick", "dereplicate(this.id)");

        var row = tableRef.insertRow();
        var cell = row.insertCell(0);
        cell.appendChild(selectNode);
        var cell = row.insertCell(1);
        cell.appendChild(btnMigrate);
        cell.appendChild(btnReplicate);
        cell.appendChild(btnDereplicate);

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

        // Routing
        AddTableItem(tableRef, document.createTextNode("Routing"), document.createTextNode(port.routing));

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
        if (actor.peer_id == peer_id) {
            showError("Can't migrate to same node");
            return
        }
        var node = findRuntime(actor.peer_id);
        if (node) {
            if (node.control_uris) {
                var url = node.control_uris[0] + '/actor/' + actor.id + '/migrate';
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
                        getActor(actor_id, true, false, 0);
                        showSuccess("Actor " + actor_id + " migrated");
                    },
                    error: function() {
                        showError("Failed to migrate " + actor_id);
                    }
                });
            } else {
                showError("Node " + actor.peer_id + " has no control API");
            }
        } else {
            showError("Failed to migrate, no node with id: " + actor.peer_id);
        }
    }
}

// Replicate actor with "actor_id" to selected (or unselected) runtime in combobox in actorsTable
// FIXME now during testing we have manual control over replication, this will be removed later
function replicate(actor_id)
{
    var combo = document.getElementById('selectRuntime');
    try {
        var peer_id = combo.options[combo.selectedIndex].id;
    } catch(err) {
        var peer_id = "same";
    }
    var actor = findActor(actor_id);
    if (actor) {
        var node = findRuntime(actor.peer_id);
        if (node) {
            if (node.control_uris) {
                var url = node.control_uri[0] + '/actor/' + actor.id + '/replicate';
                if (peer_id == "same") {
                    var data = JSON.stringify({});
                } else {
                    var data = JSON.stringify({'peer_node_id': peer_id});
                }
                console.log("replicate - url: " + url + " data: " + data);
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
                    success: function(data) {
                        showSuccess("Actor " + actor.name +"("+ actor_id +")" + " replicated as " + data['actor_id']);
                    },
                    error: function() {
                        showError("Failed to replicate " + actor.name +"("+ actor_id +")");
                    }
                });
            } else {
                showError("Node " + actor.peer_id + " has no control API");
            }
        } else {
            showError("Failed to replicate, no node with id: " + actor.peer_id);
        }
    }
}

// Dereplicate actor with "actor_id"
// FIXME now during testing we have manual control over replication, this will be removed later
function dereplicate(actor_id)
{
    var actor = findActor(actor_id);
    if (actor) {
        var node = findRuntime(actor.peer_id);
        if (node) {
            if (node.control_uris) {
                var url = node.control_uris[0] + '/actor/' + actor.id + '/replicate';
                var data = JSON.stringify({'dereplicate': true, 'exhaust': true});
                console.log("replicate - url: " + url + " data: " + data);
                $.ajax({
                    timeout: 30000,  // long timeout since it takes time to exhasut tokens if downstream is slow
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
                        showSuccess("Actor " + actor.name +"("+ actor_id +")" + " dereplicated");
                    },
                    error: function(data, status) {
                        if (status == "timeout") {
                            showError("Timeout when dereplicated " + actor.name +"("+ actor_id +")");
                        } else {
                            showError("Failed to dereplicate " + actor.name +"("+ actor_id +")");
                        }
                    }
                });
            } else {
                showError("Node " + actor.peer_id + " has no control API");
            }
        } else {
            showError("Failed to dereplicate, no node with id: " + actor.peer_id);
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
                showSuccess("Application " + application_id + " destroyed");
            },
            error: function() {
                showError("Failed to destroy application");
            }
        });
    } else {
        showError("Failed to destroy application, no application with id: " + application_id);
    }
}

// Destroy runtime with id "peer_id"
function destroyPeer(peer_id)
{
    return destroyPeerByMethod(peer_id, "now");
}

// Destroy runtime with id "peer_id"
function destroyPeerByMethod(peer_id, method)
{
    var peer = findRuntime(peer_id);
    if (peer) {
        var url = peer.control_uris[0] + '/node/' + method;
        console.log("destroyPeer url: " + url);

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
                if (peer.source != null) {
                    peer.source.removeEventListener("message", eventHandler, false);
                }
                popRuntime(peer_id)
                var tableRef = document.getElementById('peersTable');
                for (var x = 0; x < tableRef.rows.length; x++) {
                    if (tableRef.rows[x].cells[0].innerHTML == peer_id) {
                        tableRef.deleteRow(x);
                        showSuccess("Runtime " + peer_id + " destroyed");
                        return;
                    }
                }
            },
            error: function() {
                if (peer.source != null) {
                    peer.source.removeEventListener("message", eventHandler, false);
                }
                showError("Failed to destroy runtime");
            }
        });
    } else {
        showError("Failed to destroy runtime, no runtime with id: " + peer_id);
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
    if (document.getElementById("chkTraceActorReplicate").checked) {
        events.push("actor_replicate");
    }
    if (document.getElementById("chkTraceActorDereplicate").checked) {
        events.push("actor_dereplicate");
    }
    if (document.getElementById("chkTraceApplicationNew").checked) {
        events.push("application_new");
    }
    if (document.getElementById("chkTraceApplicationDestroy").checked) {
        events.push("application_destroy");
    }
    if (document.getElementById("chkTraceLinkConnected").checked) {
        events.push("link_connected");
    }
    if (document.getElementById("chkTraceLinkDisconnected").checked) {
        events.push("link_disconnected");
    }
    if (document.getElementById("chkTraceLogMessage").checked) {
        events.push("log_message");
    }

    $("#traceDialog").modal('hide');
    for (var index in peers) {
        if (peers[index].control_uris) {
            if (peers[index].source) {
                showInfo("Trace already started on runtime" + peers[index].id);
            } else {
                var url = peers[index].control_uris[0] + '/log';
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
                            this.peer.source = new EventSource(this.peer.control_uris[0] + '/log/' + this.peer.user_id);
                            this.peer.source.addEventListener("message", eventHandler, false);
                        } else {
                            console.log("startLog - Empty response");
                        }
                    },
                    error: function() {
                        showInfo("Failed to start log, url: " + url);
                    }
                });
            }
        }
    }
}

// Stop trace
function stopLog()
{
    for (var index in peers) {
        var url = peers[index].control_uris[0] + '/log/' + peers[index].user_id;
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
                showInfo("Failed to stop log, url: " + url);
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
function clearLog()
{
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
        var actor = findActor(data.actor_id);
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
    } else if(data.type == "actor_replicate") {
        cell3.appendChild(document.createTextNode(data.replica_actor_id));
        cell5.appendChild(document.createTextNode(data.replication_id));
        var actor = findActor(data.actor_id);
        if (actor) {
            cell4.appendChild(document.createTextNode(actor.name + " replica"));
        }
    } else if(data.type == "actor_dereplicate") {
        cell3.appendChild(document.createTextNode(data.replica_actor_id));
        cell5.appendChild(document.createTextNode(data.replication_id));
        var actor = findActor(data.actor_id);
        if (actor) {
            cell4.appendChild(document.createTextNode(actor.name + " replica"));
        }
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
    } else if(data.type == "link_connected") {
        cell3.appendChild(document.createTextNode(data.peer_id));
        cell4.appendChild(document.createTextNode(data.uris));
    } else if(data.type == "link_disconnected") {
        cell3.appendChild(document.createTextNode(data.peer_id));
    } else if(data.type == "log_message") {
        cell3.appendChild(document.createTextNode(data.msg));
    } else {
        console.log("eventHandler - Unknown event type:" + data.type);
    }
}

// Start event stream for graph
function startGraphEvents(application)
{
    var events = ["actor_new", "actor_replicate", "actor_dereplicate"];
    var actors = application.actors;
    for (var index in peers) {
        if (peers[index].control_uris) {
            if (peers[index].graph_source) {
                showError("Graph trace already started on runtime" + peers[index].node_name.name);
            } else {
                var url = peers[index].control_uris[0] + '/log';
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
                            this.peer.graph_source = new EventSource(this.peer.control_uris[0] + '/log/' + data.user_id);
                            this.peer.graph_source.addEventListener("message", graphEventHandler, false);
                        } else {
                            console.log("startGraphEvents - Empty response");
                        }
                    },
                    error: function() {
                        console.log("Failed to get log, url: " + url);
                    }
                });
            }
        }
    }
}

// Stop event stream for graph
function stopGraphEvents()
{
    for (var index in peers) {
        if (peers[index].graph_source && peers[index].graph_user_id) {
            var url = peers[index].control_uris[0] + '/log/' + peers[index].graph_user_id;
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
                    showInfo("Failed to stop log, url: " + url);
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
    } else if(data.type == "actor_replicate") {
        var actor = findActor(data.actor_id);
        if (actor) {
            actor.master = true
            actor.replication_id = data.replication_id
        }
        if (!findRuntime(data.dest_node_id)) {
            getPeer(data.dest_node_id);
        }
        getActor(data.replica_actor_id, false, false, 1);
    } else if(data.type == "actor_dereplicate") {
        var actor = popActor(data.replica_actor_id);
        console.log("Dereplicated - " + actor);
        if (actor) {
            console.log("Dereplicated - found " + actor.id);
            removeActorFromGraph(actor);
            var actorSelector = document.getElementById("actorSelector");
            var index;
            for (index in actorSelector.options) {
                if (actorSelector.options[index].id == actor.id) {
                    break;
                }
            }
            actorSelector.options.remove(index);
            sortCombo(actorSelector);
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
        $("#deployDialog").modal.peer = peer;
        $("#deployDialog").modal({
            modal: true,
            show: true
        });
    }
}

function deployHandler()
{
    var peer = $("#deployDialog").modal.peer;
    var script = $("#deploy_script").val();
    var name = $("#script_name").val();
    var reqs = $("#migrate_reqs").val();
    var creds = $("#credentials_conf").val();
    deployApplication(peer.control_uris[0], script, reqs, name, creds);
}

// Deploy application with "script" and "name" to runtime with "uri"
function deployApplication(uri, script, reqs, name, creds)
{
    var url = uri + '/deploy';
    var tmp = {'script': script, 'name': name};

    if (reqs) {
        tmp.deploy_info = JSON.parse(reqs);
    }

    if (creds) {
        tmp.sec_credentials = JSON.parse(creds);
    }

    var data = JSON.stringify(tmp);

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
            showSuccess("Application " + name + " deployed");
        },
        error: function(data, status) {
            data = JSON.parse(data.responseText)
            var index;
            var msg = "";
            for (index in data.errors) {
                msg = msg + "Error Line: " + data.errors[index].line + " Col: " + data.errors[index].col;
                msg = msg + " " + data.errors[index].reason + "<br>";
            }
            for (index in data.warnings) {
                msg = msg + "Warning Line: " + data.warnings[index].line + " Col: " + data.warnings[index].col;
                msg = msg + " " + data.warnings[index].reason + "<br>";
            }
            showError("Failed to deploy application: " + name);
            console.log(msg);
            showMessage(msg);
        }
    });
}

// Show dialog for setting requirements
function showSetRequirements(application_id)
{
    var application = findApplication(application_id);
    if (application) {
        $("#requirementsDialog").modal.application = application;
        $("#requirementsDialog").modal({
            modal: true,
            show: true
        });
    }
}

function setRequirementsHandler() {
    var application = $("#requirementsDialog").modal.application;
    var requirements = $("#requirements").val();
    setRequirements(application, requirements);
}

// Set requirements
function setRequirements(application, requirements)
{
    var url = application.control_uri + '/application/' + application.id + '/migrate';
    var data = JSON.stringify({'deploy_info': JSON.parse(requirements)});

    console.log("setRequirements url: " + url + " data: " + data);
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
            showSuccess("Requirements updated");
        },
        error: function() {
            showError("Failed to set requirements, url: " + url + " data: " + data);
        }
    });
}

function updateControlTable()
{
    var tableRef = document.getElementById('controlTable');
    clearTable(tableRef);
    AddTableItem(tableRef, document.createTextNode("Control URI"), document.createTextNode(connect_uri));
    var btnConnect = document.createElement('input');
    btnConnect.type = 'button';
    btnConnect.className = "btn btn-primary btn-xs";
    btnConnect.value = 'Connect...';
    btnConnect.setAttribute("onclick", "connect()");
    AddTableItem(tableRef, document.createTextNode("Connect"), btnConnect);
}

jQuery(document).ready(function() {
    connect_uri = "http://" + window.location.hostname + ":5001";
    var url = connect_uri + '/id';
    $.ajax({
        timeout: 1000,
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
                getPeer(data.id, true);
                getPeersFromIndex("/node/attribute/node_name");
                updateControlTable();

            }
        },
        error: function() {
            connect();
        }
    });

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

    // handle file select in credentials
    var fileInputCredentials = document.getElementById('fileInputCredentials');
    var fileDisplayCredentials = document.getElementById('credentials_conf');
    fileInputCredentials.addEventListener('change', function(e) {
        var file = fileInputCredentials.files[0];
        var reader = new FileReader();

        reader.onload = function(e) {
            console.log(e.target.result);
            fileDisplayCredentials.innerHTML = e.target.result;
        }

        reader.readAsText(file);
    });

    // handle file select in set requirements
    var fileInputRequirements = document.getElementById('fileInputRequirements');
    var fileDisplayRequirements = document.getElementById('requirements');
    fileInputRequirements.addEventListener('change', function(e) {
        var file = fileInputRequirements.files[0];
        var reader = new FileReader();

        reader.onload = function(e) {
            fileDisplayRequirements.innerHTML = e.target.result;
        }

        reader.readAsText(file);
    });

    $('#tabMenu a').click(function (e) {
        e.preventDefault();
        $(this).tab('show');
    })

    $('#tabRuntimeConfig a').click(function (e) {
        e.preventDefault();
        $(this).tab('show');
    })

    $('#tabDeployApplication a').click(function (e) {
        e.preventDefault();
        $(this).tab('show');
    })

    $('a[data-toggle="tab"]').on('show.bs.tab', function (e) {
        if (e.target.text == "Applications") {
            getApplications();
        } else if (e.target.text == "Runtimes") {
            updatePeers();
            stopGraphEvents();
        } else if (e.target.text == "Connections") {
            updatePeers();
            stopGraphEvents();
            drawConnections();
        }
    })
});
