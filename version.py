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
import p2pp.logfile
import p2pp.variables as v


# general version info
MajorVersion = 3
MinorVersion = 3
Build = 3

latest_stable_version = ""



def UpdateP2PP(version, file_list):
    files = {}
    try:
        # download all files from internet
        for updatefile in file_list:
            p2pp.logfile.log_warning("Downloading upgrade file: {}".format(updatefile))
            fileurl = urllib.urlopen("https://github.com/tomvandeneede/p2pp/raw/master/"+updatefile[0])
            files[updatefile] = fileurl.read()
            fileurl.close()
        # only thing left to do is to unzip the file....

        p2pp.logfile.log_warning("Upgraded to version {}".format(version))
    except:
        p2pp.logfile.log_warning("Upgrade to version {} Failed".format(version))



def perform_version_check():
    global Version
    try:
        latestversionpy = urllib.urlopen("https://github.com/tomvandeneede/p2pp/raw/master/version.py")
        versioncontents = "".join(latestversionpy.read()).split('\n')
        latestversionpy.close()
        _maj = 0
        _min = 0
        _bld = 0

        for line in versioncontents:
            if line.startswith("MajorVersion"):
                _maj = int(line[line.find("=")+1:])
            if line.startswith("MinorVersion"):
                _min = int(line[line.find("=")+1:])
            if line.startswith("Build"):
                _bld = int(line[line.find("=")+1:])
            if line.startswith('# zip_file'):
                v.update_file_list.append (line[line.find("=")+1:])

        latest_stable_version = "{}.{}.{}".format(_maj, _min, _bld)
        v.upgradeprocess = UpdateP2PP

        if not (latest_stable_version == "0.0.0"):
            if Version > latest_stable_version:
                Version = Version + "  (This is a development version"
            elif Version == latest_stable_version:
                Version = Version + "  (Your version is up to date!)"
            else:
                Version = Version + "  (Newer version available: " + latest_stable_version + ")"

    except IOError:
        print"failed to load..."
        pass


Version = "{}.{}.{}".format(MajorVersion, MinorVersion, Build)

if v.versioncheck:
    perform_version_check()

##################################
# UPDATE FILES FOR CURRENT VERSION
##################################
# zip_file=p2pp_mac.zip


