# This should be run on the server-machine.
# This is the machine that actually runs the experiments.
import os
from configurun.create import server
from configurun.examples.example_run_function import example_run_function

if __name__ == "__main__":
	server(
		target_function=example_run_function,
		workspace_path=os.path.join(os.getcwd(), "ExampleServerWorkspace"),
		password="password", #Password to connect to the server
		port=469 #Port to connect to the server
	)