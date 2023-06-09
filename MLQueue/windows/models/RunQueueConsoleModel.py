
from typing import Optional, Union
from PySide6 import QtWidgets, QtCore, QtGui
import PySide6.QtCore
import PySide6.QtWidgets
from MLQueue.classes.RunQueue import RunQueue
from PySide6Widgets.Widgets.ConsoleWidget import BaseConsoleItem
from dataclasses import dataclass, field
import datetime
import threading
import typing
import logging
from collections import OrderedDict
import time
import copy
log = logging.getLogger(__name__)

class RunQueueConsoleItem(BaseConsoleItem):
	
	currentTextChanged = QtCore.Signal(str) #Emitted when the text in the file changes
	dataChanged = QtCore.Signal() #When the metadata of the item changes (e.g. last-edit-date, name, runState not txt)
	textGapChanged = QtCore.Signal(object) #Emitted when the gap in the text changes

	def __init__(self, id :int, name : str, path : str | None = None, active_state : bool = True, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._edit_mutex = threading.Lock() #When adding from/to the buffer, lock this mutex
		self._current_text : str = ""
		self._name : str = name
		self._last_edited : datetime.datetime | None = None
		self._id : int = id
		self._path : str | None = path
		# max_buffer : int = 100_000
		self._current_gap : list[int] = [0, 0] #We allow for 1 gap in the text

		self._filled_filepositions : list[tuple[int,int]]= [(0,0)] #A list of tuples (min, max) of filled filepositions
		 #If this is length 1, that means we have processed all data up to filled_filepositions[0][1] without gaps
		 # E.g. [(0, 100), (200, 300)] means we have 'processed' all chars from 0->99 and 200->299, but not 100->199

		self.runqueue_console_connection = None

		self._active_state = active_state #By default - assume that the item is running

		self._console_icon = QtGui.QIcon()
		self._console_icon.addFile(u":/Icons/icons/Console.png", 
	       QtCore.QSize(), 
		   QtGui.QIcon.Mode.Normal, 
		   QtGui.QIcon.State.Off)

		self._done_console_icon = QtGui.QIcon()
		self._done_console_icon.addFile(u":/Icons/icons/Console checked.png", 
	       QtCore.QSize(), 
		   QtGui.QIcon.Mode.Normal, 
		   QtGui.QIcon.State.Off)
	



	# def set_runqueue(self, run_queue : RunQueue):
	# 	self._run_queue = run_queue
	# 	if self.runqueue_console_connection is not None:
	# 		self.runqueue_console_connection.disconnect()
	# 	# self.reset()
	# 	#TODO: centralize the commandLineOutput into the ConsoleItemModel
	# 	self.runqueue_console_connection = self._run_queue.newCommandLineOutput.connect(self.on_commandline_output)



		# self.on_commandline_output(self._id, self._name, self._path, dt, 0, text)

	def on_commandline_output(self, 
			   					id : int,
								name : str,
								output_path : str,
								edit_dt : datetime.datetime,
								filepos : int,
								msg : str
							): #id, name, output_path, dt, filepos, new_msg
	
		if id != self._id: #Skip if not the correct id
			return
		if name != self._name:
			raise ValueError(f"Name mismatch: {name} != {self._name} but id is the same - should not happen")
		
		dataChanged = False #Whether the node-data itself changed (e.g. name (namechange not implemented) or edit_dt

		with self._edit_mutex:
			if self._last_edited is None or self._last_edited < edit_dt:
				self._last_edited = edit_dt
				dataChanged = True

			textgap_changed = False

			cur_filepositions = copy.copy(self._filled_filepositions)

			#========== Insert new filled filepositions based on new msg ===========
			for i, (cur_min, cur_max) in enumerate(cur_filepositions):
				if filepos >= cur_min and filepos <= cur_max: #If filling from this interval
					if filepos + len(msg) <= cur_max: #If already filled this part
						break
					else: 
						self._filled_filepositions[i] = (cur_min, filepos + len(msg))
						textgap_changed = True
						break
				elif i+1 < len(cur_filepositions): #If the next item is not the last item
					if filepos >= cur_max and filepos + len(msg) <= cur_filepositions[i+1][0]: #If filling in between 2
						self._filled_filepositions.insert(i+1, (filepos, filepos + len(msg)))
						textgap_changed = True
						break
				else: #If the last item, and filepos > max (already checked above)
					self._filled_filepositions.append((filepos, filepos + len(msg)))
					textgap_changed = True

			new_filled = []
			#===== Iterate over all filled filepositions and merge overlapping ones=======
			if textgap_changed: 
				i = 0
				while(i < len(self._filled_filepositions)-1):
					if self._filled_filepositions[i][1] >= self._filled_filepositions[i+1][0]:
						# new_filled.append((cur_filepositions[i][0], cur_filepositions[i+1][1]))
						self._filled_filepositions[i] = (
							cur_filepositions[i][0], max(cur_filepositions[i+1][1], cur_filepositions[i][1]))
						del self._filled_filepositions[i+1]
						continue
					i+=1
			if textgap_changed:
				self.textGapChanged.emit(self._filled_filepositions)
				print(f"New gap: {self._filled_filepositions}")

			#=========== Insert actual text into the buffer ===========
			#TODO: make use of a ringbuffer of user-specified size
			new_text = self._current_text[:filepos] if len(self._current_text) > filepos else \
				self._current_text + ("X" * (filepos - len(self._current_text)))
			new_text += msg
			self._current_text = new_text +(self._current_text[filepos + len(msg):] \
				if len(self._current_text) > filepos else "")
			

		self.currentTextChanged.emit(self._current_text)
		if dataChanged: #If the metadata changed, emit the dataChanged signal
			self.dataChanged.emit()
			# if filepos + len(msg) > len(self._current_text):

	def getCurrentText(self) -> str:
		return self._current_text #TODO: copy? 

	def data(self, role : QtCore.Qt.ItemDataRole, column : int = 0):
		if role == QtCore.Qt.ItemDataRole.DisplayRole:
			if column == 0 : return f"{self._id}: {self._name}"
			elif column == 1 : return \
				self._last_edited.strftime("%Y-%m-%d %H:%M:%S") if self._last_edited is not None else ""
			elif column == 2 : return self._path
			else:
				raise ValueError(f"Invalid column for ConsoleStandardItem (max=2 but is {column})")
		elif role == QtCore.Qt.ItemDataRole.EditRole:
			if column == 0 : return f"{self._id}: {self._name}"
			elif column == 1 : return self._last_edited
			elif column == 2 : return self._path
			else:
				raise ValueError(f"Invalid column for ConsoleStandardItem (max=2 but is {column})")
		# elif role == QtCore.Qt.ItemDataRole.DecorationRole:
		# 	return self._id
		elif role == QtCore.Qt.ItemDataRole.DecorationRole and column == 0: #if first column -> return active/inactive icon
			return self._console_icon if self._active_state else self._done_console_icon
		else:
			return None


class RunQueueConsoleModel(QtCore.QAbstractItemModel):
	def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
		super().__init__(parent)
		self._run_queue = None
		self._id_item_map_mutex = threading.Lock()
		self._id_item_map : typing.OrderedDict[int, RunQueueConsoleItem] = OrderedDict({}) #Maps run queue id to item
			# Note: we use an ordered dict to keep a consistent item-order for the UI
		self._ignored_ids : typing.Set[int] = set() #Ids that are ignored/not tracked


		self._new_cmd_text_signal : QtCore.SignalInstance | None= None
		self._active_ids_signal : QtCore.SignalInstance | None = None
		self._queue_reset_signal : QtCore.SignalInstance | None = None

	def setRunQueue(self, run_queue : RunQueue):
		self._run_queue = run_queue
		if self._new_cmd_text_signal is not None:
			self._new_cmd_text_signal.disconnect()
		if self._active_ids_signal is not None:
			self._active_ids_signal.disconnect()
		if self._queue_reset_signal is not None:
			self._queue_reset_signal.disconnect()
		
		self._active_ids_signal = self._run_queue.currentlyRunningIdsChanged.connect(self.runningIdsChanged)
		self._new_cmd_text_signal = self._run_queue.newCommandLineOutput.connect(self.newCommandLineOutput)
		self._queue_reset_signal = self._run_queue.queueResetTriggered.connect(self.reset) #Upon queue reset -> 
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
				for id, (name, path, file_size, running) in cur_queue.items():
					if id in self._ignored_ids:
						continue
					item = RunQueueConsoleItem(id, name, path, running)
					self.appendRow(item)

					all_txt, last_edit_dt = self._run_queue.get_command_line_output(id, -1, file_size)
					item.on_commandline_output( #Append all text to the item
						id=id,
						name=name,
						output_path=path,
						edit_dt=last_edit_dt,
						filepos=0,
						msg=all_txt
					) #TODO: maybe only import active items?



		self.endResetModel()
		log.info("Done resetting RunQueueConsoleModel")


	def get_ignored_ids(self) -> typing.List[int]:
		return list(self._ignored_ids)

	def newCommandLineOutput(self, id : int,
							 name : str,
							 path : str,
							 edit_dt : datetime.datetime,
							 filepos : int,
							 msg : str):
		"""Called when new command line output is received"""
		if id in self._ignored_ids:
			return
		if id not in self._id_item_map:
			item = RunQueueConsoleItem(id, name, path)
			self.appendRow(item)

		self._id_item_map[id].on_commandline_output(id, name, path, edit_dt, filepos, msg)

	def runningIdsChanged(self, runnings_ids : typing.List[int]):
		"""Called when the running ids changed, updates the console-items to reflect the active/inactive state"""
		# for id in ids:
		with self._id_item_map_mutex:
			for id in self._id_item_map:
				self._id_item_map[id]._active_state = id in runnings_ids


	def columnCount(self, parent : QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
		return 3
	
	def rowCount(self, parent : QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
		return len(self._id_item_map)
	
	def un_ignore_id(self, id : int):
		log.debug(f"Un-ignoring id {id}")
		with self._id_item_map_mutex:
			if id not in self._ignored_ids:
				return #Already un-ignored
			self._ignored_ids.remove(id)
		
		if self._run_queue is not None:
			cur_queue = self._run_queue.get_command_line_info_list()
			if id in cur_queue:
				name, path, file_size, currently_running = cur_queue[id]
				item = RunQueueConsoleItem(id, name, path, currently_running)
				self.appendRow(item)
				self.dataChanged.emit(self.index(0,0), self.index(self.rowCount()-1, self.columnCount()-1))

				#TODO: instead of re-requesting all data, only request the missing data - don't delete upon ignore,
				#instead, simply don't show/update the item in the model
				all_txt, last_edit_dt = self._run_queue.get_command_line_output(id, -1, file_size)
				item.on_commandline_output( #Append all text to the item
					id=id,
					name=name,
					output_path=path,
					edit_dt=last_edit_dt,
					filepos=0,
					msg=all_txt
				) #TODO: maybe only import active items?
	
		# item = RunQueueConsoleItem()

	def request_data(self, id : int, end_fseek : int, read_bytes : int):
		with self._id_item_map_mutex:
			if id not in self._id_item_map:
				log.warning(f"Could not request data for item with id {id} as it is not monitored in the model")
				return

		item = self._id_item_map[id]
		if self._run_queue is not None:
			self._run_queue.get_command_line_output(id, end_fseek, read_bytes)	
		

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

	def appendRow(self, item : RunQueueConsoleItem):
		"""Append a row to the model - consisting of a single ConsoleStandardItem
		Args:
			item (ConsoleStandardItem): The item to append (each row corresponds to 1 item)
		"""
		self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount()) #No parent, insert at end
		with self._id_item_map_mutex:
			assert(item._id not in self._id_item_map), "Item with this ID already in model"
			self._id_item_map[item._id] = item
			#TODO: only emit dataChanged for this item
		item.dataChanged.connect(
			# lambda *args: print(f"Data changed for item {item._id}")
			lambda id=item._id: self.dataChanged.emit(
				# self.index(0, 0),
				# self.index(self.rowCount()-1, self.columnCount()-1))
				self.index(list(self._id_item_map.keys()).index(id), 0), 
				self.index(list(self._id_item_map.keys()).index(id), self.columnCount()-1))
		)

		self.endInsertRows()

	def removeRow(self, row: int, parent : QtCore.QModelIndex) -> None:
		self.beginRemoveRows(parent, row, row)
		# self._item_list.pop(row)
		id = list(self._id_item_map.keys())[row]
		with self._id_item_map_mutex:
			del self._id_item_map[id]
			self._ignored_ids.add(id)

		ignored_list = ", ".join([str(i) for i in list(self._ignored_ids)])
		log.info(f"Removed row with id {id} - ignorelist: {ignored_list}")
		self.modelReset.emit() #Why is this needed?

	def parent(self, index : QtCore.QModelIndex) -> QtCore.QModelIndex:
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
	print("Now testing RunQueueConsoleModel")
	from PySide6Widgets.Widgets.ConsoleWidget import ConsoleWidget
	app = QtWidgets.QApplication([])
	model = RunQueueConsoleModel()
	
	widget = ConsoleWidget()
	# widget = QtWidgets.QTableView()
	widget.setModel(model)
	widget.show()
	model.appendRow(RunQueueConsoleItem(1, "test1"))
	# app.exec()
	model.newCommandLineOutput(
		id=2,
		name="test2",
		path="",
		edit_dt=datetime.datetime.now(),
		filepos=0,
		msg = "testmsg2"
	)
	samedt = datetime.datetime.now()
	model.newCommandLineOutput(
		id=3,
		name="test3",
		path="",
		edit_dt=samedt,
		filepos=0,
		msg = "testmsg3"
	)	
	model.newCommandLineOutput(
		id=4,
		name="test4",
		path="",
		edit_dt=samedt,
		filepos=0,
		msg = "testmsg4"
	)
	model._id_item_map[4]._active_state = False
	cur_text = "\n".join([f"This is a test {i}" for i in range(1, 11)]) + '\nThis should now continue...\n'


	def testfunc(model : RunQueueConsoleModel, start_pos):
		i = 10
		cur_pos = start_pos
		while(True):
			i+= 1
			new_msg = f"Currently logging {i}\n"
			model.newCommandLineOutput(
				id=1,
				name="test1",
				path="",
				edit_dt=datetime.datetime.now(),
				filepos=cur_pos,
				msg = new_msg
			)
			cur_pos += len(new_msg)
			if 1 in model._id_item_map:
				print(f"Filled text: {model._id_item_map[1]._filled_filepositions}")
			time.sleep(2)

	print("len curtext: ", len(cur_text))
	thread = threading.Thread(target=lambda: testfunc(model, len(cur_text)))
	thread.start()

	def func(model):
		time.sleep(4)
		model.newCommandLineOutput(
			id=1,
			name="test1",
			path="",
			edit_dt=datetime.datetime.now(),
			filepos=0,
			msg = cur_text
		)
	thread2 = threading.Thread(target=lambda: func(model))
	thread2.start()

	app.exec()



	