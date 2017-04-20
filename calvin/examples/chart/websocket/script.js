var sock = null;

window.onload = function() {

    var wsuri;

    if (window.location.protocol === "file:") {
        wsuri = "ws://localhost:8123";
    } else {
        // To use with wss the CA cert that has issued a certificate for the runtime must be imported by the browser
        wsuri = "ws://" + window.location.hostname + ":8123";
    }

    if ("WebSocket" in window) {
        sock = new WebSocket(wsuri);
    } else if ("MozWebSocket" in window) {
        sock = new MozWebSocket(wsuri);
    } else {
        console.log("Browser does not support WebSocket!");
    }

    if (sock) {
        sock.onopen = function() {
            console.log("Connected to " + wsuri);
        }

        sock.onclose = function(e) {
            console.log("Connection closed (wasClean = " + e.wasClean + ", code = " + e.code + ", reason = '" + e.reason + "')");
            sock = null;
        }

        sock.onmessage = function(e) {
            var json_data = JSON.parse(e.data);
            for (var i in json_data){
                var key = i;
                var val = json_data[i];
                const image = document.getElementById(key);
                image.src = "data:image/PNG;base64," + val;
            }
        }
    }
};
