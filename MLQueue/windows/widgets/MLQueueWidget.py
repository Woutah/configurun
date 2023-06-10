from PySide6 import QtWidgets, QtGui, QtCore
from MLQueue.windows.ui.MLQueueWidget_ui import Ui_MLQueueWidget
from MLQueue.windows.views.RunQueueTreeView import RunQueueTreeView
from MLQueue.windows.models.RunQueueTableModel import RunQueueTableModel
from MLQueue.classes.RunQueue import RunQueue, RunQueueItemStatus, RunQueueItemActions
import logging
log = logging.getLogger(__name__)

from PySide6Widgets.Utility.catchExceptionInMsgBoxDecorator import catchExceptionInMsgBoxDecorator

class MLQueueWidget(QtWidgets.QWidget):
	"""
	A wrapper-widget for a MLQueueView with some buttons to control the queue (start, stop, move up, move down, delete,
	cancel etc.)
	"""
	def __init__(self, widget) -> None:
		super().__init__()
		self.ui = Ui_MLQueueWidget()
		self.ui.setupUi(widget)

		# self.ui.QueueViewLayout.addWidget(self.queue_view)
		self.queue_view = self.ui.queueView

		#=============Link buttons to functions================
		self.ui.MoveUpInQueueBtn.clicked.connect(
			lambda *_: self.queue_view.do_action_on_selection(RunQueueItemActions.MOVEUP))
		self.ui.MoveDownInQueueBtn.clicked.connect(
			lambda *_: self.queue_view.do_action_on_selection(RunQueueItemActions.MOVEDOWN))
		self.ui.CancelStopButton.clicked.connect(
			lambda *_: self.queue_view.do_action_on_selection(RunQueueItemActions.STOP))
		self.ui.DeleteButton.clicked.connect(
			lambda *_: self.queue_view.do_action_on_selection(RunQueueItemActions.DELETE))
		self.ui.StartRunningQueueBtn.clicked.connect(
			self.toggle_queue_autoprocessing)

		self._action_btn_dict = {
			RunQueueItemActions.MOVEUP: self.ui.MoveUpInQueueBtn,
			RunQueueItemActions.MOVEDOWN: self.ui.MoveDownInQueueBtn,
			RunQueueItemActions.CANCEL: self.ui.CancelStopButton, #TODO: is it a good idea to have cancel and stop be the
			 # same button? Maybe make difference more apparent to user
			 # (cancel = dequeue, stop = stop if currently running and dequeue)
			RunQueueItemActions.STOP: self.ui.CancelStopButton,
			RunQueueItemActions.DELETE: self.ui.DeleteButton
		}

		self.queueItemsChangedOptionConnections = []
		self.queue_view.modelChanged.connect(lambda *_: self.setupNewmodel())

	def _queue_run_btn_set_state(self, is_running : bool):
		self.ui.StartRunningQueueBtn.setChecked(is_running)
		self.ui.StartRunningQueueBtn.setToolTip("Stop queue" if is_running else "Start running queue")

	@catchExceptionInMsgBoxDecorator
	def toggle_queue_autoprocessing(self, confirm_on_stop: bool = True):
		model = self.queue_view.model()
		assert(type(model) == RunQueueTableModel)
		if model._run_queue is None:
			return

		self._queue_run_btn_set_state(model._run_queue.is_autoprocessing_enabled())

		if model._run_queue.is_autoprocessing_enabled():
			if model._run_queue.get_running_configuration_count() <= 0:
				model._run_queue.stop_autoqueueing()
				self._queue_run_btn_set_state(False) #Set button state to false TODO: intermediary state when stopping?
				return
			else:
				confirm_dialog = QtWidgets.QMessageBox()
				#Creat a dialog with "Wait for processes to finish" and "Force Stop" and "Cancel" buttons
				confirm_dialog = QtWidgets.QMessageBox()
				confirm_dialog.setText("Are you sure you want to stop the queue? This will cancel all currently \
			   		running tasks.")
				#Creat a dialog with "Wait for processes to finish" and "Force Stop" and "Cancel" buttons
				#If "Wait and Stop" is pressed, wait for processes to finish and then stop queue
				#If "Force Stop" is pressed, stop queue immediately
				#If "Cancel" is pressed, do nothing
				stop_autoqueue_btn = \
					confirm_dialog.addButton("Stop Autoqueueing", QtWidgets.QMessageBox.ButtonRole.AcceptRole) #0
				confirm_dialog.addButton("Force Stop All", QtWidgets.QMessageBox.ButtonRole.RejectRole) #1
				confirm_dialog.addButton("Cancel", QtWidgets.QMessageBox.ButtonRole.NoRole) #2

				#Set default button to "Wait and Stop"
				confirm_dialog.setDefaultButton(stop_autoqueue_btn)

				confirm_dialog.setWindowTitle("Stop queue?")
				confirm_dialog.setWindowIcon(QtGui.QIcon("resources/icons/icon.ico"))
				confirm_dialog.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
				confirm_dialog.show()
				confirm_dialog.activateWindow()
				confirm_dialog.exec()


				if confirm_dialog.result() == 2: #If cancel is pressed (third button = index 2)
					return
				elif confirm_dialog.result() == 0: #If wait stop
					model._run_queue.stop_autoqueueing()
					self._queue_run_btn_set_state(False) #Set button state to false  #TODO: lock this to signal only
					return

			raise NotImplementedError("Stopping queue not implemented yet")
			#TODO: cancel all currently running tasks
			#TODO: save queue to file

		else:
			model._run_queue.start_autoprocessing()

	def setupNewmodel(self):

		if len(self.queueItemsChangedOptionConnections) > 0:
			for connection in self.queueItemsChangedOptionConnections:
				connection.disconnect()
			self.queueItemsChangedOptionConnections = []

		model = self.queue_view.model()

		if type(model) != RunQueueTableModel:
			self.update_available_options()
			log.warning("MLQueueWidget: Model is not of type MLQueueModel. Cannot setup new model.")
			return

		self.queueItemsChangedOptionConnections.append( #When any data changes, update the available options
			model.dataChanged.connect(lambda *_: self.update_available_options())
		)

		self.queueItemsChangedOptionConnections.append(
			model.layoutChanged.connect(lambda *_: self.update_available_options())
		) #When any rows are removed, update the available options (maybe selected item changed)
		self.queueItemsChangedOptionConnections.append(
			self.queue_view.selectionModel().selectionChanged.connect(lambda *_: self.update_available_options())
		) #When the selection changes, update the available options
		self.queueItemsChangedOptionConnections.append(
			self.queue_view.selectionModel().currentChanged.connect(lambda *_: self.update_available_options())
		) #When the selection changes, update the available options
		self.queueItemsChangedOptionConnections.append(
			model._run_queue.autoProcessingStateChanged.connect(self._queue_run_btn_set_state)
		)

		self.update_available_options()


	@catchExceptionInMsgBoxDecorator
	def stop_autoqueue(self):
		""" Stops the auto-requeueing of items in the RunQueue """
		raise NotImplementedError("MLQueueWidget: stop_queue not implemented yet")

	def update_available_options(self):
		""" Updates the available options in the user interface. """
		try:
			selection = self.queue_view.selectionModel().selectedRows()
		except AttributeError as attr_ex: #If no model is set
			log.debug(f"Could not get selection: {attr_ex}")
			return

		cur_available_actions = []
		if len(selection) > 0: #If there is a selection
			selection = selection[0] #Only allow one selection at a time (TODO: maybe change this?)
			try:
				model = self.queue_view.model()
				assert(isinstance(model, RunQueueTableModel))
				cur_available_actions = model.get_actions(selection)
			except AttributeError as attr_ex:
				log.debug(f"Could not get available actions: {attr_ex}")
				cur_available_actions = []

		for btn in self._action_btn_dict.values():
			btn.setEnabled(False)

		for action in cur_available_actions:
			if action in self._action_btn_dict:
				self._action_btn_dict[action].setEnabled(True)




