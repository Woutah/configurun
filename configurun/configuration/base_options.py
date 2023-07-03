""" 
Implements the base-options from which all user-defined options should inherit
"""


import logging
from dataclasses import dataclass
from pyside6_utils.utility.serializable import Serializable #Absolute import to avoid import PySide6
log = logging.getLogger(__name__)


@dataclass
class BaseOptions(Serializable, object):
	"""The base-option class, all other options classes should inherit from this class
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
