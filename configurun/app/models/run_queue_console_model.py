"""
Implements a RunQueue model that synchronizes with text-output from running items in the runqueue.
"""


import copy
import datetime
import logging
import threading
import time
import typing
from collections import OrderedDict

from PySide6 import QtCore, QtGui, QtWidgets
from pyside6_utils.models.console_widget_models.console_model import BaseConsoleItem
from configurun.classes.run_queue import RunQueue

log = logging.getLogger(__name__)



class MethodExecutionThread(QtCore.QThread):
	"""Very simple thread that runs a function in a separate thread and stores the return value"""
	def __init__(self, function, *args, **kwargs):
		super().__init__()
		self._function = function
		self._args = args
		self._kwargs = kwargs
		self._ret_val = None



	def run(self) -> typing.Any:
		try:
			self._ret_val = self._function(*self._args, **self._kwargs)
		except Exception as exception: #pylint: disable=broad-exception-caught
			print(f"Error when running function {self._function.__name__} in thread: {exception}")
		self.quit()


class RunQueueConsoleItem(BaseConsoleItem):
	"""
	Model that synchronizes with text-output from running items in the runqueue.
	"""
	currentTextChanged = QtCore.Signal(str, int) #Emitted when the text in the file changes, int=filepos (start-index)
	dataChanged = QtCore.Signal() #When the metadata of the item changes (e.g. last-edit-date, name, runState not txt)
	filledTextPositionsChanged = QtCore.Signal(object) #Emitted when the receieved text is filled in the buffer

	def __init__(self,
	    	item_id :int,
			name : str,
			path : str | None = None,
			active_state : bool = True,
			max_buffer_emit_size : int = 10_000 #How many character to emit (at max) when the buffer changes. Should be 
				#> the largest amount of characters that can be added in a single commandline-output signal
				#Note that we can temporarily turn this off when calling on_commandline_output (e.g. when resetting)
			):
		super().__init__()
		self._edit_mutex = threading.Lock() #When adding from/to the buffer, lock this mutex
		self._current_text : str = ""
		self._name : str = name
		self._last_edited : datetime.datetime | None = None
		self._id : int = item_id
		self._path : str | None = path
		# max_buffer : int = 100_000
		self._current_gap : list[int] = [0, 0] #We allow for 1 gap in the text
		self._max_buffer_emit_size = max_buffer_emit_size

		self._filled_filepositions : list[tuple[int,int]]= [(0,0)] #A list of tuples (min, max) of filled filepositions
		 #If this is length 1, that means we have processed all data up to filled_filepositions[0][1] without gaps
		 # E.g. [(0, 100), (200, 300)] means we have 'processed' all chars from 0->99 and 200->299, but not 100->199

		self.runqueue_console_connection = None

		self._active_state = active_state #By default - assume that the item is running

		self._console_icon = QtGui.QIcon()
		self._console_icon.addFile(":/Icons/icons/actions/Console.png",
	       QtCore.QSize(),
		   QtGui.QIcon.Mode.Normal,
		   QtGui.QIcon.State.Off)

		self._done_console_icon = QtGui.QIcon()
		self._done_console_icon.addFile(":/Icons/icons/actions/Console checked.png",
	       QtCore.QSize(),
		   QtGui.QIcon.Mode.Normal,
		   QtGui.QIcon.State.Off)
		
		self._threadlist_mutex = threading.Lock()
		self._threads = []
	

	def get_id(self) -> int:
		"""Returns the id of this item - id is set at creation and should be unique for each item"""
		return self._id

	def set_active_state(self, new_active_state : bool):
		"""Sets the active state of the item (e.g. whether it is running or not)

		Args:
			new_active_state (bool): The new state
		"""
		self._active_state = new_active_state
		self.dataChanged.emit()

	def get_active_state(self) -> bool:
		"""Returns the active state of the item (e.g. whether it is running or not)

		Returns:
			bool: The active state of the item
		"""
		return self._active_state

	# def set_runqueue(self, run_queue : RunQueue):
	# 	self._run_queue = run_queue
	# 	if self.runqueue_console_connection is not None:
	# 		self.runqueue_console_connection.disconnect()
	# 	# self.reset()
	# 	#TODO: centralize the commandLineOutput into the ConsoleItemModel
	# 	self.runqueue_console_connection = self._run_queue.newCommandLineOutput.connect(self.on_commandline_output)



		# self.on_commandline_output(self._id, self._name, self._path, dt, 0, text)

	def on_commandline_output(self,
			   					item_id : int,
								name : str,
								output_path : str,
								edit_dt : datetime.datetime,
								filepos : int,
								msg : str,
								emit_datachanged : bool = True,
								respect_max_buffer_emit_size : bool = True
							): # pylint: disable=unused-argument
		"""Called when new command line output is received, inserts the new text into the buffer and emits 
		the currentTextChanged signal if the buffer changed
		
		Args:
			item_id (int): The id of the item for which the output is received
			output_path (str): The path of the item
			name (str): The name of the item
			edit_dt (datetime.datetime): The last (known) change to the output file
			filepos (int): The start-position where the new text should be inserted
			msg (str): The new text message
			emit_datachanged (bool, optional): Whether to emit the dataChanged signal if metadata changed. 
				Defaults to True. Set to false when using this function when resetting a model that uses this item
				to avoid emitting the dataChanged signal before the data of the model is fully reset.

			respect_max_buffer_emit_size (bool, optional): Whether to respect the max_buffer_emit_size when emitting
				the currentTextChanged signal. Defaults to True. Set to false when using this function when resetting
				the contents of the buffer
		"""
		# self._process_commandline_output(item_id, name, output_path, edit_dt, filepos, msg, emit_datachanged)
		thread = MethodExecutionThread(
			self._process_commandline_output,
			# print,
			item_id,
			name,
			output_path,
			edit_dt,
			filepos,
			msg,
			emit_datachanged,
			respect_max_buffer_emit_size
		)
		#NOTE: we move thread to main thread to avoid issues with Qt signals
		thread.moveToThread(QtCore.QCoreApplication.instance().thread())
		thread.setParent(self)
		thread.start()
		thread.finished.connect(thread.deleteLater)



	def _process_commandline_output(
		self,
		item_id : int,
		name : str,
		output_path : str,
		edit_dt : datetime.datetime,
		filepos : int,
		msg : str,
		emit_datachanged : bool = True,
		respect_max_buffer_emit_size : bool = True
	):
		"""
		Actually processes the new command line output, inserts the new text into the buffer and emits a signal
		Since appending to a large string is quite expensive, 
		"""
		if item_id != self._id: #Skip if not the correct id
			return
		if name != self._name:
			raise ValueError(f"Name mismatch: {name} != {self._name} but id is the same - should not happen")

		data_changed = False #Whether the node-data itself changed (e.g. name (namechange not implemented) or edit_dt

		with self._edit_mutex:
			if self._last_edited is None or self._last_edited < edit_dt:
				self._last_edited = edit_dt
				data_changed = True

			filled_text_positions_changed = False

			cur_filepositions = copy.copy(self._filled_filepositions)

			#========== Insert new filled filepositions based on new msg ===========
			for i, (cur_min, cur_max) in enumerate(cur_filepositions):
				if filepos >= cur_min and filepos <= cur_max: #If filling from this interval
					if filepos + len(msg) <= cur_max: #If already filled this part
						break
					else:
						self._filled_filepositions[i] = (cur_min, filepos + len(msg))
						filled_text_positions_changed = True
						break
				elif i+1 < len(cur_filepositions): #If the next item is not the last item
					if filepos >= cur_max and filepos + len(msg) <= cur_filepositions[i+1][0]: #If filling in between 2
						self._filled_filepositions.insert(i+1, (filepos, filepos + len(msg)))
						filled_text_positions_changed = True
						break
				else: #If the last item, and filepos > max (already checked above)
					self._filled_filepositions.append((filepos, filepos + len(msg)))
					filled_text_positions_changed = True

			#===== Iterate over all filled filepositions and merge overlapping ones=======
			if filled_text_positions_changed:
				i = 0
				while i < (len(self._filled_filepositions)-1):
					if self._filled_filepositions[i][1] >= self._filled_filepositions[i+1][0]:
						# new_filled.append((cur_filepositions[i][0], cur_filepositions[i+1][1]))
						self._filled_filepositions[i] = (
							cur_filepositions[i][0], max(cur_filepositions[i+1][1], cur_filepositions[i][1]))
						del self._filled_filepositions[i+1]
						continue
					i+=1
			if filled_text_positions_changed:
				self.filledTextPositionsChanged.emit(self._filled_filepositions)
			#=========== Insert actual text into the buffer ===========
			#TODO: make use of a ringbuffer of user-specified size
			new_text = self._current_text[:filepos] if len(self._current_text) > filepos else \
				self._current_text + ("X" * (filepos - len(self._current_text)))
			new_text += msg
			self._current_text = new_text +(self._current_text[filepos + len(msg):] \
				if len(self._current_text) > filepos else "")

			print(f"Updating item...")
			from_index = 0
			if respect_max_buffer_emit_size and len(self._current_text) > self._max_buffer_emit_size:
				from_index = len(self._current_text) - self._max_buffer_emit_size

			self.currentTextChanged.emit(self._current_text[from_index:], from_index) #For now, the full buffer is always emitted

		if data_changed and emit_datachanged: #If the metadata changed, emit the dataChanged signal
			self.dataChanged.emit()
			# if filepos + len(msg) > len(self._current_text):

	def get_current_text(self) -> str:
		return self._current_text

	def data(self, role : QtCore.Qt.ItemDataRole, column : int = 0):
		if role == QtCore.Qt.ItemDataRole.DisplayRole:
			if column == 0 :
				return f"{self._id}: {self._name}"
			elif column == 1 :
				return self._last_edited.strftime("%Y-%m-%d %H:%M:%S") if self._last_edited is not None else ""
			elif column == 2 :
				return self._path
			else:
				raise ValueError(f"Invalid column for ConsoleStandardItem (max=2 but is {column})")
		elif role == QtCore.Qt.ItemDataRole.EditRole:
			if column == 0 :
				return f"{self._id}: {self._name}"
			elif column == 1 :
				return self._last_edited
			elif column == 2 :
				return self._path
			else:
				raise ValueError(f"Invalid column for ConsoleStandardItem (max=2 but is {column})")
		# elif role == QtCore.Qt.ItemDataRole.DecorationRole:
		# 	return self._id
		elif role == QtCore.Qt.ItemDataRole.DecorationRole and column == 0: #if first column -> return active/inactive icon
			return self._console_icon if self._active_state else self._done_console_icon
		else:
			return None


