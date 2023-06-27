# Configurun
Configurun is a pyside6-based packge that implements several tools for managing, creating and running python configurations. 
It was designed mainly with machine-learning tasks in mind, but can be used for running any kind of python code that takes arguments as an input, either from argparse or from a python-`@dataclass`.


This package makes it easier to manage complex configurations using a user-interface and enables the user to queue & run the configurations on a remote system in a simple and efficient manner.
The configurun-app is especially useful for scripts/experiments that require a lot of arguments to be tweaked. This package was created in tandem with [pyside6-utils](https://github.com/Woutah/pyside6-utils/).


<p align="center">
	<img src="https://raw.githubusercontent.com/Woutah/configurun/main/configurun/examples/images/main_window_example.png" width="1200" />
</p>


The app's configuration-input is built around python `@dataclass` objects, and their `field()` properties. We can either provide a custom `@dataclass` with all attributes we would like to edit, or directly pass an existing `argparse.Argumentparser` object to the app-creator.

For an example how to use this app, see [this section](#How to run?)


# installation
This package can be installed manually by downloading from this repository, or directly from PyPi by using pip:
```bash
pip install configurun
```

# How to run?
There are 2 versions of the app:
- Local app
  - For running locally on your machine
- Client app 
  - For running the configurations on a remote machine

## Example-app
```python
### This example will run the app with an example configuration
from configurun.create import local_app
from configurun.examples import example_run_function, example_deduce_new_option_class_types

local_app(
	target_function=example_run_function,
	options_source=deduce_new_option_class_types,
)
```
## Your own target function


## Using an argparse.ArgumentParser

```python

```
# Using Argparse
```python
import argparse
from 
```
