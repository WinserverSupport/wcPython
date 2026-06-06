# setup.py
from setuptools import setup

setup(
    name='wcpapi',
    version='10.0.500.2',
    packages=['wcpapi'],
    author='Hector Santos',
    author_email='hsantos@isdg.net',
    description='Wildcat! Python API (wcPAPI) - Santronics Software, Inc.',
    url='https://github.com/WinserverSupport/wcPython',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    python_requires='>=3.6',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: Microsoft :: Windows',
    ],
)
