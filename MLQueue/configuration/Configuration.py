
import json
import typing
from dataclasses import dataclass
from PySide6 import QtCore, QtGui
from PySide6Widgets.Models.DataClassModel import DataclassModel

from MLQueue.configuration.ConfigurationData_old import ConfigurationData


@dataclass
class ConfigurationModel(QtCore.QObject):
	def __init__(self, use_cache = False, use_undo_stack=False) -> None:
		"""The initialize of the class

		Args:
			use_cache (bool, optional): Whether the options class should use a cache. When the main_options are changed and .e.g. the model_options have to be changed, this checks the cache for an existing configuration of this type.
			This is useful when this class is used in a user interface. Defaults to False.
			use_undo_stack (bool, optional): Whether to use an undo stack. This makes it so undo/redo can be called to undo/redo actions. To ensure this works, enabling use_undo_stack automatically enables use_cache. Defaults to False.
		"""
		super().__init__()
		self.undo_stack = None
		if use_undo_stack:
			self.undo_stack = QtGui.QUndoStack()
			self._use_cache = True


		self._options_data = ConfigurationData()

		#Initialize the options classes
		self._options_data.main_options = MainOptions() #Should always stay the same
		self._options_data.general_options = GeneralOptions()
		self._options_data.model_options = None
		self._options_data.dataset_options = None
		self._options_data.training_options = None

		#Initialize the options models
		self._main_options_model = DataclassModel(self._options_data.main_options, undo_stack=self.undo_stack)
		self._general_options_model = DataclassModel(self._options_data.general_options, undo_stack=self.undo_stack)
		self._model_options_model = None
		self._dataset_options_model = None
		self._training_options_model = None

		#Proxy models (used to communicate with the UI so we don't have to broadcast new models every time the options change)
		self._main_options_proxymodel = QtCore.QSortFilterProxyModel()
		self._general_options_proxymodel = QtCore.QSortFilterProxyModel()
		self._model_options_proxymodel = QtCore.QSortFilterProxyModel()
		self._dataset_options_proxymodel = QtCore.QSortFilterProxyModel()
		self._training_options_proxymodel = QtCore.QSortFilterProxyModel()

		self._main_options_proxymodel.setSourceModel(self._main_options_model)
		self._general_options_proxymodel.setSourceModel(self._general_options_model)


		self._main_options_proxymodel.dataChanged.connect(lambda *_: self.updateSubOptions()) #Upon change of the main options, update the sub-options as well

			# raise NotImplementedError("Undo stack not implemented yet")
		self._use_cache = use_cache
		self._cached_option_instances :typing.Dict[object, tuple[object ,DataclassModel]] = { #Tuple of dataclass and dataclass model
		}

	#Some help-functions to initialize new views
	def getMainOptionsProxyModel(self):
		return self._main_options_proxymodel
	def getGeneralOptionsProxyModel(self):
		return self._general_options_proxymodel
	def getModelOptionsProxyModel(self):
		return self._model_options_proxymodel
	def getDatasetOptionsProxyModel(self):
		return self._dataset_options_proxymodel
	def getTrainingOptionsProxyModel(self):
		return self._training_options_proxymodel

	def hasattr(self, key):
		return self._options_data.hasattr(key)

	def __getitem__(self, key):
		return self._options_data.__getattr__(key) #Just pass on the call to getattr
	def __getattr__(self, key):
		return self._options_data.__getattr__(key) #Pass on the call to the options data class

	def updateSubOptions(self):
		"""
		Updates the used options classes based on the main options
		"""
		log.debug("Updating sub-options!")
		option_classes = self.get_configs_from_main_options(self._options_data.main_options) #
		options_instance_list = [self._options_data.model_options, self._options_data.dataset_options, self._options_data.training_options] #Convenience list of all options classes
		options_instance_model_list = [self._model_options_model, self._dataset_options_model, self._training_options_model] #Convenience list of all options models
		options_instance_proxymodel_list = [self._model_options_proxymodel, self._dataset_options_proxymodel, self._training_options_proxymodel] #Convenience list of all options models

		for i, (new_options_class) in enumerate(option_classes):
			option_instance = None
			option_instance_model = None

			if type(new_options_class) == type(options_instance_list[i]): #If the new options class is the same as the old one, skip
				continue
			elif self._use_cache and self._cached_option_instances.get(type(new_options_class), None) is not None: #If the options class is already in the cache
				option_instance, option_instance_model = self._cached_option_instances[type(new_options_class)]
			else: #If not cached
				if self._use_cache and options_instance_list[i] is not None: #If the old options class (that is to be overwritten) is not None and caching is enabled
					self._cached_option_instances[type(options_instance_list[i])] = (options_instance_list[i], options_instance_model_list[i]) #Add the old options class to the cache

				if new_options_class is not None: #If the new options class is None, skip
					option_instance = new_options_class() #initialize new option-instance (with default values)
					option_instance_model = DataclassModel(option_instance, undo_stack=self.undo_stack)

			options_instance_list[i] = option_instance #Set the new option-instance
			options_instance_model_list[i] = option_instance_model #Set the new option-model
			options_instance_proxymodel_list[i].setSourceModel(option_instance_model) #Set the new option-model

		#TODO: this isn't very tidy - maybe use a dictionary instead to iterate over the options classes?
		self._options_data.model_options = options_instance_list[0]
		self._options_data.dataset_options = options_instance_list[1]
		self._options_data.training_options = options_instance_list[2]

		self._model_options_model = options_instance_model_list[0]
		self._dataset_options_model = options_instance_model_list[1]
		self._training_options_model = options_instance_model_list[2]
			# options_signal_list[i].emit(option_instance_model) #Emit the signal that the option-model has changed

	def validateSubOptions(self):
		#TODO: make sure that the options are valid -> no duplicate keys in each suboptions instance
		raise NotImplementedError("ValidateSubOptions not implemented yet")

	def save_as(self, path : str):
		main_json = self._options_data.main_options.__dict__
		general_json = self._options_data.general_options.__dict__
		#Model, dataset and trainig options are dependent on the main options -> get them from the tree views (alternatively we could use cur_option_types icw self._cached_models)
		try:
			model_dict = self._options_data.model_options.__dict__
		except Exception:
			model_dict = {}

		try:
			dataset_dict = self._options_data.dataset_options.__dict__
		except Exception:
			dataset_dict = {}

		try:
			training_dict = self._options_data.training_options.__dict__
		except Exception:
			training_dict = {}


		composite_json = {
			"main_options": main_json,
			"general_options": general_json,
			"model_options": model_dict,
			"dataset_options": dataset_dict,
			"training_options": training_dict
		}

		with open(path, "w") as f:
			f.write(json.dumps(composite_json, indent=4))
			return True

		return False


	def load_from(self, path=None):
		with open(path, "r") as f:
			composite_json = json.loads(f.read())

		self._cached_option_instances = {} #Clear the cache
		self.undo_stack.setActive(False) #Temporarily disable undo stack
		self.undo_stack.clear() #Clear the undo stack


		main_options = MainOptions()
		general_options = GeneralOptions()

		problem_dict = {
		}

		try:
			# main_options.from_json(composite_json["main_options"])
			problem_keys = main_options.copy_from_dict(composite_json["main_options"], ignore_new_attributes=True)
			if len(problem_keys) > 0:
				problem_dict["main_options"] = KeyError(f"The following keys could not be found in the options-class: {', '.join(problem_keys)} - unknown keys were ignored(!)")
		except Exception as e:
			print(e)
			problem_dict["main_options"] = e

		try:
			# general_options.from_json(composite_json["general_options"])
			problem_keys = general_options.copy_from_dict(composite_json["general_options"], ignore_new_attributes=True)
			if len(problem_keys) > 0:
				problem_dict["general_options"] = KeyError(f"The following keys could not be found in the options-class: {', '.join(problem_keys)} - unknown keys were ignored(!)")
		except Exception as e:
			print(e)
			problem_dict["general_options"] = e

		option_classes = self.get_configs_from_main_options(main_options)
		model_options = None
		dataset_options = None
		training_options = None

		try: #TODO: maybe place in a loop?
			if option_classes[0] is not None:
				model_options = option_classes[0]()
				# model_options.from_json(composite_json["model_options"])
				problem_keys = model_options.copy_from_dict(composite_json["model_options"])
				if len(problem_keys) > 0:
					problem_dict["general_options"] = KeyError(f"The following keys could not be found in the options-class: {', '.join(problem_keys)} - unknown keys were ignored(!)")
		except Exception as e:
			print(e)
			problem_dict["model_options"] = e

		try:
			if option_classes[1] is not None:
				dataset_options = option_classes[1]()
				# model_options.from_json(composite_json["dataset_options"])
				problem_keys = dataset_options.copy_from_dict(composite_json["dataset_options"])
				if len(problem_keys) > 0:
					problem_dict["dataset_options"] = KeyError(f"The following keys could not be found in the options-class: {', '.join(problem_keys)} - unknown keys were ignored(!)")
		except Exception as e:
			print(e)
			problem_dict["dataset_options"] = e

		try:
			if option_classes[2] is not None:
				training_options = option_classes[2]()
				problem_keys = training_options.copy_from_dict(composite_json["training_options"])
				if len(problem_keys) > 0:
					problem_dict["training_options"] = KeyError(f"The following keys could not be found in the options-class: {', '.join(problem_keys)} - unknown keys were ignored(!)")
		except Exception as e:
			print(e)
			problem_dict["training_options"] = e

		self.set_all_options(
			main_options=main_options,
			general_options=general_options,
			model_options=model_options,
			dataset_options=dataset_options,
			training_options=training_options
		)

		self.undo_stack.setActive(True)

		log.info(f"Finished loading config from {path}")
		return problem_dict

	def get_options_data_copy(self):
		return copy.deepcopy(self._options_data)

	def set_option_data(self, options_data : FrameworkOptionsData):
		self.set_all_options( #TODO: create a copy function instead?
			main_options=options_data.main_options,
			general_options=options_data.general_options,
			model_options=options_data.model_options,
			dataset_options=options_data.dataset_options,
			training_options=options_data.training_options
		)


	def set_all_options(
			self,
			main_options,
			general_options,
			model_options = None,
			dataset_options = None,
			training_options = None
	):
		"""Function that sets all options at once. This is useful for loading configs from a file and copying options 
		from one config to another. No copies are made of the options objects, so the original objects will be saved & 
		modified - make sure to copy them if you want to keep using them.

		This function first sets the attributes for each options subclass, then creates the corresponding 
		DataClassModels, after which they are connected to the proxy models.

		NOTE: resets the undo stack!
		Args:
			main_options (MainOptions): The main options to be copied
			general_options (BaseGeneralOptions): The general options to be used (no copy will be made)
			model_options (BaseModelOptions, optional): The model options to be used (no copy). Defaults to None.
			dataset_options (DatasetOptioons, optional): The dataset options to be used (no copy). Defaults to None.
			training_options (BaseTrainingOptions, optional): The Training Options to be used. Defaults to None.
		"""
		if self.undo_stack:
			self.undo_stack.setActive(False)
			self.undo_stack.clear() #Clear the undo stack

		self._options_data.main_options = main_options
		self._options_data.general_options = general_options
		self._options_data.model_options = model_options
		self._options_data.dataset_options = dataset_options
		self._options_data.training_options = training_options

		self._main_options_model = DataclassModel(self._options_data.main_options, undo_stack=self.undo_stack)
		self._general_options_model = DataclassModel(self._options_data.general_options, undo_stack=self.undo_stack)
		self._model_options_model = DataclassModel(self._options_data.model_options, undo_stack=self.undo_stack)
		self._dataset_options_model = DataclassModel(self._options_data.dataset_options, undo_stack=self.undo_stack)
		self._training_options_model = DataclassModel(self._options_data.training_options, undo_stack=self.undo_stack)

		self._main_options_proxymodel.setSourceModel(self._main_options_model)
		self._general_options_proxymodel.setSourceModel(self._general_options_model)
		self._model_options_proxymodel.setSourceModel(self._model_options_model)
		self._dataset_options_proxymodel.setSourceModel(self._dataset_options_model)
		self._training_options_proxymodel.setSourceModel(self._training_options_model)

		if self.undo_stack:
			self.undo_stack.setActive(True)


	# def copy_options(self, options_to_copy : 'Options'):
	# 	"""Creates a deep copy of all suboptions of the given options object and sets them as the options of this object.

	# 	Args:
	# 		options_to_copy (Options): From which to copy the options
	# 	"""
	# 	self.set_all_options(
	# 		main_options = copy.deepcopy(options_to_copy._options_data.main_options),
	# 		general_options=copy.deepcopy(options_to_copy._options_data.general_options),
	# 		model_options=copy.deepcopy(options_to_copy._options_data.model_options),
	# 		dataset_options=copy.deepcopy(options_to_copy._options_data.dataset_options),
	# 		training_options=copy.deepcopy(options_to_copy._options_data.training_options)
	# 	)
	@staticmethod
	def get_model_options(model_type : MODEL_TYPES) -> ALL_MODEL_CLASSES:
		"""
		Get the model options class based on the model type
		"""

		model_name_dict = {
			"linear": MVTSModelOptions,
			"mvtsmodel" : MVTSModelOptions,
			"sklearnmodel" : SklearnModelOptions,
		}
		model_class = model_name_dict.get(model_type.lower(), None)
		if model_class is None:
			try:
				model_class = SklearnModelOptions.get_algorithm_options_class(model_type)
			except:
				pass

		if not model_class:
			raise ValueError(f"Model type {model_type} not recognized/implemented")
		return model_class

	@staticmethod
	def get_dataset_options(dataset_type : DATASET_TYPES) -> ALL_DATASET_CLASSES:
		"""
		Get the dataset options class based on the dataset type
		"""
		dataset_name_dict = {
			"drilling" : DrillingDatasetOptions,
			'weld' : BaseDatasetOptions,
			'hdd' : BaseDatasetOptions,
			'tsra' : BaseDatasetOptions,
			'semicond' : BaseDatasetOptions,
			'pmu' : BaseDatasetOptions
		}

		dataset_class = dataset_name_dict.get(dataset_type.lower(), None)

		if not dataset_class:
			raise ValueError(f"Dataset type {dataset_type} not recognized/implemented")

		return dataset_class

	@staticmethod
	def get_training_options(model_type : MODEL_TYPES) -> ALL_TRAINING_CLASSES:
		"""
		Get the training options class based on the training type
		"""
		training_name_dict = {
			"mvtsmodel" : MvtsTrainingOptions,
			"linear": MvtsTrainingOptions,
			"sklearnmodel" : SklearnTrainingOptions
		}
		temp = model_type.lower()
		training_class = training_name_dict.get(model_type.lower(), None)
		if temp.startswith("sklearn") and training_class is None: #if not yet found -> try to get the training options from the sklearn model options
			try:
				training_class = SklearnTrainingOptions.get_training_options(model_type)
			except:
				pass
		if not training_class:
			raise ValueError(f"Training-settings  for model {model_type} not recognized/implemented")

		return training_class



	@staticmethod
	def get_configs_from_main_options(main_options : MainOptions) -> list[ALL_OPTION_CLASSES]:
		"""
		Return all options from the main options in order:
		model_options, data_options, training_options

		If the model type is not recognized, return None for the model options
		"""

		opts = []
		try:
			opts.append(FrameworkConfiguration.get_model_options(main_options.model)) #type: ignore
		except (ValueError, AttributeError) as exception:
			opts.append(None)

		try:
			opts.append(FrameworkConfiguration.get_dataset_options(main_options.data_class)) #type: ignore
		except (ValueError, AttributeError) as exception:
			opts.append(None)

		try:
			opts.append(FrameworkConfiguration.get_training_options(main_options.model)) #type: ignore
		except (ValueError, AttributeError) as exception:
			opts.append(None)


		return opts



	@staticmethod
	def get_config_from_passed_args(
					main_options : MainOptions, #Everything always contains this
					general_options : GeneralOptions, #
					model_options : ALL_MODEL_CLASSES, #The model options
					dataset_options : ALL_DATASET_CLASSES, #The dataset options
					training_options : ALL_TRAINING_CLASSES,
					): #The training options

		"""
		Returns a newly instantiated configuration object from the passed options
		"""

		update_list = []
		type_list = []
		options_dict = {}

		for i in [main_options, general_options, model_options, dataset_options, training_options]:
			if i is not None:
				type_list.append(type(i))
				update_list.append(i)
				options_dict.update(i.__dict__)



		#==== Create combined class for a
		options = FrameworkConfiguration._get_combined_class(type_list)



		#================ Load all passed options into the new class =================
		super(type(main_options), options).copy_from(main_options)
		super(type(general_options), options).copy_from(general_options)
		super(type(model_options), options).copy_from(model_options)
		super(type(dataset_options), options).copy_from(dataset_options)
		super(type(training_options), options).copy_from(training_options)


		#======= check if model_options concurs with main_options.model
		if main_options.model != model_options.model_name: #TODO: make a better check than this?
			raise ValueError(f"Model options passed ({model_options.__class__.__name__} used for model type {model_options.model_name}) does not match model name passed in main options ({main_options.model})")

		return options




	@staticmethod
	def _get_combined_class(class_list : typing.List[typing.Type]) -> ALL_OPTION_CLASSES: #, init_kwargs : typing.Dict[str, any]) -> ALL_OPTION_CLASSES:
		"""
		Combine multiple dataclasses into one
		"""
		#Create a new dataclass with the same name as the first class in the list
		class newclass(*class_list):
			pass
		return newclass()



