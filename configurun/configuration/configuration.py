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

	The individual option-instances are stored in the 'options' dict. The keys of this dict are the names of the
	sub-options classes, e.g. "model_options", "dataset_options", "training_options", etc.


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

	def hasinstance(self, instance_type: type) -> bool:
		"""
		Check if Configuration.options has an instance of the given type
		E.g.
		self.options = {
			"model_options": SklearnModelOptions,
			"dataset_options": BaseDatasetOptions,
		}
		self.hasinstance(SklearnModelOptions) -> True
		self.hasinstance(BaseDatasetOptions) -> True
		self.hasinstance(SklearnTrainingOptions) -> False
		"""
		for value in self.options.values():
			if isinstance(value, instance_type):
				return True
		return False
		# return any(isinstance(value, instance_type) for value in self.options.values())

	def hasattr(self, key):
		"""
		Check if one of the sub-options classes has the given attribute
		"""

		for options_class in self.options.values():
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

	def __getitem__(self, key):
		return self.__getattr__(key)
	
	def get(self, key : str, default : typing.Any):
		"""
		A safe alternative to the __getattr__ function. This function will return the default value if the given
		key is not found.

		Args:
			key (str): The attribute to look for
			default (typing.Any): The default value to return if the attribute is not found
		"""
		if key is None:
			return default
		try:
			return self.__getattr__(key)
		except AttributeError:
			return default


	def get_dict(self):
		"""
		Return the full configuration as a dict.
		"""
		new_dict = {}
		for key, value in self.options.items(): #Convert all sub-options instances to dicts
			new_dict[key] = value.__dict__
		return new_dict

	@staticmethod
	def get_configuration_from_passed_options(option_dict : typing.Dict[str, BaseOptions]) -> 'Configuration':
		"""
		Create a new Configuration instance from the passed options.

		Args:
			option_dict (typing.Dict[str, BaseOptions]): A dict of options to add to the configuration. Options must
				inherit from BaseOptions and must have the @dataclass-decorator to be fully compatible with
				the Configuration-ui app. If directly used for the attribute-lookup function of this class,
				this is not neccesry.

				NOTE: all options must have unique attribute names, otherwise the attribute-lookup function will
				return the first attribute it finds with the given name.

				#TODO: enforce this in the __init__ function of this class?
		"""
		new_config = Configuration()
		new_config.options = option_dict #type: ignore
		return new_config


if __name__ == "__main__":
	#Run some tests on the ConfigurationData class to see whether lookup is working
	test_config = Configuration()

	@dataclass
	class TestDataClass(BaseOptions):
		"""Test dataclass"""
		model_type : str = "sklearn"
		comment : str = "This is a test class"


	test_config.options["model_options"] = TestDataClass()
	print(hasattr(test_config, "model_type"))
	print(hasattr(test_config, "option"))
	print(isinstance(test_config, Configuration))
	print(isinstance(test_config, TestDataClass))
	# print(test_config.options)
	# print(test_config.model_type)
	# copy = deepcopy(test_config)
