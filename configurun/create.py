
"""
Convenience function to quickly create a local or networked app-instance (server/client/both) with the specified
target function and option source.
"""
import argparse
import sys
import typing

from PySide6 import QtWidgets, QtCore

from configurun.classes.run_queue import RunQueue
from configurun.classes.run_queue_client import RunQueueClient
from configurun.classes.run_queue_server import RunQueueServer
from configurun.configuration.base_options import BaseOptions
from configurun.configuration.configuration import Configuration
from configurun.configuration.configuration_model import ConfigurationModel
from configurun.windows.main_window import MainWindow
from configurun.windows.network_main_window import NetworkMainWindow


def _get_option_function(option_source:\
			typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]] | \
			argparse.ArgumentParser
		) -> typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]]:
	"""Get the option-function from the passed argument.
	User is able to pass:
	- A function returning a dict of option (dataclass) objects,
	- A single BaseOptions object
	- An argparse.ArgumentParser object

	In this function, all are converted to the first - a function returning a dict of option objects.
	"""

	if isinstance(option_source, argparse.ArgumentParser):
		raise NotImplementedError("argparse.ArgumentParser not yet implemented")
	elif isinstance(option_source, type) and issubclass(option_source, BaseOptions):
		def option_function(*_): #'Dumb'-options: Just return the option type
			return {"Options" : option_source}
		return option_function #type: ignore
	elif callable(option_source):
		return option_source
	else:
		raise ValueError(f"Invalid option_source: {option_source} of type {type(option_source)}")




def local_app(
		target_function : typing.Callable,
		options_source : \
			typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]] | \
			argparse.ArgumentParser | \
			typing.Type[BaseOptions]
				,
		run_queue_n_processes : int = 1,
		run_queue_kwargs : typing.Optional[typing.Dict[str, typing.Any]] = None,
		config_model_kargs : typing.Optional[typing.Dict[str, typing.Any]] = None,

	):
	"""Convenience function that constructs a local instance of the app with the specified target function and option
	source.

	Args:
		target_function (typing.Callable): The target function on which tasks will be run, this function should take
			a configuration as the first argument, and the rest of the arguments should be the arguments passed to the
			```RunQueue._process_queue_item()```-method.

		options_source (typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions]
		 		|  typing.Type[None]]]
				|, optional):
			The source of the options in the ui. This can either be:
				- A function returning a dict of option (dataclass) objects,
				- A single BaseOptions object
				- An argparse.ArgumentParser object
			Defaults to None.

		run_queue_n_processes (int, optional): The number of processes to use in the run queue. Defaults to 1.
		run_queue_kwargs (typing.Dict[str, typing.Any], optional): The keyword arguments passed to the
			RunQueue constructor. Defaults to {}.
			E.g.:
			- log_location (str) : The path where the log file should be outputted (should be a folder)
				if blank, use default location using TEMP folder
		config_model_kargs (typing.Dict[str, typing.Any], optional): The keyword arguments passed to the
			ConfigurationModel constructor. Defaults to {}.
			E.g.:
			- use_cache (bool): Whether to use the cache or not to temporarily save configurations. This makes it so
				option-group settings are remembered when switching back/forth (for example between 2 model-options).
				Defaults to True. If true undo_stack is also used
			- use_undo_stack (bool): Whether to use the undo stack or not. Defaults to True

	"""
	if run_queue_kwargs is None:
		run_queue_kwargs = {}
	if config_model_kargs is None:
		config_model_kargs = {}

	#Check if qt app is already running
	# if QtWidgets.QApplication.instance() is not None:
	# 	app = QtWidgets.QApplication.instance()
	# else:
	app = QtWidgets.QApplication(sys.argv)


	run_queue = RunQueue(
		target_function=target_function,
		n_processes=run_queue_n_processes,
		**run_queue_kwargs
	) #Create the run queue
	options_function = _get_option_function(options_source) #Create the options-function

	#Select a config-model, pass the deduce_new_option_class_types function to the constructor
	config_model = ConfigurationModel(option_type_deduction_function=options_function)

	#Create the Qt-main window in which the app will be placed
	main_window = QtWidgets.QMainWindow()

	#Create the actual app
	MainWindow(
		configuration_model=config_model,
		run_queue=run_queue,
		window=main_window
	)

	main_window.show() #Show the window
	app.exec()




