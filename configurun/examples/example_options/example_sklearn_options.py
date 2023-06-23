"""
Implements a automatic/dynamic dataclass generation for several sklearn models.
"""
# from MachineLearning.framework.options.mvts_options import MVTSGeneralOptions
import inspect
import logging
import sys
import typing
from dataclasses import field, make_dataclass

# import dill
from numpydoc.docscrape import NumpyDocString
from pyside6_utils.utility.constraints import StrOptions
from sklearn.ensemble import AdaBoostClassifier, RandomForestClassifier
from sklearn.gaussian_process import GaussianProcessClassifier
# from sklearn.gaussian_process.kernels import RBF
from sklearn.linear_model import RidgeClassifierCV
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from configurun.configuration.base_options import BaseOptions


class SklearnClass:
	"""Example class for sklearn model - all sklearn classes have a parameter constraints dict."""
	_parameter_constraints: dict = {}


log = logging.getLogger(__name__)
_NAME_ALGORITHM_DICT : dict[str, type[SklearnClass | typing.Any]] = {
							"SKLEARN_NearestNeighbors" : KNeighborsClassifier,
							"SKLEARN_LinearSVM" : SVC,
							"SKLEARN_GaussianProcessClassifier" : GaussianProcessClassifier,
							"SKLEARN_DecisionTreeClassifier" : DecisionTreeClassifier,
							"SKLEARN_RandomForestClassifier" : RandomForestClassifier,
							"SKLEARN_MPLClassifier" : MLPClassifier,
							"SKLEARN_AdaBoostClassifier" : AdaBoostClassifier,
							"SKLEARN_NaiveBayes" : GaussianNB,
							"SKLEARN_RidgeClassifierCV" : RidgeClassifierCV
							#Add to this list to add more algorithms
}

_NAME_DOC_DICT : dict[str, NumpyDocString] = { #This dictionary will hold all the docstrings for each algorithm
	name : NumpyDocString(algorithm.__doc__) for name, algorithm in _NAME_ALGORITHM_DICT.items()
}

_NAME_SIGNATUR_DICT : dict[str, inspect.Signature] = { #This dictionary will hold all the signatures for each algorithm
	name : inspect.signature(algorithm) for name, algorithm in _NAME_ALGORITHM_DICT.items()
}

NAME_COMMENTS_DICT : dict[str, str] = { #This dictionary will hold all the comments for each algorithm
	key: algorithm.__doc__ if algorithm.__doc__ is not None else "No comments available"\
		for key, algorithm in _NAME_ALGORITHM_DICT.items()
}



def _get_model_options(algorithm_name : str) -> type:
	"""Sklearn classes all have a constraints dictionary for the types and limits of each parameter. We use this
	to automatically generate a dataclass for each algorithm which can be used to create a UI for each algorithm.
	Adding more algorithms should then be as simple as adding the algorithm to the _name_algorithm_dict dictionary.

	Args:
		algorithm_name (str): Name of the algorithm (key in _name_algorithm_dict)

	Returns:
		type: A dataclass type with all settings of the algorithm as fields
	"""
	global _NAME_DOC_DICT, _NAME_SIGNATUR_DICT, _NAME_ALGORITHM_DICT #pylint: disable=global-variable-not-assigned
	doc = _NAME_DOC_DICT[algorithm_name]
	algorithm : type[SklearnClass] = _NAME_ALGORITHM_DICT[algorithm_name]
	parameters = doc['Parameters'] #Parameters of the algorithm
	parsed_description_dict = {
		arg.name : "\n".join(arg.desc) for arg in parameters
	}
	function_signature = _NAME_SIGNATUR_DICT[algorithm_name] #Get the signature of the algorithm class using the doc
	args = []
	for param_name, param_data in function_signature.parameters.items():
		if param_name == 'self':
			continue
		args.append(( #Create a tuple: (parameter name, type, field(<neccesary data for UI>))
						param_name, #Name of the parameter
						#Try to get the type of the parameter, if not possible, use Any:
						type(param_data.default) if param_data.default is not inspect.Parameter.empty else any,
						field(default=param_data.default if param_data.default is not inspect.Parameter.empty else None,
								metadata=dict(
										#Replace underscores with spaces and capitalize each word
										display_name = param_name.replace('_', ' ').title(),
										#Get the help string from the docstring:
										help=parsed_description_dict[param_name] \
											if param_name in parsed_description_dict else None,
										#Get the constraints from the docstring:
										constraints=algorithm._parameter_constraints[param_name] #pylint: disable=protected-access\
											if param_name in algorithm._parameter_constraints else None #pylint: disable=protected-access
								)

							)

					)
		)

	new_dataclass = make_dataclass(f"{algorithm_name}ModelOptions",
									args,
									bases=(BaseOptions,)
									# namespace = { "__reduce__"} #NOTE: We can also use this to make class pickleable
									)

	return new_dataclass

