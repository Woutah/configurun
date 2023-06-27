# Configurun
Configurun is a PySide6-based packge that implements several tools for managing, creating and running python configurations. 
It was designed mainly with machine-learning tasks in mind, but can be used for any python script that takes arguments as an input, using either an argparse or a python-`@dataclass`.


This package makes it easier to manage complex configurations using a user-interface and enables the user to queue & run the configurations on a remote system in a simple and efficient manner.
The configurun-app is especially useful for scripts/experiments that require a lot of arguments to be tweaked. This package was created in tandem with [pyside6-utils](https://github.com/Woutah/pyside6-utils/).


<p align="center">
	<img src="https://raw.githubusercontent.com/Woutah/configurun/main/configurun/examples/images/main_window_example.png" width="1200" />
</p>


The app's configuration-input is built around python `@dataclass` objects, and their `field()` properties. We can either provide a custom `@dataclass` with all attributes we would like to edit, or directly pass an existing `argparse.Argumentparser` object to the app-creator.

For an example how to use this app, see [this section](#How to run?)

# Table of contents
- [Configurun](#configurun)
- [Table of contents](#table-of-contents)
- [Installation](#installation)
- [How to run?](#how-to-run)
	- [Example Options](#example-options)
- [Configuration](#configuration)
	- [Custom `@dataclass` Options](#custom-dataclass-options)
	- [Custom Options (`ArgumentParser`)](#custom-options-argumentparser)
	- [Custom Options (`Callable`)](#custom-options-callable)
- [Run Function](#run-function)
- [Target function](#target-function)
	- [Configuration](#configuration-1)
	- [Using an argparse.ArgumentParser](#using-an-argparseargumentparser)
- [Using Argparse](#using-argparse)


# Installation
This package can be installed manually by downloading from this repository, or directly from PyPi by using pip:
```bash
pip install configurun
```

# How to run?
Creating the app is done via the [`configurun.create`]-module. This module contains two functions:
- **Local app** - For running locally on your machine
- **Client app** - For running the configurations on a remote machine, connects to a `server`-instance
- **Server instance** - Runs the configurations on a remote machine, connects to a `client`-instance 

On the app-side, the `options_source` should be set.
On the server/running-machine, the `target_function` should be set.<br>
The following examples show some examples of how to get the app running.

## Example Options
To run the example app, we can either call `run_example_app()` from `configurun.examples.run_example_app` or run the following commands to construct the app
ourselves.

```python
### This example will run the app with an example configuration
# See `configurun/examples/example_run_function.py`
# See `configurun/examples/example_deduce_new_option_class_types.py`
import os
from configurun.create import local_app
from configurun.examples import example_run_function, example_deduce_new_option_class_types

local_app(
	target_function=example_run_function, #The function that will be called with the configuration
	options_source=deduce_new_option_class_types, #Source can be Callable/@datclass/ArgumentParser
	workspace_path = os.path.join(os.getcwd(), "Example1") #Settings and run-queue will be saved/loaded from/to here
)
```
# Configuration
The `Configuration`-instances contain 1 or more option (`@dataclass`) objects in its `options`-attribute. We can think of these `@dataclass`-objects as the different groups of options we want to edit (e.g. "GeneralOptions", "LogOptions", "ModelOptions", etc.)
When creating an app using the `create`-module, we can define a custom source for the editor, so we can edit/save and queue our own configurations.  
## Custom `@dataclass` Options
**NOTE:** Using fields results in more control over the final UI, for a more thorough example, please see [configurun/examples/example_configuration.py](https://github.com/Woutah/configurun/blob/main/configurun/examples/example_configuration.py)

**NOTE:**  When implementing custom option-classes, don't forget to add the @dataclass
```python
from dataclasses import dataclass
from configurun.create import local_app
from configurun.examples import example_run_function

@dataclass #Don't forget to add this(!) - otherwise the app will not recognize the fields
class MyCustomOptions(BaseOptions):
	simple_int : int = 1
	#...

local_app(
	target_function=example_run_function, #The function that will be called with the configuration
	options_source=MyCustomOptions, #Simple source: each configuration only has 1 option-class
	workspace_path = os.path.join(os.getcwd(), "Example2") #Settings and run-queue will be saved/loaded from/to here
)

```

## Custom Options (`ArgumentParser`)
We can use a `ArgumentParser`-object [this](#option-source)
```python
import argparse
from configurun.create import local_app
from configurun.examples import example_run_function

parser = argparse.ArgumentParser()
parser_example.add_argument("--required_arg", type=str, required=True, help="Required argument help")
#... add more arguments here

local_app(
	target_function=example_run_function, #The function that will be called with the configuration
	options_source=parser, #This parser is converted internally to a dataclass-class which is then used as the options-class
	workspace_path = os.path.join(os.getcwd(), "Example3") #Settings and run-queue will be saved/loaded from/to here
)
```
## Custom Options (`Callable`)
We can create a callable which takes the current Configuration-instance as an argument and returns the new options-instance.
This can be useful if we want to group options together, and only show certain groups when an attribute of another group is set to a certain value.

```python
#In this example, we will create a callable which returns a new options-instance based on the current configuration
import os
from dataclasses import dataclass
from configurun.create import local_app
from configurun.examples import example_run_function
from configurun.configuration import BaseOptions

@dataclass 
class AlwaysTheSame:
	base_int : int = 1
	#...

@dataclass
class CustomOptionsDefault:
	simple_int : int = 1
	#...

@dataclass
class CustomOptionsUnderConditions:
	simple_int : int = 2
	some_more_options : str = 'Some string'
	#...

def deduce_new_option_classes(configuration: Configuration) -> MyCustomOptions:
	if configuration.base_int == 2 and configuration.simple_int != 1: 
		#Only return the UnderConditions-options when base_int == 2 & simple_int != 1
		return { #Each category will get its own tab in the UI, ordered according to this dict
			'always_the_same' : AlwaysTheSame,
			'custom_options' : CustomOptionsUnderConditions
		}
	return { 
		'always_the_same' : AlwaysTheSame,
		'custom_options' : CustomOptionsDefault
	}
	#NOTE: we can return as many datacasses as we want

local_app(
	target_function=example_run_function, #The function that will be called with the configuration
	options_source=deduce_new_option_classes
	workspace_path = os.path.join(os.getcwd(), "Example3") #Settings and run-queue will be saved/loaded from/to here
)

```
# Run Function
Configurun works with a `configuration`-object, which contains a dictionary of `dataclass`-objects, which we refer to as `(sub)options`-objects.
One or more configuration-objects create one `configuration`-object, which is then passed to the target-function.

Items in the `Configuration`-instance, can be accessed using the `[]`-operator. E.g.:

```python
@dataclass
class GeneralOptionsClass(): #A general-options-dataclass
	simple_int : int = 1
	#etc.

@dataclass
class SpecificOptionsClass(): #A specific-options-dataclass
	specific_string : str = 'Some string' 
	#etc.

config = Configuration()
config.options['general'] = GeneralOptionsClass()
config.options['specific'] = SpecificOptionsClass()

#Accessing the options
print(config['simple_int']) #We can directly access simple_int => results in `1`
print(config['specific_string']) #We can directly access specific_string => results in `Some string`
```



# Target function
## Configuration

**How to create:**
This configuration-object can then be loaded into the configuration editor. 

The `datclass`-objects can either be loaded using a `@dataclass`-object, by passing an `argparse.ArgumentParser`-object.



## Using an argparse.ArgumentParser

```python

```
# Using Argparse
```python
import argparse
from 
```
