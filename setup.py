from setuptools import setup, find_packages

setup(
	name = "configurun",
	version= "0.0.1",
	packages=find_packages('.'),
    description="PySide6 based user-interface tools to create and manage machine learning training/testing-configurations and run them automatically and/or remotely..",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author="Wouter Stokman",
    url="https://github.com/Woutah/configurun",
    license="LGPLv2",
    include_package_data=True,
    install_requires=[ #Generated using pipreqs
        'pandas>=1.5.2', #Works for 1.23.5
        'numpy>=1.0.0', #Works for 1.23.5
        'PySide6>=6.0.0', # Qt for Python, works for 6.5.1.1
        'PySide6_Addons>=6.0.0', #Works for 6.5.1.1
        'PySide6_Essentials>=6.0.0', #Works for 6.5.1.1
        'pathos>=0.3.0', #Works for 0.3.0
        'setuptools>=65.0.0', #Works for 65.5.0
        'winshell>=0.6; platform_system == "Windows"',
		'dill>=0.3.0', #Works for 0.3.6
		'multiprocess>=0.70.00', #Works for 0.70.14
		'numpydoc>=1.4.0', #Works for 1.5.0
		'pycryptodome>=3.10.0', #Works for 3.18.0
        'pyside6-utils==1.1.0'
	]
)