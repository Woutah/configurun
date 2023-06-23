"""
Example of argparse options, used to create a configuration model
"""
import argparse

parser_example = argparse.ArgumentParser()

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


parsed_args = parser_example.parse_args()


if __name__ == "__main__":
	from configurun.create import local_app
	from configurun.configuration.argparse_to_dataclass import argparse_to_dataclass

	new_dataclass = argparse_to_dataclass(parser_example)
	the_globals = globals()
	local_app(
		target_function = lambda x, *_: print(x),
		options_source = new_dataclass
	)
