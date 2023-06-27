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
		- [**Server-Side**](#server-side)
- [Option-source](#option-source)
	- [Custom Options (`@dataclass`)](#custom-options-dataclass)
	- [Custom Options (`ArgumentParser`)](#custom-options-argumentparser)
	- [Custom Options (`Callable`)](#custom-options-callable)
- [Run Function](#run-function)
- [Target function](#target-function)
	- [Configuration](#configuration)
- [Configuration](#configuration-1)
- [Option metadata](#option-metadata)


# Installation
This package can be installed manually by downloading from this repository, or directly from PyPi by using pip:
```bash
pip install configurun
```

# How to run?
Creating the app is done via the `configurun.create`-module. We can create 3 different types of apps:
- **Local app** - For running locally on your machine
- **Client app** - For running the configurations on a remote machine, connects to a `server`-instance
- **Server app** - Runs the configurations on a remote machine, connects to a `client`-instance to receive new configurations

On the client-side, the `options_source` should be set.
On the server/running-machine, the `target_function` should be set.<br>
To run the example app, we can either call `run_example_app()` from `configurun.examples` or run the following code to construct the app ourselves:

```python
### This example will run the app with an example configuration
# Also see `configurun/examples/example_run_function.py`
# Also see `configurun/examples/example_deduce_new_option_class_types.py`
import os
from configurun.create import local_app
from configurun.examples import example_run_function, example_deduce_new_option_classes

if __name__ == "__main__": #Makes sure bootstrapping process is done when running app
	local_app(
		target_function=example_run_function, #The function that will be called with the configuration
		options_source=example_deduce_new_option_classes, #Source can be Callable/@datclass/ArgumentParser
		workspace_path = os.path.join( #Settings, configs adn the Run-Queue will be saved/loaded from/to here
			os.getcwd(), 
			"LocalExampleWorkspace"
		) 
	)
```
In this example, [`example_run_function`]([./configurun/examples/example_run_function.py](https://github.com/Woutah/configurun/blob/main/configurun/examples/example_run_function.py)) runs a dummy task for 20 seconds. We can [specify our own run-function](#run-function) to run our own scripts.

We can [specify our own options source](#option-source) to create our own options-class for the configuration-editor, for example by [using an existing `ArgumentParser`-object.](#custom-options-argumentparser)

To run the example above on a remote machine, we can run the following code: <br>
### **Server-Side** 
```python 
import os
from configurun.create import local_app
from configurun.examples import example_run_function, example_deduce_new_option_class_types
```



# Option-source
When creating an app using the `create`-module, we can define a custom source so we can edit/save and queue our own custom options.

## Custom Options (`@dataclass`)
**NOTE:** Using fields results in more control over the final UI, for a more thorough example, please see [this section](#option-metadata) and/or the example implementations in [configurun/examples/example_options/example_options.py](https://github.com/Woutah/configurun/blob/main/configurun/examples/example_options/example_options.py).

**NOTE:**  When implementing custom option-classes, don't forget to add the `@dataclass`-decorator, and always inherit from `BaseOptions`
```python
import os
from dataclasses import dataclass
from configurun.configuration.base_options import BaseOptions
from configurun.create import local_app
from configurun.examples import example_run_function


@dataclass #Don't forget to add this(!) - otherwise the app will not recognize the fields
class MyCustomOptions(BaseOptions): #Always inherit from BaseOptions (required to run config)
	simple_int : int = 1
	# etc...

if __name__ == "__main__":
	local_app(
		target_function=example_run_function,
		options_source=MyCustomOptions, #Simple: each configuration only has 1 option-class
		workspace_path = os.path.join(os.getcwd(), "ExampleDataclass")
	)

```

## Custom Options (`ArgumentParser`)
We can use a `ArgumentParser`-object as an options source, this will internally convert the argument parser into a `@dataclass`-object, which is then used as an options-class. Certain arguments are also parsed to control the UI (e.g. `required=True`, `help="Will be displayed on hover"`).
```python
import argparse
from configurun.create import local_app
from configurun.examples import example_run_function

parser = argparse.ArgumentParser()
parser_example.add_argument("--required_arg", type=str, required=True, help="Required argument help")
#... add more arguments here

local_app(
	target_function=example_run_function,
	options_source=parser, #Parser is converted internally to a dataclass-class which is used as the options-class
	workspace_path = os.path.join(os.getcwd(), "ExampleArgparse")
)
```
## Custom Options (`Callable`)
A configuration is a collection of option-instances, which are grouped toghether in a `Configuration`-wrapper, which enables us to access the attributes of all enclosed options-instances using the `configuration[attribute]`/`configuration.<attribute>`/`option_class.get(attribute, default)`. For more information, see [this section](#configuration).

As an options-source, we can create a callable which takes the current Configuration-instance as an argument and returns the new options-classes (***not** instances*).
This can be useful if we want to group options together, and only show certain groups when an attribute of another group is set to a certain value.

```python
#In this example, we will create a callable which returns new options-classes based on the 
# current configuration
import os
import typing
from dataclasses import dataclass
from configurun.create import local_app
from configurun.examples import example_run_function
from configurun.configuration import BaseOptions, Configuration

@dataclass #NOTE: Always use @dataclass for options
class AlwaysTheSame(BaseOptions): #NOTE: Always use BaseOptions as base class for options
	base_int : int = 1
	#...

@dataclass
class CustomOptionsDefault(BaseOptions):
	simple_int : int = 1
	#...

@dataclass
class CustomOptionsUnderConditions(BaseOptions):
	simple_int : int = 2
	some_more_options : str = 'Some string'
	#...

def deduce_new_option_classes(configuration: Configuration)\
		-> typing.Dict[str, typing.Type[BaseOptions | None]]: #Always return a dict of option 
	 		# classes the key of the dict is the name of the option class, the value is the 
			# option class itself the name is used to create the tab/window in the UI.
	if configuration.options is None or len(configuration.options) == 0:
		pass #If initial configuration is being retrieved -> return default dict
	elif configuration.base_int == 2 and configuration.simple_int != 1:
		#Only return the UnderConditions-options when base_int == 2 & simple_int != 1
		#NOTE: if we're not sure if attributes exist, we can use the `.get(key, default)` method
		return { #Each category will get its own tab in the UI, ordered according to this dict
			'always_the_same' : AlwaysTheSame,
			'custom_options' : CustomOptionsUnderConditions
		}
	
	return { #config.options will contain dataclass/options-instances of these types:
		'always_the_same' : AlwaysTheSame,
		'custom_options' : CustomOptionsDefault
	} #NOTE: we must ALWAYS return a dictionary with at least 1 option class, otherwise we will 
		# get stuck in a situation in which there are no options to display/edit 

if __name__ == '__main__':
	local_app(
		target_function=example_run_function,
		options_source=deduce_new_option_classes,
		workspace_path = os.path.join(os.getcwd(), "Example3")
	)

```



# Run Function
To implement a run-function, the only thing that we have to do, is make a function which takes a [`Configuration`-instance](#configuration) as an argument.
The configuration contains all the options that we have defined in our [`options_source`](#option-source).

```python
```

# Target function
## Configuration

**How to create:**
This configuration-object can then be loaded into the configuration editor. 

The `datclass`-objects can either be loaded using a `@dataclass`-object, by passing an `argparse.ArgumentParser`-object.


# Configuration
Configurun works with `configuration`-objects. A configuration is a collection of option-instances, which are grouped toghether in a `Configuration`-wrapper, which enables us to access the attributes of all enclosed options-instances using the `configuration[attribute]`/`configuration.<attribute>`/`option_class.get(attribute, default)`.

We can think of these `@dataclass`-objects as the different groups of options we want to edit and use in our run (e.g. "GeneralOptions", "LogOptions", "ModelOptions", etc.)

E.g.:

``` python
from dataclasses import dataclass
from configurun.configuration import Configuration
from configurun.configuration import BaseOptions

@dataclass
class GeneralOptionsClass(BaseOptions):
	simple_int : int = 1
	#etc.

@dataclass
class OtherOptionClass(BaseOptions):
	some_other_int : int = 2
	#etc.


config = Configuration()
config.options['general_options'] = GeneralOptionsClass()
config.options['other_options'] = OtherOptionClass()

#Accessing the options, all of the following are equivalent:
print(config['simple_int'])
print(config.simple_int)
print(config.get('simple_int', -1)))

#These are also equivalent:
print(config['some_other_int'])
print(config.some_other_int)
print(config.get('some_other_int', -1)))
```



# Option metadata
The UI is mainly built around the `field()` functionality of dataclasses, which allows the model to make use of the default values, type hints and other information provided by the dataclass.
For each field, we can provide additional information in the `metadata` attribute of `field()` for each setting. This provides additional information to the UI, which uses this information to determine the editor-type, constraints etc. <br>

For example:
```python
from pyside6_utils.utility.constraints import Interval #Used to constrain the fields

@dataclass
class TestOptions(BaseOptions):
	test_int_property : int | None = field(
		default=None, #The default value used in the UI - if it is changed, the UI will display the new value in bold
		metadata=dict( #Contains additional information for the UI
			display_name="Test int/none property", #The name to display in the UI
			help="This is a test property that can also be none", #The help-message to display when hovering over the item
			required=True #Whether this field is required - if true - a red background will appear if the value is None
			constraints = [Interval(type=int, left=1, right=None, closed="both"), None]
			# etc...
		)
)
```
For more examples, please see the [example-options](https://github.com/Woutah/configurun/blob/main/configurun/examples/example_options/example_options.py). 

We can add metadata to

| Metadata Key | Type | Description |
| --- | --- | --- |
| `"display_name"` | `str` | Name to display for this attribute in the view - defaults to the variable name itself |
| `"display_path"` | `str` | Path to display this attribute - we can group/structure items when using a treeview - defaults to no parents|
| `"help"` | `str` | Help-message which will be shown when the user hovers over this item - empty by default|
| `"constraints"` | `List[sklearn_param_validation constraints]` | Additional constraints on which the editor will be determined to apply to the field [^constraintnote] , if none provided, use typehint of the field|
| `"required"` | `bool` | Whether this field is required to be filled in - if true - a red background will appear if the value is not set|
| `"editable"` | `bool` | Whether this field is editable - if false - the editor will be disabled|

[^constraintnote] Constraints are (almost fully) sourced from the `sklearn.utils._validation` module and provides a way to constrain the dataclass fields such that the user can only enter valid values. They are also packed into this package under `utility.constraints`. The following constraints are supported:
| Constraint | Description | Editor Type
| --- | --- | --- |
| `type` | The type of the value should match the type of the constraint | based on type |
| `Options` / `Container` | The value should be one of the options provided in the constraint | `QComboBox` |
| `StrOptions` | The value should be one of the str-options provided in the constraint | `QComboBox` |
| `Interval` | The value should be within the interval provided in the constraint | `QSpinBox` or `QDoubleSpinBox` (limited) |
| `None` | `None` is a valid value for this field `typing.Optional` | Adds reset-button to editor |
| `Range` | The value should be within the range provided in the constraint | `QSpinBox` (limited) |