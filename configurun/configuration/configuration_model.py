"""
Implements the ConfigurationModel class - a wrapper around the Configuration which enables us
to interact with a UI in a more friendly manner and provides an undo/redo stack as well as a method to
iteratively build up a configuration by returning Configuration suboption dataclass-instances based on the
current configuration.

Provides us with a signal called proxyModelDictChanged, which is emitted whenever the proxy-models for the options
change.

NOTE: ConfigurationModel and ConfigurationData are separate to facilitate pickling, since the model inherits from
a QtObject, this would otherwise not be possible
"""
import copy
import json
import logging
from pydoc import locate
import typing
# from abc import abstractmethod
from dataclasses import dataclass
from collections import OrderedDict

from PySide6 import QtCore, QtGui
from pyside6_utils.models import DataclassModel
from pyside6_utils.utility import SignalBlocker

from configurun.configuration.base_options import BaseOptions
from configurun.configuration.configuration import Configuration
#import pyside6 qtobject metaclass


log = logging.getLogger(__name__)

JSON_DATACLASS_TYPES_KEY = "__dataclass_types__" #The key used in the json to store the dataclass types

class UnkownOptionClassError(Exception):
	"""Exception raised when an unknown option class is encountered"""

class NotInOptionsDataClassError(Exception):
	"""Exception raised when an attribute is not in the options dataclass"""

class NotInLoadFileError(Exception):
	"""Exception raised when an attribute is not in the load file"""

class NoClassTypesError(Exception):
	"""Exception raised when no class types are found when loading the settings from a file"""

