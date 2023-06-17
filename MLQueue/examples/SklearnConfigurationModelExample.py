"""This is a wrapper around the ConfigurationData class. It allows the options to be used in a UI using Pyside6 Views.
It implements a list of Sklearn-based machine-learning models
"""


from MLQueue.configuration.ConfigurationModel import ConfigurationModel
from MLQueue.examples.ExampleOptions.ExampleOptions import ExampleDatasetOptions
from MLQueue.examples.ExampleOptions.SklearnOptions import SklearnModelOptions

import typing

class SklearnConfigurationModel(ConfigurationModel):
	"""Sklearn model configuration model - """
    
	def _deduce_new_option_class_types_from_current(self) -> typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]:
		return {
			"main_options" : MainOptions,
			"general_options" : GeneralOptions,
			"model_options" : SklearnModelOptions,
			"dataset_options" : ExampleDatasetOptions,
			"training_options" : SklearnTrainingOptions
		}
    