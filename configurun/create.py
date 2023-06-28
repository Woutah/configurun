
"""
Convenience function to quickly create a local or networked app-instance (server/client/both) with the specified
target function and option source.
"""
import argparse
import logging
import os
import signal
import sys
import typing

from PySide6 import QtCore, QtWidgets

from configurun.classes.run_queue import RunQueue
from configurun.classes.run_queue_client import RunQueueClient
from configurun.classes.run_queue_server import RunQueueServer
from configurun.configuration.base_options import BaseOptions
from configurun.configuration.configuration import Configuration
from configurun.configuration.configuration_model import ConfigurationModel
from configurun.windows.main_window import APP_NAME, MainWindow
from configurun.windows.network_main_window import NetworkMainWindow
from configurun.configuration.argparse_to_dataclass import argparse_to_dataclass

log = logging.getLogger(__name__)


def _get_option_function(option_source:\
			typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]] | \
			argparse.ArgumentParser | \
			typing.Type[BaseOptions]
		) -> typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]]:
	"""Get the option-function from the passed argument.
	User is able to pass:
	- A function returning a dict of option (dataclass) objects,
	- A single BaseOptions object
	- An argparse.ArgumentParser object

	In this function, all are converted to the first - a function returning a dict of option objects.
	"""

	if isinstance(option_source, argparse.ArgumentParser):
		# raise NotImplementedError("argparse.ArgumentParser not yet implemented")
		argparse_dataclass = argparse_to_dataclass(option_source, "ArgparseOptions")
		def argparse_option_function(*_): #argparse-options: Return the argparse-dataclass
			return {"Options" : argparse_dataclass}
		return argparse_option_function #type: ignore
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
		workspace_path : str = "",
		create_workspace_path : bool = True, #Whether to create the workspace path if it does not exist
		run_queue_n_processes : int = 1,
		log_level : int = logging.INFO,
		run_queue_kwargs : typing.Optional[typing.Dict[str, typing.Any]] = None,
		config_model_kwargs : typing.Optional[typing.Dict[str, typing.Any]] = None,

	):
	"""Convenience function that constructs a local instance of the app with the specified target function and option
	source. Workspace path is option, if none is provided, uses '~/Configurun/'.

	Args:
		target_function (typing.Callable): The target function on which tasks will be run, this function should take
			a configuration as the first argument, and the rest of the arguments should be the arguments passed to the
			```RunQueue._process_queue_item()```-method.

		options_source (typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions]
		 		|  typing.Type[None]]]
				|, optional):
			The source of the options in the ui. This can either be:
				- A function returning a dict of option (dataclass) class,
				- A single BaseOptions-type class
				- An argparse.ArgumentParser class
			Defaults to None.
		workspace_path (str, optional): The path to the workspace folder. Attempts to load progress from here, also saves
		 	progress to here. Defaults to "". If empty/default, the default workspace folder is used (~/Configurun/)
		create_workspace_path (bool, optional): Whether to create the workspace path if it does not exist.
			Defaults to True.
		run_queue_n_processes (int, optional): The number of processes to use in the run queue. Defaults to 1.
		log_level (int, optional): The log level to use. Defaults to logging.INFO
		run_queue_kwargs (typing.Dict[str, typing.Any], optional): The keyword arguments passed to the
			RunQueue constructor. Defaults to {}.
			E.g.:
			- log_location (str) : The path where the log file should be outputted (should be a folder)
				if blank, use default location based on workspace folder
		config_model_kargs (typing.Dict[str, typing.Any], optional): The keyword arguments passed to the
			ConfigurationModel constructor. Defaults to {}.
			E.g.:
			- use_cache (bool): Whether to use the cache or not to temporarily save configurations. This makes it so
				option-group settings are remembered when switching back/forth (for example between 2 model-options).
				Defaults to True. If true undo_stack is also used
			- use_undo_stack (bool): Whether to use the undo stack or not. Defaults to True

	"""
	#=========== Initialize logger ===========
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}]  {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=log_level) #Without time
	root_logger = logging.getLogger()
	root_logger.setLevel(log_level)

	
	if run_queue_kwargs is None:
		run_queue_kwargs = {}
	if config_model_kwargs is None:
		config_model_kwargs = {}

	app = QtWidgets.QApplication(sys.argv)

	if workspace_path == "" or workspace_path is None: #Set to default workspace path if not set
		workspace_path = os.path.join(os.path.expanduser("~"), APP_NAME)
		log.info(f"No workspace path provided, using default: {workspace_path}")

	if not create_workspace_path and not os.path.exists(workspace_path):
		raise ValueError(f"Workspace path {workspace_path} does not exist and workspace-creation is set to False.")
	os.makedirs(workspace_path, exist_ok=True) #Create the workspace folder if it does not exist yet
	QtCore.QDir.setCurrent(workspace_path) #Set the current working directory to the workspace path

	run_queue = RunQueue(
		target_function=target_function,
		n_processes=run_queue_n_processes,
		log_location=os.path.join(workspace_path, "logs"),
		**run_queue_kwargs
	) #Create the run queue
	options_function = _get_option_function(options_source) #Create the options-function

	#Select a config-model, pass the deduce_new_option_class_types function to the constructor
	config_model = ConfigurationModel(
		option_type_deduction_function=options_function,
		**config_model_kwargs
	)

	#Create the Qt-main window in which the app will be placed
	main_window = QtWidgets.QMainWindow()

	#Create the actual app
	MainWindow(
		configuration_model=config_model,
		run_queue=run_queue,
		window=main_window,
		workspace_path=workspace_path
	)

	main_window.show() #Show the window
	app.exec()


