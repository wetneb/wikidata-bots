#!/bin/sh
export CLASSPATH=/home/antonin/.bin/jython2.7.1/javalib/*
export TERM=abc
/home/antonin/.bin/jython2.7.1/bin/jython wdtk.py "$@"
