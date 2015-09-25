"""This module provides actors related to exception handling.

A common case of exception is end-of-stream (EOS) that indicates that the source cannot produce anymore tokens, e.g. when a file reader reaches the end of the file.
Depending the application, this may or may not indicated that the process has completed execution, on possible scenario is that a file reader will start reading another file after reaching the end of a first file. It is up to the application developer to decide how to interpret EOS tokens.

Another common use of EOS tokens is to create lists and dictionaries with varying number of members, see docs for module 'json', in particular 'json.List' and 'json.Dict'.
"""