class OptionTypesMismatch(Exception):
	"""Exception raised when the option-types of the configuration and loaded file do not match"""

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

	proxyModelDictChanged = QtCore.Signal(OrderedDict) #Signal that is emitted when the list of


	def __init__(self,
	      	option_type_deduction_function :\
				typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]],
	      	use_cache : bool = True,
			use_undo_stack=True) -> None:
		"""The initialize of the class

		Args:
			option_type_deduction_function (typing.Callable[[Configuration], typing.Dict[str, typing.Type[BaseOptions | None]]]):
				A function that returns a dict of option-class-types for each option-group (e.g. model_options,
				dataset_options, training_options). This is useful when dynamically switching between different sub-options
				classes based on the current configuration. The function should return a dict with the option-name
				(e.g. model_options) as key, and the option class as value.
				NOTE: this function should ALWAYS return >= 1 option classes, otherwise the user will not be able to
				change the configuration at all (we would be stuck with an empty configuration).

			use_cache (bool, optional): Whether the options class should use a cache. When the main_options are changed
				and .e.g. the model_options have to be changed, this checks the cache for an existing configuration
				of this type.
				This is useful when this class is used in a user interface. Defaults to False.
			use_undo_stack (bool, optional): Whether to use an undo stack. This makes it so undo/redo can be called to
				undo/redo actions. To ensure this works, enabling use_undo_stack automatically enables use_cache.
				Defaults to False.
		"""
		super().__init__()

		self._option_type_deduction_function = option_type_deduction_function
		self.undo_stack = None
		if use_undo_stack:
			self.undo_stack = QtGui.QUndoStack()
		self._use_cache = use_cache or use_undo_stack #If use_undo_stack is enabled, automatically enable use_cache
		self._configuration = Configuration()
		self._option_proxy_model_dict : typing.OrderedDict[str, QtCore.QSortFilterProxyModel] = OrderedDict({})
			# A dict of proxy-models for
			# each options-group (e.g. model_options, dataset_options, training_options)
			# Order can be used e.g. by the UI to display the options in the right order

		# self._option_proxy_model_connection : typing.Dict[str, typing.Any] = {} #A dict of connections for each model
		self._cached_option_instances : typing.Dict[type, BaseOptions] = {} #For each options-group (dataclass), we
			# can cache on instance, so that we don't have to create a new instance every time the options are changed
			# If use_cache is enabled, the last cached instance will be used when the options are changed, otherwise
			# a new instance will be created every time the options are changed
			#TODO: cache DataClassModel instead, might be nice - maybe save item-fold-state as well


	def get_proxy_model_dict(self) -> typing.OrderedDict[str, QtCore.QSortFilterProxyModel]:
		"""Return the dict with proxy models for each options class"""
		return self._option_proxy_model_dict

	def hasattr(self, key):
		"""Returns whether the underlying options dataclass has the given attribute"""
		return self._configuration.hasattr(key)
	def __getitem__(self, key):
		return self._configuration.__getattr__(key) #Just pass on the call to getattr
	def __getattr__(self, key):
		#Filter _ attributes
		# if key.startswith("_"):
		# 	super().__getattr__(key)
		return self._configuration.__getattr__(key) #Pass on the call to the options data class


	def update_sub_options(self):
		"""
		Should be called upon change of one of the settings. Updates the option classes based on the current
		configuration. E.g. if we select ```linear``` as model, the model_options class should be updated to
		the ```LinearModelOptions``` dataclass. This logic is defined by ```get_option_data_types```

		Calls the ```get_sub_options``` function to get the sub-options classes, then updates the sub-options classes
		by calling ```set_sub_options```

		Args:
			emit_changes (bool, optional): Whether to emit the proxyModelDictChanged signal if changes occur.
				Defaults to True.
		"""
		all_classes = self._deduce_new_option_classes_from_current()
		assert(len(all_classes) > 0), "No option classes were deduced from the current configuration, that means that \
			user will never be able to change the configuration - this should not happen"
		self.set_option_class_types(all_classes)

	def _deduce_new_option_classes_from_current(self) -> typing.Dict[str, typing.Type[BaseOptions | None]]:
		"""
		Returns a list of all option-dataclass types for each option-group deduced from the current configuration.

		User should define their own logic inside of the type-deduction-function, which is set when initiating this class.
		A simple example would be:
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
			else:
				etc...

		NOTE: the user-implemented class must ALWAYS return >= 1 option (data)classes, otherwise the user will not be able
		to change the configuration at all, this assert is also checked. The option-classes should all inherit from
		BaseOptions.
		"""
		new_option_classes = self._option_type_deduction_function(self._configuration)
		assert len(new_option_classes) > 0, ("No option classes were deduced from the current configuration, that means "
			"user will never be able to change the configuration - this should not happen. Make sure "
			"deduce_new_option_classes returns at least 1 dataclass-type that inherits from BaseOptions.")
		return new_option_classes

	def set_option_class_types(self,
			    type_dict : typing.Dict[str, typing.Type[BaseOptions| None]]
			):
		"""Set the data_class_types by passing a dictionary with the option_name (e.g. model_options) as key, and the
		option class as value. This is useful when the options class is not yet known when initializing the class.

		NOTE: the order of the keys does matter, if the order changes, a change is still emitted
		NOTE: if a pre-existing key is not present in type_dict, it will be deleted from the configuration

		Args:
			type_dict (typing.Dict[str, typing.Type[BaseOptions]]): A dictionary mapping a option-name to the actual
				option class type (not instance!), e.g. "model_options" -> SklearnModelOptions

		"""
		proxy_models_changed = False

		delete_items = set([i for i in self._configuration.options if i not in type_dict]) #Get all option-groups that
			# are in the current configuration but not in the new configuration -> delete these and their proxy models

		delete_items = delete_items.union(
			set([i for i in self._option_proxy_model_dict if i not in type_dict])) #Also delete proxy models

		for del_item in list(delete_items): #Remove all items that are not in the new configuration
			if del_item in self._configuration.options.keys():
				del self._configuration.options[del_item]
			if del_item in self._option_proxy_model_dict.keys():
				del self._option_proxy_model_dict[del_item]
			proxy_models_changed = True

		for i, (option_name, option_class) in enumerate(type_dict.items()):
			if option_name not in self._configuration.options: #If key doesn't yet exist
				self._configuration.options[option_name] = None #Create key #type: ignore
				self._option_proxy_model_dict[option_name] = QtCore.QSortFilterProxyModel()
				proxy_models_changed = True
			elif option_class is None or isinstance(option_class, type(None)): #If None or Nonetype -> empty
				pass
			# elif type(self._configuration.options[option_name]) != option_class: #If the option class changed #pylint: disable=unidiomatic-typecheck
			elif type(self._configuration.options[option_name]).__name__ != option_class.__name__: #If the option class changed #pylint: disable=unidiomatic-typecheck
				#NOTE: this only checks the type NAME not the actual type. This makes us more flexible when saving/loading
				# dill pickles, but might result in issues if the user uses class names interchangeably. 
				# Note that on-load, we check for any attributes that are missing, so this might not be an issue.
				pass
			else:  #If everything is the same, skip
				continue

			#If we arrived here, we're changing the options-instance

			#First cache current options instance (if enabled)
			if self._use_cache and self._configuration.options[option_name] is not None:
				self._cached_option_instances[
					type(self._configuration.options[option_name]) #type:ignore #NOTE: can't be none here
				] = self._configuration.options[option_name]

			#Then create new options instance
			if option_class is not None:
				self._configuration.options[option_name] = \
					self._cached_option_instances.get(option_class, option_class()) #Try cache, then create new instance
			else:
				self._configuration.options[option_name] = None
			
			if self._configuration.options[option_name] is not None:
				new_model = DataclassModel(self._configuration.options[option_name], undo_stack=self.undo_stack)
				#TODO: if ANY of the models change, this signal is emitted. Might not be neccesary in most cases (e.g.)
				# Main options might update the model options, but not the other way around. Maybe use a list of
				# option-groups for which we monitor changes, and only emit the signal if one of those changes.
				new_model.dataChanged.connect(self.update_sub_options)
			else:
				new_model = None
			self._option_proxy_model_dict[option_name].setSourceModel(
				new_model
			) #Set the new option-model



		#======= Sort the keys of the proxy model according to the received order ============
		for key1, key2 in zip(self._option_proxy_model_dict.keys(), type_dict.keys()):
			if key1 != key2: #If key order not the same
				proxy_models_changed = True
				new_dict = OrderedDict({})
				for key in type_dict.keys(): #Construct new dict in the right order
					new_dict[key] = self._option_proxy_model_dict[key]
				self._option_proxy_model_dict = new_dict
				break

		#Inform UI of changes, if any
		if proxy_models_changed:
			self.proxyModelDictChanged.emit(self._option_proxy_model_dict)




	# def validate_option_class_types(self):
	# 	"""TODO: make sure that the options are valid -> no duplicate keys in each suboptions instance
	# 	E.g. after loading a config from file
	# 	"""
	# 	class_types = self._deduce_new_option_class_types_from_current()

	# 	assert set(class_types.keys()) == set(self._configuration.options.keys()), f"The keys in the options dict \
	# 		did not match the keys in the class_types dict ({set(class_types.keys())} != \
	# 		{set(self._configuration.options.keys())})"
	# 	for key, value in class_types.items():
	# 		assert isinstance(value, type(self._configuration.options[key])), f"Type of options class {key} did \
	# 			not match the type in the class_types dict"


	def save_json_to(self, path : str, encoding="utf-8"):
		"""Save the current configuration as a json to the given path

		Each option-name is saved as a separte dict entry. The option-class-types are saved as a separte dict entry
		using the key JSON_DATACLASS_TYPES_KEY. This is useful for loading the configuration back from a file.
		"""

		composite_json = {}
		for option_name, option_instance in self._configuration.options.items():
			composite_json[option_name] = option_instance.__dict__

		str_dataclass_types = { #Save the dataclass types as strings to json for loading purposes
			key : str(type(val).__module__ + "." + type(val).__qualname__)\
					for key, val in self._configuration.options.items() #Generate <module>.<classname> string
		}
		composite_json[JSON_DATACLASS_TYPES_KEY] = str_dataclass_types


		with open(path, "w", encoding=encoding) as write_file:
			write_file.write(json.dumps(composite_json, indent=4))
			return True


	def load_json_from(self,
				path : str,
				encoding : str="utf-8",
				load_using_classtypes_key = True,
				ignore_unknown_option_types : bool = False
		) -> dict[str, list[Exception]]:
		"""
		Load configuration from (json) file and validate that the options are valid.

		Args:
			path (str): The path to the file to load from
			encoding (str, optional): The encoding to use. Defaults to "utf-8".
			load_using_classtypes_key (bool, optional): Whether to load the configuration using the
				classtypes-key that is saved in the json file. Defaults to True. If not true, we will start with
				the default options and load as many of the options as possible, then update the configuration,
				then try to fill sub-options again until no changes are made.
			ignore_unknown_option_types (bool, optional): Only used when loading using classtype keys.
				If the dataclass types in the json file do not match any known class-types, decides whether to continue
				loading, or to raise an exception. Defaults to True.
		"""
		if load_using_classtypes_key:
			return self._load_json_using_classtypes_key(
					path, encoding, ignore_unknown_option_types=ignore_unknown_option_types
				)
		else:
			return self._load_using_option_deduction(path, encoding)

	def _load_using_option_deduction(self,
				path : str,
				encoding : str ="utf-8"
			) -> dict[str, list[Exception]]:
		"""Load the configuration from json using the deduced option types

		We start by first loading the default options, then loading the json file and filling
		as much of the options as possible, then updating the configuration and filling options again until all
		suboptions have been loaded or until no changes occur. This method makes it so it is not neccesary to save the
		class-types in the json, but may make errors more unclear if old configurations are loaded when using a new
		configuration class. It might be preferable to first try to load using the classtypes key, and if that fails,
		try to load using option deduction.

		"""
		log.info("Now trying to load configuration using option deduction")
		with open(path, "r", encoding=encoding) as infile:
			composite_json : dict[str, dict] = json.loads(infile.read())

		loaded_options = set({})
		option_keys = set( #Load all settings from json that do not describe the dataclass types, or start with _
			[key for key in composite_json if key != JSON_DATACLASS_TYPES_KEY and not key.startswith("_")]
		)

		problem_dict : dict[str, list[Exception]] = {}
		with SignalBlocker(self): #Temporarily block signals while updating
			self.reset_configuration_data_to_default() #Reset the configuration data to the default values
			has_changed = True
			while has_changed: #as long as updates occur
				self.update_sub_options() #Update the new sub-options
				has_changed = False
				for option_groupname in list(option_keys):
					if option_groupname == JSON_DATACLASS_TYPES_KEY \
							or option_groupname.startswith("_") \
							or option_groupname in loaded_options: #Skip already loaded options
						continue
					if option_groupname in self._configuration.options.keys() \
							and self._configuration.options[option_groupname] is not None \
							and option_groupname not in loaded_options: #If the dataclass-type is known, start loading
						loaded_options.add(option_groupname)
						in_json_but_not_dataclass, in_dataclas_but_not_json =\
							self._configuration.options[option_groupname].copy_from_dict( #type: ignore
								composite_json.get(option_groupname, {}), ignore_new_attributes=True
						) #Set the options dict
						has_changed = True
						for key in in_json_but_not_dataclass:
							err = NotInOptionsDataClassError(f"<tt>{key}</tt> setting was set in the json file "
								f"for group <tt>{option_groupname}</tt>, but "
								f"settings-dataclass has no attr by this name - its value was discarded.")
							if option_groupname in problem_dict:
								problem_dict[option_groupname].append(err)
							else:
								problem_dict[option_groupname] = [err]

						for key in in_dataclas_but_not_json:
							err = NotInLoadFileError(f"<tt>{key}</tt> is a dataclass attribute for group "
									f"<tt>{option_groupname}</tt>, but this key could "
									f"not be found in the loaded file - its value was discarded.")
							if option_groupname in problem_dict:
								problem_dict[option_groupname].append(err)
							else:
								problem_dict[option_groupname] = [err]

		#Add non-existing options to problem dict
		for option_groupname in option_keys - loaded_options:
			if option_groupname not in problem_dict:
				problem_dict[option_groupname] = []
			problem_dict[option_groupname] += [KeyError(
				f"Was not able to load <{option_groupname}> by deducing option-classtypes. All settings in this "
				f"  option-group were discarded(!). Is this group missing from the loaded file?")]

		self.reload_all_dataclass_models() #Update all linked proxymodels to reflect the new dataclass instances
		self.proxyModelDictChanged.emit(self._option_proxy_model_dict) #Just emit signal, assume that changes were made

		return problem_dict

	def _load_json_using_classtypes_key(self,
				path : str,
				encoding : str="utf-8",
				ignore_unknown_option_types : bool = False
		) -> dict[str, list[Exception]]:
		"""
		Load configuration from (json) file and validate that the options are valid.
		This load-method assumes the class-types are held inside of the json file, using the key JSON_DATACLASS_TYPES_KEY

		Alternatively, loading can be done by first loading the default options, then loading the json file and filling
		as much of the options as possible, then updating the configuration and filling options again until all
		suboptions have been loaded. This method makes it so it is not neccesary to save the class-types in the json,
		but may make errors more unclear if old configurations are loaded when using a new configuration class.

		Args:
			path (str): The path to the file to load from
			encoding (str, optional): The encoding to use. Defaults to "utf-8".
			ignore_unknown_option_types (bool, optional): If the dataclass types in the json file do not match any
				known class-types, decides whether to continue loading, or to raise an error. Defaults to True.
				If true, raises a UnknowOptionClassError, otherwise continues loading.
		"""
		with open(path, "r", encoding=encoding) as infile:
			composite_json : dict = json.loads(infile.read())

		if JSON_DATACLASS_TYPES_KEY not in composite_json:
			raise NoClassTypesError(f"Could not find {JSON_DATACLASS_TYPES_KEY} in json file - this is required"
				f"to load the appropriate dataclass types")

		self._cached_option_instances = {} #Clear the cache
		if self.undo_stack:
			self.undo_stack.setActive(False) #Temporarily disable undo stack
			self.undo_stack.clear() #Clear the undo stack

		problem_dict = {}

		self._configuration.options = {} #Clear the options dict

		new_option_class_types : typing.Dict[str, type[BaseOptions | None]]= {} #The new option-class types

		for option_groupname, class_type in composite_json[JSON_DATACLASS_TYPES_KEY].items(): #parse types
			try:
				current_options_classtype = locate(class_type) #Try to get the class from the module
				if current_options_classtype is None:
					raise UnkownOptionClassError(
						f"Could not find option-class <tt>{class_type}</tt> for options-group <tt>{option_groupname}</tt>"
						f", the whole(!) options group will be discarded...")

				assert(isinstance(current_options_classtype, type(BaseOptions))), \
					f"Found option type {current_options_classtype} for options-group {option_groupname}, but this is not a"\
					f"subclass of {type(BaseOptions).__name__} - this is required, whole(!) options group will be discarded..."

				new_option_class_types[option_groupname] = current_options_classtype #Add the new option class type #type:ignore
			except Exception as exception: #NOTE: catch all problems and report #pylint: disable=broad-exception-caught
					# make user decide whether to continue or not
				problem_dict[option_groupname] = [exception]

		if problem_dict and not ignore_unknown_option_types: #If unkown option types were found
			new_ex = UnkownOptionClassError(
				f"Could not load configuration from {path} because of unknown option dataclass"\
				f"types for {', '.join(problem_dict.keys())}"
			)
			new_ex.args += (problem_dict,)
			raise new_ex

		assert set.issubset(set(composite_json.keys()),
		      set( list(composite_json.keys()) + [JSON_DATACLASS_TYPES_KEY])),\
				"The keys in the loaded json file did not match the keys in the dataclass types dict, each item \
				should have its type defined, and each type should have its options defined (or None)"

		self.set_option_class_types(new_option_class_types) #Set the new option class types

		#Load the options from the json
		for option_groupname, options_class in self._configuration.options.items():
			if option_groupname == JSON_DATACLASS_TYPES_KEY: #Skip the dataclass types
				continue
			if option_groupname.startswith("_"): #Skip private attributes
				log.warning(
					f"Skipping private attribute {option_groupname} - names starting with _ are skipped when loading")
			if options_class is None:
				in_json_but_not_dataclass = composite_json.get(option_groupname, {}).keys() #We can't load, all keys are errors
				in_dataclas_but_not_json = []
			else:
				in_json_but_not_dataclass, in_dataclas_but_not_json = options_class.copy_from_dict(
					composite_json[option_groupname], ignore_new_attributes=True
				) #Set the options dict
			for key in in_json_but_not_dataclass:
				err = NotInOptionsDataClassError(f"<tt>{key}</tt> setting was set in the json file "
					f"for group <tt>{option_groupname}</tt>, but "
					f"settings-dataclass has no attr by this name - its value was discarded.")
				if option_groupname in problem_dict:
					problem_dict[option_groupname].append(err)
				else:
					problem_dict[option_groupname] = [err]

			for key in in_dataclas_but_not_json:
				err = NotInLoadFileError(f"<tt>{key}</tt> is a dataclass attribute for group "
						f"<tt>{option_groupname}</tt>, but this key could "
						f"not be found in the loaded file - its value was discarded.")
				if option_groupname in problem_dict:
					problem_dict[option_groupname].append(err)
				else:
					problem_dict[option_groupname] = [err]
