"""An example run function that takes about 20 seconds to complete"""

import logging

from MLQueue.configuration.Configuration import Configuration
import time

log = logging.getLogger(__name__)

def run(config : Configuration):
	"""Example run function"""
	log.info("The example run function was called with the following configuration:")
	for key, value in config.options.items():
		log.info(f"{key} : {type(value).__name__}")

	log.info("We will now be simulating a task that takes about 20 seconds to complete")

	for i in range(20):
		log.info(f"Progress: {i}/20")
		time.sleep(1)

	log.info("Done with the example run function... Now exiting...")