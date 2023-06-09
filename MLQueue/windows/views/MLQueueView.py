
from PySide6 import QtWidgets, QtCore, QtGui
import typing
from MLQueue.windows.models.MLQueueModel import MLQueueModel
from MLQueue.classes.RunQueue import RunQueue, RunQueueItemStatus, QueueItemActions
import logging
log = logging.getLogger(__name__)

class MLQueueView(QtWidgets.QTreeView):

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

		# self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
		# self.customContextmenuRequested.connect(self._context_menu.popup)
		# self.customContextMenuRequested.triggered.connect(lambda *x : print('kaas'))
		self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
		self.customContextMenuRequested.connect(self.customMenuRequested)


		self.setSortingEnabled(True)
		
		self._action_dict = {
			QueueItemActions.Delete: self._delete_action,
			QueueItemActions.Cancel: self._cancel_action,
			QueueItemActions.MoveUp: self._move_up_action,
			QueueItemActions.MoveDown: self._move_down_action,
			QueueItemActions.MoveTop: self._move_top_action,
			QueueItemActions.Stop: self._stop_action
		}

		# =========== Link actions ===========
		for key in self._action_dict.keys():
			self._action_dict[key].triggered.connect(lambda *_, action=key : self.doActionOnSelection(action))

		
		#Connect double-click
		self.doubleClicked.connect(self._on_double_click)

	def _on_double_click(self, index: QtCore.QModelIndex) -> None:
		log.debug(f"Double clicked on index {index.row()}")
		model = self.model()
		if type(model) is MLQueueModel:
			model.setHighlightIdByIndex(index)

	def setModel(self, model: MLQueueModel) -> None:
		super().setModel(model)
		# self.model().moveToThread(self.model_thread)
		self.modelChanged.emit(model)


	def customMenuRequested(self, pos):
		#Get the index of the item under the mouse
		index = self.indexAt(pos)
		#If the index is valid, create a menu
		if not index.isValid():
			return

		#Get the item from the model
		model = self.model()
		if not isinstance(model, MLQueueModel):
			return
		
		possible_actions = model.get_actions(index) #Get the possible actions for this item
		for action in self._action_dict.keys():
			if action in possible_actions:
				self._action_dict[action].setVisible(True)
			else:
				self._action_dict[action].setVisible(False)
		self._rc_menu.popup(self.mapToGlobal(pos))


	def doActionOnSelection(self, action: QueueItemActions) -> None:
		log.debug(f"Trying to perform action {action.__str__()} on selection ({self.currentIndex().row()})")
		model = self.model()
		if isinstance(model, MLQueueModel):
			try:
				model.do_action(self.currentIndex(), action)
			except Exception as e:
				log.error(f"Failed to perform action {action.__str__()}: {e}")
				#Create qt message box with this notification
				msg = QtWidgets.QMessageBox()
				msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
				msg.setText(f"Failed to perform action {action.__str__()} on selected index ({self.currentIndex().row()})")
				msg.setInformativeText(f"{type(e).__name__}: {e}")
				msg.setWindowTitle("Error")
				msg.exec_()


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
	run_queue._queue.remove(4)
	run_queue._all_dict[4].status = RunQueueItemStatus.Running
	run_queue.add_to_queue("ItemFinished", "TheConfig")
	run_queue._all_dict[5].status = RunQueueItemStatus.Finished
	run_queue._queue.remove(5)
	run_queue.add_to_queue("ItemCancelled", "TheConfig")
	run_queue._all_dict[6].status = RunQueueItemStatus.Stopped
	run_queue._queue.remove(6)
	run_queue.add_to_queue("ItemFailed", "TheConfig")
	run_queue._all_dict[7].status = RunQueueItemStatus.Failed
	
	run_queue._queue.remove(7)

	app = QtWidgets.QApplication([])
	model = MLQueueModel(run_queue)
	# view = QtWidgets.QTableView()
	view = MLQueueView()
	view.setModel(model)
	view.show()
	view.resize(1200, 400)
	app.exec()
	