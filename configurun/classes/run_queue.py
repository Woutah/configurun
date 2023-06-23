"""
Implements the Runqueue class - a class that manages a list of configurations to pass to a run-function.
"""

import logging
import os
import queue
import sys
import tempfile
import threading
import time
import traceback
import typing
from copy import copy, deepcopy
from datetime import datetime
from enum import Enum

import dill
import multiprocess  # NOTE: 2023-06-20 we use multiprocess instead of multiprocessing because it allows
import multiprocess.managers as managers  # Same here, use multiprocess
import multiprocess.queues


#Import Lock() from multiprocess
# import multiprocess.synchronize

from PySide6 import QtCore

from configurun.configuration.configuration_model import Configuration





log = logging.getLogger(__name__)


CONFIGURATION_MODULE_NAME = "configuration_module"

class LoggerWriter:
	"""
	Simple wrapper that acts as a file-like object and redirects writes to a logger instance
	"""

	def __init__(self, writer):
		#E.g. pass LoggerWriter(log.info) to redirect to log.info
		self._writer = writer
		self._msg = ""

	def write(self, message):
		"""Write the message to the buffer - upon flush, the buffer will be written to the logger"""
		self._msg = self._msg + message
		while '\n' in self._msg:
			pos = self._msg.find('\n')
			self._writer(self._msg[:pos])
			self._msg = self._msg[pos+1:]

	def flush(self):
		"""Flush the buffer"""
		if self._msg != '':
			self._writer(self._msg)
			self._msg = ''

class FileAndQueueHandler(logging.FileHandler):
	"""
	A class that handles logging to a file and to a queue for runQueue items. A thread can then read from the queue
	and emit signals to the main thread to update the console. The queue is used to send log messages to the main thread
	so that they can be displayed in the UI. Simple wrapper around logging.FileHandler and logging.QueueHandler
	"""
	def __init__(self,
	    	item_id : int,
			item_name : str,
			log_queue : typing.Union[queue.Queue,multiprocess.queues.Queue],
	      	log_filename,
			mode='a',
			encoding=None,
			delay=False
		):
		super().__init__(log_filename, mode, encoding, delay)
		self._log_queue = log_queue
		self._last_fs_pos = 0 #Last file system position (in bytes) - used to keep track of where we are in the file
		self._last_fs_pos = self.stream
		self._item_id = item_id
		self._item_name = item_name
		self._filename = log_filename


	def emit(self, record):
		self._last_fs_pos = os.path.getsize(self._filename) #Get the current file size
		super().emit(record)

		#Format the message according to the format of the logger
		msg = self.format(record)
		linesep = os.linesep #Otherwise we will be offset by 1 due to automatic logging to file adding \r\n (2char)
		msg = msg.replace("\n", linesep)#Replace newline char with the os line separator (otherwise we get offset again)
		if self._log_queue is not None:
			self._log_queue.put_nowait(
				(
					self._item_id,
					self._item_name,
					self._filename, #NOTE: we use the file path as the name - this should be unique even across runs
					datetime.now(),
					self._last_fs_pos,
					msg + linesep
				)
			)

#Enum with possible statuses for a run queue item
class RunQueueItemStatus(Enum):
	"""The status of a run queue item, e.g. queued, running, finished etc."""
	#pylint: disable=invalid-name
	Queued = 0 #Waiting to be run (in queue)
	Running = 1 #Currently running
	Finished = 2 #Finished running succesfully
	Stopped = 3 #Stopped by user during running
	Failed = 4 #Failed during execution
	Cancelled = 5 #Removed from the queue



# @dataclass
class RunQueueItem():
	"""
	A class representing a single item in the run queue
	"""
	def __init__(self,
		  	item_id : int,
		  	name : str,
		  	dt_added : datetime,
		  	config : object | Configuration,
			dt_started : datetime | None = None,
		  	status : RunQueueItemStatus = RunQueueItemStatus.Queued,
		  	dt_done : typing.Union[datetime, None] = None,
		  	exit_code : typing.Union[int, None] = None,
		  	stderr : str = ""
		) -> None:
		self.item_id = item_id
		self.name = name
		self.dt_added = dt_added
		self.config = config
		self.dt_started = dt_started
		self.status = status
		self.dt_done = dt_done
		self.exit_code = exit_code
		self.stderr = stderr

	item_id: int
	name: str #Descriptive name used to display in the queue
	dt_added: datetime
	config: object
	status: RunQueueItemStatus = RunQueueItemStatus.Queued

	# done : bool = False
	dt_done : typing.Union[datetime, None] = None #When done running/cancelled/stopped etc.
	dt_started : typing.Union[datetime, None] = None #When running started
	exit_code : typing.Union[int, None] = None
	stderr : str = ""

	def get_copy(self):
		"""
		Get a copy of the object
		"""
		return RunQueueItem(
			item_id=self.item_id,
			name=self.name,
			dt_added=self.dt_added,
			config=copy(self.config),
			dt_started=self.dt_started,
			status=self.status,
			dt_done=self.dt_done,
			exit_code=self.exit_code,
			stderr=self.stderr
		)

