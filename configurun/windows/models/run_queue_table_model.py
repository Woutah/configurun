"""
Implements the RunQueueTableModel class. Enabling the user to display a RunQueue in a QT-view (e.g. QTableView).
"""

# from MachineLearning.framework.RunQueueClient import RunQueueClient
import logging
import os
import textwrap
import traceback
import typing
from enum import IntEnum

import dill
from PySide6 import QtCore, QtGui, QtWidgets

# from MachineLearning.framework.RunQueue import RunQueue, RunQueueItem, RunQueueItemStatus, QueueItemActions
from configurun.classes.run_queue import (RunQueue,
                                          RunQueueHasRunningItemsException,
                                          RunQueueItem, RunQueueItemActions,
                                          RunQueueItemStatus)

log = logging.getLogger(__name__)



class RunQueueTableModel(QtCore.QAbstractTableModel):

	"""
	Class that resides between the RunQueue and the view (QTableView) and provides the data for the view in a
	convenient way. Since Runqueue can also interface over a network - this class can be used to somewhat
	buffer the data and increase responsiveness of the UI.
	"""

	autoProcessingStateChanged = QtCore.Signal(bool)

	itemHighlightIdChanged = QtCore.Signal(int) #Emitted when the highlighted item changes, emits the new id

	class CustomDataRoles(IntEnum):
		"""
		Enum containing custom data roles that can be used to retrieve data from the model
		"""
		#pylint: disable=invalid-name
		IDRole = QtCore.Qt.ItemDataRole.UserRole.value + 1
		ActionRole = QtCore.Qt.ItemDataRole.UserRole.value + 2 #An action is being performed on this item
		StatusRole = QtCore.Qt.ItemDataRole.UserRole.value + 3 #The status of this item (Queued, Running etc.)


	def __init__(self,
	    	run_queue : RunQueue,
			parent: typing.Optional[QtCore.QObject] = None
		) -> None:
		super().__init__(parent)

		self._run_queue_connections = [] #List of signal connectiosn to the run_queue, enables us to disconnect them
		self._run_queue = run_queue

		self._cur_queue_copy = []
		self._cur_run_queue_item_dict_copy = {}
		self._cur_item_dict_id_order = [] #The order of the ids in the current run_queue_item_dict, this determines
			# the order of the items in the model since the order of the dict itself is not neccessarily guaranteed
			# and because it makes sense to order by id because this makes it so insertions always happen at the end

		self.set_run_queue(run_queue) #Connects signals etc.



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
		self._cur_autoprocessing_state = False


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
		for connection in self._run_queue_connections:
			connection.disconnect()

		self._run_queue_connections.append(self._run_queue.queueChanged.connect(self._queue_changed))
		self._run_queue_connections.append( #On item-insertion in runQueue
			self._run_queue.allItemsDictInsertion.connect(self._handle_run_queue_insertion)
		)
		self._run_queue_connections.append( #On item deletion in runQueue
			self._run_queue.allItemsDictRemoval.connect(self._handle_run_queue_deletion)
		)
		self._run_queue_connections.append(self._run_queue.itemDataChanged.connect(self._run_item_changed))
		self._run_queue_connections.append(self._run_queue.resetTriggered.connect(self.reset_model))
		self._run_queue_connections.append(self._run_queue.autoProcessingStateChanged.connect(
			self.autoprocessing_state_changed))


		# self._cur_queue_copy = self._run_queue.get_queue_snapshot_copy()
		# self._cur_run_list_copy = self._run_queue.get_run_list_snapshot_copy()


		# if also_instantiate:
		self._reset_model()
		self.endResetModel()

	def stop_autoprocessing(self):
		"""Signal current runqueue to stop autoqueueing"""
		self._run_queue.stop_autoprocessing()

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
			self._cur_run_queue_item_dict_copy = self._run_queue.get_all_items_dict_snapshot_copy()
			self._cur_autoprocessing_state = self._run_queue.is_autoprocessing_enabled()
			if self._cur_queue_copy is None:
				self._cur_queue_copy = []
			if self._cur_run_queue_item_dict_copy is None:
				self._cur_run_queue_item_dict_copy = {}
			self._cur_item_dict_id_order = list(self._cur_run_queue_item_dict_copy.keys())
			self._cur_item_dict_id_order.sort()



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
	column_positions = { #Opposite of column_names
		"name": 0,
		"status": 1,
		"item_id": 2,
		"dt_added": 3,
		"dt_started": 4,
		"config": 5,
		"dt_done": 6,
		"exit_code": 7,
		"stderr": 8
	}

	def load_from_file(self,
		    file_path : str,
			allow_load_running_items : typing.Literal["allow", "ask", "disallow"] = "ask"
		):
		"""Loads the runqueue from a file

		Args:
			path (str): The path to the file to load from
			allow_load_running_items (typing.Literal["allow", "ask", "disallow"], optional): Whether to allow loading
				a RunQueue in which 1 or more items were running at save-time. Defaults to "ask".
		"""

		#Check if user cancelled
		if file_path is None or file_path == "":
			log.info("User cancelled loading queue from file.")
			return
		try:
			try:
				# self._run_queue.load_queue_contents_from_file(file_path)
				load_dict = RunQueue.get_queue_contents_dict_from_file(file_path)
			except RunQueueHasRunningItemsException as exception:
				if allow_load_running_items == "disallow":
					return
				elif allow_load_running_items == "allow":
					pass
				elif allow_load_running_items == "ask":
					msg = f"{type(exception).__name__}: {exception}"
					log.warning(f"Could not load RunQueue from file - {msg}")
					msg_box = QtWidgets.QMessageBox()
					msg_box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
					msg_box.setWindowTitle("Could not load RunQueue from file")
					msg_box.setText("<b>Do you want to set load mode to allow importing configurations that were saved when "
						"1 or more configurations were running?</b>")
					msg_box.setInformativeText(f"<b>{type(exception).__name__}:</b> {exception}<br><br>All running items "
						"of this backup were saved with a 'stopped'-state, this might indicate that the loaded runQueue-data "
						"is not entirely up to date."
						)
					msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
					msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
					msg_box.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
					msg_box.show()
					msg_box.activateWindow()
					msg_box.exec()
					if msg_box.result() == QtWidgets.QMessageBox.StandardButton.Yes:
						load_dict = RunQueue.get_queue_contents_dict_from_file(file_path, allow_load_running_items=True)
					else:
						log.info("User cancelled loading queue from file.")
						return

			self._run_queue.load_queue_contents_dict(load_dict) #type: ignore #Actually load the queue-data into existing

		except Exception as exception: #pylint: disable=broad-exception-caught
			msg = f"{type(exception).__name__}: {exception}"
			trace = traceback.format_exc()
			log.warning(f"Could not load RunQueue from path {file_path} - {msg}")
			msg_box = QtWidgets.QMessageBox()
			msg_box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
			msg_box.setWindowTitle("Could not load RunQueue from file")
			msg_box.setText("Could not load RunQueue from file due to an unexpected error.")
			msg_box.setInformativeText(msg)
			msg_box.setDetailedText(trace)
			log.warning(trace)
			msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
			msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)
			msg_box.show()
			msg_box.activateWindow()
			msg_box.exec()
			return

		log.info(f"Loaded RunQueue from file {file_path}.")

	def load_from_file_popup(self):
		"""
		Opens a popup to load the RunQueue-items from a file.
		Loading itself is done by the run_queue itself.
		"""
		if self._run_queue.get_running_configuration_count() > 0:
			msg_box = QtWidgets.QMessageBox()
			msg_box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
			msg_box.setWindowTitle("Cannot load queue from file")
			msg_box.setText("Cannot load queue from file while there are still running items in the queue.")
			msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
			msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)
			msg_box.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
			msg_box.show()
			msg_box.activateWindow()
			msg_box.exec()
			return


		file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
			None, "Load config", QtCore.QDir.currentPath(), "RunQueue files (*.rq)") #type:ignore

		file_path = file_path.replace("/", os.sep) #Get the actual path (qt uses / as separator)

		self.load_from_file(file_path)

	def get_n_processes(self) -> int:
		"""Returns the number of processes to use for the queue.
		"""
		return self._run_queue.get_n_processes()

	def set_n_processes(self, n_processes : int) -> None:
		"""Sets the number of processes to use for the queue.

		Args:
			n_processes (int): The number of processes to use for the queue
		"""
		self._run_queue.set_n_processes(n_processes)

	def save_to_file_popup(self):
		"""Opens a popup to save the queue to a file.

		Save-handling is done by the run_queue itself.

		NOTE: if we make more models based on the run_queue, we should probably move this to a shared base-class
		"""
		try:
			try:
				save_dict = self._run_queue.get_queue_contents_dict(save_running_as_stopped=False)
			except RunQueueHasRunningItemsException as exception: #pylint: disable=broad-exception-caught
				log.warning("")
				#Ask if user wants to save anyway, in the savefile, all running items will be marked as "stopped"
				#and the queue will be saved
				msg_box = QtWidgets.QMessageBox()
				msg_box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
				msg_box.setWindowTitle("Save queue to file anyway?")
				msg = f"Problem when saving queue to file: {type(exception).__name__}: {exception}"
				log.warning(msg)
				msg_box.setText("<b>Do you want to set save mode to allow saving running configurations?</b>")
				msg_box.setInformativeText(
					f"<b>{type(exception).__name__}:</b> {exception} <br><br>"
					"We can enable saving running configurations, but this will cause the running configurations to "
					"be saved with a 'stopped'-state.  "
					"Alternatively, you can cancel all running items or wait for them to finish and try again. "

				)
				msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
				msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
				msg_box.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
				msg_box.show()
				msg_box.activateWindow()
				msg_box.exec()

				if msg_box.result() == QtWidgets.QMessageBox.StandardButton.Yes: #Load and allow running items
					save_dict = self._run_queue.get_queue_contents_dict(save_running_as_stopped=True)
				else:
					log.info("User cancelled saving queue to file.")
					return

			file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
				None, "Save config", QtCore.QDir.currentPath(), "RunQueue files (*.rq)") #type:ignore

			if file_path is None or file_path == "":
				log.info("User cancelled saving queue to file.")
				return

			with open(file_path, "wb") as save_file:
				dill.dump(save_dict, save_file)

			log.info(f"Saved RunQueue to file {file_path}.")

		except Exception as exception: #pylint: disable=broad-exception-caught
			msg = f"{type(exception).__name__}: {exception}"
			log.warning(f"Could not save RunQueue to file - {msg}")
			msg_box = QtWidgets.QMessageBox()
			msg_box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
			msg_box.setWindowTitle("Could not save RunQueue to file")
			msg_box.setInformativeText(msg)
			msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
			msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)
			msg_box.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
			msg_box.show()
			msg_box.exec()
			return


		#Check if user cancelled




	def rowCount(self,
	      	parent: typing.Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex, None] = None #pylint: disable=unused-argument
		) -> int:
		return len(self._cur_item_dict_id_order) #NOTE: the _cur_item_dict_id order determines what items are shown
			# even when more items are in the _cur_item_dict


		# return super().rowCount(parent)
	def columnCount(self,
			parent: typing.Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex, None] = None #pylint: disable=unused-argument
		) -> int:
		return len(self.column_names)


	def _handle_run_queue_insertion(self, new_item_ids : list[int], new_items_dict : typing.Dict[int, RunQueueItem]):
		"""
		Handles the insertion of new item(s) in the runQueue. Should be linked to the allItemsDictInsertion signal
		of the attached runQueueManager. On item insertion, updates the table-model.

		Args:
			new_item_ids (list[int]): list of ids of the new items
			new_items_dict (typing.Dict[int, RunQueueItem]): a copy of the all_items_dict with the new item added
		"""
		if (len(new_item_ids) - len(new_items_dict)) != len(self._cur_run_queue_item_dict_copy):
			log.warning("New item(s) added to runQueue, but the updated length of the runQueue is different from the currently"
	     		"known length of the table-model plus the amount of added items. The runqueue seems to be out of sync...")

		self._cur_run_queue_item_dict_copy = new_items_dict #Update the copy of the runQueue

		#Also look for the new item-order (sort the dict keys = sort by id)
		new_item_dict_id_order = list(new_items_dict.keys())
		new_item_dict_id_order.sort()

		insertion_points = [new_item_dict_id_order.index(id) for id in new_item_ids] #Check where the new items were inserted
		#Make the insertion points negative so we can iteratively add items while the insertion points will be determined

		cur_insertion_point_index = 0
		while True: #Group all consecutive insertions together ([1,2,3,5] -> [1,2,3] and [5])
			start_insertion_point_idx = cur_insertion_point_index
			stop_insertion_point_idx  = cur_insertion_point_index
			for i, insertion_point in enumerate(insertion_points[cur_insertion_point_index+1:]): #All next insertion points
				last_insertion_point = insertion_points[cur_insertion_point_index]
				if (last_insertion_point + i + 1) == insertion_point:
					stop_insertion_point_idx  = insertion_point
					cur_insertion_point_index += 1
				else:
					break

			self.beginInsertRows(QtCore.QModelIndex(), start_insertion_point_idx, stop_insertion_point_idx)
			for i in range(start_insertion_point_idx, stop_insertion_point_idx +1): #Insert the ids into the id-order-list
				insert_loc  = insertion_points[i]
				self._cur_item_dict_id_order.insert(insert_loc, new_item_dict_id_order[insert_loc])
			self.endInsertRows()
			cur_insertion_point_index += 1
			if cur_insertion_point_index >= len(insertion_points): #If inserted all items
				break

		if self._cur_item_dict_id_order != new_item_dict_id_order:
			log.warning("Item order in model does not match item order in runQueue")

	def force_stop_all_running(self):
		"""Force stop all items in the runqueue, also stops autoprocessing

		NOTE: all unsaved progress will be lost(!!!)
		"""
		self._run_queue.force_stop_all_running()

	def _handle_run_queue_deletion(self, deleted_item_ids : list[int], new_items_dict : typing.Dict[int, RunQueueItem]):
		"""
		Handles the deletetion of item(s) in the runQueue

		Args:
			deleted_item_ids (list[int]): list of ids of the deleted items
			new_items_dict (typing.Dict[int, RunQueueItem]): a copy of the all_items_dict with the new item added
		"""
		if (len(new_items_dict) - len(deleted_item_ids)) != len(self._cur_run_queue_item_dict_copy):
			log.warning("Item(s) removed from runQueue, but the updated length of the runQueue is different from the currently"
	     		"known length of the table-model minus the amount of removed items. The runqueue seems to be out of sync...")

		# self._cur_run_queue_item_dict_copy = new_items_dict #Update the copy of the runQueue

		#Also look for the new item-order (sort the dict keys = sort by id)
		new_item_dict_id_order = list(new_items_dict.keys())
		new_item_dict_id_order.sort() #

		deletion_points = [self._cur_item_dict_id_order.index(id) for id in deleted_item_ids] #Check where the new items
			#were deleted
		deletion_points = deletion_points[::-1] #So we can delete items from the back to the front so indexes don't change
		#Make the insertion points negative so we can iteratively add items while the insertion points will be determined

		cur_deletion_point_index = 0
		while True : #Group all consecutive deletions together ([5,3,2,1] -> [5] [3,2,1])
			start_deletion_point_idx = cur_deletion_point_index
			stop_deletion_point_idx  = cur_deletion_point_index
			for i, insertion_point in enumerate(deletion_points[cur_deletion_point_index+1:]): #All next insertion points
				last_insertion_point = deletion_points[cur_deletion_point_index]
				if (last_insertion_point + i - 1) == insertion_point:
					stop_deletion_point_idx  = insertion_point
					cur_deletion_point_index += 1
				else:
					break

			# self.beginInsertRows(QtCore.QModelIndex(), start_deletion_point_idx, stop_deletion_point_idx)
			self.beginRemoveRows(QtCore.QModelIndex(), start_deletion_point_idx, stop_deletion_point_idx)
			for i in range(start_deletion_point_idx, stop_deletion_point_idx +1): #Insert the ids into the id-order-list
				delete_loc  = deletion_points[i]
				delete_id = self._cur_item_dict_id_order[delete_loc]

				#Remove item from dict and id-order-list
				del self._cur_run_queue_item_dict_copy[delete_id]
				del self._cur_item_dict_id_order[delete_loc]

				# self._cur_item_dict_id_order.insert(delete_loc, new_item_dict_id_order[delete_loc])
			self.endRemoveRows()
			cur_deletion_point_index += 1
			if cur_deletion_point_index >= len(deletion_points): #If inserted all items
				break

		if self._cur_item_dict_id_order != new_item_dict_id_order:
			log.warning("Item order in model after deletion does not match item order in runQueue")

	def _queue_changed(self, queue_copy):
		self._cur_queue_copy = queue_copy
		# self.layoutChanged.emit()
		log.debug(f"The queue order changed to {', '.join([str(i) for i in queue_copy])}. "
	    	"Now emitting datachanged for column...")

		row = self.column_positions["status"]
		self.dataChanged.emit(
			self.index(row, 0),
			self.index(row, self.columnCount()),
			[QtCore.Qt.ItemDataRole.DisplayRole, QtCore.Qt.ItemDataRole.EditRole] #Change the displayed queue-position
		) #TODO: Only emit changed. rows


	def _run_item_changed(self, changed_item_id : int, new_item_copy : RunQueueItem):
		# row = list(self._cur_run_queue_item_dict_copy.keys()).index(changed_item_id)
		row = self.get_index_row_by_id(changed_item_id)

		assert(changed_item_id in self._cur_run_queue_item_dict_copy), "ID of update-item not in currently known itemList"
		self._cur_run_queue_item_dict_copy[changed_item_id] = new_item_copy
		self.dataChanged.emit(
			self.index(row, 0),
			self.index(row, self.columnCount())
		) #TODO: Only emit for the changed rows

	def get_index_row_by_id(self, item_id : int) -> int:
		"""Get the index-row of the item with the given id

		Args:
			item_id (int): The id of the item to get the index for

		Returns:
			row (int): The row of the item with the given id
		"""
		if item_id in self._cur_item_dict_id_order:
			# id_list = list(self._cur_run_queue_item_dict_copy.keys())
			# id_list.sort()
			# return id_list.index(item_id)
			return self._cur_item_dict_id_order.index(item_id)
		else:
			return -1

	def get_index_by_id(self, item_id : int, column : int):
		"""Get the row if the index by id, and construct the index from that row and the given column"""
		return self.index(self.get_index_row_by_id(item_id), column)



	def set_highlight_by_index(self, index: QtCore.QModelIndex) -> None:
		"""Set the highlighted item by its index in the model
		Args:
			index (QtCore.QModelIndex): The index of the item to highlight
		"""
		if index.isValid():
			new_id = index.data(role=RunQueueTableModel.CustomDataRoles.IDRole)
			self._prev_highlighted_id = self._highlighted_id
			self._highlighted_id = new_id

			self.dataChanged.emit(
				self.index(index.row(), 0),
				self.index(index.row(),self.columnCount()), #update column
				[QtCore.Qt.ItemDataRole.FontRole] #Only update font as it is the only thing that changes due to highlighting
			)

			self.itemHighlightIdChanged.emit(new_id) #Emit signal to UI
		else:
			log.info("Invalid index given to set_highlight_by_index, resetting highlight")
			self.itemHighlightIdChanged.emit(None) #Emit signal to UI
			self._highlighted_id = -1

		if self._prev_highlighted_id is not None: #Also clear boldness of the previous item
			self.dataChanged.emit(
				self.index(self.get_index_row_by_id(self._prev_highlighted_id), 0),
				self.index(self.get_index_row_by_id(self._prev_highlighted_id), self.columnCount()),
				[QtCore.Qt.ItemDataRole.FontRole] #Only update font as it is the only thing that changes due to highlighting
			)

	def set_highligh_by_id(self, highlight_item_id : int | None) -> None:
		"""Set the highlighted item by its item id
		Args:
			id (int): The id of the item to highlight or None/--1 to clear the highlight
		"""
		self._prev_highlighted_id = self._highlighted_id
		if highlight_item_id is None or highlight_item_id < 0:
			self._highlighted_id = -1
		else:
			self._highlighted_id = highlight_item_id
			self.dataChanged.emit(
				self.get_index_by_id(self._highlighted_id, 0),
				self.get_index_by_id(self._highlighted_id, self.columnCount()), #update column
				[QtCore.Qt.ItemDataRole.FontRole] #Only update font as it is the only thing that changes due to highlighting
			) #TODO: Only update the row with the new/old id
		if self._prev_highlighted_id is not None: #Also clear boldness of the previous item
			self.dataChanged.emit(
				self.get_index_by_id(self._prev_highlighted_id, 0),
				self.get_index_by_id(self._prev_highlighted_id, self.columnCount()), #update column
				[QtCore.Qt.ItemDataRole.FontRole] #Only update font as it is the only thing that changes due to highlighting
			)
		self.itemHighlightIdChanged.emit(highlight_item_id) #Emit signal to UI

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
			status = self.get_item_status(index)
			if status is not None:
				return RunQueue.get_actions_from_status(status)
			else:
				return []
		else:
			return []

	def add_to_queue(self, name, config) -> None:
		"""Addd a new item to the queue with the given name and config"""
		self._run_queue.add_to_queue(name, config)

	def do_action_by_id(self, item_id : int, action : RunQueueItemActions) -> None:
		"""Perform the given action on the item with the given id

		Args:
			item_id (int): The id of the item to perform the action on
			action (RunQueueItemActions): The action to perform
		"""
		self._run_queue.do_action_for_id(item_id, action)

	def do_action(self, index : QtCore.QModelIndex, action : RunQueueItemActions) -> None:
		"""Determine the id of the item at the given index and perform the given action on it

		Args:
			index (QtCore.QModelIndex): The index of the item to perform the action on
			action (RunQueueItemActions): The action to perform
		"""
		target_id = index.data(role=RunQueueTableModel.CustomDataRoles.IDRole)
		log.debug(f"Item id is: {target_id}")
		if index.isValid():
			log.debug(f"Performing action {action} on item with id {target_id}")
			self._run_queue.do_action_for_id(target_id, action)


	def get_item_status(self, index : QtCore.QModelIndex) -> RunQueueItemStatus | None:
		"""Get the item status by index

		Args:
			index (QtCore.QModelIndex): the index for which to fetch the status

		Returns:
			RunQueueItemStatus | None: The status of the item, or None if the index is invalid
		"""
		if index.isValid():
			target_id = self._cur_item_dict_id_order[index.row()]
			return self._cur_run_queue_item_dict_copy[target_id].status
		else:
			return None

	def setData(self, index: QtCore.QModelIndex, value: typing.Any, role: int | None = None) -> bool:
		"""The setData function, in this case only implements the action role. Makes it possible to perform an action
		(e.g. delete, move up, etc.) on an item in the queue with proxy-models in between.

		Calls to setData are propagated through all proxy-models to the underlying model (RunQueueTableModel).

		NOTE: this method differs somewhat from the normal implementation of setData in that it doesn't directly
		emit a dataChanged signal if the set was succesful. Instead, it attempts to do the action on the runqueue
		and if that succeeds, the runQueue will emit a signal that will cause the model to update itself.
		"""
		log.debug(f"setData called for index {index} with value {value} and role {role}")
		try:
			if index.isValid():
				# if role == QtCore.Qt.ItemDataRole.EditRole:
				# 	if index.column() == 0:
				# 		self._cur_run_list_copy[index.row()].name = value
				# 		self.dataChanged.emit(index, index)
				# 		return True
				log.debug("Index valid, not checking type and action")
				if role == RunQueueTableModel.CustomDataRoles.ActionRole:
					if not isinstance(value, RunQueueItemActions):
						log.error(f"Invalid role {role} for setData for index {index} in RunQueueTableModel")
						return False
					log.debug("Now actually doing action")
					self.do_action(index, value)
					log.debug("Done doing action")
					#Emit whole row:
					return False
				else:
					log.error(f"Invalid role {role} for setData for index {index} in RunQueueTableModel")
		except Exception as exception: # pylint: disable=broad-except
			log.error(f"Failed to set data for index {index}: {exception}")
		return False

	def data(self, index: QtCore.QModelIndex, role: int | None = None) -> typing.Any:
		try:
			item_id = self._cur_item_dict_id_order[index.row()]
			item = self._cur_run_queue_item_dict_copy[item_id]

			if role == QtCore.Qt.ItemDataRole.DisplayRole:
				key :str = self.column_names[index.column()][0]
				key = key.lower()
				attr = getattr(item, key)

				if key == "config":
					return "-"
				if key == "status": #Display position in queue
					cur_id = list(self._cur_run_queue_item_dict_copy.keys())[index.row()]
					if item.status == RunQueueItemStatus.Queued and cur_id in self._cur_queue_copy:
						return f"In Queue: {self._cur_queue_copy.index(cur_id)+1}/{len(self._cur_queue_copy)}"
					elif item.status == RunQueueItemStatus.Queued:
						#If the item says it is queued, but it is not in the queue, the model is out of sync
						# with the current state of the queue and or the runqueue-items
						return "ERROR: MODEL OUT OF SYNC"
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
			elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
				ret = str(self.data(index, QtCore.Qt.ItemDataRole.DisplayRole))
				#Go over ret lines and if they are too long, split them
				ret_lines = ret.split("\n")
				for i, line in enumerate(ret_lines):
					if len(line) > 80: #If line is too long, split it
						ret_lines[i] = "\n".join(textwrap.wrap(line, 80))
				return "\n".join(ret_lines)
			elif role == QtCore.Qt.ItemDataRole.FontRole: #Font role: highlight if item is highlighted
				if item.item_id == self._highlighted_id:
					return self._highlight_font
			elif role == RunQueueTableModel.CustomDataRoles.IDRole:
				return item.item_id
			elif role == RunQueueTableModel.CustomDataRoles.ActionRole:
				return self.get_actions(index)
			elif role == RunQueueTableModel.CustomDataRoles.StatusRole:
				return (item.status,) #Returned as tuple, because otherwise the return value is converted to an int (?)
				# return "kaas"
			return None

		except Exception as exception: # pylint: disable=broad-except
			log.error(f"Failed to get data for index {index}: {exception}")

	def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int | None = None) -> typing.Any:
		if role == QtCore.Qt.ItemDataRole.DisplayRole:
			if orientation == QtCore.Qt.Orientation.Horizontal and section > 0:
				return self.column_names[section][1]
		return None
