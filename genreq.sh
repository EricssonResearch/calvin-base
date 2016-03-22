
if [ "$1" == "-c" ]; then
	VENV=$(mktemp -d 2>/dev/null || mktemp -d -t 'mytmpdir')
	virtualenv $VENV
	source $VENV/bin/activate
	sed -i.bak 's|[><=].*||' test-requirements.txt requirements.txt
	pip install -r test-requirements.txt -r requirements.txt > /dev/null
fi	

if [ ! -z "$VENV" ]; then
	source $VENV/bin/activate
fi

echo
# generate
echo "cat << EOF > requirements.txt"
for a in $(cat requirements.txt)
do
	TAG=$(pip freeze | grep "^$a==")
	#NAME=$(pip show $a | grep "^Name: " | sed 's|Name: \(.\+\)|\1|')
	#VERSION=$(pip show $a | grep "^Version: " | sed 's|Version: \(.\+\)|\1|')
	echo $TAG
done
echo "EOF"
echo 
echo "cat << EOF > test-requirements.txt"
for a in $(cat test-requirements.txt)
do
	TAG=$(pip freeze | grep "^$a==")
	#NAME=$(pip show $a | grep "^Name: " | sed 's|Name: \(.\+\)|\1|')
	#VERSION=$(pip show $a | grep "^Version: " | sed 's|Version: \(.\+\)|\1|')
	echo $TAG
done
echo "EOF"

if [ ! -z "$VENV" ]; then
	deactivate
fi