class RunQueueItemActions(Enum):
	"""Describe the actions which can be performed on a run queue item"""
	DELETE = 0
	STOP = 1 #A more forceful "cancel" which will also kill the process if it is running
	MOVEUP = 2
	MOVEDOWN = 3
	MOVETOP = 4
	# Requeue = 5 #Re-put #TODO: reput the item in queue? Or reput copy of item in queue?
	CANCEL = 6 #Maybe name as "pause"

class CustomManager(managers.SyncManager):
	"""
	Source:
	https://docs.python.org/3/library/multiprocessing.html#multiprocessing.managers.SyncManager
	allows the default object to be shared between processes
	"""

class CustomProxy(managers.NamespaceProxy): #type:ignore
	"""
	#NOTE: Normally, the proxy used by BaseManager only exposes methods from the object it is referring to.
	This class exposes all attributes - but not the methods"""
	_exposed_ = ('__getattribute__', '__setattr__', '__delattr__')

CustomManager.register(RunQueueItem.__name__, RunQueueItem, CustomProxy)
	#Register the class so that it can be shared
	#  between processes NOTE: making changes in the config itself will not be propagated - only if the whole object is
	# replaced (https://docs.python.org/3/library/multiprocessing.html#multiprocessing-proxy-objects)


class CommandlineQueueEmitter(QtCore.QObject):
	"""
	A class that keeps track of a command-line-queue and emits a signal each time an item is added to the queue.
	Enables the use of multiple threads, while still logging to the UI without polling files.
	"""
	commandLineOutput = QtCore.Signal(int, str, str, datetime, int, str) #id, name, output_path, dt, filepos, new_msg

	def __init__(self, monitored_queue : typing.Union[queue.Queue, multiprocess.queues.Queue]) -> None:
		super().__init__()
		self._monitored_queue = monitored_queue
		self.stop_flag = False

	def run(self):
		"""Worker function that continuously waits for new items in the queue and emits a signal when a new item is
		found, if stop_flag is set, the thread will stop after the next timeout (<1s)
		"""
		while not self.stop_flag: #Continuously wait for new items in the queue
			try:
				args = self._monitored_queue.get(block=True, timeout=0.5) #Timeout every 0.5 seconds to check if we should stop
				self.commandLineOutput.emit(*args)
			except queue.Empty:
				pass
			except BrokenPipeError:
				log.warning("Broken pipe error in CommandlineQueueEmitter - if this occured while app was closing, you can "
	      				"ignore this warning. Queue-emitter will now stop monitoring the command-line output queue.")
				self.stop_flag = True



