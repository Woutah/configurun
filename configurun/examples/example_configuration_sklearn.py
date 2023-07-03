"""
This script runs the example in which we can select our model/dataset type - including Sklearn models
This example, in addition to the requirements.txt, requires the Sklearn library to be installed.
"""


import logging
import typing

from configurun.configuration.base_options import BaseOptions
from configurun.configuration.configuration import Configuration
from configurun.examples.example_options.example_options import (
    ExampleDatasetOptions, ExampleGeneralOptions,
    ExtendedExampleDatasetOptions)
from configurun.examples.example_options.example_sklearn_options import (
    SKLEARN_NAME_DATACLASS_DICT, SklearnMainOptions)

log = logging.getLogger(__name__)



def deduce_new_option_class_types(
			configuration : Configuration #|ExampleMainOptions | ExampleDatasetOptions | ExampleGeneralOptions #type: ignore
		) -> typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]:

	"""Deduce the new option class types from the current configuration"""
	configuration : SklearnMainOptions = configuration #Typehint the configuration  #type: ignore

	ret_dict = {
		"main_options" : SklearnMainOptions,
		"general_options" : ExampleGeneralOptions
	}

	if hasattr(configuration, "model_type"):
		if configuration.model_type is not None and configuration.model_type in SKLEARN_NAME_DATACLASS_DICT:
			#Return dataclass based on selected model
			ret_dict["model_options"] = SKLEARN_NAME_DATACLASS_DICT[configuration.model_type]
		else:
			pass

	if hasattr(configuration, "dataset_type"):
		if configuration.dataset_type is not None and configuration.dataset_type == "ExampleDataset":
			ret_dict["dataset_options"] = ExampleDatasetOptions
		elif configuration.dataset_type is not None and configuration.dataset_type == "ExtendedExampleDataset":
			ret_dict["dataset_options"] = ExtendedExampleDatasetOptions
		else:
			pass

	return ret_dict


def run_sklearn_example(log_level : int = logging.INFO):
	"""
	Starts the example-app using a dynimically created sklearn-model-options class
	"""
	# pylint: disable=import-outside-toplevel
	import os
	import tempfile
	from configurun.create.app import local_app
	from configurun.examples.example_target_function import example_target_function
	from configurun.windows.main_window import APP_NAME
	log.info("Starting the example implementation, including Sklearn models")
	tempdir = tempfile.gettempdir()
	workspace_path = os.path.join(tempdir, APP_NAME, "Configurun-Sklearn-Example")
	local_app(
		target_function = example_target_function,
		options_source = SklearnMainOptions,
		workspace_path=workspace_path,
		log_level=log_level

	)



if __name__ == "__main__":
	run_sklearn_example(log_level=logging.DEBUG)
