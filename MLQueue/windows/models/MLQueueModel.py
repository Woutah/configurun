

from PySide6 import QtCore, QtGui, QtWidgets
import typing
# from MachineLearning.framework.RunQueue import RunQueue, RunQueueItem, RunQueueItemStatus, QueueItemActions
from MLQueue.classes.RunQueue import RunQueue, RunQueueItem, RunQueueItemStatus, QueueItemActions
# from MachineLearning.framework.RunQueueClient import RunQueueClient
from MLQueue.classes.RunQueueClient import RunQueueClient
import logging
log = logging.getLogger(__name__)


class MLQueueModel(QtCore.QAbstractTableModel):

	"""
	Class that resides between the RunQueue and the view (QTableView) and provides the data for the view in a convenient
	way. Since Runqueue can also interface over a network - this class can be used to somewhat buffer the data and
	increase responsiveness of the UI.
	"""
	# currentActionListChanged = QtCore.Signal(object) #Emits a list of actions (List[QueueItemActions]) that can be \
	#  performed on the current selection, can be used to enable/disable buttons
	
	#All processes' stdout/stderr will be redirected to a file, this signal will be emitted when a new file is created 
	# (and thus when a new process is started) #NOTE: for now, both in the same file
	newRunConsoleOutputPath = QtCore.Signal(int, str, str) #id, name, path 


	def set_run_queue(self, run_queue : RunQueue) -> None:
		"""Sets the runqueue of this model to the given run_queue. This will disconnect all signals from the previous
		run_queue and connect the signals from the new run_queue

		Args:
			run_queue (RunQueue): The new run_queue to use
			also_instantiate (bool, optional): Whether to request the current state of the run_queue and store it in
			this model. Defaults to True. If False, the model will only be updated upon the next change to the run_queue
			This is useful when the runqueue is an instance of RunQueueClient, since it will not have any data until
			an authenticated server is connected.
		"""
		self.beginResetModel() #Invalidate all data in current views
		if self. _run_queue_consoleoutput_signal_connection is not None:
			self._run_queue.newRunConsoleOutputPath.disconnect(self._run_queue_consoleoutput_signal_connection)

		self._run_queue = run_queue
		self._run_queue_consoleoutput_signal_connection = run_queue.newRunConsoleOutputPath.connect(
										self.newRunConsoleOutputPath.emit
									)
		#============= Signal connections linking UI to RunQueue =============
		if self._queue_changed_signal_connection is not None:
			self._run_queue.queueChanged.disconnect(self._queue_changed_signal_connection)
		if self._run_list_changed_signal_connection is not None:
			self._run_queue.runListChanged.disconnect(self._run_list_changed_signal_connection)
		if self._run_item_changed_signal_connection is not None:
			self._run_queue.runItemChanged.disconnect(self._run_item_changed_signal_connection)

		self._queue_changed_signal_connection = self._run_queue.queueChanged.connect(self._queue_changed)
		self._run_list_changed_signal_connection = self._run_queue.runListChanged.connect(self._run_list_changed)
		self._run_item_changed_signal_connection = self._run_queue.runItemChanged.connect(self._run_item_changed)
		self._queue_reset_signal_connection = self._run_queue.queueResetTriggered.connect(self.reset_model)

		self._cur_queue_copy = []
		self._cur_run_list_copy = {}

		# if also_instantiate:
		self._reset_model()
		self.endResetModel()

	def reset_model(self) -> None:
		"""Reset the model, this will emit the beginResetModel and endResetModel signals"""
		self.beginResetModel()
		self._reset_model()
		self.endResetModel()

	def _reset_model(self) -> None:
		"""Private variant of reset_model, does not emit the beginResetModel and endResetModel signals
		"""
		if self._run_queue is not None:
			self._cur_queue_copy = self._run_queue.get_queue_snapshot_copy() 
			self._cur_run_list_copy = self._run_queue.get_run_list_snapshot_copy()
			if self._cur_queue_copy is None:
				self._cur_queue_copy = []
			if self._cur_run_list_copy is None:
				self._cur_run_list_copy = {}


	def __init__(self, run_queue : RunQueue, parent: typing.Optional[QtCore.QObject] = None) -> None:
		super().__init__(parent)
			
		# self._cur_queue_copy = None
		# self._cur_run_list_copy = None
		# self._run_queue = run_queue
		# self._run_queue_consoleoutput_signal_connection = None
		# self._queue_changed_signal_connection = None
		# self._run_list_changed_signal_connection = None
		# self._run_item_changed_signal_connection = None
		self._run_queue_consoleoutput_signal_connection = None
		self._queue_changed_signal_connection = None
		self._run_list_changed_signal_connection = None
		self._run_item_changed_signal_connection = None
		self._queue_reset_signal_connection = self
		self.set_run_queue(run_queue)
		#=========== Moved to set_run_queue ===========
		# self._run_queue = run_queue
		# self._run_queue_consoleoutput_signal = self._run_queue.newRunConsoleOutputPath.connect(self.newRunConsoleOutputPath.emit)
		


		self._cur_actions = [] #The actions possible for the currently hightlighted item


		#======================= Some icons =======================
		self._selection_pixmap = QtWidgets.QStyle.SP_DialogApplyButton #Checkmark #type: ignore
		self._selection_icon = QtWidgets.QApplication.style().standardIcon(self._selection_pixmap)

		self._waiting_pixmap = QtWidgets.QStyle.SP_FileDialogDetailedView #Pause button #type: ignore
		self._waiting_icon = QtWidgets.QApplication.style().standardIcon(self._waiting_pixmap)

		self._running_pixmap = QtWidgets.QStyle.SP_MediaPlay #Play button #type: ignore
		self._running_icon = QtWidgets.QApplication.style().standardIcon(self._running_pixmap)

		self._finished_pixmap = QtWidgets.QStyle.SP_DialogApplyButton #Checkmark #type: ignore
		self._finished_icon = QtWidgets.QApplication.style().standardIcon(self._finished_pixmap)

		self._stopped_pixmap = QtWidgets.QStyle.SP_DialogCancelButton #X #type: ignore
		self._stopped_icon = QtWidgets.QApplication.style().standardIcon(self._stopped_pixmap)

		self._cancelled_pixmap = QtWidgets.QStyle.SP_DialogNoButton #red circle #type: ignore
		self._cancelled_icon = QtWidgets.QApplication.style().standardIcon(self._cancelled_pixmap)

		self._failed_pixmap = QtWidgets.QStyle.SP_BrowserStop #X #type: ignore
		self._failed_icon = QtWidgets.QApplication.style().standardIcon(self._failed_pixmap)


		self._icon_dict = {
			RunQueueItemStatus.Queued: self._waiting_icon,
			RunQueueItemStatus.Running: self._running_icon,
			RunQueueItemStatus.Finished: self._finished_icon,
			RunQueueItemStatus.Stopped: self._stopped_icon,
			RunQueueItemStatus.Cancelled: self._cancelled_icon,
			RunQueueItemStatus.Failed: self._failed_icon
		}

		#=== Font for Highlighting ===
		
		self._highlight_font = QtGui.QFont()
		self._highlight_font.setBold(True)

		#======= Other =======
		self._highlighted_id = None
		self._prev_highlighted_id = None


		#============= Connect changes to the queue to the model =============
		# self._run_queue.queueChanged.connect(self._update_current_action_list) #Update list when the queue changes
		# self._run_queue.runListChanged.connect(self._update_current_action_list) #Update list when run list changes
		# self._run_queue.runItemChanged.connect(self._update_current_action_list) #Update list when  run item changes 
	

	column_names = { #Used to map column index to a name/property of a RunQueueItem
		0: ("name", "Name"),
		1: ("status", "Status"),
		2: ("id", "ID"),
		3: ("dt_added", "Added"),
		4: ("dt_started", "Started"),
		5: ("config", "Config"),
		6: ("dt_done", "Finished"),
		7: ("exit_code", "Exit Code"),
		8: ("stderr", "Stderr")
	}
	# def _update_current_action_list(self):
	# 	"""Update the list of actions that can be performed on the current selection
	# 	"""
	# 	print("updating action list!")
	# 	actions = []
	# 	if self._highlighted_id is not None:
	# 		actions = self._run_queue.get_actions_for_id(self._highlighted_id)

	# 	if set(actions) != set(self._cur_actions): #Only emit if the list has changed
	# 		self._cur_actions = actions
	# 		self.currentActionListChanged.emit(self._cur_actions)

	

	def rowCount(self, parent: typing.Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex, None] = None) -> int:
		return len(self._cur_run_list_copy)

		# return super().rowCount(parent)
	def columnCount(self, parent: typing.Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex, None] = None) -> int:
		return len(self.column_names)
	
	def _queue_changed(self, queue_copy):
		self._cur_queue_copy = queue_copy
		self.layoutChanged.emit()
		self.dataChanged.emit(
			self.index(0, 0), 
			self.index(self.rowCount(), self.columnCount())
		) #TODO: Only emit changed. rows

	def _run_list_changed(self, run_list_copy):
		self._cur_run_list_copy = run_list_copy
		self.layoutChanged.emit()
		self.dataChanged.emit(
			self.index(0, 0), 
			self.index(self.rowCount(), self.columnCount())
		) #TODO: Only emit for the changed rows

	def _run_item_changed(self, id : int, new_item_copy : RunQueueItem):
		row = list(self._cur_run_list_copy.keys()).index(id)
		self._cur_run_list_copy[id] = new_item_copy
		self.dataChanged.emit(
			self.index(row, 0), 
			self.index(row, self.columnCount())
		) #TODO: Only emit for the changed rows

	def setHighlightIdByIndex(self, index: QtCore.QModelIndex) -> None:
		if index.isValid():
			new_id = self._cur_run_list_copy[list(self._cur_run_list_copy.keys())[index.row()]].id
			self._prev_highlighted_id = self._highlighted_id
			self._highlighted_id = new_id
			self.dataChanged.emit(index, index)

	def setHightlightId(self, id: int) -> None:
		self._prev_highlighted_id = self._highlighted_id
		self._highlighted_id = id
		self.dataChanged.emit(
			self.index(0, 0), 
			self.index(self.rowCount(), self.columnCount())
		) #TODO: Only update the row with the new/old id

	def hightlightedId(self) -> int | None:
		return self._highlighted_id

	
	#TODO: use RunqueueItemStatus instead of id to get options for ID -> otherwise we have to "ask"remote 
	#server for item status every time we select a row -> might not be desireable
	def getHighlightedActions(self) -> typing.List[QueueItemActions]:
		return self._run_queue.get_actions_for_id(self._highlighted_id) 

	def get_actions(self, index : QtCore.QModelIndex) -> typing.List[QueueItemActions]:
		"""Retrieve the possible actions for a given index (queue item), such as delete, move up in queue, etc.

		Args:
			index (QtCore.QModelIndex): The index of the item for which to retrieve the possible actions

		Returns:
			typing.List[QueueItemActions]: A list of possible actions for the given index.
		"""
		if index.isValid():
			return self._run_queue.get_actions_for_id(
				self._cur_run_list_copy[list(self._cur_run_list_copy.keys())[index.row()]].id)
		else:
			return []

	def add_to_queue(self, name, config) -> None:
		self._run_queue.add_to_queue(name, config)

	def do_action(self, index : QtCore.QModelIndex, action : QueueItemActions) -> None:
		if index.isValid():
			self._run_queue.do_action_for_id(
				self._cur_run_list_copy[list(self._cur_run_list_copy.keys())[index.row()]].id, action)


	def get_item_status(self, index : QtCore.QModelIndex) -> RunQueueItemStatus | None:
		if index.isValid():
			return self._cur_run_list_copy[index.row()].status
		else:
			return None

	def data(self, index: QtCore.QModelIndex, role: int | None = None) -> typing.Any:
		item = self._cur_run_list_copy[list(self._cur_run_list_copy.keys())[index.row()]]
		if role == QtCore.Qt.ItemDataRole.DisplayRole:
			key :str = self.column_names[index.column()][0]
			key = key.lower()
			attr = getattr(item, key)

			if key == "config":
				return "-"
			if key == "status": #Display position in queue
				cur_id = list(self._cur_run_list_copy.keys())[index.row()]
				if item.status == RunQueueItemStatus.Queued and cur_id in self._cur_queue_copy:
					return f"In Queue: {self._cur_queue_copy.index(cur_id)+1}/{len(self._cur_queue_copy)}"
				else: #Convert enum to string
					return str(item.status.name)
			if (key == "dt_added") or (key == "dt_done") or (key == "dt_started"):
				if attr:
					# print(key, attr)
					return attr.strftime("%Y-%m-%d %H:%M:%S")
			return attr
			
	
		elif role == QtCore.Qt.ItemDataRole.DecorationRole:
			if index.column() == 0:
				return self._icon_dict.get(item.status, None)
			else:
				return None		
		#Font role
		elif role == QtCore.Qt.ItemDataRole.FontRole:
			if item.id == self._highlighted_id:
				return self._highlight_font
		return None
	
	def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int | None = None) -> typing.Any:
		if role == QtCore.Qt.ItemDataRole.DisplayRole:
			if orientation == QtCore.Qt.Orientation.Horizontal:
				# if section == 0:
				# 	return "Name"
				# if section == 1:
				# 	return "Status" 
				return self.column_names[section][1]
		return None
	


if __name__ == "__main__":
		
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}] {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.DEBUG) #Without time
	
	log.info("Running small test for MLQueueModel")

	run_queue = RunQueue()
	run_queue.add_to_queue("Item1", "TheConfig")
	run_queue.add_to_queue("Item2", "TheConfig")
	run_queue.add_to_queue("Item3", "TheConfig")
	run_queue.add_to_queue("Item4", "TheConfig")
	run_queue.add_to_queue("ItemRunning", "TheConfig")
	run_queue._all_dict[4].name = "kaas" 
	run_queue.add_to_queue("ItemFinished", "TheConfig")
	run_queue._all_dict[5].status = RunQueueItemStatus.Finished
	run_queue.add_to_queue("ItemCancelled", "TheConfig")
	run_queue._all_dict[6].status = RunQueueItemStatus.Stopped
	run_queue.add_to_queue("ItemFailed", "TheConfig")
	run_queue._all_dict[7].status = RunQueueItemStatus.Failed
	app = QtWidgets.QApplication([])
	model = MLQueueModel(run_queue)
	view = QtWidgets.QTreeView()
	view.setModel(model)
	view.show()
	view.resize(1200, 400)
	app.exec()
	