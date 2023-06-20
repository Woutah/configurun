"""
This script runs the example in which we can select our model/dataset type - including Sklearn models
This example, in addition to the requirements.txt, requires the Sklearn library to be installed.
"""


import logging

from MLQueue.configuration.ConfigurationModel import ConfigurationModel
from MLQueue.examples.ExampleOptions.ExampleOptions import \
    ExampleDatasetOptions
from MLQueue.examples.ExampleOptions.SklearnOptions import (
    SKLEARN_NAME_DATACLASS_DICT, SklearnMainOptions)

log = logging.getLogger(__name__)

if __name__ == "__main__":
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}]  {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.INFO) #Without time
	log.info("Starting the example implementation, including Sklearn models")