def _cleanup_server(app : QtCore.QCoreApplication, run_queue_server : RunQueueServer):
	"""
	Callback function to, on process end (Ctrl+C), cleanup the server and close the app

	Args:
		app (QtCore.QCoreApplication): The app in which the server is running
		run_queue_server (RunQueueServer): The runqueue-server instance
	"""
	log.info("Received shutdown signal, now attempting to cleaning up server and close app")
	run_queue_server.terminate() #Disconnect all, stop running and save progress
	app.quit()
	
	log.info("Server cleanup complete, exiting")

def server(
			target_function : typing.Callable,
			workspace_path : str = "",
			run_queue_n_processes : int = 1,
			password : str = "",
			hostname : str = "localhost",
			port : int = 469,
			log_level : int = logging.INFO,
			run_queue_kwargs : typing.Optional[typing.Dict[str, typing.Any]] = None
		):
	"""
	WARNING: RUNNING A SERVER ALLOWS OTHER MACHINES ON THIS NETWORK TO EXECUTE ARBITRARY CODE IF THEY KNOW THE PASSWORD
	PLEASE RUN THIS IN A TRUSTED NETWORK ENVIRONEMENT. Run at your own risk.

	Convenience function that constructs a local instance of the runqueue-server with the specified target function.
	It then runs the server in a QtCore app.

	Args:
		target_function (typing.Callable): The target function on which tasks will be run, this function should take
			a configuration as the first argument, and the rest of the arguments should be the arguments passed to the
			```RunQueue._process_queue_item()```-method.

		workspace_path (str, optional): The path to the workspace folder. Attempts to load progress from here, also saves
			progress to here. Defaults to "". If empty/default, the default workspace folder is used (~/Configurun-server/)

		run_queue_n_processes (int, optional): The number of processes to use in the run queue. Defaults to 1.

		run_queue_kwargs (typing.Dict[str, typing.Any], optional): The keyword arguments passed to the
			RunQueue constructor. Defaults to {}.
			Possible kwargs:
				log_location (str) : The path where the log file should be outputted (should be a folder)
					if blank, use default location using TEMP folder
	"""
	#=========== Initialize logger ===========
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}]  {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=log_level) #Without time
	root_logger = logging.getLogger()
	root_logger.setLevel(log_level)



	if run_queue_kwargs is None:
		run_queue_kwargs = {}

	assert len(password) > 0, "Password for server cannot be empty"

	if workspace_path == "" or workspace_path is None:
		workspace_path = os.path.join(os.path.expanduser("~"), APP_NAME+"-Server")
		log.info(f"No workspace path provided, using default: {workspace_path}")

	os.makedirs(workspace_path, exist_ok=True) #Create the workspace folder if it does not exist yet
	QtCore.QDir.setCurrent(workspace_path) #Set the current working directory to the workspace path


	runqueue = RunQueue(
		target_function=target_function,
		n_processes=run_queue_n_processes,
		log_location=os.path.join(workspace_path, "logs"),
		**run_queue_kwargs
	)

	run_queue_server = RunQueueServer(
			run_queue=runqueue,
			password=password,
			hostname=hostname,
			port=port,
			workspace_path=workspace_path
	)

	app = QtCore.QCoreApplication(sys.argv) #Run the main event-loop (used for signals)
	#Create a runqueue client to run the runqueue in
	run_queue_server.run()
	log.info("Server started, listening for client connections...")

	timer = QtCore.QTimer()
	timer.start(500)
	timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms to catch signals
	signal.signal(signal.SIGINT, lambda *_: _cleanup_server(app, run_queue_server)) #Cleanup on Ctrl+C
	app.exec()


