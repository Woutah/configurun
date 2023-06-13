"""Implements the Options & Optionsdata dataclass

The options class is a wrapper around the OptionsData class that provides convenience functions for loading/saving 
options from/to a file and for creating a new options class from a set of passed options.
"""



import logging
import typing
from dataclasses import dataclass

from MachineLearning.framework.options.dataset_options.base_dataset_options import \
    BaseDatasetOptions
from MachineLearning.framework.options.dataset_options.drilling_dataset_options import \
    DrillingDatasetOptions
from MachineLearning.framework.options.general_options import (DATASET_TYPES,
                                                               MODEL_TYPES,
                                                               TASK_TYPES,
                                                               GeneralOptions)
from MachineLearning.framework.options.main_options import MainOptions
from MachineLearning.framework.options.model_options.mvts_model_options import \
    MVTSModelOptions
from MachineLearning.framework.options.model_options.sklearn_model_options import \
    SklearnModelOptions
from MachineLearning.framework.options.training_options.mvts_training_options import \
    MvtsTrainingOptions
from MachineLearning.framework.options.training_options.sklearn_training_options import \
    SklearnTrainingOptions
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6Widgets.Models.DataClassModel import DataclassModel

from MLQueue.configuration.BaseOptions import BaseOptions
from MLQueue.configuration.ConfigurationData import ConfigurationData
from MLQueue.configuration.ConfigurationModel import ConfigurationModel

log = logging.getLogger(__name__)
# import PySide6Widgets.


ALL_TRAINING_CLASSES = MvtsTrainingOptions | SklearnTrainingOptions
ALL_DATASET_CLASSES = BaseDatasetOptions | DrillingDatasetOptions
ALL_MODEL_CLASSES = MVTSModelOptions | SklearnModelOptions
ALL_OPTION_CLASSES = ALL_TRAINING_CLASSES | ALL_DATASET_CLASSES | ALL_MODEL_CLASSES | GeneralOptions | MainOptions




@dataclass
class FrameworkOptionsData(ConfigurationData):
	"""
	ConfigurationData object specifically meant for this framework
	"""
	main_options : MainOptions | None = None
	general_options : GeneralOptions | None = None
	model_options : ALL_MODEL_CLASSES | None = None
	dataset_options : ALL_DATASET_CLASSES | None = None
	training_options : ALL_TRAINING_CLASSES | None = None

@dataclass
class FrameworkConfigurationModel(ConfigurationModel): #TODO:
	"""
	This is a wrapper around the ConfigurationData class. It allows the options to be used in a UI using Pyside6 Views.
	NOTE: changes to the sub-options are only synced to the view if the changes are made through this model.
	"""

	def __init__(self):
		super().__init__()

	def deduce_new_option_class_types(self) -> typing.Dict[str, typing.Type[BaseOptions] | typing.Type[None]]:

		return {
			"main_options" : MainOptions,
			"general_options" : GeneralOptions,
			"model_options" : SklearnModelOptions,
			"dataset_options" : BaseDatasetOptions,
			"training_options" : MvtsTrainingOptions
		}


if __name__ == "__main__":
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}]  {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.DEBUG) #Without time
	log.debug("Now running some tests for options dataclass parser")
