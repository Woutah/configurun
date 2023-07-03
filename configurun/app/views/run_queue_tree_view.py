"""
Implements the RunQueueTreeView class that is used to display a RunQueue in a Qt-Treeview
"""
import logging
import typing

from PySide6 import QtCore, QtWidgets
from pyside6_utils.models import ExtendedSortFilterProxyModel

from configurun.classes.run_queue import (RunQueue, RunQueueItemActions,
                                          RunQueueItemStatus)
from configurun.app.models.run_queue_table_model import RunQueueTableModel

log = logging.getLogger(__name__)

class RunQueueTreeView(QtWidgets.QTreeView):
	"""
	Treeview-equivalent used for run-queue items (MLQueueItems)
	"""

	def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
		super().__init__(parent)

		# self.setModel(model)

		#===========Create menu ============
		self._rc_menu = QtWidgets.QMenu(self)
		self._delete_action = self._rc_menu.addAction("Delete")
		self._cancel_action = self._rc_menu.addAction("Cancel")
		self._move_up_action = self._rc_menu.addAction("Move Up")
		self._move_down_action = self._rc_menu.addAction("Move Down")
		self._move_top_action = self._rc_menu.addAction("Move to Top")
		self._stop_action = self._rc_menu.addAction("Stop")
		self._start_action = self._rc_menu.addAction("Run Item")

		self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
		self.customContextMenuRequested.connect(self.custom_menu_requested)

		self.setSortingEnabled(True)

		self._action_dict = {
			RunQueueItemActions.DELETE: self._delete_action,
			RunQueueItemActions.CANCEL: self._cancel_action,
			RunQueueItemActions.MOVEUP: self._move_up_action,
			RunQueueItemActions.MOVEDOWN: self._move_down_action,
			RunQueueItemActions.MOVETOP: self._move_top_action,
			RunQueueItemActions.STOP: self._stop_action,
			RunQueueItemActions.START: self._start_action,
		}

		# =========== Link actions ===========
		for key in self._action_dict: # pylint: disable=consider-using-dict-items
			if key != RunQueueItemActions.STOP:
				self._action_dict[key].triggered.connect(lambda *_, action=key : self.do_action_on_selection(action))

		#Stop is a special case, ask for confirmation
		self._action_dict[RunQueueItemActions.STOP].triggered.connect(lambda *_: self.confirm_stop_current_index())

		self.proxy_model = ExtendedSortFilterProxyModel(self)
		self.proxy_model.setDynamicSortFilter(True)
		self.proxy_model.set_filter_function("status_filter", self.check_if_current_filter_accepts_row)
		#Make sure the dataChanged signal is emitted when the source model changes

		super().setModel(self.proxy_model)


		#Connect double-click
		self._double_click_connection = self.doubleClicked.connect(self._default_on_double_click)
		self._hide_status_list = []

	def check_if_current_filter_accepts_row(self,
				source_row: int,
				source_parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
				source_model: QtCore.QAbstractItemModel
			) -> bool:
		"""Check if the passed row should be visible or not

		Args:
			source_row (int): The row to check
			source_parent (QtCore.QModelIndex): The parent of the row to check

		Returns:
			bool: True if the row should be visible, False otherwise
		"""
		#Status column:
		index = source_model.index(source_row, 0, source_parent)
		# data_roles = [role for role in RunQueueTableModel.CustomDataRoles]
		status = index.data(RunQueueTableModel.CustomDataRoles.StatusRole)[0]
		if status in self._hide_status_list:
			return False
		return True

	def set_item_status_filter(self, hide_status_list : list[RunQueueItemStatus] | None = None) -> None:
		"""Sets the list of statuses that should be filtered (hidden)

		Args:
			hide_status_list (list[RunQueueItemStatus], optional): A list of statuses that should be filtered (hidden).
				Defaults to None.
		"""
		if hide_status_list is None:
			hide_status_list = []
		self._hide_status_list = hide_status_list
		self.proxy_model.invalidateFilter()

	def set_whether_status_filtered(self, status : RunQueueItemStatus,  hide_item : bool) -> None:
		"""Sets whether the passed status should be filtered (hidden) or not

		Args:
			status (RunQueueItemStatus): The status to hide or show
			hide_item (bool): Whether to hide the passed status or not
		"""
		if hide_item:
			if status not in self._hide_status_list:
				self._hide_status_list.append(status)
				self.proxy_model.invalidateFilter()
		else:
			if status in self._hide_status_list:
				self._hide_status_list.remove(status)
				self.proxy_model.invalidateFilter()


	def get_item_status_filter(self) -> list[RunQueueItemStatus]:
		"""Returns a list of all statuses that are filtered (hidden)

		Returns:
			list[RunQueueItemStatus]: A list of all statuses that are filtered (hidden)
		"""
		return self._hide_status_list


	def set_double_click_callback(self,
				function : typing.Callable[[QtCore.QModelIndex], None]
			) -> None:
		"""Used to overwrite the current callback when double-clicking on an item.
		E.g. if we first want to try to load the clicked-item, and on fail, do nothing

		NOTE: disconnects any existing connections

		Args:
			function (typing.Callable[[QtCore.QModelIndex], None]): The function to call when double-clicking on an item
				should take a single argument, the index of the double-clicked item
		"""
		if self._double_click_connection is not None:
			self.doubleClicked.disconnect(self._double_click_connection)
		self._double_click_connection = self.doubleClicked.connect(function)

	def _default_on_double_click(self, index: QtCore.QModelIndex) -> None:
		""" Default action when double-clicking on an item in the treeview.
		Set the hightlight-item when double-clicking on an item

		Args:
			index (QtCore.QModelIndex): The double-clicked item
		"""
		cur_id = index.data(RunQueueTableModel.CustomDataRoles.IDRole)
		log.debug(f"Double clicked on index {index.row()} with id {cur_id}")
		cur_model = self.proxy_model.sourceModel()
		if isinstance(cur_model, RunQueueTableModel):
			cur_model.set_highligh_by_id(cur_id)

	# def model(self):
	# 	"""Return the model for this view
	# 	"""
	# 	return self.proxy_model


	def setModel(self, new_model: RunQueueTableModel) -> None:
		"""Set the model for this view

		NOTE: this treeview uses a proxy model, so the passed model is set as the source model of the proxy model
			<this>.getModel() will return the proxy model, not this passed model
		"""
		ret = self.proxy_model.setSourceModel(new_model)
		#Make sure the dataChanged signal is emitted when the source model changes:
		new_model.dataChanged.connect(self.proxy_model.dataChanged) #NOTE: if we don't this, the proxy model won't emit
			# dataChanged signals. This seems to be a bug in Qt, though I could not find a mention of it on 25-06-2023

		return ret
	def confirm_stop_index(self, index : QtCore.QModelIndex) -> None:
		""" Ask user for confirmation to stop the item at the passed index
		Args:
			index (QtCore.QModelIndex): The index to confirm the stop action on
		"""
		msg = QtWidgets.QMessageBox()
		msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
		msg.setText("Are you sure you want to stop this item?")
		msg.setInformativeText("This will force stop the item process - any unsaved progress of this run will be lost.")
		msg.setWindowTitle("Confirm stop")
		msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
		msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
		ret = msg.exec()
		if ret == QtWidgets.QMessageBox.StandardButton.Yes:
			return self.do_action_on_index(RunQueueItemActions.STOP, index)


	def confirm_stop_current_index(self) -> None:
		""" Ask user for confirmation to stop the currently selected item
		"""
		index = self.currentIndex()
		return self.confirm_stop_index(index)



	def custom_menu_requested(self, pos : QtCore.QPoint) -> None:
		"""Create a context menu for the possible actions on the item under the mouse

		Args:
			pos (QtCore.QPoint): The position of the mouse
		"""

		#Get the index of the item under the mouse
		index = self.indexAt(pos)
		#If the index is valid, create a menu
		if not index.isValid():
			return

		possible_actions = index.data(RunQueueTableModel.CustomDataRoles.ActionRole)
		for action in self._action_dict: # pylint: disable=consider-using-dict-items
			if action in possible_actions:
				self._action_dict[action].setVisible(True)
			else:
				self._action_dict[action].setVisible(False)
		self._rc_menu.popup(self.mapToGlobal(pos))

	def do_action_on_index(self, action: RunQueueItemActions, index : QtCore.QModelIndex) -> None:
		"""Do the passed action on the passed index

		NOTE: no safety checks are performed, calling stop on an item will force stop it if it's running
		without asking for user confirmation

		Args:
			action (RunQueueItemActions): The action to perform
			index (QtCore.QModelIndex): The index to perform the action on
		"""
		log.debug(f"Trying to perform action {str(action)} on index {index.row()}")
		# cur_model = self.model()
		if not index.isValid():
			log.info(f"Could not perform action {str(action)} on index {index.row()} - index is invalid")
			return
		try:
			self.model().setData(index, action, RunQueueTableModel.CustomDataRoles.ActionRole)
		except Exception as exception: # pylint: disable=broad-exception-caught
			log.error(f"Failed to perform action {str(action)}: {exception}")
			#Create qt message box with this notification
			msg = QtWidgets.QMessageBox()
			msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
			msg.setText(f"Failed to perform action {str(action)} on selected index ({index.row()})")
			msg.setInformativeText(f"{type(exception).__name__}: {exception}")
			msg.setWindowTitle("Error")
			msg.exec_()

	def do_action_on_selection(self, action: RunQueueItemActions) -> None:
		"""Do the passed action on the currently selected item (singular)

		Args:
			action (RunQueueItemActions): The action to perform
		"""
		log.debug(f"Trying to perform action {str(action)} on selection ({self.currentIndex().row()})")
		index = self.currentIndex()
		if not index.isValid():
			return
		self.do_action_on_index(action, index)
		log.debug("Done performing action on selection")







