"""An example run function that takes about 20 seconds to complete"""

import logging
import time

from configurun.configuration.configuration import Configuration

log = logging.getLogger(__name__)

def example_run_function(config : Configuration, *args, **kwargs): #pylint: disable=unused-argument
	"""Example run function. The run-function always takes a configuration as the first argument.

	The arguments after that are the arguments passed to the ```RunQueue._process_queue_item()```-method.

	args:
		config (Configuration): The configuration to use
		*args: The arguments passed to the ```RunQueue._process_queue_item()```-method.
		**kwargs: The keyword arguments passed to the ```RunQueue._process_queue_item()```-method.

	returns:
		(None): Nothing is returned
	"""
	log.info("The example run function was called with the following configuration:")
	for key, value in config.options.items():
		log.info(f"{key} : {type(value).__name__}")

	log.info("We will now be simulating a task that takes about 20 seconds to complete")

	for i in range(20):
		log.info(f"Progress: {i}/20")
		time.sleep(1)

	log.info("Done with the example run function... Now exiting...")
