"""
Contains the ApplyMachineLearningWindow class, which is a window which provides the user with several tools to
edit/manage/run machine learning settings.

Also contains OptionsSource, which is used to determine if the current file should be saved to a file or to the queue.
"""

import logging

log = logging.getLogger(__name__)
if __name__ == "__main__":
	logging.getLogger('matplotlib').setLevel(logging.INFO)
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}] {levelname:<7s}   {message}", style='{')
	log.propagate = False
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.DEBUG) #Without time

import os
import typing
from enum import Enum

# import PySide6Widgets.Widgets
import PySide6Widgets.Models.FileExplorerModel
from MachineLearning.framework.options.options import Options
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6Widgets.Utility.catchExceptionInMsgBoxDecorator import \
    catchExceptionInMsgBoxDecorator
from PySide6Widgets.Utility.DataClassEditorsDelegate import \
    DataClassEditorsDelegate

from MLQueue.classes.RunQueue import RunQueue
from MLQueue.windows.models.MLQueueModel import MLQueueModel
from MLQueue.windows.models.RunQueueConsoleModel import RunQueueConsoleModel
from MLQueue.windows.ui.ApplyMachineLearningWindow_ui import \
    Ui_ApplyMachineLearningWindow
from MLQueue.windows.widgets.MLQueueWidget import MLQueueWidget

SETTINGS_PATH_MACHINE_LEARNING_WINDOW = "/Settings/MachineLearning"

class OptionsSource(Enum):
	"""
	Source of the options. Used to determine whether the options should be saved to a file or to the queue.
	"""
	FILE = 0
	QUEUE = 1



