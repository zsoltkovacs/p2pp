from setuptools import setup
import version

setup(
    name='p2pp',
    version="{}.{:2}.{:3}".format(version.MajorVersion, version.MinorVersion, version.Build),
    packages=['p2pp'],
    url='https://github.com/tomvandeneede/p2pp',
    license='GPLv3',
    author='tomvandeneede',
    author_email='t.vandeneede@pandora.be',
    description='Prusa Slicer 2 Palette Processor'
)
