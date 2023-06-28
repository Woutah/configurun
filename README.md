# Configurun
Configurun is a PySide6-based packge that implements several tools for managing, creating and running python configurations. 
It was designed mainly with machine-learning tasks in mind, but can be used for any python script that takes arguments as an input. We can automatically build the configuration-editor's UI using either an `argparse.Argumentparser` or a python-`@dataclass`.


The Configurun-app is especially useful for scripts/experiments that require a lot of arguments to be tweaked across many experiment-runs. This package was created in tandem with [pyside6-utils](https://github.com/Woutah/pyside6-utils/).


<p align="center">
	<img src="https://raw.githubusercontent.com/Woutah/configurun/main/configurun/examples/images/main_window_example.png" width="1200" />
</p>


The app's configuration-input is built around python `@dataclass` objects, and their `field()` properties. We can either provide a custom `@dataclass` with all attributes we would like to edit, or directly pass an existing `argparse.Argumentparser` object to the app-creator.

For an example how to use this app, see [this section](#How to run?)

# Table of contents
- [Configurun](#configurun)
- [Table of contents](#table-of-contents)
- [Features](#features)
	- [Configuration Editor](#configuration-editor)
	- [Run Queue](#run-queue)
- [Installation](#installation)
- [How to run?](#how-to-run)
	- [Local App](#local-app)
	- [Server-side](#server-side)
	- [Client-Side](#client-side)
- [Option-source](#option-source)
	- [Custom Options (`@dataclass`)](#custom-options-dataclass)
	- [Custom Options (`ArgumentParser`)](#custom-options-argumentparser)
	- [Custom Options (`Callable`)](#custom-options-callable)
- [Run Function](#run-function)
	- [Configuration](#configuration)
- [Configuration](#configuration-1)
- [Option metadata](#option-metadata)


# Features
## Configuration Editor
The configuration editor allows the user to specify a configuration-template using either (groups of) [`@dataclass`-class](#custom-options-dataclass) or an [`ArgumentParser`-instance](#custom-options-dataclass). The editor will then automatically create a UI based on the provided template. Editors are specifically created for each option-property based on provided template-types (and [extra constraints](#option-metadata)). Help-messages are displayed on hover, required arguments are highlighted when not filled in, etc.
<p align="center">
	<img src="./configurun/examples/images/configuration_editor_example.png" width="600" />
	<!-- <img src="https://raw.githubusercontent.com/Woutah/configurun/main/configurun/examples/images/configuration_editor_example.png" width="600" /> -->
</p>

We can define our own [option-source-method](#custom-options-callable) to dynamically create new option-groups based on the current configuration. This can be useful if we want to group options together, and only show certain groups when an attribute of another group is set to a certain value. E.g: only show `ExtendedExampleModel`-options if property `model_type` in `MainOptions` is set to `"ExtendedExampleModel"`. <br>

Configurations can be saved and loaded, a file-explorer view for the current workspace is made available.:
<p align="center">
	<img src="./configurun/examples/images/file_explorer_example.png" width="400" />
	<!-- <img src="https://raw.githubusercontent.com/Woutah/configurun/main/configurun/examples/images/file_explorer_example.png" width="400" /> -->
</p>

## Run Queue
The run-queue window manages the currently running items. This could either be [locally](#local-app), or remote, when using a [client-app](#client-side) and a [server-instance](#server-side) on which the actual Run-Queue is running. The Run-Queue allows us to add/remove items, pause/resume items, change the queue-order of items, and start autoprocessing, which will automatically start the next item in the queue when the current item is finished. We can set the number of processors as well, to run multiple items in parallel.
<p align="center">
	<img src="./configurun/examples/images/run_queue_example.png" width="1100" />
	<!-- <img src="https://raw.githubusercontent.com/Woutah/configurun/main/configurun/examples/images/run_queue_example.png" width="400" /> -->
</p>

Configurations are passed to the user-provided [run-function](#run-function) in separate processes. The stdout/stderr of each of the items is captured and displayed as a selectable console-output-view in the command-line-output window:
<p align="center">
	<img src="./configurun/examples/images/command_line_output_example.png" width="1100" />
	<!-- <img src="https://raw.githubusercontent.com/Woutah/configurun/main/configurun/examples/images/command_line_output_example.png" width="400" /> -->
</p>



# Installation
This package can be installed manually by downloading from this repository, or directly from PyPi by using pip:
```bash
pip install configurun
```

# How to run?
Creating the app is done via the `configurun.create`-module. We can create 3 different types of apps:
- [**Local app**](#local-app) - For running everything locally on your machine
- [**Client-app**](#client-side) - For running the configurations on a remote machine, connects to a `server`-instance
- [**Server-instance**](#server-side) - Command-line instance that listens to connections from a `client`-instance to receive new configurations and commands to manage the RunQueue

On the client-side, the `options_source` should be set.
On the server/running-machine, the `target_function` should be set.<br>

## Local App
A local app is an all-in-one app that can be used to run configurations locally on your machine.
To run the example app, we can either call `run_example_app()` from `configurun.examples` or run the following code to construct the app ourselves:
```python
### This example will run the app with an example configuration
# Also see `configurun/examples/example_run_function.py`
# Also see `configurun/examples/example_deduce_new_option_class_types.py`
import os
from configurun.create import local_app
from configurun.examples import example_run_function, example_deduce_new_option_classes

if __name__ == "__main__": #Makes sure bootstrapping process is done when running app
	local_app( #Create and runs a local configurun app-instance
		target_function=example_run_function, #The function that will be called with the configuration
		options_source=example_deduce_new_option_classes, #Template for UI-optiosn: Callable/@datclass/ArgumentParser
		workspace_path = os.path.join( #Settings, configs and the Run-Queue will be saved/loaded from/to here
			os.getcwd(), 
			"LocalExampleWorkspace"
		) 
	)
```
In this example, [`example_run_function`]([./configurun/examples/example_run_function.py](https://github.com/Woutah/configurun/blob/main/configurun/examples/example_run_function.py)) runs a dummy task that logs to a file for 20 seconds. We can [specify our own run-function](#run-function) to run our own scripts.

We can [specify our own options source](#option-source) to create our own options-class for the configuration-editor, for example by [using an existing `ArgumentParser`-object.](#custom-options-argumentparser)

## Server-side
After creating the server, we can connect to it using a [client-app](#client-side).<br>
**NOTE:** *after* authentication, `pickle`/`dill` is used to transmit data, which indirectly enables arbitrary code execution on the server-side if the password is known. Please run the server trusted network environments only. Run at your own risk!
```python 
# Opens a server-instance which tries to connect with clients and allows
# them to add configurations to the queue to be run on this machine
import os
from configurun.create import server
from configurun.examples.example_run_function import example_run_function

if __name__ == "__main__":
	# WARNING:
	# THIS ALLOWS OTHER MACHINES THAT RESIDE ON THE SAME NETWORK
	# TO EXECUTE ARBITRARY CODE ON THIS MACHINE IF THEY KNOW THE 
	# PASSWORD. PLEASE RUN IN A TRUSTED NETWORK ENVIRONMENT ONLY
	# RUN AT YOUR OWN RISK!
	server(
		target_function=example_run_function,
		workspace_path=os.path.join(os.getcwd(), "ServerExampleWorkspace"),
		password="password", #Password to connect to the server, make sure to change this!
		port=469 #Port to connect to the server, defaults to 469
	)
```
## Client-Side
After creating the [server](#server-side), we can create a client-app and use it to login to the server. We can then use the client-app as if it's a local-app to add/run/manage configurations on the remote machine.<br>

```python
# Opens a client-side app that we can use to connect to and control
# the server-instance
import os
from configurun.create import client
from configurun.examples import example_deduce_new_option_classes

if __name__ == "__main__":
	client(
		options_source=example_deduce_new_option_classes,
		workspace_path=os.path.join(os.getcwd(), "ClientExampleWorkspace"),
	)
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
		options_source=MyCustomOptions, #Simple: each configuration consists of a single options-class
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

# Note that we can use the Configuration-instance to our adventage when
# creating our run-functions. e.g. defining the run-function as:
# `def run_function(configuration: GeneralOptionsClass)`
# Would result in our editor of choice recognizing/autocompleting
# the `configuration.simple_hint` variable. 
```



# Option metadata
The UI is mainly built around the [`field()`](https://docs.python.org/3/library/dataclasses.html#dataclasses.field) functionality of python-`dataclass`, which allows the display-model to make use of the default values, type hints and other information. 
For each attribute, we can provide additional information in the `metadata` attribute of `field()`. This provides additional information to the UI, which uses this to determine the editor-type, constraints etc. <br>

For example:
```python
from configurun.configuration import base_options
from dataclasses import field, dataclass
from pyside6_utils.utility.constraints import Interval #Used to constrain the fields

@dataclass
class TestOptions(BaseOptions):
	test_int_property : int | None = field(
		default=None, #The default value used in the UI
		metadata=dict( #Contains additional information for the UI
			display_name="Test property", #The display-name
			help="This is a test property that can also be none", #On-hover help-messagem
			required=True, #If required, the field is red if not filled in
			constraints = [ #Limit editors (min/max, options, etc.)
				#The following constrains the editor to have value > 1
				Interval(type=int, left=1, right=None, closed="both"), 
				None #Or value can be None
			] 
			# etc...
		)
)
```
For more examples, please see the [example-options](https://github.com/Woutah/configurun/blob/main/configurun/examples/example_options/example_options.py). 

The following metadata-keys are supported:

| Metadata Key | Type | Description |
| --- | --- | --- |
| `"display_name"` | `str` | Name to display for this attribute in the view - defaults to the variable name itself |
| `"display_path"` | `str` | Path to display this attribute - we can group/structure items. If parent does not exist, creates folders. Format as "|
| `"help"` | `str` | Help-message which will be shown when the user hovers over this item - empty by default|
| `"constraints"` | `List[sklearn_param_validation constraints]` | Additional constraints on which the editor will be determined to apply to the field [^constraintnote] , if none provided, use typehint of the field|
| `"required"` | `bool` | Whether this field is required to be filled in - if true - a red background will appear if the value is not set|
| `"editable"` | `bool` | Whether this field is editable - if false - the editor will be disabled|

[^constraintnote] Constraints are (almost fully) sourced from the `sklearn.utils._validation` module and provides a way to constrain the dataclass fields such that the user can only enter valid values. They are also packed into the [pyside6-utils](https://github.com/Woutah/pyside6-utils) package under [`utility.constraints`](https://github.com/Woutah/pyside6-utils/blob/main/pyside6_utils/utility/constraints.py). The following constraints are supported:
| Constraint | Description | Editor Type
| --- | --- | --- |
| `type` | The type of the value should match the type of the constraint | based on type |
| `Options` / `Container` | The value should be one of the options provided in the constraint | `QComboBox` |
| `StrOptions` | The value should be one of the str-options provided in the constraint | `QComboBox` |
| `Interval` | The value should be within the interval provided in the constraint | `QSpinBox` or `QDoubleSpinBox` (limited) |
| `None` | `None` is a valid value for this field `typing.Optional` | Adds reset-button to editor |
| `Range` | The value should be within the range provided in the constraint | `QSpinBox` (limited) |