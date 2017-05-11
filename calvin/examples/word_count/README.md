# WordCount example #

The following calvin script reads a file `words.txt` and counts the occurrence of every word:


## Setup

### Hardware

- A computer to run the script is enough.
- A file to read, e.g. `words.txt`.

## Running

Run the script with one of the following commands:

### With DHT

    § csruntime --host localhost word_count.calvin 

### Without DHT

Calvin's internal registry is not strictly needed when running this small
example. To turn it off and run the application locally add `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"`
to the command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost word_count.calvin 