SKLEARN_NAME_DATACLASS_DICT = { #This dictionary will hold all the dataclasses for the options of each algorithm

}

for key, val in _NAME_ALGORITHM_DICT.items():
	class_def = _get_model_options(key)
	#make_dataclass does not set the module attribute of the new class appropriately (as of python 3.10.8),
	# so we have to do it manually
	try: #NOTE: this should be fixed in Python version 3.12.0 alpha 7
			# (https://github.com/python/cpython/commit/b48be8fa18518583abb21bf6e4f5d7e4b5c9d7b2)
			#make_dataclass now has a module parameter which fixes this issue (even if not specified)
		module = sys._getframemodulename(0) or '__main__' #pylint: disable=protected-access #type:ignore
	except AttributeError:
		try:
			module = sys._getframe(0).f_globals.get('__name__', '__main__') #pylint: disable=protected-access
		except (AttributeError, ValueError):
			log.error(f"Could not set module attribute of dataclass {class_def.__name__}")
			continue
	class_def.__module__ = module #Set the module attribute of the new class to the module of the caller
	SKLEARN_NAME_DATACLASS_DICT[key] = class_def
	globals()[class_def.__name__] = class_def #Add class to global scope to enable pickling



class SklearnMainOptions(BaseOptions):
	"""
	Similar to example options, but with the choice of selecting a sklearn model
	"""

	# def __post_init__(self):
	# 	name_field_dict = {field.name: field for field in fields(self)}
		# for algorithm in SklearnModelOptions.get_name_algorithm_dict().keys():
		# 		#Make sure we added all possible algorithms to the model options (inside .Literal)
		# 	assert algorithm in name_field_dict["model"].type.__args__,
		# 		f"Algorithm {algorithm} not in {name_field_dict['model'].type.__args__}"

	# Model
	model_type : typing.Literal[" "] | None = field( #We dynamically set the constraints of this field using the
			# 'constraints' parameter, so we can apply the dynamically generated sklearn-model
		default=None,
		metadata=dict(
					#TODO: add a required flag
			display_name="Model",
			constraints_help= {
					"MVTSMODEL" : ("A model especially intended in use for time series representation"
					 	"learning based on the transformer encoder architecture"),
					"LINEAR":  "A simple baseline Linear Model"} #Take union of other method key-dict and this one
				| { name : comment for name, comment in NAME_COMMENTS_DICT.items()}, #Get doc-description of each algo
			help=("What model class to use" #Add the (short description) of each model to the help string
				),
			constraints = [StrOptions({ "MVTSMODEL", "LINEAR", *(NAME_COMMENTS_DICT.keys())})]
		)
	)

	#Dataset Type
	dataset_type : typing.Literal['exampleDataclass', "extendedExampleDataclass"] | None = field(
		default=None,
		metadata=dict(
			display_name="Dataset Type",
			help="""Which type of dataset is going to be processed."""
		)
	)



if __name__ == "__main__":
	print("Running SklearnModelOptions.py")
	for cur_name, cur_class in SKLEARN_NAME_DATACLASS_DICT.items():
		print(f"{cur_name} : {cur_class}")
	print("Done")
