import queue
import multiprocessing as multiprocessing
import multiprocessing.managers as managers
from datetime import datetime
from copy import copy, deepcopy
from PySide6 import QtCore
import typing
from enum import Enum
import time
import threading
import sys
import os
import tempfile
import traceback
from MachineLearning.framework.options.options import Options
import pickle
import queue
import logging
log = logging.getLogger(__name__)


class LoggerWriter:
	"""
	Simple wrapper that acts as a file-like object and redirects writes to a logger instance
	"""
	
	def __init__(self, writer): 
		#E.g. pass LoggerWriter(log.info) to redirect to log.info
		self._writer = writer
		self._msg = ""

	def write(self, message):
		self._msg = self._msg + message
		while '\n' in self._msg:
			pos = self._msg.find('\n')
			self._writer(self._msg[:pos])
			self._msg = self._msg[pos+1:]

	def flush(self):
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
			queue : typing.Union[queue.Queue,multiprocessing.Queue], 
	      	filename, 
			mode='a', 
			encoding=None,
			delay=False
		):
		super().__init__(filename, mode, encoding, delay)
		self._queue = queue
		self._last_fs_pos = 0 #Last file system position (in bytes) - used to keep track of where we are in the file
		self._last_fs_pos = self.stream
		self._item_id = item_id
		self._item_name = item_name
		self._filename = filename

		
	def emit(self, record):
		self._last_fs_pos = os.path.getsize(self._filename) #Get the current file size 
		super().emit(record)

		#Format the message according to the format of the logger
		msg = self.format(record)
		linesep = os.linesep #Otherwise we will be offset by 1 due to automatic logging to file adding \r\n (2char)
		msg = msg.replace("\n", linesep)#Replace newline char with the os line separator (otherwise we get offset again)
		if self._queue is not None:
			self._queue.put_nowait(
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
		  	id : int,
		  	name : str,
		  	dt_added : datetime,
		  	config : object,
			dt_started : datetime | None = None,
		  	status : RunQueueItemStatus = RunQueueItemStatus.Queued,
		  	dt_done : typing.Union[datetime, None] = None,
		  	exit_code : typing.Union[int, None] = None,
		  	stderr : str = ""
		) -> None:
		self.id = id
		self.name = name
		self.dt_added = dt_added
		self.config = config
		self.dt_started = dt_started
		self.status = status
		self.dt_done = dt_done
		self.exit_code = exit_code
		self.stderr = stderr

	id: int
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
			id=self.id,
			name=self.name,
			dt_added=self.dt_added,
			config=copy(self.config),
			dt_started=self.dt_started,
			status=self.status,
			dt_done=self.dt_done,
			exit_code=self.exit_code,
			stderr=self.stderr
		)

class QueueItemActions(Enum):
	Delete = 0
	Stop = 1 #A more forceful "cancel" which will also kill the process if it is running
	MoveUp = 2
	MoveDown = 3
	MoveTop = 4
	# Requeue = 5 #Re-put #TODO: reput the item in queue? Or reput copy of item in queue?
	Cancel = 6 #Maybe name as "pause"

class CustomManager(managers.SyncManager): 
	"""
	Source: 
	https://docs.python.org/3/library/multiprocessing.html#multiprocessing.managers.SyncManager
	allows the default object to be shared between processes
	"""
	pass

class CustomProxy(managers.NamespaceProxy): #type:ignore 
	"""
	#NOTE: Normally, the proxy used by BaseManager only exposes methods from the object it is referring to. 
	This class exposes all attributes - but not the methods"""
	_exposed_ = ('__getattribute__', '__setattr__', '__delattr__')



CustomManager.register(RunQueueItem.__name__, RunQueueItem, CustomProxy) #Register the class so that it can be shared
	#  between processes NOTE: making changes in the config itself will not be propagated - only if the whole object is 
	# replaced (https://docs.python.org/3/library/multiprocessing.html#multiprocessing-proxy-objects) 


class CommandlineQueueEmitter(QtCore.QObject):
	"""
	A class that keeps track of a command-line-queue and emits a signal each time an item is added to the queue.
	Enables the use of multiple threads, while still logging to the UI without polling files. 
	"""
	commandLineOutput = QtCore.Signal(int, str, str, datetime, int, str) #id, name, output_path, dt, filepos, new_msg
	
	def __init__(self, queue : typing.Union[queue.Queue, multiprocessing.Queue]) -> None:
		super().__init__()
		self._queue = queue
		self.stop_flag = False
	
	def run(self):
		while(not self.stop_flag): #Continuously wait for new items in the queue
			try:
				args = self._queue.get(block=True, timeout=0.5) #Timeout every 0.5 seconds to check if we should stop
				self.commandLineOutput.emit(*args)
			except queue.Empty: 
				pass



