# A simple webserver implemented using Calvin

This is an example of a moderately complex application written using CalvinScript. 

Disregarding the fact that this is probably not the kind of application that you would want to use Calvin for in general, it serves as an example of how to structure a CalvinScript (CS) of some complexity.

Additionally, it also exposes some ugly spots in CS, most notably the frequent use of Constant-actors. We plan to add support for literal constants in future releases.

## Overview

The directory contains the following files and subdirectories: 

    ├── devactors
    │   └── http
    │       └── HTTPResponseGenerator.py
    ├── html
    │   ├── bar.html
    │   ├── foo.html
    │   └── index.html
    └── webserver.calvin

The main script is `webserver.calvin`, and the `devactors` directory contains a utility actor `http.HTTPResponseGenerator` that will format an HTTP-response given a body of text. The `html` directory unsurprisingly contains a couple of HTML files.

## Running the webserver

Running the webserver should be as simple as stepping into the directory and starting the script:

    webserver$ csdeploy --keep-alive webserver.calvin 

Next, open up a web browser and goto:

    http://localhost:8089/index.html

Note that there is no default route for `/` so omitting the `index.html` will render a 404 response.