def client(
			options_source : \
				typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]] | \
				argparse.ArgumentParser | \
				typing.Type[BaseOptions],
			workspace_path : str = "",
			create_workspace_path : bool = True, #Whether to create the workspace path if it does not exist
			log_level : int = logging.INFO,
			config_model_kwargs : typing.Optional[typing.Dict[str, typing.Any]] = None,
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
	
	workspace_path (str, optional): The path to the workspace folder. Attempts to load progress from here, also saves
		configs/logs/settings to here. Defaults to "". If empty/default, the default workspace folder is used
		(~/Configurun-Client/)

	create_workspace_path (bool, optional): Whether to create the workspace path if it does not exist.
		Defaults to True.

	config_model_kwargs (typing.Dict[str, typing.Any], optional): The keyword arguments passed to the
		ConfigurationModel constructor. Defaults to {}.
		E.g.:
		- use_cache (bool): Whether to use the cache or not to temporarily save configurations. This makes it so
			option-group settings are remembered when switching back/forth (for example between 2 model-options).
			Defaults to True. If true undo_stack is also used
		- use_undo_stack (bool): Whether to use the undo stack or not. Defaults to True
	
	log_level (int, optional): The log level to use. Defaults to logging.INFO
	"""
	#=========== Initialize logger ===========
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}]  {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=log_level) #Without time
	root_logger = logging.getLogger()
	root_logger.setLevel(log_level)


	if config_model_kwargs is None:
		config_model_kwargs = {}

	app = QtWidgets.QApplication(sys.argv)

	if workspace_path == "" or workspace_path is None: #Set to default workspace path if not set
		workspace_path = os.path.join(os.path.expanduser("~"), APP_NAME+'-Client')
		log.info(f"No workspace path provided, using default: {workspace_path}")

	if not create_workspace_path and not os.path.exists(workspace_path):
		raise ValueError(f"Workspace path {workspace_path} does not exist and workspace-creation is set to False.")
	os.makedirs(workspace_path, exist_ok=True) #Create the workspace folder if it does not exist yet
	QtCore.QDir.setCurrent(workspace_path) #Set the current working directory to the workspace path

	options_function = _get_option_function(options_source) #Create the options-function

	#Select a config-model, pass the deduce_new_option_class_types function to the constructor
	config_model = ConfigurationModel(option_type_deduction_function=options_function, **config_model_kwargs)

	#Create the Qt-main window in which the app will be placed
	main_window = QtWidgets.QMainWindow()

	run_queue_client = RunQueueClient(	
	)


	#Create the actual app
	NetworkMainWindow(
		configuration_model=config_model,
		run_queue_client=run_queue_client,
		window=main_window,
		workspace_path=workspace_path,
	)

	main_window.show() #Show the window
	app.exec()

if __name__ == "__main__":
	from configurun.examples.example_configuration import \
	    example_deduce_new_option_classes
	from configurun.examples.example_run_function import example_run_function
	local_app(
		target_function=example_run_function,
		options_source=example_deduce_new_option_classes,
		run_queue_n_processes=1,
		log_level=logging.DEBUG
	)