class RunQueue(QtCore.QObject):
	"""
	A class in which we can queue configurations to run tasks. The Configurations are ran in separate processes.
	We can turn on automatic processing, which will automatically start processing items in the queue if the number
	of processes allows for it.

	TODO: We should also be able to manually start processing items in the queue.
	"""
	queueChanged = QtCore.Signal(object) #Emits a snapshot of the queue when the queue changes (list of ints)
	runListChanged = QtCore.Signal(object) #Emits a snapshot of the all_list when the all_list changes
			# type is (typing.Dict[int, RunQueueItem])
	runItemChanged = QtCore.Signal(int, object) #Emits an id with the new RunQueueItem when a single item in the
			# all_dict has been changed
	queueRunStateChanged = QtCore.Signal(bool) #True if the queue is running, False if it is no longer running
	newRunConsoleOutputPath = QtCore.Signal(int, str, str) #id, name, path --- All processes' stdout/stderr will be
			#redirected to a file, this signal will be emitted when a new file is created (and thus when a new process
			#  is started) #NOTE: for now, both in the same file

	autoProcessingStateChanged = QtCore.Signal(bool) #Emits True if autoprocessing is enabled, False if it is disabled
	# newRunStderrPath = QtCore.Signal(str) #All processes' stdout/stderr will be redirected to a file,
			# this signal will be emitted when a new file is created (and thus when a new process is started)

	#TODO: implement a thread that keeps watch of a separate thread in which a queue with log-updates is processed
	newCommandLineOutput = QtCore.Signal(int, str, str, datetime, int, str) #id, name, output_path, dt, filepos, new_msg
	currentlyRunningIdsChanged = QtCore.Signal(object) #Emits a list of ids that are currently running

	queueResetTriggered = QtCore.Signal() #Emitted when the queue is reset (indicates that all models should be reset)

	def __init__(self,
	      		target_function : typing.Callable[[Configuration], typing.Any],
				n_processes : int = 1,
				log_location : str= "",
				log_location_make_dirs : bool = True
			) -> None:
		"""_summary_

		Args:
			target_function (typing.Callable[[Configuration], typing.Any]): The function which is passed the configuration
				and which is run in a separate process.

			n_processes (int, optional): How many processes to use for processing the queue. Defaults to 1.

			log_location (str, optional): Stdout/stderr of each subprocess is logged to a file for ease-of-access from
				the main process/ui if no path is given, we try to find the temp-path (using tempfile.TemporaryFile()).
				Defaults to None.
			
			log_location_make_dirs (bool, optional): Whether to create the log location if it does not exist. Defaults to True.
		"""

		super().__init__()


		self._target_function = target_function
		self._stopflag = multiprocess.Event()
		self._stopflag.clear()
		self._config_class : type = type(None) #The class of the configuration object

		self._log_location = log_location
		if self._log_location is None or self._log_location == "": #If no
				#log location is given, use the tempdir (os-specific)
			self._log_location = tempfile.gettempdir()
			#Create sub folder Configurun in tempdir so we have everything in one place
			self._log_location = os.path.join(self._log_location, "configurun")
			if not os.path.exists(self._log_location):
				os.mkdir(self._log_location)
		elif not os.path.exists(self._log_location):
			if log_location_make_dirs:
				os.makedirs(self._log_location)
			else:
				raise ValueError(f"Passed log location {self._log_location} does not exist - either create it before "
		     		"running or set it to None to use the temp-directory, or enable log_location_make_dirs to create "
					"the directory")
		
		log.info(f"Runqueue log location: {self._log_location}")

		self._manager = CustomManager() #To share data between processes
		self._manager.start() #Start the manager

		# self._queue : queue.Queue = queue.Queue()
		self._queue : typing.List[int] = self._manager.list() # type: ignore #Consists of a queue of id's which can be
			# used to retrieve the configuration from the all_dict - can't be an actual queue because we want to be able
			# to remove/move items in the queue
		self._queue_mutex = multiprocess.Lock() #Lock for the queue

		self._all_dict : typing.Dict[int, RunQueueItem] = self._manager.dict() #type: ignore #Should consists of a list
			# of dicts with keys (id, dt_added, Name, Config, done, dt_done, exit_code, stderr)
		self._all_dict_mutex = multiprocess.Lock()


		self._autoprocessing_enabled = False #Whether to automatically start processing items in the queue
		self._running_processes : typing.Dict[int, multiprocess.Process] = {} #ID -> process
		self._running_processes_mutex = multiprocess.Lock()

		self._n_processes = n_processes
		self._cur_id = 0 #Start at 0

		self._queue_processor_thread : threading.Thread | None = None #Thread that processes the queue
		self._queue_signal_updater_thread : threading.Thread | None = None #Thread that keeps the queue updated

		self._cmd_id_name_path_dict : typing.Dict[int, typing.Tuple[str, str]] = self._manager.dict() # type: ignore
			# Dictionary that keeps track of the output file for each process
		self._cmd_id_name_path_dict_mutex = multiprocess.Lock() #Lock for the cmd_id_path_dict
		#Queue that keeps track of outputs to the command line for each running process.
		self._command_line_output_queue = self._manager.Queue()



		self.queue_emitter = CommandlineQueueEmitter(self._command_line_output_queue)
		self.queue_emitter_thread = QtCore.QThread()
		self.queue_emitter.moveToThread(self.queue_emitter_thread)
		self.queue_emitter_thread.started.connect(self.queue_emitter.run)
		self.queue_emitter_thread.start()
		self.queue_emitter.commandLineOutput.connect(self.newCommandLineOutput.emit)
		# self.queue_emitter.commandLineOutput.connect(lambda *args: print(f"Got command line output: {args}"))

	def get_command_line_output(self, item_id : int, fseek_end : int, max_bytes : int) -> typing.Tuple[str, datetime]:
		"""
		Get the command line output for a given id.

		args:
			id (int): the id of the item to get the command line output for
			fseek_end (int): the position in the file to end reading at, -1 is EOF
			max_bytes (int): the maximum number of bytes to read, -1 for all bytes

		return (str, datetime.datetime): the command line output for the given id and the datetime at which the output
			was last updated
		"""
		last_edit_dt = datetime(1970,1,1)
		with self._cmd_id_name_path_dict_mutex:
			if item_id not in self._cmd_id_name_path_dict or not os.path.exists(self._cmd_id_name_path_dict[item_id][1]):
				return ("", last_edit_dt)

			last_edit_dt = datetime.fromtimestamp(os.path.getmtime(self._cmd_id_name_path_dict[item_id][1]))
			filepath = self._cmd_id_name_path_dict[item_id][1]

		with open(filepath, "r", encoding="utf-8") as read_file:
			if fseek_end == -1 and max_bytes == -1: #If just reading the whole file
				return read_file.read(), last_edit_dt
			elif fseek_end == -1: #If reading from the end of the file
				read_file.seek(0, max(0, os.SEEK_END - max_bytes))
			if max_bytes == -1:
				return read_file.read(), last_edit_dt

			return read_file.read(max_bytes), last_edit_dt

	def get_command_line_info_list(self) -> typing.Dict[int, typing.Tuple[str, str, int, bool]]:
		"""
		Get a list of the info of all command lines outputs from items that have been ran or are running.

		returns:
			dict[int, tuple[str, str, int, bool]]: a dictionary with the id as key and a tuple with the:
			 - name of the item
			 - path to the output file
			 - length of the output file
			 - Whether the id is currently running (bool)
		"""
		with self._cmd_id_name_path_dict_mutex:
			# return copy(dict(self._cmd_id_name_path_dict)) #TODO: copy probably unnecesary after converting
			cur_dict = dict(self._cmd_id_name_path_dict)

		new_dict = {}

		for key, val in cur_dict.items():
			if not os.path.exists(val[1]) and os.path.isfile(val[1]):
				length = 0
			else:
				length = os.path.getsize(val[1])

			currently_running = False
			with self._running_processes_mutex:
				currently_running = key in self._running_processes #If running

			new_dict[key] = (val[0], val[1], length, currently_running)
		return new_dict


	def load_queue_contents_from_file(self, path : str):
		"""
		Load a queue from a file - using pickle as to make things easy no matter what type of settings object is used.
		Settings such as _n_processes are not loaded.
		TODO: maybe enforce JSON?

		Args:
			path (str): the path to the file to load the queue from
		"""
		if not os.path.exists(path):
			raise OSError(f"Could not load queue from path {path}, path does not exist.")

		with open(path, "rb") as file:
			loaded_all_dict, loaded_queue, loaded_cur_id = dill.load(file)
			with self._all_dict_mutex, self._queue_mutex:
				log.info(f"Loading queue from file {path}...")
				self._all_dict = loaded_all_dict
				self._queue = loaded_queue
				self._cur_id = loaded_cur_id

	def save_queue_contents_to_file(self, path : str, save_running_as_stopped : bool = False):
		"""
		Save the queue to a file - using pickle as to make things easy no matter what type of settings object is used.
		Runqueue-settings such as _n_processes are not saved

		Args:
			path (str): the path to the file to save the queue to
		"""
		with open(path, "wb") as file:
			with self._all_dict_mutex, self._queue_mutex: #Make sure queue and all_dict are consistent with one another
				all_dict_copy = self._get_run_list_snapshot_copy_nolocks()
				queue_copy = self._get_queue_snapshot_copy_no_locks()

			for key, runqueue_item in all_dict_copy.items():
				if runqueue_item.status == RunQueueItemStatus.Running:
					if save_running_as_stopped:
						runqueue_item.status = RunQueueItemStatus.Stopped
						runqueue_item.stderr = "Process was running when queue was saved, so it was saved as cancelled."
						runqueue_item.dt_done = datetime.now()
					else:
						raise OSError(f"Could not save queue to file {path}, item with ID {key} is still running and\
		      						save mode does not allow for saving running items as cancelled.")


			dill.dump((all_dict_copy, queue_copy, self._cur_id), file) #Save a tuple of the queue and all_dict



	def get_actions_for_id(self, item_id : int | None) -> typing.List[RunQueueItemActions]:
		"""
		Get a list of actions that can be performed on the item with id

		Args:
			id (int): the id of the item to get the actions for
		"""
		actions = []
		if item_id is None:
			return actions
		if item_id in self._queue:
			actions = [
				RunQueueItemActions.DELETE,
				RunQueueItemActions.CANCEL, #Remove from queue (="cancel")
				RunQueueItemActions.MOVEUP,
				RunQueueItemActions.MOVEDOWN,
				RunQueueItemActions.MOVETOP
			]
		elif item_id in self._all_dict:
			#Lock queue when removing
			with self._all_dict_mutex, self._queue_mutex:
				if self._all_dict[item_id].status == RunQueueItemStatus.Stopped \
						or self._all_dict[item_id].status == RunQueueItemStatus.Finished \
						or self._all_dict[item_id].status == RunQueueItemStatus.Cancelled:
					actions = [
						RunQueueItemActions.DELETE #TODO: Add requeue
					]
				elif self._all_dict[item_id].status == RunQueueItemStatus.Failed:
					actions = [
						RunQueueItemActions.DELETE #TODO: Add retry
					]
				elif self._all_dict[item_id].status == RunQueueItemStatus.Running:
					actions = [
						RunQueueItemActions.STOP
					]
				elif self._all_dict[item_id].status == RunQueueItemStatus.Queued: #When popping from the queue, just before
						#settings the status to "running", the status is "queued" without it being in the queue
						# do we need to handle this case?
					actions = [
						RunQueueItemActions.STOP
					]

				else:
					raise KeyError(f"Could not get actions for item with ID {item_id} due to unknown status: \
		     				{str(self._all_dict[item_id].status)}"
		     			)


		return actions

	def is_autoprocessing_enabled(self):
		"""Whether autoprocessing is enabled"""
		return self._autoprocessing_enabled

	def do_action_for_id(self, item_id : int, action : RunQueueItemActions):
		"""
		Do an action for a given id

		Args:
			id (int): the id of the item to do the action for
			action (QueueItemActions): the action to perform on the item
		"""
		if action == RunQueueItemActions.DELETE:
			self.delete_id(item_id)
		elif action == RunQueueItemActions.STOP:
			self.stop_id(item_id)
		elif action == RunQueueItemActions.CANCEL:
			self.cancel_id(item_id)
		elif action == RunQueueItemActions.MOVEUP:
			self.rel_move_in_queue(item_id, -1)
		elif action == RunQueueItemActions.MOVEDOWN:
			self.rel_move_in_queue(item_id, 1)
		elif action == RunQueueItemActions.MOVETOP:
			self._move_id_in_queue(item_id, 0)
		else:
			raise NotImplementedError(f"Unknown action: {str(action)}")

	def cancel_id(self, item_id):
		"""
		Cancel by id -> Remove a configuration from the queue (by id), but don't delete it

		Args:
			id (int): the id of the item to cancel
		"""
		#Lock queue when removing
		with self._all_dict_mutex, self._queue_mutex:
			if item_id not in self._queue: #Only do something if the id is in the queue
				raise KeyError(f"Could not cancel {item_id}, ID not in queue.")
			self._all_dict[item_id].status = RunQueueItemStatus.Cancelled
			self._queue.remove(item_id)
			queue_snapshot = self._get_queue_snapshot_copy_no_locks()
			item_copy = deepcopy(self._all_dict[item_id])

		self.queueChanged.emit(queue_snapshot)
		self.runItemChanged.emit(item_id, item_copy)
		return



	def stop_id(self, item_id : int):
		"""
		Stop by id. Tries to stop a currently running configuration (by id). If the configuration is not running,
		it will be removed from the queue and it will be marked as cancelled instead of stopped.

		Args:
			id (int): the id of the item to stop

		#TODO: create force_stop argument, raise ItemRunningError if not force_stop and item is running, which can then
		be caught by the caller to ask the user if they want to force stop the item
		"""
		#Lock queue when removing
		log.debug(f"Current queue: {self._queue}")
		self._all_dict_mutex.acquire()
		self._queue_mutex.acquire()
		if item_id in self._queue:
			self._queue.remove(item_id)
			self._all_dict[item_id].status = RunQueueItemStatus.Cancelled
			queue_snapshot = self._get_queue_snapshot_copy_no_locks()
			item_copy = self._all_dict[item_id].get_copy()
			self._all_dict_mutex.release()
			self._queue_mutex.release()
			self.queueChanged.emit(queue_snapshot)
			self.runItemChanged.emit(item_id, item_copy)
			return
		elif item_id in self._all_dict: #When raising an exception, we need to release the locks
			self._all_dict_mutex.release()
			self._queue_mutex.release()
			if self._all_dict[item_id].status == RunQueueItemStatus.Running:
				raise NotImplementedError("Stopping a running process is not implemented yet.")
			raise KeyError(f"Could not stop {item_id}, item with ID is not running, and item with this ID was not in \
		  		queue.")



	def _move_id_in_queue(self, item_id : int, new_queue_pos : int, use_locks=True):
		"""
		Move a configuration in the queue.

		Args:
			id (int): the id of the item to move
			new_queue_pos (int): the new position in the queue
			use_locks (bool, optional): whether to use locks when moving the item. Defaults to True. Is used internally
				when items are already locked
		"""
		#Lock queue when removing (unless we are already holding the locks)
		if use_locks:
			self._all_dict_mutex.acquire()
			self._queue_mutex.acquire()

		if item_id in self._queue:
			self._queue.remove(item_id)
			self._queue.insert(new_queue_pos, item_id)
		else: #Throw exception
			if use_locks:
				self._all_dict_mutex.release()
				self._queue_mutex.release()
			raise KeyError(f"Could not move item with id {item_id}, ID not in queue.")

		self.queueChanged.emit(self._get_queue_snapshot_copy_no_locks())
		if use_locks:
			self._all_dict_mutex.release()
			self._queue_mutex.release()



	def rel_move_in_queue(self, item_id : int, rel_move : int):
		"""Relative move in the queue, -1 = move up, 1 = move down. 0 is the top of the queue.

		Args:
			id (int): the id of the item to move
			rel_move (int): the mount to move the item. Negative values move the item up in the queue, positive values
			  move it down
		"""
		with self._all_dict_mutex, self._queue_mutex:
			if item_id in self._queue:
				cur_pos = self._queue.index(item_id)
				new_pos = min(len(self._queue), max(0, cur_pos + rel_move))
				self._move_id_in_queue(item_id, new_pos, use_locks=False) #We already acquired the locks
			else:
				self._all_dict_mutex.release()
				self._queue_mutex.release()
				raise KeyError(f"Could not move item with id {item_id}, ID not in queue.")





	def delete_id(self, item_id : int):
		"""
		Remove a configuration from the queue and list
		args:
			id (int): the id of the item to remove
		"""
		#Lock queue when removing
		with self._all_dict_mutex, self._queue_mutex:
			if self._all_dict[item_id].status == RunQueueItemStatus.Running:
				self._all_dict_mutex.release()
				self._queue_mutex.release()
				raise NotImplementedError(f"Could not delete item with id {item_id}, item is running.") #TODO: Add force del?

			if item_id in self._queue:
				self._queue.remove(item_id)

			#Also remove from all_dict -> the two should be in sync
			del self._all_dict[item_id]

			run_list_snapshot = self._get_run_list_snapshot_copy_nolocks()
			queue_snapshot = self._get_queue_snapshot_copy_no_locks()

		self.queueChanged.emit(queue_snapshot)
		self.runListChanged.emit(run_list_snapshot)




	def get_queue_snapshot_copy(self) -> list[int]:
		"""
		Get a snapshot of the queue

		returns:
			list[int]: a copy of the queue (list of ids)
		"""
		#Lock queue when getting snapshot
		with self._queue_mutex:
			snapshot = copy(list(self._queue)) #TODO: copy might be unnecesary after converting proxylist to list
		return snapshot

	def _get_queue_snapshot_copy_no_locks(self) -> list[int]:
		snapshot = copy(self._queue)
		return list(snapshot)


	def _get_run_list_snapshot_copy_nolocks(self) -> typing.Dict[int, RunQueueItem]:
		"""Get a snapshot of the all_list without locks - should only be used internally when locks are already held

		Returns:
			typing.Dict[int, RunQueueItem]: A copy of the run_list
		"""
		ret_dict = {}
		for key, value in self._all_dict.items(): #Since this is a nested proxy-object, call get_copy on each item
			ret_dict[key] = value.get_copy()
		return ret_dict

	def get_run_list_snapshot_copy(self) -> typing.Dict[int, RunQueueItem]:
		"""
		Get a snapshot of the all_list
		"""
		with self._all_dict_mutex:
			snapshot = self._get_run_list_snapshot_copy_nolocks()
		return snapshot


	def start_autoprocessing(self):
		"""
		Start automatically processing items in the queue
		"""
		self._autoprocessing_enabled = True
		self.autoProcessingStateChanged.emit(True)
		self._run_queue()

	# def set_n_processes(self, n_processes):
	# 	"""
	# 	Set the number of processes
	# 	"""
	# 	self._n_processes = n_processes
	# 	self.start()

	def get_running_configuration_count(self):
		"""
		Get a list of the currently running configurations
		"""
		count = 0
		with self._all_dict_mutex, self._queue_mutex:
			for queue_item in self._all_dict.values():
				if queue_item.status == RunQueueItemStatus.Running: #Count all running processes
					count+=1

		return count

	# def _wait_stop(self, timeout = 10_000):
	# 	self._stopflag.set()
	# 	start_time = time.time()
	# 	for process in self._running_processes.values():
	# 		remaining_time = start_time + timeout - time.time()
	# 		process.join(timeout )

	# 	self._running = False

	def stop_autoqueueing(self):
		"""
		Stop automatically processing new items, finish processing the current items and then stop the queue.
		"""
		# self.stop_autoqueueing()
		self._autoprocessing_enabled = False
		self._stopflag.set()
		self.autoProcessingStateChanged.emit(False)

		# if block:
		# 	self._wait_stop(timeout=timeout)
		# else:
		# 	threading.Thread(target=self._wait_stop, args=(timeout,)).start()

	def force_stop(self):
		"""
		Force stop all running processes and set the configuration to cancelled
		"""
		raise NotImplementedError("Force stopping the run queue is not implemented yet.")
		#TODO: set stop flag, then force stop all running processes and set the configurations of each to cancelled


	def add_to_queue(self, name : str, config : Configuration):
		"""
		Add a configuration to the queue

		Args:
			name (str): What name to display in the queue
			config (typing.Any): The configuration (data) that is held by this item. Is only processed by the target
				of the run queue
		"""
		log.debug(f"Adding config with name {name} to queue.")
		new_item_id = self._cur_id
		self._cur_id += 1
		dt_added = datetime.now()
		new_item = self._manager.RunQueueItem(item_id=new_item_id,name=name, dt_added=dt_added, config=config) #pylint: disable=no-member #type: ignore
		# new_item = RunQueueItem(item_id=new_item_id,name=name, dt_added=dt_added, config=config)

		with self._all_dict_mutex, self._queue_mutex:
			self._queue.append(new_item_id)
			self._all_dict[new_item_id] = new_item
			snapshot = self._get_run_list_snapshot_copy_nolocks()
			queue_snapshot = self._get_queue_snapshot_copy_no_locks()

		self.runListChanged.emit(snapshot) #Emit outside of lock
		self.queueChanged.emit(queue_snapshot) #Emit outside of lock

		log.debug("Done adding config to queue.")

	def _run_queue(self):
		"""
		Run the queue (the producer), removes items from the queue and puts them in the currently-processing-queue
		(at which point the consumer will pick them up, and editing will no longer be possible)
		"""
		# self._stopflag = multiprocessing.Event()
		self._stopflag.clear()

		if self._queue_processor_thread is None or not self._queue_processor_thread.is_alive():
			self._queue_processor_thread = threading.Thread(target=self._run_queue_item_processor)
		self._queue_processor_thread.start()


		#Create thread and run _run_queue_item_producer if it doesn't exist yet
		if self._queue_signal_updater_thread is None or not self._queue_signal_updater_thread.is_alive():
			self._queue_signal_updater_thread = threading.Thread(target=self._run_queue_item_updater)
			self._queue_signal_updater_thread.start()




	def _run_queue_item_updater(self):
		#While we are not stopping, or there are still processes running, keep updating
		while not self._stopflag.is_set() or len(self._running_processes) > 0:
			self.runListChanged.emit(self.get_run_list_snapshot_copy()) #For now, just update the whole list every x s.
			self.queueChanged.emit(self.get_queue_snapshot_copy())
			time.sleep(1)




	@staticmethod
	def _process_queue_item(
				target_function : typing.Callable[[Configuration], typing.Any],
				queue_item_id : int,
				queue_item_name : str,
				command_line_output_path : str,
				command_line_output_queue : multiprocess.queues.Queue,
				all_dict : typing.Dict[int, RunQueueItem],
				id_queue : typing.List[int],
				all_dict_mutex : threading.Lock,
				queue_mutex : threading.Lock
			): #TODO: add log_changed queue
		"""
		Process a single queue item
		"""
		log.info(f"Now processing queue item {queue_item_id}")

		#Output stdou/stderr to file
		# file = open(std_path, "a", buffering=1)

		# TODO: might be more neat to log using the logging module instead - but
		root = logging.getLogger()
		root.setLevel(logging.DEBUG)
		handler = FileAndQueueHandler(
				item_id=queue_item_id,
				item_name=queue_item_name,
				log_queue=command_line_output_queue,
				log_filename=command_line_output_path,
				mode="a",
				encoding="utf-8"
			)
		handler.setLevel(logging.DEBUG)
		formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}] {asctime}  {levelname:<7s}   {message}", style='{')
		handler.setFormatter(formatter)
		root.addHandler(handler)

		sys.stdout = LoggerWriter(log.info)
		sys.stderr = LoggerWriter(log.error)


		with all_dict_mutex, queue_mutex:
			queue_item = all_dict[queue_item_id]
			queue_item.status = RunQueueItemStatus.Running #Should no longer be editable -> probably already done in
			 #_run_queue_item_processor, but just to be sure
			queue_item.dt_started = datetime.now()

		try:
			log.info(f"Started running queue item {queue_item_id} inside process {os.getpid()}")
			configuration = copy(queue_item.config) #Just to be sure we don't change the original config, make a copy
			# config.set_option_data(options_data) #NOTE: Although Options allow for a lot of types -
			# #in the runqueue, we should always expect a 'OptionsData' type
			assert isinstance(configuration, Configuration), f"Expected runqueue item config to be of type Configuration, \
				but got {type(configuration)} instead."
			target_function(configuration)
			log.info("Done running target function.")

		except Exception as exception: # pylint: disable=broad-exception-caught #Catch all exceptions in this runqueue
			msg = f"{type(exception).__name__}:{exception}"
			log.error(msg)

			#use log.error to print traceback
			log.error(traceback.format_exc())

			if queue_item: #If queue item is set -> also report item as error
				with all_dict_mutex:
					queue_item.status = RunQueueItemStatus.Failed
					queue_item.dt_done = datetime.now()
					queue_item.exit_code = -1 #error exit code
					queue_item.stderr = msg
			# raise e #TODO: create
			log.error(f"Encountered error while running queue item {queue_item_id} inside process {os.getpid()}... \
	     		Terminating process.")
			return


		with all_dict_mutex, queue_mutex:
			queue_item.status = RunQueueItemStatus.Finished
			queue_item.dt_done = datetime.now()
			queue_item.exit_code = 0 #normal exit code


		log.info(f"Processed item with id {queue_item.item_id} and name {queue_item.name}, "
	   		f"queue size is now {len(id_queue)}.")




	def _run_queue_item_processor(self):
		"""
		To be ran in a separate thread.
		1. Continuously checks the queue for items to process, then calls the _run_queue_item function to process the item
			If there is process-space (n_processes), it will start a new process to process the item
			Checks the processes for completion and updates the queue accordingly

		2. Continuously checks the processes for completion and updates the queue accordingly
		"""
		log.debug("Now running queue item processor")


		while True:
			if self._stopflag.is_set(): #If stopping, break TODO: force stop?
				return
			try:
				if len(self._queue) > 0 and len(self._running_processes) < self._n_processes: #If there are items in the
							# queue and there is process-space, we can start a new process

					with self._all_dict_mutex, self._queue_mutex:
						#Pop first, then set to running state
						queue_item_id = self._queue.pop(0) #
						queue_item_name = self._all_dict[queue_item_id].name
						self._all_dict[queue_item_id].status = RunQueueItemStatus.Running #Should no longer be editable

					log.debug(f"Attempting to start process-function for item with id {queue_item_id}")
					#TODO: run the actual item -> maybe wrap in a try/except to catch errors. Make sure no locks are
					#  held when running the item


					cur_logfile_loc = os.path.join(self._log_location, f"{queue_item_id}_{queue_item_name}")
					number = 1
					extra_string = ""
					while os.path.exists(f"{cur_logfile_loc}{extra_string}.out"): #If file exists, add number
						#to the end NOTE: otherwise, if a run fails and is restarted, the old log will be overwritten
						extra_string = f"_{number}"
						number += 1
					cur_logfile_loc = f"{cur_logfile_loc}{extra_string}.out"
					#Create file NOTE: we need to create the file before emitting the signal, otherwise we can't start
					#  "watching" the file
					open(cur_logfile_loc, "w", encoding="utf-8").close()
					log.debug(f"Will log to file: {cur_logfile_loc}")
					with self._cmd_id_name_path_dict_mutex:
						self._cmd_id_name_path_dict[queue_item_id] = (queue_item_name, cur_logfile_loc)

					self.newRunConsoleOutputPath.emit(queue_item_id, queue_item_name, cur_logfile_loc)
					assert(queue_item_id not in self._running_processes), "Queue item id already in running processes"
					with self._running_processes_mutex:
						self._running_processes[queue_item_id] = multiprocess.Process(
								target=RunQueue._process_queue_item,
								args = (
									self._target_function,
									queue_item_id,
									queue_item_name,
									cur_logfile_loc,
									self._command_line_output_queue,
									self._all_dict,
									self._queue,
									self._all_dict_mutex,
									self._queue_mutex,
								)
							)

						self._running_processes[queue_item_id].start() #Start processing the item

						running_ids = list(self._running_processes.keys())
					self.currentlyRunningIdsChanged.emit(running_ids)
					log.info(f"Started processing item with id {queue_item_id} and name {queue_item_name}, \
	   						queue is now {self._queue}, all_dict is of size {len(self._all_dict)}")
				else: #TODO: maybe instead pass a "done-queue" to process_queue_item and have it put itself inside
					updated = False
					with self._running_processes_mutex:
						id_list = list(self._running_processes.keys())
						for cur_id in id_list:
							if not self._running_processes[cur_id].is_alive() \
									and self._running_processes[cur_id].exitcode is not None: #If the process is finished
								self._running_processes[cur_id].join()
								del self._running_processes[cur_id]
								updated = True
						running_ids = list(self._running_processes.keys())

					if not updated: #If we achieved nothing, sleep for a bit
						time.sleep(0.4)
					else:
						self.currentlyRunningIdsChanged.emit(running_ids)

			except queue.Empty:
				pass




if __name__ == "__main__":
	from PySide6 import QtWidgets  # pylint: disable=ungrouped-imports
	test_app = QtWidgets.QApplication(sys.argv)
	test_queue = RunQueue(lambda *_: print("Target function has been called... Now quitting..."))
	print("Created a queue")
	test_app.exec()
