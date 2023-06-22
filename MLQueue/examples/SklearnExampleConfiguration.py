"""
This script runs the example in which we can select our model/dataset type - including Sklearn models
This example, in addition to the requirements.txt, requires the Sklearn library to be installed.
"""


import logging
import typing

from MLQueue.configuration.BaseOptions import BaseOptions
from MLQueue.configuration.Configuration import Configuration
from MLQueue.configuration.ConfigurationModel import ConfigurationModel
from MLQueue.examples.ExampleOptions.ExampleOptions import (
    ExampleDatasetOptions, ExampleGeneralOptions,
    ExtendedExampleDatasetOptions)
from MLQueue.examples.ExampleOptions.SklearnOptions import (
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





if __name__ == "__main__":
	from MLQueue.create import local_app
	from MLQueue.examples.ExampleRunFunction import example_run_function
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}]  {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.INFO) #Without time
	log.info("Starting the example implementation, including Sklearn models")

	local_app(
		target_function = example_run_function,
		options_source = SklearnMainOptions
	)