def run_example_app():
	""" Run an example of the run_queue tree view"""
	#pylint: disable=import-outside-toplevel
	import sys

	from configurun.examples.example_target_function import example_target_function
	app = QtWidgets.QApplication([])
	window = QtWidgets.QMainWindow()
	window.resize(800, 600)
	central_widget = QtWidgets.QWidget()
	window.setCentralWidget(central_widget)
	layout = QtWidgets.QVBoxLayout()
	central_widget.setLayout(layout)

	queue_view = RunQueueTreeView()
	run_queue = RunQueue(
		target_function=example_target_function
	)
	queue_model = RunQueueTableModel(run_queue=run_queue)

	queue_view.setModel(queue_model)
	layout.addWidget(queue_view)

	for i in range(10):
		run_queue.add_to_queue(
			f"Testitem {i}",
			config={"test": i}, #nonsense config #type: ignore
		)

	window.show()
	res = app.exec()
	log.info("Done!")
	sys.exit(res)


if __name__ == "__main__":
	logging.getLogger('matplotlib').setLevel(logging.INFO)
	logging.getLogger('PySide6').setLevel(logging.DEBUG)
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}] {levelname:<7s}   {message}", style='{')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.DEBUG
	) #Without time
	root = logging.getLogger()
	root.handlers = [handler]

	run_example_app()
