"""
Implements the RunQueueWidget class which contains a treeview and several buttons to control the underlying queue-model
as well as (indirectly) the underlying RunQueue
"""

import logging

from PySide6 import QtCore, QtGui, QtWidgets
from pyside6_utils.utility.catch_show_exception_in_popup_decorator import \
    catch_show_exception_in_popup_decorator

from configurun.classes.run_queue import RunQueueItemActions
from configurun.windows.models.run_queue_table_model import RunQueueTableModel
from configurun.windows.ui.run_queue_widget_ui import Ui_RunQueueWidget
from configurun.classes.run_queue import RunQueueItemStatus

log = logging.getLogger(__name__)



class RunQueueWidget(QtWidgets.QWidget):
	"""
	A wrapper-widget for a RunQueueTreeView with some buttons to control the queue (start, stop, move up, move down,
	delete,	cancel etc.)
	"""
	def __init__(self, widget : QtWidgets.QWidget) -> None:
		super().__init__()
		self.ui = Ui_RunQueueWidget() #pylint: disable=invalid-name
		self.ui.setupUi(widget)
		self._widget = widget

		self.runQueueTreeView = self.ui.runQueueTreeView #pylint: disable=invalid-name #Make it easier to access treeview

		#=============Link buttons to functions================
		self.ui.MoveUpInQueueBtn.clicked.connect(
			lambda *_: self.runQueueTreeView.do_action_on_selection(RunQueueItemActions.MOVEUP))
		self.ui.MoveDownInQueueBtn.clicked.connect(
			lambda *_: self.runQueueTreeView.do_action_on_selection(RunQueueItemActions.MOVEDOWN))
		self.ui.CancelStopButton.clicked.connect(
			self.cancel_stop_button_pressed)
		self.ui.DeleteButton.clicked.connect(
			lambda *_: self.runQueueTreeView.do_action_on_selection(RunQueueItemActions.DELETE))
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

		self.queue_model_connections = [] #Connections to the queue model for updating the UI
		self._run_queue_table_model : RunQueueTableModel | None = None #The used run-queue model

		self.ui.toolButton.clicked.connect(self.settings_clicked)


	def settings_clicked(self):
		"""Called when a open-settings-button is clicked. Opens the settings menu."""
		cur_mouse_pos = QtGui.QCursor.pos()
		self.popup_queue_settings_context_menu(cur_mouse_pos)

	def get_current_view_filter_menu(self) -> QtWidgets.QMenu:
		"""Returns the current view filter-menu for the queue view. E.g. a checkmark for all statuses that
		are being shown, and none for all statuses that are being filtered out from the tree-view

		Returns:
			QtWidgets.QMenu: The current view filter-settings for the queue view
		"""
		menu = QtWidgets.QMenu()
		cur_filtered = self.runQueueTreeView.get_item_status_filter() #Get all filtered statuses
		for status in RunQueueItemStatus:
			action = QtGui.QAction(status.name, menu)
			action.setCheckable(True)
			action.setChecked(status not in cur_filtered)
			action.triggered.connect(
				lambda *_, status=status: self.runQueueTreeView.set_whether_status_filtered(
					status, not(status in cur_filtered)) #pylint: disable=superfluous-parens
				)
			menu.addAction(action)

		return menu


	def save_to_file_popup(self):
		"""Shows a popup to save the current queue to a file."""
		cur_model = self._run_queue_table_model
		assert isinstance(cur_model, RunQueueTableModel), f"Can't save Queue for non-RunQueueModel of type {type(cur_model)}"
		cur_model.save_to_file_popup()

	def load_from_file_popup(self):
		"""Shows a popup to load a queue from a file."""
		cur_model = self._run_queue_table_model
		assert isinstance(cur_model, RunQueueTableModel), f"Can't load Queue for non-RunQueueModel of type {type(cur_model)}"
		cur_model.load_from_file_popup()


	def get_queue_settings_context_menu(self) -> QtWidgets.QMenu:
		"""Returns the context menu for the current RunQueue, e.g. which items are filtered in the tree view
		and whether the queue is backed up to a file.

		Returns:
			QtWidgets.QMenu: The context menu for the current RunQueue
		"""
		menu = QtWidgets.QMenu()
		# filter_menu = menu.addMenu("View Filter")
		filter_menu = self.get_current_view_filter_menu()
		filter_menu.setTitle("View Filter")
		filter_menu.setIcon(QtGui.QIcon(":/Icons/icons/actions/filter.png"))
		menu.addMenu(filter_menu)


		backup_action = menu.addAction("Backup...")
		backup_action.setIcon(QtGui.QIcon(":/Icons/icons/actions/document-save-as.png"))
		cur_model = self._run_queue_table_model
		if cur_model is not None:
			backup_action.triggered.connect(self.save_to_file_popup)
		else:
			backup_action.setEnabled(False)


		load_action = menu.addAction("Load...")
		load_action.setIcon(QtGui.QIcon(":/Icons/icons/actions/document-open.png"))
		if cur_model is not None:
			load_action.triggered.connect(self.load_from_file_popup)
		else:
			load_action.setEnabled(False)

		n_processes_action = menu.addAction("Set number of processes...")
		n_processes_action.setIcon(QtGui.QIcon(":/Icons/icons/status/network-receive.png"))
		n_processes_action.triggered.connect(self.set_n_processes_popup)

		return menu

	def set_n_processes_popup(self):
		"""Shows a popup to set the number of processes to use in the run queue."""
		#Ask user for integer
		#Set number of processes to that integer

		if self._run_queue_table_model is None:
			QtWidgets.QMessageBox.warning(
				self._widget,
				"Can't set number of processes",
				"Can't set number of processes, as RunQueueModel is not set"
			)
			return
		cur_n_processes = self._run_queue_table_model.get_n_processes()


		integer, pressed_ok = QtWidgets.QInputDialog.getInt(
			self._widget,
			"Set number of processes",
			f"Set Number of processes: <br>current={cur_n_processes} unlimited=-1",
			value=cur_n_processes,
			minValue=-1,
			maxValue=30,
			step=1
		)
		if pressed_ok:
			self._run_queue_table_model.set_n_processes(integer)

	def popup_queue_settings_context_menu(self, global_position : QtCore.QPoint) -> None:
		"""Creates a menu with settings for the queue and shows it at the given position.
		e.g. filter by status.

		Args:
			global_position (QtCore.QPoint): The position to show the menu at.
		"""
		menu = self.get_queue_settings_context_menu()
		menu.exec(global_position)



	def cancel_stop_button_pressed(self):
		"""Either cancels or stops the currently selected item in the queue, depending on its status
		"""
		# cur_model = self.queue_view.model()
		# assert isinstance(cur_model, RunQueueTableModel), "Can't get options for non-MLQueueModel"
		selection = self.runQueueTreeView.currentIndex()

		actions = selection.data(RunQueueTableModel.CustomDataRoles.ActionRole)
		if RunQueueItemActions.STOP in actions:
			# self.queue_view.do_action_on_index(RunQueueItemActions.STOP, selection)
			self.runQueueTreeView.confirm_stop_index(selection)
		else:
			self.runQueueTreeView.do_action_on_index(RunQueueItemActions.CANCEL, selection)



	def _autoqueue_btn_set_state(self, is_running : bool):
		"""Set the state of the autoqueue button (start/stop autoqueueing)"""
		self.ui.StartRunningQueueBtn.setChecked(is_running)
		self.ui.StartRunningQueueBtn.setToolTip("Stop autorunning" if is_running else "Start autorunning")

	@catch_show_exception_in_popup_decorator
	def toggle_queue_autoprocessing(self):
		"""Toggles the queue autoprocessing."""
		cur_model = self._run_queue_table_model
		assert isinstance(cur_model, RunQueueTableModel)


		autoprocessing_enabled = cur_model.is_autoprocessing_enabled()
		self._autoqueue_btn_set_state(autoprocessing_enabled)

		if autoprocessing_enabled:
			if cur_model.get_running_configuration_count() <= 0:
				cur_model.stop_autoprocessing()
				self._autoqueue_btn_set_state(False) #Set button state to false TODO: intermediary state when stopping?
				return
			else:
				confirm_dialog = QtWidgets.QMessageBox()
				#Creat a dialog with "Wait for processes to finish" and "Force Stop" and "Cancel" buttons
				confirm_dialog = QtWidgets.QMessageBox()
				confirm_dialog.setText("You are about to stop the autoprocessing process, do you want to cancel all "
			   		"currently running processes as well?")
				#Create a dialog with "Wait for processes to finish" and "Force Stop" and "Cancel" buttons
				#If "Wait and Stop" is pressed, stop autoqueueing
				#If "Force Stop" is pressed, stop all items currently running in the queue and stop autoqueueing
				#If "Cancel" is pressed, do nothing
				stop_autoqueue_btn = \
					confirm_dialog.addButton("Stop Autoqueueing", QtWidgets.QMessageBox.ButtonRole.AcceptRole) #0
				force_stop_btn = \
					confirm_dialog.addButton("Force Stop All", QtWidgets.QMessageBox.ButtonRole.NoRole) #1
				cancel_btn = \
					confirm_dialog.addButton("Cancel", QtWidgets.QMessageBox.ButtonRole.RejectRole) #2

				#Set default button to "Wait and Stop"
				confirm_dialog.setDefaultButton(stop_autoqueue_btn)

				confirm_dialog.setWindowTitle("Stop queue?")
				confirm_dialog.setWindowIcon(QtGui.QIcon("resources/icons/icon.ico"))
				confirm_dialog.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
				confirm_dialog.show()
				confirm_dialog.activateWindow()
				confirm_dialog.exec()


				if confirm_dialog.clickedButton() == cancel_btn: #If cancel is pressed (third button = index 2)
					return
				elif confirm_dialog.clickedButton() == stop_autoqueue_btn: #If wait stop
					cur_model.stop_autoprocessing()
					self._autoqueue_btn_set_state(False) #Set button state to false
					return
				elif confirm_dialog.clickedButton() == force_stop_btn:
					#1 last check if user really wants to force stop (use one-liner messagebox here)
					confirm_window = QtWidgets.QMessageBox()
					confirm_window.setText("<b>Are you sure you want to force stop all currently running processes?</b>")
					confirm_window.setInformativeText("This will forcefully stop all currently running processes. "
						"All unsaved progress will be lost. This action cannot be undone.")
					confirm_window.setWindowTitle("Force stop?")

					confirm_window.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes
						| QtWidgets.QMessageBox.StandardButton.No)
					confirm_window.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
					if confirm_window.exec() == QtWidgets.QMessageBox.StandardButton.No:
						return
					cur_model.force_stop_all_running()
		else:
			cur_model.start_autoprocessing()

	def set_model(self, model : RunQueueTableModel):
		"""Resets all signals and connections and invalidates the current data in the view.
		"""
		assert isinstance(model, RunQueueTableModel), "Can't set non-MLQueueModel as model"
		if len(self.queue_model_connections) > 0:
			for signal_connection in self.queue_model_connections:
				signal_connection.disconnect()
			self.queue_model_connections = []

		# cur_model = self.queue_view.model()
		self.runQueueTreeView.setModel(model)
		self._run_queue_table_model = model

		if not isinstance(model, RunQueueTableModel):
			self.update_available_options()
			log.warning("MLQueueWidget: Model is not of type MLQueueModel. Cannot setup new model.")
			return

		self.queue_model_connections.append( #When any data changes, update the available options
			model.dataChanged.connect(lambda *_: self.update_available_options())
		)

		#=============== Subscribe to signals =================
		self.queue_model_connections.append(
			model.layoutChanged.connect(lambda *_: self.update_available_options())
		) #When any rows are removed, update the available options (maybe selected item changed)
		self.queue_model_connections.append(
			self.runQueueTreeView.selectionModel().selectionChanged.connect(lambda *_: self.update_available_options())
		) #When the selection changes, update the available options
		self.queue_model_connections.append(
			self.runQueueTreeView.selectionModel().currentChanged.connect(lambda *_: self.update_available_options())
		) #When the selection changes, update the available options
		self.queue_model_connections.append(
			model.autoProcessingStateChanged.connect(self._autoqueue_btn_set_state)
		)

		self._autoqueue_btn_set_state(model.is_autoprocessing_enabled())
		self.update_available_options()


	@catch_show_exception_in_popup_decorator
	def force_stop_queue(self):
		""" Stops the auto-requeueing of items in the RunQueue """
		raise NotImplementedError("MLQueueWidget: stop_queue not implemented yet")

	def update_available_options(self):
		""" Updates the available options in the user interface. """
		index = self.runQueueTreeView.currentIndex()
		# log.debug(f"Updating available options for selection {index}")
		if not index.isValid():
			cur_available_actions = []
		else:
			cur_available_actions = index.data(RunQueueTableModel.CustomDataRoles.ActionRole) #Retrieve the available actions


		for btn in self._action_btn_dict.values():
			btn.setEnabled(False)

		if cur_available_actions is not None:
			for action in cur_available_actions:
				if action in self._action_btn_dict:
					self._action_btn_dict[action].setEnabled(True)




def run_example_app():
	""" Run an example of the run_queue widget with some nonsense data and the example run function"""
	#pylint: disable=import-outside-toplevel
	from configurun.examples.example_target_function import example_target_function
	from configurun.classes.run_queue import RunQueue

	app = QtWidgets.QApplication([])
	window = QtWidgets.QMainWindow()
	window.resize(800, 600)
	central_widget = QtWidgets.QWidget()

	queue_widget = RunQueueWidget(central_widget)
	run_queue = RunQueue(
		target_function=example_target_function
	)
	queue_model = RunQueueTableModel(run_queue=run_queue)

	queue_widget.set_model(queue_model)

	for i in range(10):
		run_queue.add_to_queue(
			f"Testitem {i}",
			config={"test": i}, #nonsense config #type:ignore
		)

	window.setCentralWidget(central_widget)

	window.show()
	app.exec()


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
