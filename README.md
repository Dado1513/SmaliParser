# Smali Parser

The Smali Parser is a tool with the aim to analyze Smali code (produced by APktool) in order to find the methods selected through the command line and the relative parameter values passed to them.

 to find how method was used and how parameters, based on list method passed on CLI

```bash
    python3 smaliparser.py -m loadUrl evaluateJavaScript -d apktooldiroutput
```