class RunQueueConsoleModel(QtCore.QAbstractItemModel):
	"""
	A RunQueue model that synchronizes with text-output from running items in the runqueue by requesting all text-data
	from the runqueue upon connection, and then subscribing to any changes to the text-output of the items
	running in the runqueue.

	On reset, will try to fetch the history of the consoles using the runqueue fetch methods.
	"""


	def __init__(self, 
	    		parent: QtWidgets.QWidget | None = None,
				max_initial_console_history : int = 200_000
			) -> None:
		"""Initializes the runqueueconsolemodel

		Args:
			parent (QtWidgets.QWidget | None, optional): The parent. Defaults to None.
			max_initial_console_history (int, optional): Limits the max amount of characters that the model will 
				fetch on-reset (per item) this makes sure that the initial load times on model-reset do not become 
				too outrageous by only loading part of the data. Especially useful useful when working over network 
				connections. NOTE: this limit is not enforced when gradually loading data from the runqueue as 
				we assume that it's not feasible to load too much text-data in a single session.
				Defaults to 200_000. #TODO: probably better to do this anyway as creating new strings for each 
				append can be very expensive if the string is very large.
				-1 for no limit. 
		"""

		super().__init__(parent)
		self._run_queue = None
		self._id_item_map_mutex = threading.Lock()
		self._id_item_map : typing.OrderedDict[int, RunQueueConsoleItem] = OrderedDict({}) #Maps run queue id to item
			# Note: we use an ordered dict to keep a consistent item-order for the UI
		self._ignored_ids : typing.Set[int] = set() #Ids that are ignored/not tracked

		self._max_initial_console_history = max_initial_console_history

		self._new_cmd_text_signal : QtCore.SignalInstance | None= None
		self._active_ids_signal : QtCore.SignalInstance | None = None
		self._queue_reset_signal : QtCore.SignalInstance | None = None

	def set_run_queue(self, run_queue : RunQueue):
		"""Set the runqueue to synchronize with

		Args:
			run_queue (RunQueue): The new runqueue to synchronize with
		"""
		self._run_queue = run_queue
		if self._new_cmd_text_signal is not None:
			self._new_cmd_text_signal.disconnect()
		if self._active_ids_signal is not None:
			self._active_ids_signal.disconnect()
		if self._queue_reset_signal is not None:
			self._queue_reset_signal.disconnect()

		self._active_ids_signal = self._run_queue.currentlyRunningIdsChanged.connect(self.running_ids_changed)
		self._new_cmd_text_signal = self._run_queue.newCommandLineOutput.connect(self.new_command_line_output)
		self._queue_reset_signal = self._run_queue.resetTriggered.connect(self.reset) #Upon queue reset ->
			# re-request all data from the runqueue

	def reset(self, reset_ignored_ids : bool = False):
		"""
		Re-request all data from runQueue and fill model
		#TODO: maybe create a soft-reset that only checks if there is any missing data e.g. when reconnecting to
		a disconnected runqueue - not all data is neccesarily invalid
		"""
		log.info("Resetting RunQueueConsoleModel - re-requesting all console-output from runQueue")
		self.beginResetModel()
		with self._id_item_map_mutex:
			self._id_item_map = OrderedDict({})
		if reset_ignored_ids:
			self._ignored_ids = set()

		if self._run_queue is not None:
			cur_queue = self._run_queue.get_command_line_info_list()
			if cur_queue:
				for cur_id, (name, path, file_size, running) in cur_queue.items():
					if cur_id in self._ignored_ids:
						continue
					item = RunQueueConsoleItem(cur_id, name, path, running)
					self._append_row(item)

					if self._max_initial_console_history > 0 and file_size > self._max_initial_console_history: #if limit to initial console history
						all_txt, last_edit_dt = self._run_queue.get_command_line_output(
							cur_id, -1, self._max_initial_console_history) #TODO: this probably goes wrong if we resume
							# logging on an existing logfile, as we will "start again" at filepos 0
							# while the actual filepos = file_size-self._max_initial_console_history.
							# probably best to put a start_pos inside run_queue_item 
					else: #Fetch all data NOTE: this can be very costly, especially over network connections
						all_txt, last_edit_dt = self._run_queue.get_command_line_output(cur_id, -1, file_size)
					item.on_commandline_output( #Append all text to the item #TODO: do this before reading file to avoid
							# missing any of the data that was added during reading
						item_id=cur_id,
						name=name,
						output_path=path,
						edit_dt=last_edit_dt,
						filepos=0,
						msg=all_txt,
						emit_datachanged=False #Don't emit changes, otherwise we will try to update items that are not
							# yet known to the model
					) #TODO: maybe only import active items?



		self.endResetModel()
		log.info("Done resetting RunQueueConsoleModel")


	def get_ignored_ids(self) -> typing.List[int]:
		"""
		Get the ids that are ignored/not tracked.
		Returns:
			list[int]: A list of ids that are ignored/not tracked
		"""
		return list(self._ignored_ids)

	def new_command_line_output(self,
			  				item_id : int,
							item_name : str,
							item_path : str,
							item_edit_dt : datetime.datetime,
							item_filepos : int,
							item_msg : str):
		"""alled when new command line output is received

		Args:
			item_id (int): The id of the item for which the output is received
			item_name (str): The name of the item
			item_path (str): The path of the item
			item_edit_dt (datetime.datetime): The last (known) change to the output file
			item_filepos (int): The start-position where the new text should be inserted
			item_msg (str): The new text message
		"""
		if item_id in self._ignored_ids:
			return
		if item_id not in self._id_item_map:
			item = RunQueueConsoleItem(item_id, item_name, item_path)
			self.append_row(item)

		#TODO: maybe process in non-main thread? Settext probably most intensive though...
		self._id_item_map[item_id].on_commandline_output(item_id, item_name, item_path, item_edit_dt, item_filepos, item_msg)

	def running_ids_changed(self, runnings_ids : typing.List[int]):
		"""Called when the running ids changed, updates the console-items to reflect the active/inactive state"""
		with self._id_item_map_mutex:
			for cur_id in self._id_item_map:
				self._id_item_map[cur_id].set_active_state(cur_id in runnings_ids)


	def columnCount(self, parent : QtCore.QModelIndex = QtCore.QModelIndex()) -> int: #pylint: disable=unused-argument
		return 3

	def rowCount(self, parent : QtCore.QModelIndex = QtCore.QModelIndex()) -> int: # pylint: disable=unused-argument
		return len(self._id_item_map)

	def un_ignore_id(self, item_id : int):
		"""Un-ignore the item with the passed id. Re-synchronizes text-data with the runqueue and re-adds the item
		to the model for the view to display
		TODO: We request the whole text file, but this might take a long while for very large files. Instead
		we should only request the missing data (e.g. the last 1000 chars) and append that to the current text
		Args:
			item_id (int): The item to un-ignore
		"""
		log.debug(f"Un-ignoring id {item_id}")
		with self._id_item_map_mutex:
			if item_id not in self._ignored_ids:
				return #Already un-ignored
			self._ignored_ids.remove(item_id)

		if self._run_queue is not None:
			cur_queue = self._run_queue.get_command_line_info_list()
			if item_id in cur_queue:
				name, path, file_size, currently_running = cur_queue[item_id]
				item = RunQueueConsoleItem(item_id, name, path, currently_running)
				self.append_row(item)
				self.dataChanged.emit(self.index(0,0), self.index(self.rowCount()-1, self.columnCount()-1))

				#TODO: instead of re-requesting all data, only request the missing data - don't delete upon ignore,
				#instead, simply don't show/update the item in the model
				all_txt, last_edit_dt = self._run_queue.get_command_line_output(item_id, -1, file_size)
				item.on_commandline_output( #Append all text to the item
					item_id=item_id,
					name=name,
					output_path=path,
					edit_dt=last_edit_dt,
					filepos=0,
					msg=all_txt
				) #TODO: maybe only import active items?

		# item = RunQueueConsoleItem()

	# def reset(self):
	# 	"""Re-request all data and refill model"""
	# 	self.beginResetModel()
	# 	self._id_item_map = {}
	# 	if self._run_queue is not None:
	# 		cur_queue = self._run_queue.get_command_line_info_list()

	# 		for id, (name, path, file_size) in cur_queue.items():
	# 			if id in self._ignored_ids:
	# 				continue
	# 			item = RunQueueConsoleItem(id, name, path)
	# 			with self._id_item_map_mutex:
	# 				self._id_item_map[id] = item
	# 			self.appendRow(item)
	# 	self.endResetModel()

	def _append_row(self, item : RunQueueConsoleItem):
		"""Append a row to the model - consisting of a single ConsoleStandardItem.
		NOTE: this is the same as appendRow, but without the begin/endInsertRows calls, better to be used during model
		reset to avoid emitting dataChanged/rowInserted signals for new items as this might cause issues when 
		begin/endresetModel is called during a reset
		
		Args:
			item (ConsoleStandardItem): The item to append (each row corresponds to 1 item)
		"""
		cur_item_id = item.get_id()
		with self._id_item_map_mutex:
			if cur_item_id in self._id_item_map:
				log.warning("Item with this ID already in model, duplicate ID? Skipping row-insertion.")
				return
			self._id_item_map[cur_item_id] = item
			#TODO: only emit dataChanged for this item
		item.dataChanged.connect(
			# lambda *args: print(f"Data changed for item {item._id}")
			lambda item_id=cur_item_id: self.dataChanged.emit(
				# self.index(0, 0),
				# self.index(self.rowCount()-1, self.columnCount()-1))
				self.index(list(self._id_item_map.keys()).index(item_id), 0),
				self.index(list(self._id_item_map.keys()).index(item_id), self.columnCount()-1))
		)



	def append_row(self, item : RunQueueConsoleItem):
		"""Append a row to the model - consisting of a single ConsoleStandardItem
		Args:
			item (ConsoleStandardItem): The item to append (each row corresponds to 1 item)
		"""
		self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount()) #No parent, insert at end
		self._append_row(item)
		self.endInsertRows()

	def removeRow(self, row: int, parent : QtCore.QModelIndex) -> None:
		self.beginRemoveRows(parent, row, row)
		item_id = list(self._id_item_map.keys())[row]
		with self._id_item_map_mutex:
			del self._id_item_map[item_id]
			self._ignored_ids.add(item_id)

		ignored_list = ", ".join([str(i) for i in list(self._ignored_ids)])
		log.info(f"Removed row with id {item_id} - ignorelist: {ignored_list}")
		self.modelReset.emit() #Why is this needed?

	def parent(self, index : QtCore.QModelIndex) -> QtCore.QModelIndex: #pylint: disable=unused-argument
		return QtCore.QModelIndex() #No parents

	def data(self, index : QtCore.QModelIndex, role : QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.DisplayRole):
		#Check if index is valid
		if not index.isValid(): #if index is not valid, return None
			return None

		#Get the item from the index
		item = index.internalPointer()
		assert(isinstance(item, RunQueueConsoleItem)), "Invalid item type in RunQueueConsoleModel"

		if role == QtCore.Qt.ItemDataRole.DisplayRole or role == QtCore.Qt.ItemDataRole.EditRole:
			# return item.data(index.column()) #Return the data (str) of the item
			return item.data(role=role, column=index.column())
		elif role == QtCore.Qt.ItemDataRole.ToolTipRole: #When hovering - also display the full name
			return item.data(role=QtCore.Qt.ItemDataRole.DisplayRole, column=index.column())
		elif role == QtCore.Qt.ItemDataRole.DecorationRole:
			return item.data(role=role, column=index.column())
		elif role == QtCore.Qt.ItemDataRole.UserRole + 1:
			return item
		else:
			return None
		# return super().data(index, role)

	def index(self, row : int, column : int, parent : QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
		"""Return the index of the item in the model specified by the given row, column and parent index.

		Args:
			row (int): The row of the item
			column (int): The column of the item
			parent (QtCore.QModelIndex, optional): The parent index. Defaults to QtCore.QModelIndex().

		Returns:
			QtCore.QModelIndex: The index of the item
		"""
		if not parent.isValid(): #If top-level item (should be all items actually)
			id_keys = list(self._id_item_map.keys())
			return self.createIndex(row, column, self._id_item_map[id_keys[row]])
		else: #If item -> no children
			return QtCore.QModelIndex()


if __name__ == "__main__":
	#pylint: disable=ungrouped-imports, protected-access, redefined-outer-name, missing-function-docstring, invalid-name
	from pyside6_utils.widgets.console_widget import ConsoleWidget
	app = QtWidgets.QApplication([])
	model = RunQueueConsoleModel()
	print("Now running a test-instance of RunQueueConsoleModel")

	widget = ConsoleWidget(ui_text_min_update_interval=0.05)
	# widget = QtWidgets.QTableView()
	widget.set_model(model)
	widget.show()
	model.append_row(RunQueueConsoleItem(1, "test1"))
	# app.exec()
	model.new_command_line_output(
		item_id=2,
		item_name="test2",
		item_path="",
		item_edit_dt=datetime.datetime.now(),
		item_filepos=0,
		item_msg = "testmsg2"
	)
	samedt = datetime.datetime.now()
	model.new_command_line_output(
		item_id=3,
		item_name="test3",
		item_path="",
		item_edit_dt=samedt,
		item_filepos=0,
		item_msg = "testmsg3"
	)
	model.new_command_line_output(
		item_id=4,
		item_name="test4",
		item_path="",
		item_edit_dt=samedt,
		item_filepos=0,
		item_msg = "testmsg4"
	)
	model._id_item_map[4]._active_state = False
	cur_text = "\n".join([f"This is a test {i}" for i in range(1, 1_000_000)]) + '\nThis should now continue...\n'


	def testfunc(model : RunQueueConsoleModel, start_pos):
		i = 10
		cur_pos = start_pos
		while True:
			i+= 1
			new_msg = f"Currently logging {i}\n\n"
			model.new_command_line_output(
				item_id=1,
				item_name="test1",
				item_path="",
				item_edit_dt=datetime.datetime.now(),
				item_filepos=cur_pos,
				item_msg = new_msg
			)
			cur_pos += len(new_msg)
			# if 1 in model._id_item_map:
			# 	print(f"Filled text: {model._id_item_map[1]._filled_filepositions}")
			# time.sleep(1)
			time.sleep(0.01)

	print("len curtext: ", len(cur_text))
	test_thread = threading.Thread(target=lambda: testfunc(model, len(cur_text)))
	test_thread.start()

	def func(model):
		time.sleep(4)
		model.new_command_line_output(
			item_id=1,
			item_name="test1",
			item_path="",
			item_edit_dt=datetime.datetime.now(),
			item_filepos=0,
			item_msg = cur_text
		)
	thread2 = threading.Thread(target=lambda: func(model))
	thread2.start()
	print("Now executing app")
	app.exec()
