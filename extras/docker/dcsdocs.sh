#!/bin/sh

IMAGE=erctcalvin/calvin:master

usage() {
    echo "Usage: $(basename $0) <actor or namespace>\n\
      -i <image>[:<tag>]   : Calvin image (and tag) to use [$IMAGE]\n\
      <args sent to csdocs>\n\
      (use --help to get help on csdocs usage)"
    exit 1
}

CMD=cat

while getopts "hi:-:" opt; do
	case $opt in
		h) 
            usage
            ;;
        i)
            IMAGE=$OPTARG
            ;;

		-) 
			VAL=${!OPTIND}
			ARGS+=" --$OPTARG ${!OPTIND}"
			OPTIND=$(( $OPTIND + 1))
			;;
	esac
done

shift $((OPTIND-1)) 


docker run -it --entrypoint csdocs $IMAGE $ARGS $@
