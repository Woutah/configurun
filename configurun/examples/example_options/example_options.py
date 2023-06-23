"""
Implements several option-dataclasses to show how to use this framework.
"""
import typing
from dataclasses import dataclass, field

from pyside6_utils.utility.constraints import (Interval,
                                                             StrOptions)

from configurun.configuration.base_options import BaseOptions


@dataclass
class ExampleDatasetOptions(BaseOptions):
	"""Example dataset options
	"""

	dataset_name : str | None = field(default=None, metadata=dict(
			display_name="Dataset Name",
			help="Name of the dataset to be used, is used for logging purposes and keeping track of the results",
			constraints = [str, None]
	)
	)


	test_ratio : float = field(
		default=0,
		metadata=dict(
			display_name="Test Ratio",
			help=  		"Set aside this ratio of the dataset as a test set",
			constraints = [Interval(float, 0,1, closed='both')]
		)
	)
	val_ratio : float = field(
		default=0.2,
		metadata=dict(
			display_name="Validation Ratio",
			help= 		"Ratio of the dataset to be used as a validation set",
			constraints = [Interval(float, 0,1, closed='both')]
		)
	)

	data_dir : str = field(
		default="./data",
		metadata=dict(
			display_name="Data Directory", #TODO: make this a path
			help="Data directory path",
			constraints = [str]
		)
	)
	pattern : str | None = field(
		default=None,
		metadata=dict(
			display_name="Pattern",
			help="Regex pattern used to load the files",
			constraints = [str, None]
		)
	)
	val_pattern : str | None = field(
		default=None,
		metadata=dict(
			display_name="Validation File Pattern",
			help=("Regex pattern used to select files contained in `data_dir` for the validation set"),
			constraints = [str, None]
		)
	)

	cross_validation_folds : int | None = field(
		default=None,
		metadata=dict(
			display_name="Cross Validation Folds",
			help=("If specified (>1), will perform cross-validation with the specified number of folds. "
					"Note that this setting is not compatible with using a: val_pattern, test_pattern or test_ratio > 0"
					"The dataset loaded from <pattern> will be split into non-overlapping folds using the val_ratio. "
					"The task should always be <train_only> since the whole dataset will be split in <n> splits, and "
					"for each split, a subsplit will be made into train/validation (and test) set on which the tasks "
					"will be performed. This is useful for hyperparameter tuning, especially when the dataset is small."
			),
			constraints = [Interval(type=int, left=1, right=None, closed="both"), None]
		)
	)

	test_pattern : str | None = field(default=None, metadata=dict(
			display_name="Test File Pattern",
			help=("Regex pattern used to select files inside data_dir for the test set"),
			constraints = [str, None]
	)
	)



@dataclass
class ExtendedExampleDatasetOptions(ExampleDatasetOptions):
	"""Extends the example dataset options with some more options"""
	labels : str | None = field(
		default=None,
		metadata=dict(
			display_name="Labels",
			help=("In case a dataset contains several labels (multi-task), "
				   "which type of labels should be used in regression or classification, the name of column(s)."),
			constraints = [str, None] #TODO: list of strings?
	))
	normalization : typing.Literal['standardization', 'minmax', 'per_sample_std', 'per_sample_minmax'] = field(
		default='standardization',
		metadata=dict(
			display_name="Normalization",
			help="If specified, will apply normalization on the dataset.",
			display_path="Normalization",
			constraints = [StrOptions({'standardization', 'minmax', 'per_sample_std', 'per_sample_minmax'}), None]
		)
	)

	norm_from : str | None = field(
		default=None,
		metadata=dict(
			display_name="Load Settings from file",
			help=("If given, will read normalization values from the specified file instead of computing them."),
			display_path="Normalization",
			constraints = [str, None]
		)
	)