class RunQueue(QtCore.QObject):
	"""
	A class in which we can queue configurations to run tasks. The Configurations are ran in separate processes.

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

	def __init__(self, n_processes : int = 1, 
	      			log_location : str= "", 
					save_load_location : str = "", 
					save_interval : typing.Literal["AfterAction", "Manually"] = "Manually"
				) -> None:
		"""_summary_

		Args:
			n_processes (int, optional): How many processes to use for processing the queue. Defaults to 1.

			log_location (str, optional): Stdout/stderr of each subprocess is logged to a file for ease-of-access from 
				the main process/ui if no path is given, we try to find the temp-path (using tempfile.TemporaryFile()). 
				Defaults to None.

			save_location (str, optional): Where to save the queue to - depends on ``save_interval``. Defaults to None.

			save_interval (typing.Literal["AfterAction", "Manually"], optional): When to save the queue. Defaults to 
				"Manually". If AfterAction - will save the queue after each action (add, remove, move, etc.).
				If Manually - will only save the queue when the user manually saves it. AfterAction is only enabled
				if a save_location is given. #TODO: implement
		"""

		super().__init__()

		if save_interval != "Manually" or save_load_location != "":
			raise NotImplementedError("Only manual saving is implemented for now (no location/interval supported).")

		self._log_location = log_location
		if self._log_location is None or self._log_location == "" or not os.path.exists(self._log_location): #If no log location is given, use the tempdir (os-specific) 
			self._log_location = tempfile.gettempdir()
			#Create sub folder MLTaskScheduler in tempdir so we have everything in one place
			self._log_location = os.path.join(self._log_location, "MLTaskScheduler")
			if not os.path.exists(self._log_location):
				os.mkdir(self._log_location)
		log.debug(f"Runqueue log location: {self._log_location}")

		self._manager = CustomManager() #To share data between processes
		self._manager.start() #Start the manager

		# self._queue : queue.Queue = queue.Queue() 
		self._queue : typing.List[int] = self._manager.list() # type: ignore #Consists of a queue of id's which can be 
			# used to retrieve the configuration from the all_dict - can't be an actual queue because we want to be able 
			# to remove/move items in the queue
		self._queue_mutex = multiprocessing.Lock()

		self._all_dict : typing.Dict[int, RunQueueItem] = self._manager.dict() #type: ignore #Should consists of a list 
			# of dicts with keys (id, dt_added, Name, Config, done, dt_done, exit_code, stderr)
		self._all_dict_mutex = multiprocessing.Lock()

		self._autoprocessing_enabled = False #Whether to automatically start processing items in the queue
		self._running_processes : typing.Dict[int, multiprocessing.Process] = {} #ID -> process
		self._running_processes_mutex = multiprocessing.Lock()

		self._n_processes = n_processes
		self._cur_id = 0 #Start at 0

		self._queue_processor_thread : threading.Thread | None = None #Thread that processes the queue
		self._queue_signal_updater_thread : threading.Thread | None = None #Thread that keeps the queue updated

		self._cmd_id_name_path_dict : typing.Dict[int, typing.Tuple[str, str]] = self._manager.dict() # type: ignore 
			# Dictionary that keeps track of the output file for each process
		self._cmd_id_name_path_dict_mutex = multiprocessing.Lock() #Lock for the cmd_id_path_dict
		#Queue that keeps track of outputs to the command line for each running process.
		self._command_line_output_queue = self._manager.Queue()



		self.queue_emitter = CommandlineQueueEmitter(self._command_line_output_queue)
		self.queue_emitter_thread = QtCore.QThread()
		self.queue_emitter.moveToThread(self.queue_emitter_thread)
		self.queue_emitter_thread.started.connect(self.queue_emitter.run)
		self.queue_emitter_thread.start()
		self.queue_emitter.commandLineOutput.connect(self.newCommandLineOutput.emit)
		# self.queue_emitter.commandLineOutput.connect(lambda *args: print(f"Got command line output: {args}"))



	def get_command_line_output(self, id : int, fseek_end : int, max_bytes : int) -> typing.Tuple[str, datetime]:
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
			if id not in self._cmd_id_name_path_dict or not os.path.exists(self._cmd_id_name_path_dict[id][1]):
				return ("", last_edit_dt)

			last_edit_dt = datetime.fromtimestamp(os.path.getmtime(self._cmd_id_name_path_dict[id][1]))
			filepath = self._cmd_id_name_path_dict[id][1]
		
		with open(filepath, "r") as f:
			if fseek_end == -1 and max_bytes == -1: #If just reading the whole file
				return f.read(), last_edit_dt
			elif fseek_end == -1: #If reading from the end of the file
				f.seek(0, max(0, os.SEEK_END - max_bytes))	
			if max_bytes == -1:
				return f.read(), last_edit_dt

			return f.read(max_bytes), last_edit_dt

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
			raise Exception(f"Could not load queue from path {path}, path does not exist.")
	
		with open(path, "rb") as f:
			loaded_all_dict, loaded_queue, loaded_cur_id = pickle.load(f)
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
		with open(path, "wb") as f:
			with self._all_dict_mutex, self._queue_mutex: #Make sure queue and all_dict are consistent with one another
				all_dict_copy = self.get_run_list_snapshot_copy_nolocks()
				queue_copy = self._get_queue_snapshot_copy_no_locks()

			for key, runqueue_item in all_dict_copy.items():
				if runqueue_item.status == RunQueueItemStatus.Running:
					if save_running_as_stopped:
						runqueue_item.status = RunQueueItemStatus.Stopped
						runqueue_item.stderr = "Process was running when queue was saved, so it was saved as cancelled."
						runqueue_item.dt_done = datetime.now()
					else:
						raise Exception(f"Could not save queue to file {path}, item with ID {key} is still running and\
		      						save mode does not allow for saving running items as cancelled.")


			pickle.dump((all_dict_copy, queue_copy, self._cur_id), f) #Save a tuple of the queue and all_dict



	def get_actions_for_id(self, id : int | None) -> typing.List[QueueItemActions]:
		"""
		Get a list of actions that can be performed on the item with id

		Args:
			id (int): the id of the item to get the actions for
		"""
		actions = []
		if id is None:
			return actions
		if id in self._queue:
			actions = [
				QueueItemActions.Delete,
				QueueItemActions.Cancel, #Remove from queue (="cancel")
				QueueItemActions.MoveUp,
				QueueItemActions.MoveDown,
				QueueItemActions.MoveTop
			]
		elif id in self._all_dict:
			#Lock queue when removing
			with self._all_dict_mutex, self._queue_mutex:
				if self._all_dict[id].status == RunQueueItemStatus.Stopped \
						or self._all_dict[id].status == RunQueueItemStatus.Finished \
						or self._all_dict[id].status == RunQueueItemStatus.Cancelled:
					actions = [
						QueueItemActions.Delete #TODO: Add requeue
					]
				elif self._all_dict[id].status == RunQueueItemStatus.Failed:
					actions = [
						QueueItemActions.Delete #TODO: Add retry
					]
				elif self._all_dict[id].status == RunQueueItemStatus.Running:
					actions = [
						QueueItemActions.Stop
					]
				elif self._all_dict[id].status == RunQueueItemStatus.Queued: #When popping from the queue, just before 
						#settings the status to "running", the status is "queued" without it being in the queue 
						# do we need to handle this case?
					actions = [
						QueueItemActions.Stop
					]

				else:
					raise Exception(f"Could not get actions for item with ID {id} due to unknown status: \
		     				{self._all_dict[id].status.__str__()}"
		     			)
		

		return actions
	
	def is_autoprocessing_enabled(self):
		return self._autoprocessing_enabled

	def do_action_for_id(self, id : int, action : QueueItemActions):
		"""
		Do an action for a given id
		
		Args:
			id (int): the id of the item to do the action for
			action (QueueItemActions): the action to perform on the item
		"""
		if action == QueueItemActions.Delete:
			self.delete_id(id)
		elif action == QueueItemActions.Stop:
			self.stop_id(id)
		elif action == QueueItemActions.Cancel:
			self.cancel_id(id)
		elif action == QueueItemActions.MoveUp:
			self.rel_move_in_queue(id, -1)
		elif action == QueueItemActions.MoveDown:
			self.rel_move_in_queue(id, 1)
		elif action == QueueItemActions.MoveTop:
			self._move_id_in_queue(id, 0)
		else:
			raise NotImplementedError(f"Unknown action: {action.__str__()}")

	def cancel_id(self, id):
		"""
		Cancel by id -> Remove a configuration from the queue (by id), but don't delete it

		Args:
			id (int): the id of the item to cancel
		"""
		#Lock queue when removing
		with self._all_dict_mutex, self._queue_mutex:
			if id not in self._queue: #Only do something if the id is in the queue
				raise Exception(f"Could not cancel {id}, ID not in queue.")
			self._all_dict[id].status = RunQueueItemStatus.Cancelled
			self._queue.remove(id)
			queue_snapshot = self._get_queue_snapshot_copy_no_locks()
			item_copy = deepcopy(self._all_dict[id])

		self.queueChanged.emit(queue_snapshot)
		self.runItemChanged.emit(id, item_copy)
		return
		
	

	def stop_id(self, id : int):
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
		if id in self._queue:
			self._queue.remove(id)
			self._all_dict[id].status = RunQueueItemStatus.Cancelled
			queue_snapshot = self._get_queue_snapshot_copy_no_locks()
			item_copy = self._all_dict[id].get_copy()
			self._all_dict_mutex.release()
			self._queue_mutex.release()
			self.queueChanged.emit(queue_snapshot)
			self.runItemChanged.emit(id, item_copy)
			return
		elif id in self._all_dict: #When raising an exception, we need to release the locks
			self._all_dict_mutex.release()
			self._queue_mutex.release()
			if self._all_dict[id].status == RunQueueItemStatus.Running:
				raise NotImplementedError("Stopping a running process is not implemented yet.")
			raise Exception(f"Could not stop {id}, item with ID is not running, and item with this ID was not in queue,\
		   			this should not be possible.")
			
	

	def _move_id_in_queue(self, id : int, new_queue_pos : int, use_locks=True):
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

		if id in self._queue:
			self._queue.remove(id)
			self._queue.insert(new_queue_pos, id)
		else: #Throw exception
			if use_locks:
				self._all_dict_mutex.release()
				self._queue_mutex.release()
			raise Exception(f"Could not move item with id {id}, ID not in queue.")
		
		self.queueChanged.emit(self._get_queue_snapshot_copy_no_locks())
		if use_locks:
			self._all_dict_mutex.release()
			self._queue_mutex.release()

	

	def rel_move_in_queue(self, id : int, rel_move : int):
		"""Relative move in the queue, -1 = move up, 1 = move down. 0 is the top of the queue.

		Args:
			id (int): the id of the item to move
			rel_move (int): the mount to move the item. Negative values move the item up in the queue, positive values
			  move it down
		"""
		with self._all_dict_mutex, self._queue_mutex:
			if id in self._queue:
				cur_pos = self._queue.index(id)
				new_pos = min(len(self._queue), max(0, cur_pos + rel_move))
				self._move_id_in_queue(id, new_pos, use_locks=False) #We already acquired the locks 
			else:
				self._all_dict_mutex.release()
				self._queue_mutex.release()
				raise KeyError(f"Could not move item with id {id}, ID not in queue.")
			
			



	def delete_id(self, id : int):
		"""
		Remove a configuration from the queue and list
		args:
			id (int): the id of the item to remove
		"""
		#Lock queue when removing
		with self._all_dict_mutex, self._queue_mutex:
			if self._all_dict[id].status == RunQueueItemStatus.Running:
				self._all_dict_mutex.release()
				self._queue_mutex.release()
				raise NotImplementedError(f"Could not delete item with id {id}, item is running.") #TODO: Add force del?

			if id in self._queue:
				self._queue.remove(id)
				
			#Also remove from all_dict -> the two should be in sync
			del self._all_dict[id]

			run_list_snapshot = self.get_run_list_snapshot_copy_nolocks()
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
	
	
	def get_run_list_snapshot_copy_nolocks(self) -> typing.Dict[int, RunQueueItem]:
		ret_dict = {} 
		for key, value in self._all_dict.items(): #Since this is a nested proxy-object, call get_copy on each item 
			ret_dict[key] = value.get_copy()
		return ret_dict

	def get_run_list_snapshot_copy(self) -> typing.Dict[int, RunQueueItem]:
		"""
		Get a snapshot of the all_list
		"""
		with self._all_dict_mutex:
			snapshot = self.get_run_list_snapshot_copy_nolocks()
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


	def add_to_queue(self, name, config):
		"""
		Add a configuration to the queue
		"""
		log.debug(f"Adding config with name {name} to queue.")
		id = self._cur_id
		self._cur_id += 1
		dt_added = datetime.now()
		new_item = self._manager.RunQueueItem(id=id,name=name, dt_added=dt_added, config=config) #type: ignore

		with self._all_dict_mutex, self._queue_mutex:
			self._queue.append(id)
			self._all_dict[id] = new_item
			snapshot = self.get_run_list_snapshot_copy_nolocks()
			queue_snapshot = self._get_queue_snapshot_copy_no_locks()

		self.runListChanged.emit(snapshot) #Emit outside of lock
		self.queueChanged.emit(queue_snapshot) #Emit outside of lock
			
		log.debug("Done adding config to queue.")

	def _run_queue(self):
		"""
		Run the queue (the producer), removes items from the queue and puts them in the currently-processing-queue 
		(at which point the consumer will pick them up, and editing will no longer be possible)
		"""
		self._stopflag = multiprocessing.Event()
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
				queue_item_id : int,
				queue_item_name : str,
				command_line_output_path : str, 
				command_line_output_queue : multiprocessing.Queue,
				all_dict : typing.Dict[int, RunQueueItem], 
				id_queue : typing.List[int], 
				all_dict_mutex : threading.Lock, 
				queue_mutex : threading.Lock
			): #TODO: add log_changed queue
		"""
		Process a single queue item
		"""
		print(f"Now processing queue item {queue_item_id}")
		
		#Output stdou/stderr to file
		# file = open(std_path, "a", buffering=1)

		# TODO: might be more neat to log using the logging module instead - but 
		root = logging.getLogger()
		root.setLevel(logging.DEBUG)
		handler = FileAndQueueHandler(
				item_id=queue_item_id,
				item_name=queue_item_name,
				queue=command_line_output_queue, 
				filename=command_line_output_path,
				mode="a"
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
			options_data = copy(queue_item.config) #Just to be sure we don't change the original config, make a copy
			
			config = Options()
			config.set_option_data(options_data) #type: ignore #NOTE: Although Options allow for a lot of types - 
			#in the runqueue, we should always expect a 'OptionsData' type

			import MachineLearning.framework.learner as learner
			#Reload the main module to make sure we have the latest version
			import importlib
			importlib.reload(learner)
			experiment_runner = learner.experimentRunner(config)
			experiment_runner.run_experiment()

		except Exception as e:
			msg = f"{type(e).__name__}:{e}"
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


		log.info(f"Processed item with id {queue_item.id} and name {queue_item.name} , queue is now {id_queue}, \
	   		all_dict is of size {len(all_dict)}")




	def _run_queue_item_processor(self):
		"""
		To be ran in a separate thread. 
		1. Continuously checks the queue for items to process, then calls the _run_queue_item function to process the item
			If there is process-space (n_processes), it will start a new process to process the item
			Checks the processes for completion and updates the queue accordingly
			
		2. Continuously checks the processes for completion and updates the queue accordingly
		"""
		print("Now running queue item processor")
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
					while(os.path.exists(f"{cur_logfile_loc}{extra_string}.out")): #If file exists, add number 
						#to the end NOTE: otherwise, if a run fails and is restarted, the old log will be overwritten
						extra_string = f"_{number}"
						number += 1
					cur_logfile_loc = f"{cur_logfile_loc}{extra_string}.out"
					#Create file NOTE: we need to create the file before emitting the signal, otherwise we can't start
					#  "watching" the file
					open(cur_logfile_loc, "w").close()
					log.debug(f"Will log to file: {cur_logfile_loc}")
					with self._cmd_id_name_path_dict_mutex:
						self._cmd_id_name_path_dict[queue_item_id] = (queue_item_name, cur_logfile_loc)

					self.newRunConsoleOutputPath.emit(queue_item_id, queue_item_name, cur_logfile_loc)
					assert(queue_item_id not in self._running_processes), "Queue item id already in running processes"
					with self._running_processes_mutex:
						self._running_processes[queue_item_id] = multiprocessing.Process(
								target=RunQueue._process_queue_item, 
								args = (
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
					print(f"Started processing item with id {queue_item_id} and name {queue_item_name}, \
	   						queue is now {self._queue}, all_dict is of size {len(self._all_dict)}")
				else: #TODO: maybe instead pass a "done-queue" to process_queue_item and have it put itself inside
					updated = False
					with self._running_processes_mutex:
						id_list = list(self._running_processes.keys())
						for id in id_list:
							if not self._running_processes[id].is_alive() \
									and self._running_processes[id].exitcode is not None: #If the process is finished
								self._running_processes[id].join()
								del self._running_processes[id]
								updated = True
						running_ids = list(self._running_processes.keys())

					if not updated: #If we achieved nothing, sleep for a bit
						time.sleep(0.4)
					else:
						self.currentlyRunningIdsChanged.emit(running_ids)

			except queue.Empty:
				pass




if __name__ == "__main__":
	from PySide6 import QtWidgets, QtCore, QtGui
	import sys
	import dill
	app = QtWidgets.QApplication(sys.argv)
	thequeue = RunQueue()
	print("Created a queue")
	app.exec()