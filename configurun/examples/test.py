#In this example, we will create a callable which returns new options-classes based on the 
# current configuration
import os
import typing
from dataclasses import dataclass
from configurun.examples import example_target_function
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
	# from pyside6_utils.widgets.extended_mdi_area import run_example_app
# 	run_example_app()
	from configurun.examples.example_configuration import example_deduce_new_option_classes

	from configurun.create import server, client
	server(
		target_function=example_target_function,
		workspace_path = os.path.join(os.getcwd(), "Server-Example")
	)
	
	client(
		options_source=example_deduce_new_option_classes,
		workspace_path = os.path.join(os.getcwd(), "Server-Example")
	)
