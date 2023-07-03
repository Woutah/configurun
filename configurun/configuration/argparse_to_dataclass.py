"""Implements a function to convert an argparse.ArgumentParser to a dataclass which can be used as an option source."""



import argparse
import logging
import sys
from dataclasses import field, make_dataclass

from pyside6_utils.classes.constraints import (Interval, Options)

from configurun.configuration.base_options import BaseOptions

log = logging.getLogger(__name__)


def argparse_to_dataclass(
		argument_parser : argparse.ArgumentParser,
		dataclass_name : str = "ArgparseOptions",
	) -> type:
	"""Convert an argparse.ArgumentParser to a dataclass which can be used as an option source.

	NOTE: when this function is called, it automatically adds the dataclass_name to the global scope,
	overwriting any existing class with the same name.

	NOTE: if using a server, make sure to also define this class on the server-side, otherwise the server/client 
	communication will fail.
	
	Args:
		argument_parser (argparse.ArgumentParser): The argparse.ArgumentParser to convert

	Returns:
		type: The dataclass
	"""
	dataclass_args = []
	for action in argument_parser._actions: #pylint: disable=protected-access #NOTE: protected access is neccesary here
			#to access the properties of the actions
		#Iterate over parser args, and create a dataclass field for each
		if action.dest == 'help': #Skip help
			continue

		new_type = action.type
		new_constraints = [new_type]
		if action.choices is not None: #if limited to choices,
			#If range
			if isinstance(action.choices, range):
				new_constraints = [Interval(new_type, action.choices.start, action.choices.stop, closed='both')]
			else:
				new_constraints = [Options(new_type, set(action.choices))] #If list of options
		elif new_type is None: #If no choice but also no type
			if isinstance(action, argparse._StoreTrueAction): #pylint: disable=protected-access
				new_type = bool
				new_constraints = [bool]

		display_name = action.dest.replace('_', ' ').title() #Convert varname to title-like display name
		if action.metavar: #If a specific display name is given, use that instead
			display_name = action.metavar

		if action.nargs is not None and int(action.nargs) > 1:
			raise NotImplementedError("Nargs > 1 not yet implemented for conversion to dataclass")

		dataclass_args.append( #Append tuples of (name, type, field(<neccesary data for UI>))
			(
				action.dest, #Name of the parameter
				action.type,
				field(
					default=action.default,
					metadata=dict(
						display_name = display_name,
						help = action.help,
						constraints = new_constraints, #TODO: add constraints
						required = action.required
					)
				)
			)
		)

	new_dataclass = make_dataclass(
		dataclass_name,
		dataclass_args,
		bases=(BaseOptions,)
	)
	module = None
	try: #NOTE: this should be fixed in Python version 3.12.0 alpha 7
			# (https://github.com/python/cpython/commit/b48be8fa18518583abb21bf6e4f5d7e4b5c9d7b2)
			#make_dataclass now has a module parameter which fixes this issue (even if not specified)
		module = sys._getframemodulename(0) or '__main__' #pylint: disable=protected-access #type:ignore
	except AttributeError:
		try:
			module = sys._getframe(0).f_globals.get('__name__', '__main__') #pylint: disable=protected-access
		except (AttributeError, ValueError):
			log.error(f"Could not set module attribute of dataclass {new_dataclass.__name__}")
	new_dataclass.__module__ = module #Set the module attribute of the new class to the module of the caller #type:ignore
	globals()[dataclass_name] = new_dataclass #Also add class to global scope to enable pickling from this module
		# note that it is probably easier to make use of dill
	return new_dataclass


if __name__ == "__main__":
	from configurun.app.create_run import run_local
	from configurun.examples.example_argparse import parser_example
	test_dataclass = argparse_to_dataclass(parser_example)
	run_local(
		target_function = lambda x, *_: print(x),
		options_source = test_dataclass
	)
