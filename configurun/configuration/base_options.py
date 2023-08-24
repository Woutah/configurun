"""
Implements the base-options from which all user-defined options should inherit
"""


import logging
import typing
from dataclasses import dataclass

from pyside6_utils.classes import \
    Serializable  # Absolute import to avoid import PySide6

log = logging.getLogger(__name__)


class InstanceMeta(type):
	"""
	Metaclass for BaseOptions, this contains an instancecheck method that allows us to check if an instance of a class
	is present in the options dict of a Configuration instance.

	This means that we can use typehinting more easily.

	NOTE: this also means that instance-checks might now wor
	"""

	def __instancecheck__(cls, __instance: typing.Any) -> bool:
		"""
		If __instance is not a Configuration instance: use the normal behaviour

		If __instance is a Configuration instance:
		Returns whether the given instance is present in the options dict, which means that we can access its attributes
		using the . operator. This is especially helpful for typehinting, e.g.:
		
		config = Configuration()
		config.options["model_options"] = SklearnModelOptions()
		assert(isinstance(config, SklearnModelOptions)) #True
		config.<sklearn_model_options_attribute> #This will work, and will also show typehinting/autofill in IDEs


		NOTE: if we add methods to the BaseOptions class, this means that it LOOKS like we can call these methods, but
		this will not work as the Configuration-wrapper only exposes the attributes of the sub-options classes, not
		their methods. TODO: maybe warn?
		"""
		#pylint: disable=import-outside-toplevel
		from configurun.configuration.configuration import Configuration #Import here to avoid circular import 
		if type(__instance) == Configuration: #pylint: disable=unidiomatic-typecheck
			return __instance.hasinstance(cls)

		return super().__instancecheck__(__instance) #Otherwise use normal behaviour


@dataclass
class BaseOptions(Serializable, object, metaclass=InstanceMeta):
# class BaseOptions(Serializable, object):
	"""
	he base-option class, all other options classes should inherit from this class
	A configuration is built by using 1 or more of these options classes.
	"""

	def update_using_dict(self, update_dict : dict):
		"""Update the current object with the passed dictionary

		Args:
			update_dict (dict): The dictionary to update with
		"""
		#TODO: only set existing keys?
		for key, value in update_dict.items():
			setattr(self, key, value)


	def copy_from(self, other : 'BaseOptions'):
		"""Copy all values from other to self

		Args:
			other (BaseOptions): The other object to copy from
		"""
		for key, value in other.__dict__.items():
			setattr(self, key, value)

	def get_public_attrs_as_str(self, sep = "\n") -> str:
		"""Get all public attributes of the class as a string
		"""
		retval : str = ""
		for key, value in self.__dict__.items():
			if not key.startswith('_'):
				retval += f"{key} : {value}{sep}"
		return retval


	def __getitem__(self, key : str):
		"""Interface for []-itemgetters used in MVTS datasets, if key (class property) not found, returns None

		Args:
			key (str): The key of the item

		Returns:
			(typing.Any) : None if key not found, or the item if key found
		"""
		if key in self.__dict__:
			return self.__dict__[key]
		else:
			return None

	def __setitem__(self, key, value):
		"""Set the value of a property.

		Args:
			key (str): Name of the property
			value (any): Value to be set
		"""
		setattr(self, key, value)
