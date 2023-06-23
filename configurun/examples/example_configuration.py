"""
This script runs the example in which we can select our model/dataset type.
"""



import logging
import typing

from PySide6 import QtWidgets

from configurun.classes.run_queue import RunQueue
from configurun.windows.main_window import MainWindow
from configurun.configuration.base_options import BaseOptions
from configurun.configuration.configuration_model import ConfigurationModel
from configurun.configuration.configuration import Configuration
from configurun.examples.example_options.example_options import (
    ExampleDatasetOptions, ExampleGeneralOptions, ExampleMainOptions, ExampleModelOptions, ExtendedExampleModelOptions,
    ExtendedExampleDatasetOptions)
from configurun.examples.example_run_function import example_run_function

log = logging.getLogger(__name__)

def deduce_new_option_class_types(
			#NOTE: all suboptions of the configucation can be accesed via the configuration.<attr> syntax.
			# For type hinting, we can create a union of all the suboptions classes we would like to use
			# in this example, we only use the main options. The actual type of the configuration argument is
			# Configuration, but we can use the ExampleMainOptions class as a type hint
			configuration : Configuration #|ExampleMainOptions | ExampleDatasetOptions | ExampleGeneralOptions #type: ignore
		) -> typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]:
	"""Deduce the new option class types from the current configuration

	Based on the selection of the mainoptions, we can deduce the new option class types, in this example:
		- main_options : Always ExampleMainOptions
		- general_options : Always ExampleGeneralOptions
		- model_options : ExampleDatasetOptions | ExtendedExampleDatasetOptions
		- dataset_options : ExampleDatasetOptions | ExtendedExampleDatasetOptions

	Args:
		configuration (Configuration): The current configuration, we can typehint the main options
	"""
	configuration : ExampleMainOptions = configuration #Typehint the configuration  #type: ignore

	ret_dict = { #Always return the same main and general options
		"main_options" : ExampleMainOptions,
		"general_options" : ExampleGeneralOptions
	}

	#========== Select the dataset-class based on the dataset-selection in main-options ==========
	if hasattr(configuration, "dataset_type"):
		if configuration.dataset_type is not None and configuration.dataset_type == "ExampleDataset":
			ret_dict["dataset_options"] = ExampleDatasetOptions
		elif configuration.dataset_type is not None and configuration.dataset_type == "ExtendedExampleDataset":
			ret_dict["dataset_options"] = ExtendedExampleDatasetOptions
		else:
			# ret_dict["dataset_options"] = None #No dataset options - uncomment to display empty window
			pass #Remove if None selected
	# else: #NOTE: if we want to display an empty options-window, we can set the dataset_options to None
	# 	ret_dict["dataset_options"] = None



	#=========== Select the model based on the model-selection in main-options ===========
	if hasattr(configuration, "model_type"):
		if configuration.model_type is not None and configuration.model_type == "ExampleModel":
			ret_dict["model_options"] = ExampleModelOptions
		elif configuration.model_type is not None and configuration.model_type == "ExtendedExampleModel":
			ret_dict["model_options"] = ExtendedExampleModelOptions
		else:
			# ret_dict["model_options"] = None #No Model options Uncomment to display empty window
			pass #Remove if None selected
	# else: #NOTE: if we want to display an empty model-options-window, we can set the dataset_options to None
	# 	ret_dict["model_options"] = None

	return ret_dict


if __name__ == "__main__":
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}]  {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.INFO) #Without time
	log.debug("Now running a config-UI for the example options")

	#=========================== Do the following to create a configuration UI ===========================
	app = QtWidgets.QApplication([]) #We must first create a QApplication, after initializations, we call app.exec()

	#Select a config-model, pass the deduce_new_option_class_types function to the constructor
	config_model = ConfigurationModel(option_type_deduction_function=deduce_new_option_class_types)

	#Create the Qt-main window
	main_window = QtWidgets.QMainWindow()

	#Create a run-queue
	queue = RunQueue(target_function=example_run_function)

	#Build the main window in the qmainwindow using the configuration model and the run-queue
	ml_window = MainWindow(
		configuration_model=config_model,
		run_queue=queue,
		window=main_window
	)

	#Finally, show the main window and run the application
	main_window.show() #We must call show on the main window
	app.exec() #Run the application
