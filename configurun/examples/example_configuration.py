"""
This script runs the example in which we can select our model/dataset type.
"""



import logging
import typing

from configurun.configuration.base_options import BaseOptions
from configurun.configuration.configuration import Configuration
from configurun.examples.example_options.example_options import (
    ExampleDatasetOptions, ExampleGeneralOptions, ExampleMainOptions,
    ExampleModelOptions, ExtendedExampleDatasetOptions,
    ExtendedExampleModelOptions)
from configurun.examples.example_run_function import example_run_function

log = logging.getLogger(__name__)

def example_deduce_new_option_classes(
			#NOTE: all suboptions of the configucation can be accesed via the configuration.<attr> syntax.
			# For type hinting, we can create a union of all the suboptions classes we would like to use
			# in this example, we only use the main options. The actual type of the configuration argument is
			# Configuration, but we can use the ExampleMainOptions class as a type hint
			configuration : Configuration #|ExampleMainOptions | ExampleDatasetOptions | ExampleGeneralOptions #type: ignore
		) -> typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]:
	"""Deduce the new option classes from the current configuration

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


def run_example_app(log_level=logging.INFO):
	"""Run an example instance of the Configurun-App using the example run function and example-option-deducer
	"""
	# pylint: disable=import-outside-toplevel
	from configurun.create import \
	    local_app
	import os
	from configurun.windows.main_window import APP_NAME
	import tempfile

	#=========================== Create the app using the example ===========================
	tempdir = tempfile.gettempdir()
	workspace_path = os.path.join(tempdir, APP_NAME, os.path.splitext(__name__)[0])
	log.info(f"Saving example app workspace to {workspace_path}")
	local_app(
		target_function=example_run_function,
		options_source=example_deduce_new_option_classes,
		workspace_path=workspace_path,
		log_level=log_level
	)



if __name__ == "__main__":
	run_example_app(logging.DEBUG)
