"""
Example of argparse options, used to create a configuration model
"""
import argparse

parser_example = argparse.ArgumentParser()

parser_example.add_argument("--required_arg", type=str, required=True, help="Required argument help")
parser_example.add_argument("--str_arg", type=str, default="Default str", help="Comment")
parser_example.add_argument("--int_arg", type=int, default=0, help="Int argument help")
parser_example.add_argument("--float_arg", type=float, default=0.0, help="Float argument help")
parser_example.add_argument("--bool_arg", type=bool, default=False, help="Bool argument help")
parser_example.add_argument("--float_in_range", type=float, default=0.0, help="A float in a range", choices=range(0,10))

#=== Store true====
parser_example.add_argument("--store_true_arg", action="store_true", help="Do something")

#=== Choices ====
parser_example.add_argument("--str_choice_arg", type=str, choices=["a", "b", "c"], default="a", help="Choice 1")
parser_example.add_argument("--int_choice_arg", type=int, choices=[1, 2, 3], default=1, help="Choice 2")

def run_argparse_example():
	"""
	Runs an example local app with the example argparse options
	"""
	# pylint: disable=import-outside-toplevel
	import os
	import tempfile

	from configurun.app.create_run import run_local
	from configurun.app.main_window import APP_NAME

	tempdir = tempfile.gettempdir()
	workspace_path = os.path.join(tempdir, APP_NAME, "Configurun-Argparse-Example")
	run_local(
		target_function = lambda x, *_: print(x),
		options_source = parser_example,
		workspace_path=workspace_path
	)

if __name__ == "__main__":
	run_argparse_example()
