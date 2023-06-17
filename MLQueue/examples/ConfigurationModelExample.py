"""Implements the Options & Optionsdata dataclass

The options class is a wrapper around the OptionsData class that provides convenience functions for loading/saving
options from/to a file and for creating a new options class from a set of passed options.
"""



import logging
import typing
from dataclasses import dataclass

from MLQueue.configuration.BaseOptions import BaseOptions
from MLQueue.configuration.ConfigurationModel import ConfigurationModel
from MLQueue.examples.ExampleOptions.ExampleOptions import (
    ExampleDatasetOptions, ExampleGeneralOptions, ExampleMainOptions,
    ExtendedExampleDatasetOptions, exam)

log = logging.getLogger(__name__)

# from MLQueue.configuration.Configuration import Configuration

@dataclass
class FrameworkConfigurationModel(ConfigurationModel): #TODO:
	"""
	Simple example of a configuration model
	"""

	def __init__(self):
		super().__init__()


	@staticmethod
	def deduce_new_option_class_types(
				#NOTE: all suboptions of the configucation can be accesed via the configuration.<attr> syntax
				# for type, hinting, we can create a union of all the suboptions classes we would like to use
				# in this example, we only use the main options. The actual type of the configuration argument is
				# Configuration, but we can use the ExampleMainOptions class as a type hint
				configuration : ExampleMainOptions #| ExampleDatasetOptions | ExampleGeneralOptions | 
			) -> typing.Dict[str, typing.Type[BaseOptions | None]]:
		"""Deduce the new option class types from the current configuration
		
		Based on the selection of the mainoptions, we can deduce the new option class types:
		 - main_options : Always ExampleMainOptions
		 - general_options : Always ExampleGeneralOptions
		 - model_options : ExampleDatasetOptions | ExtendedExampleDatasetOptions
		 - dataset_options : ExampleDatasetOptions | ExtendedExampleDatasetOptions

		Args:
			configuration (Configuration): The current configuration, we can typehint the main options
		"""
		ret_dict = {
			"main_options" : ExampleMainOptions,
			"general_options" : ExampleGeneralOptions
		}
		if configuration.dataset_type is not None and configuration.dataset_type == "extended_example":
			ret_dict["model_options"] = ExtendedExampleDatasetOptions
			ret_dict["dataset_options"] = ExtendedExampleDatasetOptions


		return ret_dict
	

if __name__ == "__main__":
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}]  {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.DEBUG) #Without time
	log.debug("Now running some tests for options dataclass parser")



