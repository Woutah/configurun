from setuptools import setup, find_packages

setup(
	name = "configurun",
	version= "0.1.0",
	packages=find_packages('.'),
    description="PySide6 based user-interface tools to create and run experiment-configurations with Python.",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author="Wouter Stokman",
    url="https://github.com/Woutah/configurun",
    license="LGPLv2",
    include_package_data=True,
    install_requires=[
		"PySide6",
	]
)