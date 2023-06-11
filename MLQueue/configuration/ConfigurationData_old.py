"""
Implements ConfigurationData dataclass - this is a dataclass that holds the data for the actual Configuration class.
The configuration-class is a wrapper around the ConfigurationData class that provides convenience functions for 
loading/saving options from/to a file and for creating a new options class from a set of passed options as well
as QT signals/slots for updating the GUI when the options are changed.

"""

from dataclasses import dataclass


@dataclass
class ConfigurationData():
	"""
	A ConfigurationData object is built up using several (sub-configuration / option) dataclass objects. 

	1. The main options, which are the options that are common to all models
	2. The general options, which are the options that are common to all tasks
	3. The model options, which are the options that are specific to the selected model
	4. The dataset options, which are the options that are specific to the selected dataset
	5. The training options, which are the options that are specific to the training goal/model/task

	These sub-options-classes are combined during runtime into a class instance which is similar to a dict of arguments.
	
	Note 
	"""
	main_options : object | None = None
	general_options : object | None = None
	model_options : object | None = None
	dataset_options : object | None = None
	training_options : object | None = None


	def hasattr(self, key):
		"""
		Check if one of the sub-options classes has the given attribute
		"""
		for options_class in [
					self.main_options,
					self.general_options,
					self.model_options,
					self.dataset_options,
					self.training_options
				]:
			if hasattr(options_class, key):
				return True
		return False

	def __getattr__(self, key):
		"""
		Allows the 'OptionsData' class to be used as a flattened dictionary / by using the . operator.
		This is useful when using this options class in training code as we can typehint to one of
		the option-classes and address the options using one . operator, e.g.:
		config.model_options.model_type becomes config.model_type

		NOTE: the limitation to this is that the suboptions classes must not have overlapping attribute names
		This is why validateSubOptions should be called when chaning suboptions
		TODO: check for overlapping attribute names in the __init__ function?
		"""
		for options_class in [
					self.main_options,
					self.general_options,
					self.model_options,
					self.dataset_options,
					self.training_options
				]:
			if hasattr(options_class, key):
				return getattr(options_class, key)

		raise AttributeError(f"Attribute {key} not found in any of the options classes TODO: does this work correctly?")

	def get_dict(self):
		"""
		Return the sub-options instances as a dictionary
		"""
		return {
			"main_options": self.main_options.__dict__,
			"general_options": self.general_options.__dict__,
			"model_options": self.model_options.__dict__,
			"dataset_options": self.dataset_options.__dict__,
			"training_options": self.training_options.__dict__
		}