class ApplyMachineLearningWindow():
	"""
	A QT window which provides the user with several tools to edit/manage/run machine learning settings.
	"""
	#A controller to manage the machine learning window
	def __init__(self, run_queue : RunQueue, window : QtWidgets.QMainWindow) -> None:
		self.ui = Ui_ApplyMachineLearningWindow() # pylint: disable=C0103
		self.ui.setupUi(window)

		self.window = window
		self._cur_source = None
		self._default_splitter_states = {
			splitter.objectName() : splitter.saveState() \
				for splitter in self.ui.splitter.findChildren(QtWidgets.QSplitter)
		} #Save all splitter states (to be able to reset them later)
		#====================== Base variables ===================
		self.set_run_queue(run_queue)
		self.ml_queue_widget = MLQueueWidget(self.ui.MLQueueWidget) #Create queue-interface with buttons

		self.ml_queue_widget.queue_view.setModel(self.ml_queue_model)

		# self._cur_path = None
		self._default_save_path = SETTINGS_PATH_MACHINE_LEARNING_WINDOW
		self._config_file_picker_model = PySide6Widgets.Models.FileExplorerModel.FileExplorerModel(
			allow_select_files_only=True)


		#Loop over all splitters in the window and set the sizes to the saved sizes
		self._treeviews = { #For easy looping over all treeviews
			"main_options" : self.ui.mainOptionsTreeView,
			"general_options" : self.ui.generalOptionsTreeView,
			"model_options" : self.ui.modelOptionsTreeView,
			"dataset_options" : self.ui.datasetOptionsTreeView,
			"training_options" : self.ui.trainingOptionsTreeView
		}

		#========================= load settings =========================
		self._settings = QtCore.QSettings("MLTools", "AllSettingsWindow")
		self._font_point_size = int(
			self._settings.value("font_size", 0, type=int) #type: ignore #If zero->set to system default
		)
		self.set_font_point_size(self._font_point_size)
		self.window.restoreGeometry(self._settings.value(
			"window_geometry", self.window.saveGeometry(), type=QtCore.QRect)) # type: ignore
		self.window.restoreState(self._settings.value("window_state", self.window.windowState())) # type: ignore


		self._cur_file_path = str(self._settings.value("loaded_file_path", None))#The path to the current config. None
			#if no config is loaded from file. If set, the config will be saved to this path when the save button is
			# pressed.

		# for splitter in self.window.findChildren(QtWidgets.QSplitter):
		# 	splitter.restoreState(self._settings.value(f"splitter_state_{splitter.objectName()}", splitter.saveState()))

		#====================== Suboptions window and automatic updating ===================
		for treeview in self._treeviews.values(): #Set item delegate for all treeviews
			treeview.setItemDelegate(DataClassEditorsDelegate())
			treeview.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents) # type: ignore

		self._options = Options(use_cache=True, use_undo_stack=True)

		view_model_list : typing.List[typing.Tuple[QtWidgets.QTreeView, QtCore.QSortFilterProxyModel]]=  [
			(self.ui.mainOptionsTreeView, self._options.getMainOptionsProxyModel()),
			(self.ui.generalOptionsTreeView, self._options.getGeneralOptionsProxyModel()),
			(self.ui.modelOptionsTreeView, self._options.getModelOptionsProxyModel()),
			(self.ui.datasetOptionsTreeView, self._options.getDatasetOptionsProxyModel()),
			(self.ui.trainingOptionsTreeView, self._options.getTrainingOptionsProxyModel())
		]

		for (cur_view, cur_model) in view_model_list:
			cur_view.setModel(cur_model)

		self._options.getMainOptionsProxyModel().sourceModelChanged.connect(
			lambda *_: self.tree_view_source_model_changed(
				"main_options",
				self.ui.mainOptionsTreeView,
				self._options.getMainOptionsProxyModel())
		)
		self._options.getGeneralOptionsProxyModel().sourceModelChanged.connect(
			lambda *_: self.tree_view_source_model_changed(
				"general_options",
				self.ui.generalOptionsTreeView,
				self._options.getGeneralOptionsProxyModel())
		)
		self._options.getModelOptionsProxyModel().sourceModelChanged.connect(
			lambda *_: self.tree_view_source_model_changed(
				"model_options",
				self.ui.modelOptionsTreeView,
				self._options.getModelOptionsProxyModel())
		)
		self._options.getDatasetOptionsProxyModel().sourceModelChanged.connect(
			lambda *_: self.tree_view_source_model_changed(
				"dataset_options",
				self.ui.datasetOptionsTreeView,
				self._options.getDatasetOptionsProxyModel())
		)
		self._options.getTrainingOptionsProxyModel().sourceModelChanged.connect(
			lambda *_: self.tree_view_source_model_changed(
				"training_options",
				self.ui.trainingOptionsTreeView,
				self._options.getTrainingOptionsProxyModel())
		)


		self._config_file_picker_model.setReadOnly(False)
		log.debug(f"Root path used for saving machine learning settings: {SETTINGS_PATH_MACHINE_LEARNING_WINDOW}")
		self._config_file_picker_model.setRootPath(QtCore.QDir.rootPath()) #Subscribe to changes in this path
		self.ui.ConfigFilePickerView.setModel(self._config_file_picker_model)
		self.ui.ConfigFilePickerView.setRootIndex(
			self._config_file_picker_model.index(SETTINGS_PATH_MACHINE_LEARNING_WINDOW)
		)

		self.ui.ConfigFilePickerView.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents) #type: ignore


		#Disable shortcuts for the file picker
		# self.ui.ConfigFilePickerView.actionRedo.setShortcutContext(QtCore.Qt.WidgetShortcut) #File picker context
		# self.ui.ConfigFilePickerView.actionUndo.setShortcutContext(QtCore.Qt.WidgetShortcut) #File picker context


		#======== Open a window which shows the undo/redo stack ========
		if self._options.undo_stack:
			self.ui.undoView.setStack(self._options.undo_stack)

		#Un undo-stack change, change the title of the window with a * to indicate that the file has been changed
		if self._options.undo_stack:
			self._options.undo_stack.cleanChanged.connect(
				lambda: self.window.setWindowModified(not self._options.undo_stack.isClean()) #type:ignore
			)

		#Link close-event to a confirmation box
		self.window.closeEvent = self.close_event


		self._hightlight_changed_signal = self._config_file_picker_model.highlightPathChanged.connect(
			self._config_file_picker_model_highlight_path_changed)

		#============= Post-load settings =============
		self.load_from_file(self._cur_file_path) #Attempt to load from file

		#==================Console ================
		self._console_item_model = RunQueueConsoleModel()
		self._console_item_model.setRunQueue(self._run_queue)
		self.ui.consoleWidget.setModel(self._console_item_model)

		#Connect right click on console-widget to a context menu
		self.ui.consoleWidget.ui.fileSelectionTableView.setContextMenuPolicy(
			QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
		self.ui.consoleWidget.ui.fileSelectionTableView.customContextMenuRequested.connect(
			self.create_console_context_menu
		)


		#======================== Actions/Shortcuts ========================
		self.ui.OpenFileLocationBtn.clicked.connect(self.open_save_location_in_explorer)

		self.ui.actionUndo.triggered.connect(self.undo_triggered)
		self.ui.actionRedo.triggered.connect(self.redo_triggered)
		self.ui.saveCurrentConfigAsBtn.clicked.connect(self.save_config_as_triggered)
		self.ui.saveCurrentConfigBtn.clicked.connect(self.save_config_triggered)

		self.ui.addToQueueButton.clicked.connect(self.add_to_queue_triggered)
		self.ui.actionIncreaseFontSize.triggered.connect(
			lambda *_: self.set_font_point_size(min(96, self._font_point_size + 1)) #type: ignore
		) #This should be more than enough
		self.ui.actionDecreaseFontSize.triggered.connect(
			lambda *_: self.set_font_point_size(max(3, self._font_point_size - 1)) #type: ignore
		)
		self.ui.actionDefaultFontSize.triggered.connect(
			lambda *_: self.set_font_point_size(0) #0 makes it so that the system default is used
		)

		self.ui.actionSave.triggered.connect(self.save_config_triggered)
		self.ui.actionSave_As.triggered.connect(self.save_config_as_triggered)
		self.ui.actionReset_Splitters.triggered.connect(self.reset_splitter_states)


	def create_console_context_menu(self, pos):
		"""Create a context menu at the provided position, displaying all ignored ids. When clicked, un-ignore the id
		and reload the model.

		Args:
			pos (): The local position of the mouse click (sent from self.ui.ConsoleWidget.ui.fileSelectionTableView)
		"""
		ignored_ids = self._console_item_model.get_ignored_ids()

		#Create a context menu with all ids, when clicked, un-ignore the id
		menu = QtWidgets.QMenu()
		#Add text "Re-show ignored ids" to the menu, followed by a splitter
		if len(ignored_ids) == 0:
			action = menu.addAction("(No ignored ids)")
			action.setEnabled(False)
		for cur_id in ignored_ids:
			log.info(f"Ignored ids {ignored_ids} - currently adding item {cur_id} to menu")
			action = menu.addAction(f"(Re)show item: {cur_id}")
			action.triggered.connect(lambda id=int(cur_id): self._console_item_model.un_ignore_id(int(id)))
		menu.exec(self.ui.consoleWidget.ui.fileSelectionTableView.mapToGlobal(pos))

	def set_run_queue(self, run_queue : RunQueue):
		"""Sets a new runqueue. Indicates that all models need to reload their data.

		Args:
			run_queue (RunQueue): the new runQueue
		"""
		self._run_queue = run_queue
		self.ml_queue_model = MLQueueModel(self._run_queue)

	def update_ui_by_connection_state(self, new_connection_state : bool) -> None:
		"""Updates the UI based on the connection state (disabled certain buttons, etc).
		Should only be called when runmode is set to network. When running locally - disconnects cannot happen.
		TODO: also put a "reconnect" button in front of the UI?

		Args:
			new_connection_state (bool): The new connection
		"""

		if not new_connection_state:
			self.ui.MLQueueWidget.setOverlayHidden(False)
			self.ui.ConsoleOverlayWidget.setOverlayHidden(False)
		else:
			self.ui.MLQueueWidget.setOverlayHidden(True)
			self.ui.ConsoleOverlayWidget.setOverlayHidden(True)


	def tree_view_source_model_changed(
			self,
			tree_name : str,
			tree_view : QtWidgets.QTreeView,
			proxy_model : QtCore.QSortFilterProxyModel
		):
		"""
		Slot that should be called when the source model of the treeview has changed.
		#TODO: Should restore the tree-expand state and the selection state of the treeview.
		"""
		# pylint: disable=unused-argument
		# print(f"Source model changed for treeview {tree_view.objectName()} ({tree_name})")
		# if tree_view is None:
		# 	print("Tree is none")
		# 	return

		return




	def reset_splitter_states(self):
		"""
		Resets the state of all splitters to the default state
		"""
		for splitter in self.window.findChildren(QtWidgets.QSplitter):
			if splitter.objectName() in self._default_splitter_states.keys():
				splitter.restoreState(self._default_splitter_states[splitter.objectName()])

	def set_font_point_size(self, new_font_size : int) -> None:
		"""
		Set the point size of the font used in this window.
		Args:
			new_font_size (int): The new font size
		"""
		the_window = self.window
		new_font = the_window.font()
		self._font_point_size = new_font_size
		if new_font_size == 0:#Use system default
			self._font_point_size = QtGui.QFont().pointSize()

		new_font.setPointSize(self._font_point_size)
		the_window.setFont(new_font)
		log.info(f"Set font point size to {self._font_point_size}")


	def _save_settings(self) ->None:
		log.info("Saving settings")
		self._settings.setValue("window_geometry", self.window.saveGeometry())
		self._settings.setValue("window_state", self.window.saveState())
		self._settings.setValue("font_size", self._font_point_size)
		self._settings.setValue("loaded_file_path", self._cur_file_path
			  if self._cur_source == OptionsSource.FILE else None) #Only save the path if it was loaded from a file
		for tree_view_name, tree_view in self._treeviews.items():
			self._settings.setValue(f"{tree_view_name}_geometry", tree_view.geometry())


		for splitter in self.window.findChildren(QtWidgets.QSplitter): #Save the state of all splitters
			self._settings.setValue(f"splitter_state_{splitter.objectName()}", splitter.saveState())




	def open_save_location_in_explorer(self) -> None:
		"""
		Open the folder containing the current config file in the file explorer
		"""
		index = self.ui.ConfigFilePickerView.currentIndex()
		if index.isValid():
			file_path = self._config_file_picker_model.filePath(index)
			if os.path.isfile(file_path):
				file_path = os.path.dirname(file_path)
			QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(file_path))
		else:
			QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(SETTINGS_PATH_MACHINE_LEARNING_WINDOW))


	def load_from_file(self, new_path : str, show_dialog_on_problem=True) -> bool:
		"""Loads the config from a file

		Args:
			new_path (str): The new path from which to load the config
			show_dialog_on_problem (bool, optional): Whether to show a dialog when there are problems. Defaults to True.

		Returns:
			bool: Whether loading a config was succesful NOTE: still returns True if the passed file was already loaded,
			  also return True if there were problems, returns false if an unhandled exception occurs during loading
		"""
		if new_path == self._cur_file_path and self._cur_source == OptionsSource.FILE: #If file is already loaded
			if self._config_file_picker_model.getHighlightPath() != new_path:
				self._config_file_picker_model.setHightLightPath(self._cur_file_path) #Do update the highlight path
			return True #Ignore -> but action was successful

		if self.window.isWindowModified():
			msg = QtWidgets.QMessageBox()
			msg.setWindowTitle("Warning")
			msg.setIcon(QtWidgets.QMessageBox.Icon.Warning) #type: ignore
			msg.setText("The current config has unsaved changed, do you want to overwrite them with this new config?")
			msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) #type: ignore
			msg.setDefaultButton(QtWidgets.QMessageBox.No) #type: ignore
			msg.setEscapeButton(QtWidgets.QMessageBox.No) #type: ignore
			ret = msg.exec()
			if ret == QtWidgets.QMessageBox.No: #type: ignore
				self._config_file_picker_model.setHightLightPath(self._cur_file_path) #Hightlight path -> original
				return False

		self._cur_file_path = new_path
		self._cur_source = OptionsSource.FILE
		self._config_file_picker_model.setHightLightPath(self._cur_file_path) #Also update the highlight path
		log.debug(f"Started trying to load config from {new_path}")
		try:
			if new_path:
					# def load_from(self, path : str, show_msgbox_on_error :bool= True) -> bool:
				problem_dict = self._options.load_from(new_path)
				if len(problem_dict) > 0 and show_dialog_on_problem:
					msg = QtWidgets.QMessageBox()
					msg.setIcon(QtWidgets.QMessageBox.Icon.Warning) #type: ignore
					msg.setText(f"The following problems were encountered while loading the settings from path \
		 				<{new_path}>:")
					msg.setWindowTitle("Warning")
					txt = "<br>".join([f"<b>{key}:</b> {value}" for key, value in problem_dict.items()])
					txt += "<br><br>The settings have been loaded anyway, but running them as-is might result in \
						unexpected behaviour. This could be the result of a change in the settings format, or due to \
							file corruption."
					msg.setInformativeText(txt)
					msg.setDetailedText(str(problem_dict))
					msg.setStandardButtons(QtWidgets.QMessageBox.Ok) #type: ignore
					msg.setDefaultButton(QtWidgets.QMessageBox.Ok) #type: ignore
					msg.exec()
				self._config_file_picker_model.setHightLightPath(new_path)
				return True
		except Exception as exception:
			msg = QtWidgets.QMessageBox()
			msg.setWindowTitle("Error")
			msg.setIcon(QtWidgets.QMessageBox.Critical) #type: ignore
			msg.setText(f"Could not load config from {new_path}")
			msg.setInformativeText(f"Error: {exception}")
			msg.setStandardButtons(QtWidgets.QMessageBox.Ok) #type: ignore
			msg.exec()
			log.error(f"Could not load config from {new_path}. Error: {exception}")
			self._cur_file_path = None
			self._config_file_picker_model.resetHighlight()
		return False


	def _config_file_picker_model_highlight_path_changed(self, new_path : str) -> None:
		self.load_from_file(new_path) #Load from this file


	def close_event(self, event : QtGui.QCloseEvent) -> None:
		"""Overload default close event for a confirmation
		"""
		# ConfirmationBox = QtGui.QMessageBox()
		if self.window.isWindowModified():
			quit_msg = "There are unsaved changes. Do you want to save or discard changes before closing?"
			#Create a window with a "quit", "save and quit" and "cancel" button
			win = QtWidgets.QMessageBox()
			win.setWindowTitle("Unsaved changes")
			win.setText(quit_msg)
			win.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Save | QtWidgets.QMessageBox.StandardButton.Discard |
			  QtWidgets.QMessageBox.StandardButton.Cancel)
			win.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Save)
			win.setEscapeButton(QtWidgets.QMessageBox.StandardButton.Cancel)
			win.setIcon(QtWidgets.QMessageBox.Icon.Warning)
			ret = win.exec()


			if ret == QtWidgets.QMessageBox.StandardButton.Save:
				try:
					if self.save_config_triggered(): #If save has been done
						event.accept()
						self._save_settings()
						return
				except Exception as exception: #pylint: disable=broad-except
					log.error(f"Could not save config: {exception}")
					event.ignore() #If save failed - do not close
					return
			elif ret == QtWidgets.QMessageBox.StandardButton.Discard:
				log.info("Discarded changes... Now Closing...")
				event.accept()
				self._save_settings()
				return

			event.ignore() #If neither (discard) -> ignore
			return

		#If not modified -> just save settings and close
		self._save_settings()

	def get_base_name(self) -> str:
		"""
		Generates a base name for the config file based on the current main-settings
		"""
		if self._cur_file_path:
			# return os.path.basename(self._cur_file_path) #If already saved, use the save-name
			return os.path.basename(self._cur_file_path).rsplit(".", 1)[0] #If already saved, use the save-name
		name = ""
		name += ("_" + self._options.data_class) if self._options.data_class else ""
		name += ("_" + self._options.task) if self._options.task else ""
		name += ("_" + self._options.model) if self._options.model else ""
		#TODO: maybe add the first x changed-from-default settings to the name?
		return name

	@catchExceptionInMsgBoxDecorator
	def add_to_queue_triggered(self):
		"""
		Triggered when the "add to queue" button is clicked. Adds the current config to the queue.
		"""
		log.info("Add to queue triggered")
		name = self.get_base_name()
		#Ask for user input for the name
		name, ok_clicked = QtWidgets.QInputDialog.getText(self.window, "Add to queue", "Enter a name for the config",
					    QtWidgets.QLineEdit.EchoMode.Normal, name)
		if ok_clicked:
			# self.ml_queue.add_to_queue(name, self._options.get_options_data_copy())
			self.ml_queue_model.add_to_queue(name, self._options.get_options_data_copy())

	def undo_triggered(self):
		"""
		Triggered when undo is clicked. Undoes the last change to the options
		"""
		log.info("Undo triggered")
		if self._options.undo_stack:
			self._options.undo_stack.undo()

	def redo_triggered(self):
		"""
		Triggered when redo is clicked. Redoes the last change to the options
		"""

		log.info("Redo triggered")
		if self._options.undo_stack:
			self._options.undo_stack.redo()

	def save_config_triggered(self) -> bool:
		"""Save the config to the current file path. If no file path is set, calls save_config_as_triggered instead.

		Returns:
			bool: Whether the save was successful
		"""
		log.info("Save triggered")
		if self._cur_file_path is None or (self._cur_source != OptionsSource.FILE):
			ret = self.save_config_as_triggered() #Already cleans undo-stack if successful
		else:
			ret = self._options.save_as(self._cur_file_path)
			if ret and self._options.undo_stack: #If save was successful -> set clean state
				self._options.undo_stack.setClean()
				self.window.setWindowModified(False)
		return ret

	def save_config_as_triggered(self) -> bool:
		"""
		Triggered when the "save as" button is clicked. Opens a file dialog and saves the current config to the selected
		Returns:
			bool: True if the save was successful, False otherwise.
		"""
		log.info("Save as triggered")
		ret = False
		start_path = self._default_save_path
		if self._cur_file_path is not None and self._cur_source == OptionsSource.FILE:
			start_path = self._cur_file_path

		file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
			None, "Save config", start_path, "JSON (*.json)") #type:ignore
		if file_path:
			self._cur_file_path = file_path #If source is file -> this sets current file path
			self._config_file_picker_model.setHightLightPath(self._cur_file_path) #Also update the highlighted path
			ret = self._options.save_as(file_path)
			log.info(f"Save as returned {ret}")
			if ret and self._options.undo_stack: #If save was successful -> set clean state
				self._options.undo_stack.setClean()
				self.window.setWindowModified(False)
		else:
			log.info("No Save Path Selected")
		return ret
			#TODO: set selection to current file

if __name__ == "__main__":
	app = QtWidgets.QApplication([])
	window = QtWidgets.QMainWindow()
	queue = RunQueue()
	ml_window = ApplyMachineLearningWindow(run_queue=queue, window=window)
	window.show()
	app.exec()
