"""Implements the ConfigurationModel class - a wrapper around configurationData which enables us
to interact with a UI in a more friendly manner.

Provides us with a signal called proxyModelDictChanged, which is emitted whenever the proxy-models for the options
change.

NOTE: ConfigurationModel and ConfigurationData are separate to facilitate pickling, since the model inherits from
a QtObject, this would otherwise not be possible
"""
import copy
import json
import logging
import typing
from abc import abstractmethod
from dataclasses import dataclass

from PySide6 import QtCore, QtGui
from PySide6Widgets.Models.DataClassModel import DataclassModel

from MLQueue.configuration.BaseOptions import BaseOptions
from MLQueue.configuration.ConfigurationData import ConfigurationData
#import pyside6 qtobject metaclass


log = logging.getLogger(__name__)

JSON_DATACLASS_TYPES_KEY = "__dataclass_types__" #The key used in the json to store the dataclass types

# class AbstractQObjectMeta(type(QtCore.QObject), ABCMeta):
	# pass

@dataclass
class ConfigurationModel(QtCore.QObject): #TODO: Also inherit from ABC to make sure that the user implements methods
	"""
	Model-wrapper around ConfigurationData that provides an interface to get/set attributes with an underlying
	stack of undo/redo actions. This is useful for user interfaces that want to provide an undo/redo functionality
	for the options.

	NOTE: The models only stay up to date when interfacing ONLY with ConfigurationModel. If the ConfigurationData
		is changed directly, the models will not be updated.

	Abstract base-class for own implementations.
	User should implement the following methods:
		- get_option_data -> returns the options dataclass
	"""

	proxyModelDictChanged = QtCore.Signal(dict) #Signal that is emitted when the list of


	def __init__(self, use_cache : bool = True, use_undo_stack=True) -> None:
		"""The initialize of the class

		Args:
			use_cache (bool, optional): Whether the options class should use a cache. When the main_options are changed
				and .e.g. the model_options have to be changed, this checks the cache for an existing configuration
				of this type.
				This is useful when this class is used in a user interface. Defaults to False.
			use_undo_stack (bool, optional): Whether to use an undo stack. This makes it so undo/redo can be called to
				undo/redo actions. To ensure this works, enabling use_undo_stack automatically enables use_cache.
				Defaults to False.
		"""
		super().__init__()
		self.undo_stack = None
		if use_undo_stack:
			self.undo_stack = QtGui.QUndoStack()
		self._use_cache = use_cache or use_undo_stack #If use_undo_stack is enabled, automatically enable use_cache
		self._configuration_data = ConfigurationData()
		self._option_proxy_model_dict : typing.Dict[str, QtCore.QSortFilterProxyModel] = {} #A dict of proxy-models for
			#each options-group (e.g. model_options, dataset_options, training_options)

		self._option_proxy_model_connection : typing.Dict[str, typing.Any] = {} #A dict of connections for each model
		self._cached_option_instances : typing.Dict[type, BaseOptions] = {} #For each options-group (dataclass), we
			# can cache on instance, so that we don't have to create a new instance every time the options are changed
			# If use_cache is enabled, the last cached instance will be used when the options are changed, otherwise
			# a new instance will be created every time the options are changed
			#TODO: cache DataClassModel instead, might be nice - maybe save item-fold-state as well

	def get_proxy_model_dict(self):
		"""Return the dict with proxy models for each options class"""
		return self._option_proxy_model_dict

	def hasattr(self, key):
		"""Returns whether the underlying options dataclass has the given attribute"""
		return self._configuration_data.hasattr(key)
	def __getitem__(self, key):
		return self._configuration_data.__getattr__(key) #Just pass on the call to getattr
	def __getattr__(self, key):
		#Filter _ attributes
		# if key.startswith("_"):
		# 	super().__getattr__(key)
		return self._configuration_data.__getattr__(key) #Pass on the call to the options data class


	def update_sub_options(self):
		"""
		Should be called upon change of one of the settings. Updates the option classes based on the current
		configuration. E.g. if we select ```linear``` as model, the model_options class should be updated to
		the ```LinearModelOptions``` dataclass. This logic is defined by ```get_option_data_types```

		Calls the ```get_sub_options``` function to get the sub-options classes, then updates the sub-options classes
		by calling ```set_sub_options```
		"""
		all_classes = self.deduce_new_option_class_types()
		assert(len(all_classes) > 0), "No option classes were deduced from the current configuration, that means that \
			user will never be able to change the configuration - this should not happen"
		self.set_option_class_types(all_classes)

	@abstractmethod
	def deduce_new_option_class_types(self) -> typing.Dict[str, typing.Type[BaseOptions | None]]:
		"""
		Returns a list of all option-dataclass types for each option-group deduced from the current configuration.

		User should define their own logic here, a simple example would be to always return the same option classes:
			return { "Options" : AllOptionsInOneClass }
		or:
			return {
				"model_options": SklearnModelOptions,
				"dataset_options": BaseDatasetOptions,
				"training_options": SklearnTrainingOptions
			}
		But we can also return different options classes based on the current configuration, e.g.:
			if self._configuration_data.main_options.model == "linear":
				return {
					"main_options" : type(self._configuration_data.main_options) #leave unchanged
					"model_options": LinearModelOptions,
					"dataset_options": BaseDatasetOptions,
					"training_options": SklearnTrainingOptions
				}

		NOTE: the user-implemented class must ALWAYS return >= 1 option classes, otherwise the user will not be able
		to change the configuration at all
		TODO: enforce this using a wrapper in this parent class
		"""
		raise NotImplementedError("get_option_data_types not implemented yet")



	def set_option_class_types(self,
			    type_dict : typing.Dict[str, typing.Type[BaseOptions| None]]
			):
		"""Set the data_class_types by passing a dictionary with the option_name (e.g. model_options) as key, and the
		option class as value. This is useful when the options class is not yet known when initializing the class.

		Args:
			type_dict (typing.Dict[str, typing.Type[BaseOptions]]): A dictionary mapping a option-name to the actual
				option class type (not instance!), e.g. "model_options" -> SklearnModelOptions
		"""
		proxy_models_changed = False

		delete_items = [i for i in self._configuration_data.options if i not in type_dict] #Get all option-groups that
			# are in the current configuration but not in the new configuration -> delete these and their proxy models
		for del_item in delete_items:
			del self._configuration_data.options[del_item]
			del self._option_proxy_model_dict[del_item]
			proxy_models_changed = True

		for i, (option_name, option_class) in enumerate(type_dict.items()):
			if option_name not in self._configuration_data.options: #If key doesn't yet exist
				self._configuration_data.options[option_name] = None #Create key #type: ignore
				self._option_proxy_model_dict[option_name] = QtCore.QSortFilterProxyModel()
				proxy_models_changed = True
			elif option_class is None or isinstance(option_class, type(None)): #If None or Nonetype -> empty
				pass
			elif not isinstance(self._configuration_data.options[option_name], option_class): #If the option class changed
				pass
			else:  #If everything is the same, skip
				continue

			#If we arrived here, we're changing the options-instance

			#First cache current options instance (if enabled)
			if self._use_cache and self._configuration_data.options[option_name] is not None:
				self._cached_option_instances[
					type(self._configuration_data.options[option_name]) #type:ignore #NOTE: can't be none here
				] = self._configuration_data.options[option_name]

			#Then create new options instance
			if option_class is not None:
				self._configuration_data.options[option_name] = \
					self._cached_option_instances.get(option_class, option_class()) #Try cache, then create new instance
			else:
				self._configuration_data.options[option_name] = None

			self._option_proxy_model_dict[option_name].setSourceModel(
				DataclassModel(self._configuration_data.options[option_name], undo_stack=self.undo_stack)
			) #Set the new option-model

		#TODO: also emit signal for changed types

		if proxy_models_changed:
			self.proxyModelDictChanged.emit(self._option_proxy_model_dict)




	def validate_option_class_types(self):
		"""TODO: make sure that the options are valid -> no duplicate keys in each suboptions instance
		E.g. after loading a config from file
		"""
		class_types = self.deduce_new_option_class_types()

		assert set(class_types.keys()) == set(self._configuration_data.options.keys()), f"The keys in the options dict \
			did not match the keys in the class_types dict ({set(class_types.keys())} != \
			{set(self._configuration_data.options.keys())})"
		for key, value in class_types.items():
			assert isinstance(value, type(self._configuration_data.options[key])), f"Type of options class {key} did \
				not match the type in the class_types dict"


	def save_json_to(self, path : str, encoding="utf-8"):
		"""Save the current configuration as a json to the given path

		Each option-name is saved as a separte dict entry. The option-class-types are saved as a separte dict entry
		using the key JSON_DATACLASS_TYPES_KEY. This is useful for loading the configuration back from a file.
		"""

		composite_json = {}
		for option_name, option_instance in self._configuration_data.options.items():
			composite_json[option_name] = option_instance.__dict__

		str_dataclass_types = { #Save the dataclass types as strings to json for loading purposes
			key : str(type(val)) for key, val in self._configuration_data.options.items()
		}
		composite_json[JSON_DATACLASS_TYPES_KEY] = str_dataclass_types


		with open(path, "w", encoding=encoding) as write_file:
			write_file.write(json.dumps(composite_json, indent=4))
			return True


	def load_json_from(self, path : str, encoding : str="utf-8"):
		"""
		Load configuration from (json) file and validate that the options are valid.
		Args:
			path (str): The path to the file to load from
			encoding (str, optional): The encoding to use. Defaults to "utf-8".
		"""
		with open(path, "r", encoding=encoding) as infile:
			composite_json : dict = json.loads(infile.read())

		assert(JSON_DATACLASS_TYPES_KEY in composite_json), f"Could not find {JSON_DATACLASS_TYPES_KEY} in json file - \
			this is required to load the appropriate dataclass types"

		self._cached_option_instances = {} #Clear the cache
		if self.undo_stack:
			self.undo_stack.setActive(False) #Temporarily disable undo stack
			self.undo_stack.clear() #Clear the undo stack

		problem_dict = {}

		self._configuration_data.options = {} #Clear the options dict

		new_option_class_types : typing.Dict[str, type[BaseOptions | None]]= {} #The new option-class types

		for options_name, class_type in composite_json[JSON_DATACLASS_TYPES_KEY].items(): #parse types
			try:
				current_options_classtype = globals()[class_type]#Try to get the class from the module
				assert(isinstance(current_options_classtype, type(BaseOptions))), f"Could not find option-class \
					{class_type} for options-group {options_name} in this class should inherit from BaseOptions"
			except Exception as exception: #NOTE: catch all problems and report #pylint: disable=broad-exception-caught
					# make user decide whether to continue or not
				problem_dict[options_name] = f"{type(exception)}:{exception}"

		assert set.issubset(set(composite_json.keys()),
		      set( list(composite_json.keys()) + [JSON_DATACLASS_TYPES_KEY])),\
				"The keys in the loaded json file did not match the keys in the dataclass types dict, each item \
				should have its type defined, and each type should have its options defined (or None)"

		self.set_option_class_types(new_option_class_types) #Set the new option class types

		#Load the options from the json
		for options_name, options_class in self._configuration_data.options.items():
			if options_name == JSON_DATACLASS_TYPES_KEY: #Skip the dataclass types
				continue
			if options_class is None:
				problem_keys = composite_json.get(options_name, {}).keys() #We can't load anything
			else:
				problem_keys = options_class.copy_from_dict(
					composite_json[options_name], ignore_new_attributes=True
				) #Set the options dict
			if len(problem_keys) > 0:
				problem_dict[options_name] = KeyError(f"The following keys could not be found in the \
					options-class: {', '.join(problem_keys)} - unknown keys were ignored(!)")

		#Load new dataclass instances into the proxy models
		self.set_configuration_data(
			self._configuration_data, validate_after_setting=False
		)

		if self.undo_stack: #Re-enable undo stack
			self.undo_stack.setActive(True)

		log.info(f"Finished loading config from {path}")
		return problem_dict #Return the problem dict

	def get_configuration_data_copy(self):
		"""Returns a copy of the configuration_data object"""
		return copy.deepcopy(self._configuration_data)

	def reset_configuration_data_to_default(self):
		"""Reset the configuration data to the default values"""
		self._configuration_data = ConfigurationData()
		self.update_sub_options() #Update the sub-options based on empty configuration

	def set_configuration_data(self, configuration_data : ConfigurationData, validate_after_setting : bool = True):
		"""
		Set the configuration using configuration data. This is useful for copying the configuration from another
		instance. Updates all proxy-models and emits signals whenever neccesary to inform any coupled GUI's.

		Args:
			config (ConfigurationData): The configuration data to set
			validate_after_setting (bool, optional): Whether to validate the configuration after setting.
				If true, we will compare the loaded option-class-types to the option-class-types that would be loaded
				based on itself. If they don't match, we will raise an AttributeError. Defaults to True.
				Defaults to True.  #TODO: Might be better to always validate?

		NOTE: this resets the cache & undo stack
		"""

		self._configuration_data = configuration_data
		passed_class_types = configuration_data.get_option_types()

		#Clear the cache & pause the undo stack
		self._cached_option_instances = {}
		if self.undo_stack:
			self.undo_stack.setActive(False)

		proxy_model_changed = False

		for option_name, option_dataclass_instance in self._configuration_data.options.items():
			if option_name not in self._option_proxy_model_dict: #If this proxymodel does not already exists -> create
				self._option_proxy_model_dict[option_name] = QtCore.QSortFilterProxyModel()
				proxy_model_changed = True
			self._option_proxy_model_dict[option_name].setSourceModel(
				DataclassModel(option_dataclass_instance, undo_stack=self.undo_stack)
			)

		if validate_after_setting:
			deduced_types = self.deduce_new_option_class_types()
			if set(deduced_types.keys()) != set(passed_class_types.keys()):
				raise AttributeError(f"The passed configuration data has different option-class-types than the \
					deduced types. Passed: {passed_class_types.keys()}, deduced: {deduced_types.keys()} - this \
					could be because of different version, file corruption or a mistake when loading from/to json \
					functions")

		if proxy_model_changed: #Emit proxymodel changes
			self.proxyModelDictChanged.emit(self._option_proxy_model_dict)

		if self.undo_stack:
			self.undo_stack.clear()
			self.undo_stack.setActive(True)
