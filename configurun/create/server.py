"""
Declaration separate from local_app and client_app to enable the server to skip importing PySide6 altogether.
"""
import logging
import os
import typing
import time

from configurun.classes.run_queue import RunQueue
from configurun.classes.run_queue_server import RunQueueServer
log = logging.getLogger(__name__)

def _cleanup_server(run_queue_server : RunQueueServer):
	"""
	Callback function to, on process end (Ctrl+C), cleanup the server and close the app

	Args:
		app (QtCore.QCoreApplication): The app in which the server is running
		run_queue_server (RunQueueServer): The runqueue-server instance
	"""
	log.info("Received shutdown signal, now attempting to cleaning up server and close app")
	run_queue_server.terminate() #Disconnect all, stop running and save progress
	# app.quit()

	log.info("Server cleanup complete, exiting")

def server(
			target_function : typing.Callable,
			workspace_path : str = "",
			run_queue_n_processes : int = 1,
			password : str = "",
			hostname : str = "localhost",
			port : int = 5454,
			log_level : int = logging.INFO,
			run_queue_kwargs : typing.Optional[typing.Dict[str, typing.Any]] = None
		):
	"""
	WARNING: RUNNING A SERVER ALLOWS OTHER MACHINES ON THIS NETWORK TO EXECUTE ARBITRARY CODE IF THEY KNOW THE PASSWORD
	PLEASE RUN THIS IN A TRUSTED NETWORK ENVIRONEMENT. Run at your own risk.

	Convenience function that constructs a local instance of the runqueue-server with the specified target function.
	It then runs the server in a QtCore app.

	Args:
		target_function (typing.Callable): The target function on which tasks will be run, this function should take
			a configuration as the first argument, and the rest of the arguments should be the arguments passed to the
			```RunQueue._process_queue_item()```-method.

		workspace_path (str, optional): The path to the workspace folder. Attempts to load progress from here, also saves
			progress to here. Defaults to "". If empty/default, the default workspace folder is used (~/Configurun-server/)

		run_queue_n_processes (int, optional): The number of processes to use in the run queue. Defaults to 1.

		run_queue_kwargs (typing.Dict[str, typing.Any], optional): The keyword arguments passed to the
			RunQueue constructor. Defaults to {}.
			Possible kwargs:
				log_location (str) : The path where the log file should be outputted (should be a folder)
					if blank, use default location using TEMP folder
	"""
	#=========== Initialize logger ===========
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}]  {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=log_level) #Without time
	root_logger = logging.getLogger()
	root_logger.setLevel(log_level)



	if run_queue_kwargs is None:
		run_queue_kwargs = {}

	assert len(password) > 0, "Password for server cannot be empty"

	if workspace_path == "" or workspace_path is None:
		workspace_path = os.path.join(os.path.expanduser("~"), "Configurun-Server")
		log.info(f"No workspace path provided, using default: {workspace_path}")

	os.makedirs(workspace_path, exist_ok=True) #Create the workspace folder if it does not exist yet

	runqueue = RunQueue(
		target_function=target_function,
		n_processes=run_queue_n_processes,
		log_location=os.path.join(workspace_path, "logs"),
		**run_queue_kwargs
	)

	run_queue_server = RunQueueServer(
			run_queue=runqueue,
			password=password,
			hostname=hostname,
			port=port,
			workspace_path=workspace_path
	)
	run_queue_server.run()
	log.info("Server started, listening for client connections...")
	while True:
		try:
			time.sleep(1)
		except KeyboardInterrupt:
			_cleanup_server(run_queue_server)
			break