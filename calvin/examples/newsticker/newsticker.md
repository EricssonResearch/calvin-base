# A retro-style news-ticker written in Calvin

Continuously print e.g. commit messages from the Calvin repo as they happen, in a news-ticker fashion (dot-matrix printer not included).

## Overview

Get the latest commit and extract commit timestamp and ETag, print a nicely formatted commit line.
Periodically check repo for changes by comparing the response header's ETag to our latest known ETag.
If the ETag has changed, get the commits since our last recorded timestamp and print them, update timestamp and ETag.
 
## Running

    csruntime --host \<host ip\>  --controlport 5101 --port 5100 newsticker.calvin


## Notes

2017-03-27 : This version is much improved, with better structuring of the code.
