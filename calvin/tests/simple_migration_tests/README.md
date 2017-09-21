# `test_simple_migration`

This test starts up two runtimes and for each calvin-script in the `simple_migration_scripts` folder, it will (try to) deploy it, and then migrate each of the actors in the script back and forth between the runtimes.

A test will fail if

 - there is an error during deployment/migration which returns an error via the control api
 - the string `xception` occurs anywhere in the log of either runtime (<- this needs work)
 
### Adding a test

In order to add a test to this suite, just add a (small) script to the folder.

### Issues

Currently, there is no handling of non-default calvinsys or calvinlib, and the delay before beginning actor migration was chosen arbitrarily.