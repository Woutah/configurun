"""
Implements the RunQueueTreeView class that is used to display a RunQueue in a Qt-Treeview
"""
import logging
import typing

from PySide6 import QtCore, QtWidgets

from configurun.classes.run_queue import (RunQueueItemActions, RunQueue,
                                      RunQueueItemStatus)
from configurun.windows.models.run_queue_table_model import RunQueueTableModel

log = logging.getLogger(__name__)

class RunQueueTreeView(QtWidgets.QTreeView):
	"""
	Treeview-equivalent used for run-queue items (MLQueueItems)
	"""

	modelChanged = QtCore.Signal(object) #Emits the new model on model-change (should practically always be a MLQueueModel)

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

		self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
		self.customContextMenuRequested.connect(self.custom_menu_requested)


		self.setSortingEnabled(True)

		self._action_dict = {
			RunQueueItemActions.DELETE: self._delete_action,
			RunQueueItemActions.CANCEL: self._cancel_action,
			RunQueueItemActions.MOVEUP: self._move_up_action,
			RunQueueItemActions.MOVEDOWN: self._move_down_action,
			RunQueueItemActions.MOVETOP: self._move_top_action,
			RunQueueItemActions.STOP: self._stop_action
		}

		# =========== Link actions ===========
		for key in self._action_dict: # pylint: disable=consider-using-dict-items
			self._action_dict[key].triggered.connect(lambda *_, action=key : self.do_action_on_selection(action))


		#Connect double-click
		self.doubleClicked.connect(self._on_double_click)

	def _on_double_click(self, index: QtCore.QModelIndex) -> None:
		"""Set the hightlight-item when double-clicking on an item

		Args:
			index (QtCore.QModelIndex): The double-clicked item
		"""
		log.debug(f"Double clicked on index {index.row()}")
		cur_model = self.model()
		if isinstance(cur_model, RunQueueTableModel):
			cur_model.set_highlight_by_index(index)

	def setModel(self, new_model: RunQueueTableModel) -> None:
		"""Set the model for this view """
		super().setModel(new_model)
		# self.model().moveToThread(self.model_thread)
		self.modelChanged.emit(new_model)


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

		#Get the item from the model
		cur_model = self.model()
		if not isinstance(cur_model, RunQueueTableModel):
			return

		possible_actions = cur_model.get_actions(index) #Get the possible actions for this item
		for action in self._action_dict: # pylint: disable=consider-using-dict-items
			if action in possible_actions:
				self._action_dict[action].setVisible(True)
			else:
				self._action_dict[action].setVisible(False)
		self._rc_menu.popup(self.mapToGlobal(pos))


	def do_action_on_selection(self, action: RunQueueItemActions) -> None:
		"""Do the passed action on the currently selected item (singular)

		Args:
			action (RunQueueItemActions): The action to perform
		"""
		log.debug(f"Trying to perform action {str(action)} on selection ({self.currentIndex().row()})")
		cur_model = self.model()
		if isinstance(cur_model, RunQueueTableModel):
			try:
				cur_model.do_action(self.currentIndex(), action)
			except Exception as exception: # pylint: disable=broad-exception-caught
				log.error(f"Failed to perform action {str(action)}: {exception}")
				#Create qt message box with this notification
				msg = QtWidgets.QMessageBox()
				msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
				msg.setText(f"Failed to perform action {str(action)} on selected index ({self.currentIndex().row()})")
				msg.setInformativeText(f"{type(exception).__name__}: {exception}")
				msg.setWindowTitle("Error")
				msg.exec_()
