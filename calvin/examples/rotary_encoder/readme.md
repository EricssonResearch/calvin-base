# Rotary encoder example #

Ensure the configuration file is in the search path; either start the calvin runtime from this directory, or add this path to CALVIN\_CONFIG\_PATH.

Running the example:

    $ csruntime --host localhost rotary.calvin --attr-file gpio-pins.json

Remember to edit the gpio-pins.json file to reflect your pin assignment (if it differs from the one specified in the file.)