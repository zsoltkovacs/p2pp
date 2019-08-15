__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPL'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'
__status__ = 'BETA'


import urllib


# general version info
MajorVersion = 3
MinorVersion = 3
Build = 3

latest_stable_version = ""

try:
    latestversionpy = urllib.urlopen("https://github.com/tomvandeneede/p2pp/raw/master/version.py")
    versioncontents = "".join(latestversionpy.read()).split('\n')
    _maj=0
    _min=0
    _bld=0

    for line in versioncontents:
        if line.startswith("MajorVersion"):
            _maj = int(line[line.find("=")+1:])
        if line.startswith("MinorVersion"):
            _min = int(line[line.find("=")+1:])
        if line.startswith("Build"):
            _bld = int(line[line.find("=")+1:])

    latest_stable_version = "{}.{}.{}".format(_maj, _min, _bld)

except IOError:
    pass

Version = "{}.{}.{}".format(MajorVersion, MinorVersion, Build)

if len(latest_stable_version)>0:
    Version = Version + "  (Latest Stable Version: " + latest_stable_version +")"