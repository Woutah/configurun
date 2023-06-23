"""
Implements ConfigurationData dataclass - this is a dataclass that holds the data for the actual Configuration class.
The configuration-class is a wrapper around the ConfigurationData class that provides convenience functions for
loading/saving options from/to a file and for creating a new options class from a set of passed options as well
as QT signals/slots for updating the GUI when the options are changed.

"""

from dataclasses import dataclass, field
import typing
from configurun.configuration.base_options import BaseOptions

@dataclass
class Configuration(object):
	"""
	A Configuration object is built up using several (sub-configuration / option) dataclass instances.
	This class is a wrapper around a dict of these sub-options classes. The __getattr__ function is used to
	allow the user to access any of the sub-options classes using the . operator.

	1. The main options, which are the options that are common to all models
	2. The general options, which are the options that are common to all tasks
	3. The model options, which are the options that are specific to the selected model
	4. The dataset options, which are the options that are specific to the selected dataset
	5. The training options, which are the options that are specific to the training goal/model/task

	These sub-options-classes are combined during runtime into a class instance which is similar to a dict of arguments.

	NOTE: due to the way the __getattr__ function is implemented, the sub-options classes must not have overlapping 
	attribute names.
	"""
	#Use factory to create empty dict
	options : typing.Dict[str, BaseOptions | None] = field(default_factory=dict)
	 #Dict in which the sub-option dataclasses are stored. Example of a
		# A possible configuration of this dict is:
		# {
		# 	"main_options": MainOptions,
		# 	"general_options": GeneralOptions,
		# 	"model_options": ModelOptions,
		# 	"dataset_options": DatasetOptions,
		# 	"training_options": TrainingOptions
		# }
		# Where each of the instances are dataclasses that inherit from BaseOptions


	def get_option_types(self) -> typing.Dict[str, type[BaseOptions] | type[None]]:
		"""Returns a dict of the current option-class types
			E.g.:
			{
				"model_options": SklearnModelOptions,
				"dataset_options": BaseDatasetOptions,
				"training_options": SklearnTrainingOptions
			}
		"""
		return {key: type(value) for key, value in self.options.items()}


	def hasattr(self, key):
		"""
		Check if one of the sub-options classes has the given attribute
		"""

		for options_class in self.options:
			if hasattr(options_class, key):
				return True
		return False

	def __getattr__(self, key : str):
		"""
		Allows the 'OptionsData' class to be used as a flattened dictionary / by using the . operator.
		This is useful when using this options class in training code as we can typehint to one of
		the option-classes and address the options using one . operator, e.g.:
		config.model_options.model_type becomes config.model_type

		For typehinting, we can use the typing.Union type, e.g.:
		def train_model(config : typing.Union[SklearnTrainingOptions, MvtsTrainingOptions]):
			#Do something with config.model_type


		NOTE: the limitation to this is that the suboptions classes must not have overlapping attribute names
		This is why validateSubOptions should be called when chaning suboptions
		TODO: check for overlapping attribute names in the __init__ function?
		"""

		if key.startswith("__"): #Return special/internal attributes, otherwise things like copy will go wrong
			raise AttributeError(f"Attribute {key} not found in any of the options classes")

		for options_instance in self.options.values():
			if hasattr(options_instance, key):
				return getattr(options_instance, key)

		raise AttributeError(f"Attribute {key} not found in any of the options classes")

	def get_dict(self):
		"""
		Return the sub-options instances as a dictionary
		"""
		return self.options


if __name__ == "__main__":
	#Run some tests on the ConfigurationData class to see whether lookup is working
	from copy import deepcopy
	test_config = Configuration()

	@dataclass
	class TestDataClass(BaseOptions):
		"""Test dataclass"""
		model_type : str = "sklearn"
		comment : str = "This is a test class"


	test_config.options["model_options"] = TestDataClass()
	print(hasattr(test_config, "model_type"))
	print(hasattr(test_config, "option"))
	print(test_config.options)
	print(test_config.model_type)
	copy = deepcopy(test_config)
