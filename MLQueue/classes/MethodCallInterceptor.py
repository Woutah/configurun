"""
Implements a metaclass which intercepts all call to a parent-class
Can be used to create a 'virtual'-instance of a class on which calls
can be forwarded to a server on which the "actual" instance of the class is running
"""

from abc import abstractmethod
from types import FunctionType
import inspect
import PySide6.QtCore as QtCore


def get_class_implemented_methods(obj : type, exclude_parent_methods : bool = True) -> list[str]:
	"""
	Get all non-dunder methods of an object
	"""
	parent_methods = set()
	if exclude_parent_methods:
		for parent_class in obj.__bases__:
			parent_methods.update(get_class_implemented_methods(parent_class, exclude_parent_methods=False))
			# parent_methods.update(get_class_implemented_methods(parent_class, exclude_parent_methods=False))

	ret = set(
		[method for method in dir(obj) if not method.startswith("__") and not method.endswith("__")]
	)
	ret = ret - parent_methods # type: ignore
	return list(ret)

class MethodCallInterceptorClass():
	"""
	Class from which classes that use the MethodCallInterceptedMeta metaclass should inherit
	- although not really neccesary - this makes it easier for editors to detect the _interceptor method
	"""
	@abstractmethod
	def _interceptor(self, function_name : str, *args, **kwargs):
		"""
		Receive-function for intercepted method calls to a class - to be used in inheriting classes
		args:
			function_name (str) : name of the function that was called
			args : arguments to the function
			kwargs : keyword arguments to the function

		returns:
			Any : return value of the function

		"""
		raise NotImplementedError()


class MethodCallInterceptedMeta(type(QtCore.QObject)):
	"""
	Metaclass that intercepts all calls to the method-list provided by the user and sends them to
	the function: _interceptor instead. This allows the user to create a proxy-instance of a
	class which passes all function calls on to a remote server on which the actual instance of the
	class is running.

	NOTE: the interceptor-method (_interceptor) should be implemented in the class that uses this
	metaclass, this is enforced	by making the class inherit from MethodIntercceptorClass, which is an abstract class
	that defines the _interceptor method

	args:
		function_name (str) : name of the function that was called
		args : arguments to the function
		kwargs : keyword arguments to the function

	returns:
		Any : return value of the function

	"""
	def __new__(mcs, name, bases,
	     		dct : dict,
				intercept_list : list[str],
				#Use list factory to safely create a new list object:
				skip_intercept_list : list[str] | None = None
				):
		"""Instantiate a new instance of the class with an interceptor
		Args:
			name (_type_): default __new__ arg 0
			bases (_type_): default __new__ arg 1
			dct (dict): default __new__ arg 2
			intercept_list (list[str]): The list of functions that should be intercepted
			skip_intercept_list (list[str], optional): Convenience argument with a list of items that should
				not be intercepted, even if they are present in skip_intercept_list. Defaults to [].
		"""
		if skip_intercept_list is None: #If no argument is provided, use an empty list
			skip_intercept_list = [
					"__init__",
					"__getattr__",
					"__getattribute__",
					"__setattr__",
					"__get__",
					"__set__",
					"__delete__"
			]
		new_class_dict = {}

		if MethodCallInterceptorClass._interceptor.__name__ not in dct:
			raise NotImplementedError(f"Class {name} with metaclass {MethodCallInterceptedMeta.__name__} does not \
			     	implement the abstract {MethodCallInterceptorClass._interceptor.__name__} method ")
		if not inspect.isfunction(dct[MethodCallInterceptorClass._interceptor.__name__]):
			raise NotImplementedError(f"Class {name} with metaclass {MethodCallInterceptedMeta.__name__} does not \
			     implement the abstract {MethodCallInterceptorClass._interceptor.__name__} method as a function")
		#Check if args are self, function_name, *args, **kwargs
		if not inspect.signature(dct[MethodCallInterceptorClass._interceptor.__name__]) \
				== inspect.signature(MethodCallInterceptorClass._interceptor):
			raise NotImplementedError(f"Class {name} with metaclass {MethodCallInterceptedMeta.__name__} does not \
			     implement the abstract {MethodCallInterceptorClass._interceptor.__name__} method with the correct \
				 arguments ({inspect.signature(MethodCallInterceptorClass._interceptor)})")

		interceptor = dct[MethodCallInterceptorClass._interceptor.__name__]

		#Generate a lambda function that call the interceptor with all args/kwargs (and the function name)
		def get_call_interceptor_func(passed_attribute_name, interceptor):
			return lambda self, *args, **kwargs: interceptor(self, passed_attribute_name, *args, **kwargs)



		for attribute_name, attribute in dct.items():
			#If the attribute is a function
			# TODO: which dunder functions should be intercepted?
			# TODO: if intercept_list is provided by user- we no longer should have to filter here
			if isinstance(attribute, FunctionType) \
					and attribute_name != MethodCallInterceptorClass._interceptor.__name__ \
					and attribute_name in intercept_list\
					and attribute_name not in skip_intercept_list:
				# replace with the interceptor function
				attribute = get_call_interceptor_func(attribute_name, interceptor)
			new_class_dict[attribute_name] = attribute

		for base in bases: #Also intercept if base-class contains the user specified functions

			#Get all methods of the base-class
			methods = get_class_implemented_methods(base, exclude_parent_methods=False)
			for method in methods:
				if method not in new_class_dict \
						and method in intercept_list \
						and method not in skip_intercept_list:
					new_class_dict[method] = get_call_interceptor_func(method, interceptor)
		bases = (MethodCallInterceptorClass,) + bases
		#Make sure there are no duplicates in the bases
		bases = tuple(set(bases))
		return super().__new__(mcs, name, bases, new_class_dict)


def main():
	# pylint: disable=unused-argument missing-function-docstring missing-class-docstring invalid-name
	"""Test function"""
	class TestClass():
		"""_summary_
		"""
		def __init__(self) -> None:
			self.testvariable = 10

		def a_method(self, a, b, c):
			print("A")

		def b_method(self):
			print("b")

		def c_method(self, *args):
			print(f"c: {args}")

		@staticmethod
		def static():
			print("static")

	print(get_class_implemented_methods(TestClass))

	class InterceptedTestClass(TestClass, metaclass=MethodCallInterceptedMeta, intercept_list=["A", "b", "c", "static"]):
		def _interceptor(self, function_name: str, *args, **kwargs):
			print(f"Intercepted call to TestClass function {function_name} with args: {args} and kwargs: {kwargs}")

	print("Start!")
	testje = InterceptedTestClass()
	testje.a_method(1,2,3)
	testje.b_method()
	testje.c_method(1,2,3)
	testje.static()
	print("Done!")


if __name__ == "__main__":
	main()
