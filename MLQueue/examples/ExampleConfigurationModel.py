"""Implements the Options & Optionsdata dataclass

The options class is a wrapper around the OptionsData class that provides convenience functions for loading/saving
options from/to a file and for creating a new options class from a set of passed options.
"""



import logging
import typing

from PySide6 import QtWidgets

from MLQueue.classes.RunQueue import RunQueue
from MLQueue.windows.MainWindow import MainWindow
from MLQueue.configuration.BaseOptions import BaseOptions
from MLQueue.configuration.ConfigurationModel import ConfigurationModel
from MLQueue.configuration.Configuration import Configuration
from MLQueue.examples.ExampleOptions.ExampleOptions import (
    ExampleDatasetOptions, ExampleGeneralOptions, ExampleMainOptions, ExampleModelOptions, ExtendedExampleModelOptions,
    ExtendedExampleDatasetOptions)

log = logging.getLogger(__name__)

# from MLQueue.configuration.Configuration import Configuration


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

	ret_dict = {
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
			ret_dict["dataset_options"] = None #No model options


	#=========== Select the model based on the model-selection in main-options ===========
	if hasattr(configuration, "model_type"):
		if configuration.model_type is not None and configuration.model_type == "ExampleModel":
			ret_dict["model_options"] = ExampleModelOptions
		elif configuration.model_type is not None and configuration.model_type == "ExtendedExampleModel":
			ret_dict["model_options"] = ExtendedExampleModelOptions
		else:
			ret_dict["model_options"] = None

	return ret_dict


if __name__ == "__main__":
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}]  {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.DEBUG) #Without time
	log.debug("Now running a config-UI for the example options")

	config_model = ConfigurationModel(option_type_deduction_function=deduce_new_option_class_types)
	app = QtWidgets.QApplication([])
	#When creating a user interface, we instantiate a RunQueue, and a configuration model and pass them to the main window
	main_window = QtWidgets.QMainWindow()
	queue = RunQueue()
	ml_window = MainWindow(
		configuration_model=config_model,
		run_queue=queue,
		window=main_window
	)
	main_window.show()
	app.exec()