@dataclass
class ExampleGeneralOptions(BaseOptions):
	"""
	Example of general options - not specific to any model or dataset
	"""

	## Run from command-line arguments
	# I/O
	output_dir : str = field(
		default='output',
		metadata=dict(
			display_name="Output Dir",
			help="Output directory",
			display_path="Output Settings"
		)
	)

	experiment_name : str = field(
		default='',
		metadata=dict(
			display_name="Experiment Name",
			help=("A string identifier/name for the experiment to be run - it will be appended to the output directory"
				"name, before the timestamp"),
			display_path="Output Settings"
		)
	)

	comment : str = field(
		default='',
		metadata=dict(
			display_name="Comment",
			help="A comment/description for this experiment."
		)
	)



	print_interval : int = field(
		default=1,
		metadata=dict(
			display_name="Print Interval",
			help="Print every x interval"
		)
	)

	gpu_index : str =  field(
		default='0',
		metadata=dict(
			display_name="GPU Index",
			help="GPU index"
		)
	)

	processes : int = field(
		default=-1,
		metadata=dict(
			display_name="Number of processes",
			help="Number of processes to use."
		)
	)
	threads : int = field(
		default=0,
		metadata=dict(
			display_name="Threads",
			help="Number of threads to use"
		)
	)
	seed : int | None = field(
		default=None,
		metadata=dict(
			display_name="Seed",
			help="Seed to use for the process"
		)
	)


@dataclass
class ExampleModelOptions(BaseOptions):
	"""Simple example model settings"""

	simple_int_variable : int = 5

	int_model_param : int = field(
		default=1,
		metadata=dict(
			display_name="Integer Model Parameter",
			help="An integer parameter for the model",
			constraints = [int]
		)
	)

	string_model_param : str = field(
		default="",
		metadata=dict(
			display_name="String Model Parameter",
			help="A string parameter for the model",
			constraints = [str]
		)
	)
	float_in_range_model_param : float = field(
		default=0.5,
		metadata=dict(
			display_name="Float In Range Model Parameter",
			help="A float parameter for the model between 0 and 1",
			constraints = [Interval(float, 0,1, closed='both')]
		)
	)

@dataclass
class ExtendedExampleModelOptions(ExampleModelOptions):
	"""Adds some more options to the example model"""
	extended_str_param : str = field(
		default="",
		metadata=dict(
			display_name="Extra Str Parameter",
			help="An extra string parameter for the model",
			constraints = [str]
		)
	)

	extended_int_param : int = field(
		default=1,
		metadata=dict(
			display_name="Extra Int Parameter",
			help="An extra integer parameter for the model",
			constraints = [int]
		)
	)

	extended_choice_param : typing.Literal["choice1", "choice2"] = field(
		default="choice1",
		metadata=dict(
			display_name="Extra Choice Parameter",
			help="An extra choice parameter for the model",
			contraints_help = {"choice1": "Description of Choice 1",
		      "choice2": "Description of Choice 2"},
		)
	)



@dataclass
class ExampleMainOptions(BaseOptions):
	"""
	Contains the main options that determine the rest of the option-classes. The arguments in this class are parsed
	first, and then the other classes are chosen and parsed based on what is found in this class
	"""
	model_type : typing.Literal["ExampleModel", "ExtendedExampleModel"] | None = field(
		default=None,
		metadata=dict(
					#TODO: add a required flag
			display_name="Model Type",
			constraints_help= {
				"ExampleModel": "A simple example model",
				"ExtendedExampleModel": "An extended example model, extends ExampleModel"
			},
			help="Model(class) to use"
		)
	)

	dataset_type : typing.Literal['ExampleDataset', "ExtendedExampleDataset"] | None = field(
		default=None,
		metadata=dict(
			display_name="Dataset Type",
			help="""Which type of dataset is going to be used.""",
			constraints_help= {
				"ExampleDataclass": "A simple example dataset",
				"ExtendedExampleDataclass": "An extended example dataset, extends exampleDataclass"
			}
		)
	)