#Load new dataclass instances into the proxy models
		self.set_configuration_data(
			self._configuration, validate_after_setting=False
		)

		if self.undo_stack: #Re-enable undo stack
			self.undo_stack.setActive(True)

		#Also emit signal, assume that changes were made
		self.proxyModelDictChanged.emit(self._option_proxy_model_dict)

		log.info(f"Finished loading config from {path}")
		self.reload_all_dataclass_models() #Update all linked proxymodels to reflect the new dataclass instances
		return problem_dict #Return the problem dict

	def get_configuration_data_copy(self):
		"""Returns a copy of the configuration_data object"""
		return copy.deepcopy(self._configuration)

	def reset_configuration_data_to_default(self):
		"""Reset the configuration data to the default values"""
		self._configuration = Configuration()

		if self.undo_stack:
			self.undo_stack.clear()
		self.update_sub_options() #Update the sub-options based on empty configuration

	def reload_dataclass_model(self, option_name : str):
		"""Reload the dataclass-model for the given option-group name"""
		new_model = DataclassModel(self._configuration.options[option_name], undo_stack=self.undo_stack)
		self._option_proxy_model_dict[option_name].setSourceModel(
			new_model
		) #Set the new option-model

		#TODO: if ANY of the models change, we update all types. Might not be neccesary in most cases (e.g.)
		# Main options might update the model options, but not the other way around. Maybe use a list of
		# option-groups for which we monitor changes, and only emit the signal if one of those changes.
		new_model.dataChanged.connect(self.update_sub_options)

	def reload_all_dataclass_models(self):
		"""Reloads all dataclass models - re-reading all current values from the dataclass instances"""
		for option_name in self._configuration.options:
			self.reload_dataclass_model(option_name)

	def validate_current_configuration(self):
		"""Checks whether the current configuration is 'stable', meaning that the options are valid and
		no changes will be made to the sub-options classes when updating the configuration.

		If not, raises a key-error.
		"""
		cur_class_types = self._configuration.get_option_types()
		deduced_types = self._deduce_new_option_classes_from_current()

		option_group_mismatches = set.difference(set(cur_class_types.keys()), set(deduced_types.keys()))
		error_msgs = []
		if len(option_group_mismatches) > 0:
			class_group_names = ", ".join(cur_class_types.keys())
			deduced_group_names = ", ".join(deduced_types.keys())
			error_msgs.append(f"The configuration has option-names that differ from the deduced names.\n"
				f"Current option-names:\n{class_group_names}\n"
				f"Deduced option-names:\n{deduced_group_names}\n"
				)
		#NOTE: only check name-equivalence, not strong type-equivalence

		class_type_names = [i.__name__ for i in cur_class_types.values()]
		deduced_type_names = [i.__name__ for i in deduced_types.values()]
		option_type_mismatches = set.symmetric_difference(set(class_type_names), set(deduced_type_names))

		
		# option_type_mismatches = set.symmetric_difference(set(cur_class_types.values()), set(deduced_types.values()))
		#NOTE: dill pickles by value if defined in the __main__ module -> if errors are reported here when loading
		# this could be the issue... Probably best to first try to construct the class by deducing the types and 
		# copying attributes over. We currently only check the type-names. This makes us more flexible but might 
		# result in issues (though we're checking attributes when loading/saving the items so it might not be an issue)


		if len(option_type_mismatches) > 0:
			current_type_names = ", ".join([i.__name__ for i in cur_class_types.values()])
			deduced_type_names = ", ".join([i.__name__ for i in deduced_types.values()])
			option_type_mismatch_names = ", ".join([i for i in option_type_mismatches])
			error_msgs.append(f"The configuration has types that differ "
				f"differ from the expected (deduced) types.\n\n"
				f"Current Types:\n{current_type_names}\n\n"
				f"Deduced Types:\n{deduced_type_names}\n\n"
				f"Difference (should be none):\n{option_type_mismatch_names}")
		if len(error_msgs) > 0:
			raise OptionTypesMismatch("\n\n".join(error_msgs))



	def set_configuration_data(self,
				configuration_data : Configuration,
				validate_after_setting : bool = True
			):
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

		self._configuration = configuration_data

		#Clear the cache & pause the undo stack
		self._cached_option_instances = {}
		if self.undo_stack:
			self.undo_stack.setActive(False)

		proxy_model_changed = False

		for option_name, option_dataclass_instance in self._configuration.options.items():
			if option_name not in self._option_proxy_model_dict: #If this proxymodel does not already exists -> create
				self._option_proxy_model_dict[option_name] = QtCore.QSortFilterProxyModel()
				proxy_model_changed = True
			new_model = DataclassModel(option_dataclass_instance, undo_stack=self.undo_stack)
			self._option_proxy_model_dict[option_name].setSourceModel(
				new_model
			)
			new_model.dataChanged.connect(self.update_sub_options)

		#Delete all proxy models that are not in the configuration
		# for option_name in list(self._option_proxy_model_dict.keys()):
		# 	if option_name not in self._configuration.options:
		# 		del self._option_proxy_model_dict[option_name]
		# 		proxy_model_changed = True
		# 		#TODO: unlink datachanged signal?

		if proxy_model_changed: #Emit proxymodel changes
			self.proxyModelDictChanged.emit(self._option_proxy_model_dict)

		if self.undo_stack:
			# self.undo_stack.clear()
			self.undo_stack.setActive(True)

		if validate_after_setting:
			self.validate_current_configuration()