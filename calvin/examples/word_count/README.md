# WordCount example #

The following calvin script reads a file `words.txt` and counts the occurrence of every word:


## Setup

### Hardware

- A computer to run the script is enough.
- A file to read, e.g. `words.txt`.

## Running

Run the script with the following command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost word_count.calvin 

## DHT

Calvin's internal registry is not strictly needed when running this small example,
it has therefor been turned off. To turn it on and run the application with DHT
instead, remove `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` from the command. I.e:

    § csruntime --host localhost word_count.calvin 
