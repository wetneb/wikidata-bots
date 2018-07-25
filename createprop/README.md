This is a quick hack to create properties based on the content of their proposal templates.

This ugly piece of software is published in the hope that it will encourage others to write something cleaner.

To use it, just type `./launch.sh "name of the property proposal"` (where the name of the property proposal is "My ID" if the property is proposed at "Wikidata:Property proposal/My ID"). This will:
* Parse the proposal template
* Perform some checks on the proposal (for instance, for an identifier, it checks that the examples provided match the regular expression)
* Create the property, adding some default property constraints in the case of identifiers.
* Add examples on the property (and on the items mentioned in the examples)
* Add "see also" links in both directions
* Create a talk page for the property
* Close the property proposal.

Installing this script is complicated because it depends on Jython, a Java implementation of Python.
Using Jython makes it possible to use Wikidata-Toolkit, which is included in the java_libs folder.

So, to run it:
- install java, Jython and jip
- install the java requirements with `jip`, which lets you install java dependencies inside a Jython environment
- install the python requirements with the `pip` that comes with your Jython install
- write your username and password in `wikidata_username.txt` and `wikidata_password.txt` - your account should have property creation rights
- create properties!

Note that this script can fail in arbitrarily bad ways, such as creating properties without closing the corresponding proposals, or doing all sorts of bad things. USE AT YOUR OWN RISK.

