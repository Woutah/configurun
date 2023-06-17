"""
Implements the RunQueueTableModel class. Enabling the user to display a RunQueue in a QT-view (e.g. QTableView).
"""

# from MachineLearning.framework.RunQueueClient import RunQueueClient
import logging
import typing

from PySide6 import QtCore, QtGui, QtWidgets

# from MachineLearning.framework.RunQueue import RunQueue, RunQueueItem, RunQueueItemStatus, QueueItemActions
from MLQueue.classes.RunQueue import (RunQueue, RunQueueItem,
                                      RunQueueItemActions, RunQueueItemStatus)

log = logging.getLogger(__name__)


class RunQueueTableModel(QtCore.QAbstractTableModel):

	"""
	Class that resides between the RunQueue and the view (QTableView) and provides the data for the view in a
	convenient way. Since Runqueue can also interface over a network - this class can be used to somewhat
	buffer the data and increase responsiveness of the UI.
	"""

	autoProcessingStateChanged = QtCore.Signal(bool)

	def set_run_queue(self, new_run_queue : RunQueue) -> None:
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
		self._run_queue = new_run_queue

		#============= Signal connections linking UI to RunQueue =============
		if self._queue_changed_signal_connection is not None:
			self._run_queue.queueChanged.disconnect(self._queue_changed_signal_connection)
		if self._run_list_changed_signal_connection is not None:
			self._run_queue.runListChanged.disconnect(self._run_list_changed_signal_connection)
		if self._run_item_changed_signal_connection is not None:
			self._run_queue.runItemChanged.disconnect(self._run_item_changed_signal_connection)
		if self._autoprocessing_state_signal_connection is not None:
			self._run_queue.autoProcessingStateChanged.disconnect(self._autoprocessing_state_signal_connection)

		self._queue_changed_signal_connection = self._run_queue.queueChanged.connect(self._queue_changed)
		self._run_list_changed_signal_connection = self._run_queue.runListChanged.connect(self._run_list_changed)
		self._run_item_changed_signal_connection = self._run_queue.runItemChanged.connect(self._run_item_changed)
		self._queue_reset_signal_connection = self._run_queue.queueResetTriggered.connect(self.reset_model)
		self._autoprocessing_state_signal_connection = self._run_queue.autoProcessingStateChanged.connect(
			self.autoprocessing_state_changed)

		self._cur_queue_copy = self._run_queue.get_queue_snapshot_copy()
		self._cur_run_list_copy = self._run_queue.get_run_list_snapshot_copy()
		self._cur_autoprocessing_state = self._run_queue.is_autoprocessing_enabled()


		# if also_instantiate:
		self._reset_model()
		self.endResetModel()

	def stop_autoprocessing(self):
		"""Signal current runqueue to stop autoqueueing"""
		self._run_queue.stop_autoqueueing()

	def start_autoprocessing(self):
		"""Signal current runqueue to start autoprocessing items in the runqueue"""
		self._run_queue.start_autoprocessing()

	def autoprocessing_state_changed(self, new_state : bool) -> None:
		"""Synchronizes autoprocessing state to RunQueue
		"""
		self.autoProcessingStateChanged.emit(new_state) #Emit signal to UI
		self._cur_autoprocessing_state = new_state

	def get_running_configuration_count(self) -> int:
		"""Return the number of configs currently running

		Returns:
			int: The number of configs currently running
		"""
		return self._run_queue.get_running_configuration_count()

	def is_autoprocessing_enabled(self) -> bool:
		"""Return whether autoprocessing is enabled in the current runqueue"""
		return self._cur_autoprocessing_state

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


	def __init__(self,
	    	run_queue : RunQueue,
			parent: typing.Optional[QtCore.QObject] = None
		) -> None:
		super().__init__(parent)

		self._run_queue_consoleoutput_signal_connection = None
		self._queue_changed_signal_connection = None
		self._run_list_changed_signal_connection = None
		self._run_item_changed_signal_connection = None
		self._autoprocessing_state_signal_connection = None
		self._queue_reset_signal_connection = self
		self._run_queue = run_queue
		self._cur_queue_copy = []
		self._cur_run_list_copy = {}

		self.set_run_queue(run_queue)



		self._cur_actions = [] #The actions possible for the currently hightlighted item


		#======================= Some icons =======================
		self._selection_pixmap = QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton #Checkmark #type: ignore
		self._selection_icon = QtWidgets.QApplication.style().standardIcon(self._selection_pixmap)

		self._waiting_pixmap = QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView #Pause button #type: ignore
		self._waiting_icon = QtWidgets.QApplication.style().standardIcon(self._waiting_pixmap)

		self._running_pixmap = QtWidgets.QStyle.StandardPixmap.SP_MediaPlay #Play button #type: ignore
		self._running_icon = QtWidgets.QApplication.style().standardIcon(self._running_pixmap)

		self._finished_pixmap = QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton #Checkmark #type: ignore
		self._finished_icon = QtWidgets.QApplication.style().standardIcon(self._finished_pixmap)

		self._stopped_pixmap = QtWidgets.QStyle.StandardPixmap.SP_DialogCancelButton #X #type: ignore
		self._stopped_icon = QtWidgets.QApplication.style().standardIcon(self._stopped_pixmap)

		self._cancelled_pixmap = QtWidgets.QStyle.StandardPixmap.SP_DialogNoButton #red circle #type: ignore
		self._cancelled_icon = QtWidgets.QApplication.style().standardIcon(self._cancelled_pixmap)

		self._failed_pixmap = QtWidgets.QStyle.StandardPixmap.SP_BrowserStop #X #type: ignore
		self._failed_icon = QtWidgets.QApplication.style().standardIcon(self._failed_pixmap)


		self._icon_dict = {
			RunQueueItemStatus.QUEUED: self._waiting_icon,
			RunQueueItemStatus.RUNNING: self._running_icon,
			RunQueueItemStatus.FINISHED: self._finished_icon,
			RunQueueItemStatus.STOPPED: self._stopped_icon,
			RunQueueItemStatus.CANCELLED: self._cancelled_icon,
			RunQueueItemStatus.FAILED: self._failed_icon
		}

		#=== Font for Highlighting ===

		self._highlight_font = QtGui.QFont()
		self._highlight_font.setBold(True)

		#======= Other =======
		self._highlighted_id = None
		self._prev_highlighted_id = None
		self._cur_autoprocessing_state = False


		#============= Connect changes to the queue to the model =============
		# self._run_queue.queueChanged.connect(self._update_current_action_list) #Update list when the queue changes
		# self._run_queue.runListChanged.connect(self._update_current_action_list) #Update list when run list changes
		# self._run_queue.runItemChanged.connect(self._update_current_action_list) #Update list when  run item changes


	column_names = { #Used to map column index to a name/property of a RunQueueItem
		0: ("name", "Name"),
		1: ("status", "Status"),
		2: ("item_id", "ID"),
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



	def rowCount(self,
	      	parent: typing.Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex, None] = None #pylint: disable=unused-argument
		) -> int:
		return len(self._cur_run_list_copy)

		# return super().rowCount(parent)
	def columnCount(self,
			parent: typing.Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex, None] = None #pylint: disable=unused-argument
		) -> int:
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

	def _run_item_changed(self, changed_item_id : int, new_item_copy : RunQueueItem):
		row = list(self._cur_run_list_copy.keys()).index(changed_item_id)
		self._cur_run_list_copy[changed_item_id] = new_item_copy
		self.dataChanged.emit(
			self.index(row, 0),
			self.index(row, self.columnCount())
		) #TODO: Only emit for the changed rows

	def set_highlight_by_index(self, index: QtCore.QModelIndex) -> None:
		"""Set the highlighted item by its index in the model
		Args:
			index (QtCore.QModelIndex): The index of the item to highlight
		"""
		if index.isValid():
			new_id = self._cur_run_list_copy[list(self._cur_run_list_copy.keys())[index.row()]].item_id
			self._prev_highlighted_id = self._highlighted_id
			self._highlighted_id = new_id
			self.dataChanged.emit(index, index)

	def set_highligh_by_id(self, highlight_item_id: int) -> None:
		"""Set the highlighted item by its item id
		Args:
			id (int): The id of the item to highlight
		"""
		self._prev_highlighted_id = self._highlighted_id
		self._highlighted_id = highlight_item_id
		self.dataChanged.emit(
			self.index(0, 0),
			self.index(self.rowCount(), self.columnCount())
		) #TODO: Only update the row with the new/old id

	def hightlighted_id(self) -> int | None:
		"""return the currently highlighted item id in the model"""
		return self._highlighted_id


	#TODO: use RunqueueItemStatus instead of id to get options for ID -> otherwise we have to "ask"remote
	#server for item status every time we select a row -> might not be desireable
	def get_actions(self, index : QtCore.QModelIndex) -> typing.List[RunQueueItemActions]:
		"""Retrieve the possible actions for a given index (queue item), such as delete, move up in queue, etc.

		Args:
			index (QtCore.QModelIndex): The index of the item for which to retrieve the possible actions

		Returns:
			typing.List[QueueItemActions]: A list of possible actions for the given index.
		"""
		if index.isValid():
			return self._run_queue.get_actions_for_id(
				self._cur_run_list_copy[list(self._cur_run_list_copy.keys())[index.row()]].item_id)
		else:
			return []

	def add_to_queue(self, name, config) -> None:
		"""Addd a new item to the queue with the given name and config"""
		self._run_queue.add_to_queue(name, config)

	def do_action(self, index : QtCore.QModelIndex, action : RunQueueItemActions) -> None:
		"""Determine the id of the item at the given index and perform the given action on it

		Args:
			index (QtCore.QModelIndex): The index of the item to perform the action on
			action (RunQueueItemActions): The action to perform
		"""
		if index.isValid():
			self._run_queue.do_action_for_id(
				self._cur_run_list_copy[list(self._cur_run_list_copy.keys())[index.row()]].item_id, action)


	def get_item_status(self, index : QtCore.QModelIndex) -> RunQueueItemStatus | None:
		"""Get the item status by index

		Args:
			index (QtCore.QModelIndex): the index for which to fetch the status

		Returns:
			RunQueueItemStatus | None: The status of the item, or None if the index is invalid
		"""
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
				if item.status == RunQueueItemStatus.QUEUED and cur_id in self._cur_queue_copy:
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
			if item.item_id == self._highlighted_id:
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
	# pylint: disable=protected-access
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}] {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.DEBUG) #Without time

	log.info("Running small test for MLQueueModel")

	test_run_queue = RunQueue()
	test_run_queue.add_to_queue("Item1", "TheConfig")
	test_run_queue.add_to_queue("Item2", "TheConfig")
	test_run_queue.add_to_queue("Item3", "TheConfig")
	test_run_queue.add_to_queue("Item4", "TheConfig")
	test_run_queue.add_to_queue("ItemRunning", "TheConfig")
	test_run_queue._all_dict[4].name = "kaas"
	test_run_queue.add_to_queue("ItemFinished", "TheConfig")
	test_run_queue._all_dict[5].status = RunQueueItemStatus.FINISHED
	test_run_queue.add_to_queue("ItemCancelled", "TheConfig")
	test_run_queue._all_dict[6].status = RunQueueItemStatus.STOPPED
	test_run_queue.add_to_queue("ItemFailed", "TheConfig")
	test_run_queue._all_dict[7].status = RunQueueItemStatus.FAILED
	app = QtWidgets.QApplication([])
	model = RunQueueTableModel(test_run_queue)
	view = QtWidgets.QTreeView()
	view.setModel(model)
	view.show()
	view.resize(1200, 400)
	app.exec()