def server(
			target_function : typing.Callable,
			run_queue_n_processes : int = 1,
			password : str = "",
			hostname : str = "localhost",
			port : int = 469,
			run_queue_kwargs : typing.Optional[typing.Dict[str, typing.Any]] = None
		):
	"""Convenience function that constructs a local instance of the runqueue-server with the specified target function.
	It then runs the server in a QtCore app.

	Args:
		target_function (typing.Callable): The target function on which tasks will be run, this function should take
			a configuration as the first argument, and the rest of the arguments should be the arguments passed to the
			```RunQueue._process_queue_item()```-method.


		run_queue_n_processes (int, optional): The number of processes to use in the run queue. Defaults to 1.

		run_queue_kwargs (typing.Dict[str, typing.Any], optional): The keyword arguments passed to the
			RunQueue constructor. Defaults to {}.
			Possible kwargs:
				log_location (str) : The path where the log file should be outputted (should be a folder)
					if blank, use default location using TEMP folder
	"""
	if run_queue_kwargs is None:
		run_queue_kwargs = {}

	assert len(password) > 0, "Password for server cannot be empty"
	runqueue = RunQueue(target_function=target_function, n_processes=run_queue_n_processes, **run_queue_kwargs)
	run_queue_server = RunQueueServer(
			run_queue=runqueue,
			password=password,
			hostname=hostname,
			port=port
	)

	app = QtCore.QCoreApplication(sys.argv) #Run the main event-loop (used for signals)
	#Create a runqueue client to run the runqueue in
	run_queue_server.run()
	app.exec()

def client(
			options_source : \
				typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]] | \
				argparse.ArgumentParser,
			config_model_kwargs : typing.Optional[typing.Dict[str, typing.Any]] = None
		):

	"""
	options_source (typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions]
			|  typing.Type[None]]]
			|, optional):
		The source of the options in the ui. This can either be:
			- A function returning a dict of option (dataclass) objects,
			- A single BaseOptions object
			- An argparse.ArgumentParser object
		Defaults to None.

	config_model_kargs (typing.Dict[str, typing.Any], optional): The keyword arguments passed to the
		ConfigurationModel constructor. Defaults to {}.
		E.g.:
		- use_cache (bool): Whether to use the cache or not to temporarily save configurations. This makes it so
			option-group settings are remembered when switching back/forth (for example between 2 model-options).
			Defaults to True. If true undo_stack is also used
		- use_undo_stack (bool): Whether to use the undo stack or not. Defaults to True
	"""
	if config_model_kwargs is None:
		config_model_kwargs = {}

	#Check if qt app is already running
	# if QtWidgets.QApplication.instance() is not None: #TODO: check if this works
	# 	app = QtWidgets.QApplication.instance()
	# else:
	app = QtWidgets.QApplication(sys.argv)


	options_function = _get_option_function(options_source) #Create the options-function

	#Select a config-model, pass the deduce_new_option_class_types function to the constructor
	config_model = ConfigurationModel(option_type_deduction_function=options_function, **config_model_kwargs)

	#Create the Qt-main window in which the app will be placed
	main_window = QtWidgets.QMainWindow()

	run_queue_client = RunQueueClient()


	#Create the actual app
	NetworkMainWindow(
		configuration_model=config_model,
		run_queue_client=run_queue_client,
		window=main_window
	)

	main_window.show() #Show the window
	app.exec()

if __name__ == "__main__":
	# parser = argparse.ArgumentParser()
	# parser.add_argument("--server", action="store_true", help="Run as server")
	# parser.add_argument("--client", action="store_true", help="Run as client")
	# parser.add_argument("--local", action="store_true", help="Run as both server and client")

	from configurun.examples.example_configuration import \
	    deduce_new_option_class_types
	from configurun.examples.example_run_function import example_run_function
	local_app(
		target_function=example_run_function,
		options_source=deduce_new_option_class_types,
		run_queue_n_processes=1,
	)