if __name__ == "__main__":
	import sys
	import datetime
	app = QtWidgets.QApplication(sys.argv)
	widget = QtWidgets.QWidget()
	ui = MLQueueWidget(widget)



	run_queue = RunQueue()
	run_queue.add_to_queue("Item1", "TheConfig")
	run_queue.add_to_queue("Item2", "TheConfig")
	run_queue.add_to_queue("Item3", "TheConfig")
	run_queue.add_to_queue("Item4", "TheConfig")
	run_queue.add_to_queue("ItemRunning", "TheConfig")

	run_queue._all_dict[0].dt_started = datetime.datetime.now()
	run_queue._all_dict[1].dt_started = datetime.datetime.now()
	# run_queue._queue.remove(4)
	# run_queue.all_dict[4].status = RunQueueItemStatus.Running
	# run_queue.add_to_queue("ItemFinished", "TheConfig")
	# run_queue.all_dict[5].status = RunQueueItemStatus.Finished
	# run_queue._queue.remove(5)
	# run_queue.add_to_queue("ItemCancelled", "TheConfig")
	# run_queue.all_dict[6].status = RunQueueItemStatus.Stopped
	# run_queue._queue.remove(6)
	# run_queue.add_to_queue("ItemFailed", "TheConfig")
	# run_queue.all_dict[7].status = RunQueueItemStatus.Failed
	# run_queue._queue.remove(7)
	model = RunQueueTableModel(run_queue)


	ui.queue_view.setModel(model)





	widget.show()
	sys.exit(app.exec())
