"""
Contains the main window class, which is a window which provides the user with several tools to
edit/manage/run machine learning settings.

Also contains OptionsSource, which is used to determine if the current file should be saved to a file or to the queue.
"""
import logging
import os
import typing
from enum import Enum

import dill
from PySide6 import QtCore, QtGui, QtWidgets
from pyside6_utils.models import FileExplorerModel
from pyside6_utils.utility.catch_show_exception_in_popup_decorator import \
    catch_show_exception_in_popup_decorator
from pyside6_utils.widgets import DataClassTreeView
from pyside6_utils.widgets.delegates import DataclassEditorsDelegate
from pyside6_utils.widgets.frameless_mdi_window import FramelessMdiWindow

from configurun.classes.run_queue import ConfigurationIsFirmException, RunQueue
from configurun.configuration.configuration import Configuration
from configurun.configuration.configuration_model import (
    ConfigurationModel, NoClassTypesError, OptionTypesMismatch,
    UnkownOptionClassError)
from configurun.windows.models.run_queue_console_model import \
    RunQueueConsoleModel
from configurun.windows.models.run_queue_table_model import RunQueueTableModel
from configurun.windows.ui.main_window_ui import Ui_MainWindow


log = logging.getLogger(__name__)

APP_NAME = "Configurun" #The name of the app, used for the settings file
WORKSPACE_LOCK_FILE_NAME = ".configurun_workspace.lock" #Is put in the workspace folder to indicate it is in use
WORKSPACE_RUN_QUEUE_SAVE_NAME = "run_queue_data.rq" #The name of the file in which the run queue is saved on close

class OptionsSource(Enum):
	"""
	Source of the options. Used to determine whether the options should be saved to a file or to the queue.
	"""
	FILE = 0
	QUEUE = 1


class MainWindow():
	"""
	The main QT window for this app which provides the user with several tools to edit/manage/run machine learning
	settings.

	Should be provided with:
		- A configuration model - manages the creation of new configurations & the ui
		- A run queue - manages the running of the configurations
		- A window - the main window in which the app should be built
		- workspace_path (str, optional) - the default path to use for the configuration, logfiles etc. If empty, or
			folder does not exist, defaults to ~/Configurun/configurations/
		- settings_in_workspace_path (bool, optional) - Whether to store the settings in the workspace path or in the
			default QSettings location. Defaults to True
	"""
	def __init__(self,
	      		configuration_model : ConfigurationModel,
				run_queue : RunQueue,
				window : QtWidgets.QMainWindow,
				workspace_path : str = "",
				settings_in_workspace_path : bool = True
			) -> None:
		"""
		Args:
			configuration_model (ConfigurationModel): The configuration model which manages updating the ui and creating
			run_queue (RunQueue): The runqueue which manages running the configurations
			window (QtWidgets.QMainWindow): The window in which the app should be built
			workspace_path (str, optional): The base output-path used for the configurations, logfiles etc.
				If empty, or folder does not exist, defaults to ~/Configurun/configurations/
			settings_in_workspace_path (bool, optional): Whether to store the settings in the workspace path or in the default
				QSettings location. Defaults to True
		"""
		self.ui = Ui_MainWindow() # pylint: disable=C0103
		self.ui.setupUi(window)

		self.window = window
		self._cur_source = None
		self._queue_source_id = -1 #The id of the queue item which is currently selected (if cur_source == QUEUE)
		self._default_splitter_states = {
			splitter.objectName() : splitter.saveState() \
				for splitter in self.window.findChildren(QtWidgets.QSplitter)
		} #Save all splitter states (to be able to reset them later

		self.ui.saveToQueueItemBtn.setHidden(True) #Hide the save to queue button until queue-item is selected
		#====================== Base variables ===================
		self.set_run_queue(run_queue)
		self.ui.runQueueWidget.set_model(self.run_queue_table_model)
		self.ui.runQueueWidget.runQueueTreeView.set_double_click_callback(self.run_queue_widget_item_double_click)


		self._workspace_path = workspace_path
		if workspace_path is None or len(workspace_path) == 0 or not os.path.isdir(workspace_path):
			self._workspace_path = os.path.join(os.path.expanduser("~"), APP_NAME)
			if not os.path.isdir(self._workspace_path):
				os.makedirs(self._workspace_path)
			log.info(f"Using default workspace path: {self._workspace_path}")

		#Check if workspace path is in use by another instance of the app
		if os.path.isfile(os.path.join(self._workspace_path, WORKSPACE_LOCK_FILE_NAME)):
			msgbox = QtWidgets.QMessageBox()
			msgbox.setText(f"<b>Workspace path {self._workspace_path} seems to be in use by another instance of "
		  				f"the {APP_NAME}-app. Do you want to use this workspace path anyway?</b>")
			msgbox.setInformativeText("Continuing might overwrite files from the other instance. "
				"If any other instances are running, please close them first, or change the workspace path. "
				"This issue could also be caused by a previous instance of the app crashing."
				)
			msgbox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
			msgbox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
			ret = msgbox.exec()
			if ret == QtWidgets.QMessageBox.StandardButton.No:
				raise RuntimeError(f"Workspace path {self._workspace_path} is in use by another instance of the "
					f"{APP_NAME}-app. Please close the other instance or change the workspace path.")
			else:
				log.warning("User chose to use workspace path anyway, ignoring lock-file.")

		#Create a lock-file to indicate that the workspace path is in use
		with open(os.path.join(self._workspace_path, WORKSPACE_LOCK_FILE_NAME), "w", encoding="utf-8") as lock_file:
			lock_file.write("This file is used to indicate that the workspace at this path is in use by another instance of "
				f"the {APP_NAME}-app. Please only remove this file if the app crashed and this file remained.")


		config_save_path = os.path.join(self._workspace_path, "configurations")
		if not os.path.isdir(config_save_path):
			os.makedirs(config_save_path)
			log.info(f"Config output path {config_save_path} is not a valid path, using default path")
		else:
			os.makedirs(config_save_path, exist_ok=True) #Make sure the path exists

		self._config_save_path = config_save_path
		self._config_file_picker_model = FileExplorerModel(
			allow_select_files_only=True
		)


		#========================= load settings =========================
		if settings_in_workspace_path:
			settings_path = os.path.join(self._workspace_path, "settings.ini")
			self._settings = QtCore.QSettings(
				settings_path, QtCore.QSettings.Format.IniFormat, )
			log.info(f"Attempted loading app-settings from {settings_path}. "
	    		f"This resulted in a settings-file loaded from {self._settings.fileName()}")
		else: #Else save
			log.info("Loading settings from default qt-location")
			self._settings = QtCore.QSettings(APP_NAME)
		self._font_point_size = int(
			self._settings.value("font_size", 0, type=int) #type: ignore #If zero->set to system default
		)
		self.set_font_point_size(self._font_point_size)
		self.window.restoreGeometry(self._settings.value(
			"window_geometry", self.window.saveGeometry(), type=QtCore.QRect)) # type: ignore
		new_window_state = self._settings.value("window_state", self.window.windowState())
		if new_window_state != QtCore.Qt.WindowState.WindowNoState:
			self.window.restoreState(new_window_state) # type: ignore


		self._cur_file_path : None | str = self._settings.value("loaded_file_path", None)#The current config. #type: ignore
		assert isinstance(self._cur_file_path, (str, type(None))), (f"Loaded file path should be a string or None, this "
			f"but is a {type(self._cur_file_path)}.")



		#====================== Suboptions window and automatic updating ===================
		self._configuration_model = configuration_model #The configuration model manages creation/changes in the currently
			# loaded configuration

		self._mdi_area = self.ui.ConfigurationMdiArea
		self._cur_option_proxy_models : typing.Dict[str, QtCore.QSortFilterProxyModel]= {}
		self._cur_option_mdi_windows : typing.Dict[str, QtWidgets.QMdiSubWindow] = {}
		self._cur_option_tree_view : typing.Dict[str, DataClassTreeView] = {}
		self._cur_edited_signals : typing.Dict[str, typing.Callable] = {}

		self._configuration_model.proxyModelDictChanged.connect(self.option_proxy_models_changed)
		self.option_proxy_models_changed(self._configuration_model.get_proxy_model_dict()) #Initialize the mdi windows


		#====================== File explorer ===================
		self._config_file_picker_model.setNameFilters(["*.json", "*.yaml", ""])
		self._config_file_picker_model.setNameFilterDisables(False)

		self._config_file_picker_model.setReadOnly(False)
		log.debug(f"Root path used for saving machine learning settings: {self._config_save_path}")
		self._config_file_picker_model.setRootPath(QtCore.QDir.rootPath()) #Subscribe to changes in this path
		self.ui.ConfigFilePickerView.setModel(self._config_file_picker_model)
		self.ui.ConfigFilePickerView.setRootIndex(
			self._config_file_picker_model.index(self._config_save_path)
		)
		self.ui.ConfigFilePickerView.set_double_click_callback(self.file_explorer_item_double_click)
		self.ui.ConfigFilePickerView.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents) #type: ignore
		#Filter only .json and folders


		#======== Open a window which shows the undo/redo stack ========
		if self._configuration_model.undo_stack:
			self.ui.undoView.setStack(self._configuration_model.undo_stack)

		#Un undo-stack change, change the title of the window with a * to indicate that the file has been changed
		if self._configuration_model.undo_stack:
			self._configuration_model.undo_stack.cleanChanged.connect(
				lambda: self.window.setWindowModified(not self._configuration_model.undo_stack.isClean()) #type:ignore
			)

		#Link close-event to a confirmation box
		self.window.closeEvent = self.close_event


		# self._highlight_changed_signal = self._config_file_picker_model.highlightPathChanged.connect(
		# 	self._config_file_picker_model_highlight_path_changed)

		#============= Post-load settings =============
		if self._cur_file_path is not None:
			load_succesfully = self.load_from_file(self._cur_file_path, show_dialog_on_problem=False) #Attempt load
			if not load_succesfully:
				self.new_configuration(ignore_modified_window=True) #If loading failed -> reset to default
		else:
			self.new_configuration(ignore_modified_window=True) #If no file is loaded -> reset to default
		self.ui.ConfigurationMdiArea.tileSubWindows() #Tile the mdi windows

		#==================Console ================
		self._console_item_model = RunQueueConsoleModel()
		self._console_item_model.set_run_queue(self._run_queue)
		self.ui.consoleWidget.set_model(self._console_item_model)

		#Connect right click on console-widget to a context menu
		self.ui.consoleWidget.ui.fileSelectionTableView.setContextMenuPolicy(
			QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
		self.ui.consoleWidget.ui.fileSelectionTableView.customContextMenuRequested.connect(
			self.create_console_context_menu
		)


		#======================== Actions/Shortcuts ========================

		###### Configuration Actions ########
		self.ui.actionNewConfig.triggered.connect(self.new_configuration) #Set to empty config
		self.ui.actionOpenConfig.triggered.connect(self.load_config_from_file_popup)

		self.ui.actionUndo.triggered.connect(self.undo_triggered)
		self.ui.actionRedo.triggered.connect(self.redo_triggered)
		self.ui.actionSave.triggered.connect(self.save_config_triggered)
		self.ui.actionSave_As.triggered.connect(self.save_config_as_triggered)

		######### View Actions ##########
		self.ui.actionIncreaseFontSize.triggered.connect(
			lambda *_: self.set_font_point_size(min(96, self._font_point_size + 1)) #type: ignore
		) #This should be more than enough
		self.ui.actionDecreaseFontSize.triggered.connect(
			lambda *_: self.set_font_point_size(max(3, self._font_point_size - 1)) #type: ignore
		)
		self.ui.actionDefaultFontSize.triggered.connect(
			lambda *_: self.set_font_point_size(0) #0 makes it so that the system default is used
		)
		self.ui.menuMDI_Area.removeAction(self.ui.actionNone) #Remove the "none" action from the mdi menu
		self.ui.ConfigurationMdiArea.add_actions_to_menu(self.ui.menuMDI_Area)

		###### File overview buttons #########
		self.ui.saveCurrentConfigAsBtn.clicked.connect(self.save_config_as_triggered)
		self.ui.saveCurrentConfigBtn.clicked.connect(self.save_config_triggered)
		self.ui.OpenFileLocationBtn.clicked.connect(self.open_save_location_in_explorer)


		###### Run Queue Actions ########
		# self.ui.menuRun_Queue.mousePressEvent().triggered.connect(self.ui.runQueueWidget.show)
		self.ui.menuRun_Queue.aboutToShow.connect(self.expand_run_queue_view_filter_options)
		# self.ui.actionViewRunQueueFilter.triggered.connect(lambda *_: self.expand_run_queue_view_filter_options())
		# self.ui.actionViewRunQueueFilter.triggered.connect(lambda *_: print("kaas"))
		# self.ui.actionBackupRunQueue.triggered.connect(self.runQu
		self.ui.actionBackupRunQueue.triggered.connect(lambda *_: self.ui.runQueueWidget.save_to_file_popup())
		self.ui.actionLoadRunQueue.triggered.connect(lambda *_: self.ui.runQueueWidget.load_from_file_popup())

		###### Buttom-config editor buttons ########
		self.ui.addToQueueButton.clicked.connect(self.add_to_queue_triggered)
		self.ui.saveToQueueItemBtn.clicked.connect(self.save_to_queue_item_triggered)


		#======================================== POST-init ========================================
		self.initial_run_queue_load() #If all went well, try to load existing run queue data


	@catch_show_exception_in_popup_decorator
	def load_config_from_file_popup(self):
		"""Creates a popup that asks the user to select a path, if a path is selected, we will attempt to load the
		configuration from the selected path
		"""
		file_path = QtWidgets.QFileDialog.getOpenFileName(
			self.window, "Select configuration file", self._config_save_path, "Config files (*.json *.yaml)"
		)[0]
		if file_path == "" or file_path is None:
			return
		self.load_from_file(file_path)

	@catch_show_exception_in_popup_decorator
	def save_to_queue_item_triggered(self) -> None:
		"""
		Saves the current configuration to the queue item with the id self._queue_source_id. If it does not exists,
		a keyerror is raised.
		"""
		assert self._cur_source == OptionsSource.QUEUE, (f"Cannot save the config to an existing queue item "
			f"since the current source is {self._cur_source}, not {OptionsSource.QUEUE}")

		try:
			self._run_queue.set_item_config(self._queue_source_id, self._configuration_model.get_configuration_data_copy())
			if self._configuration_model.undo_stack: #Undo stack is saved
				self._configuration_model.undo_stack.setClean()
		except ConfigurationIsFirmException as exception:
			QtWidgets.QMessageBox.warning(self.window, "Cannot save to Queue item", str(exception))
			return
		except KeyError as exception:
			QtWidgets.QMessageBox.warning(self.window, "Cannot save to Queue item",
				f"{exception}. <br> This is likely because the queue item was removed from the queue. <br>"
			)

	def expand_run_queue_view_filter_options(self):
		"""Popules the run queue view filter menu with a copy of the menu provided in the run queue widget"""
		self._cur_run_queue_view_menu = self.ui.runQueueWidget.get_queue_settings_context_menu() #NOTE: even though #pylint: disable=attribute-defined-outside-init
			# we don't use this after creation of the menu, we need to keep a reference for it not to be garbage collected

		for action in self.ui.menuRun_Queue.actions(): #Remove all actions from the menu
			self.ui.menuRun_Queue.removeAction(action)
		for action in self._cur_run_queue_view_menu.actions():
			self.ui.menuRun_Queue.addAction(action)


	def option_proxy_models_changed(self, dict_of_models : typing.OrderedDict[str, QtCore.QSortFilterProxyModel]) -> None:
		"""Upon change of (one of) the dataclass editors -> update the console"""
		#================= Add mdi windows that are new to the config model =================
		for option_name, option_model in dict_of_models.items():
			if option_name in self._cur_option_proxy_models:
				#check if the same model is used
				if self._cur_option_proxy_models[option_name] == option_model:
					log.debug(f"Model for {option_name} has not changed, not updating its model or window")
				else:
					self._cur_option_proxy_models[option_name] = option_model
					self._cur_option_tree_view[option_name].setModel(option_model)
			else: #Create a new mdi window
				log.debug(f"Adding new mdi window for option {option_name}")
				self._cur_option_mdi_windows[option_name] = FramelessMdiWindow()
				self._cur_option_proxy_models[option_name] = option_model
				self._cur_option_tree_view[option_name] = DataClassTreeView()
				self._cur_option_tree_view[option_name].setModel(option_model)
				self._cur_option_tree_view[option_name].setItemDelegate(DataclassEditorsDelegate())#Set custom delegate
				self._cur_option_mdi_windows[option_name].setWidget(self._cur_option_tree_view[option_name])
				self._mdi_area.addSubWindow(self._cur_option_mdi_windows[option_name])
				self._cur_option_mdi_windows[option_name].setWindowTitle(option_name.title().replace("_", " "))
				# self._cur_option_mdi_windows[option_name].show()

		#================= Remove mdi windows that are no longer in the config model =================
		del_windows = [key for key in self._cur_option_mdi_windows if key not in dict_of_models.keys()]
		for window in del_windows:
			self._cur_option_mdi_windows[window].close()
			self._mdi_area.removeSubWindow(self._cur_option_mdi_windows[window])
			del self._cur_option_tree_view[window]
			del self._cur_option_proxy_models[window]
			del self._cur_option_mdi_windows[window]

		self._mdi_area.order_windows_by_windowlist(
			[self._cur_option_mdi_windows[option_name] for option_name in dict_of_models.keys()]
		) #Sort windows according to returned dictionary order

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
			action.triggered.connect(lambda *_, id=cur_id: self._console_item_model.un_ignore_id(id))
		menu.exec(self.ui.consoleWidget.ui.fileSelectionTableView.mapToGlobal(pos))

	def set_run_queue(self, run_queue : RunQueue):
		"""Sets a new runqueue. Indicates that all models need to reload their data.

		Args:
			run_queue (RunQueue): the new runQueue
		"""
		self._run_queue = run_queue
		self.run_queue_table_model : RunQueueTableModel = RunQueueTableModel(self._run_queue)

	@catch_show_exception_in_popup_decorator
	def run_queue_widget_item_double_click(self, index : QtCore.QModelIndex) -> None:
		"""
		Replaces the default behaviour of the on-double click signal of the RunQueueTableView.
		In this method, we first try to load the item, to the configuration-editor.
		If it fails, we just ignore the request. Otherwise mark the item as selected in the model and load
		"""
		cur_id = index.data(RunQueueTableModel.CustomDataRoles.IDRole)
		log.debug(f"Double clicked on index {index.row()} with id {cur_id}")

		ret = self.load_config_from_queue(cur_id)
		if not ret:
			log.warning(f"Failed to load queue item with id {cur_id}, ignoring request")
			return
		else:
			self.run_queue_table_model.set_highligh_by_id(cur_id)

		self.set_source(OptionsSource.QUEUE) #Source from queue
		self._queue_source_id = cur_id #Set the id of the queue item which is currently selected

		log.info(f"Loaded Configuration of queue item with id {cur_id} from RunQueue")

	@catch_show_exception_in_popup_decorator
	def file_explorer_item_double_click(self, index : QtCore.QModelIndex | QtCore.QPersistentModelIndex) -> None:
		"""
		Replaces the default behaviour of the on-double click signal of the FileExplorerView.
		In this method, we first try to load the item, to the configuration-editor.
		If it fails, we just ignore the request. Otherwise mark the item as selected in the model and load it.
		"""
		file_path = self._config_file_picker_model.filePath(index)
		log.debug(f"Double clicked on index {index.row()} with path {file_path}")

		ret = self.load_from_file(file_path)
		if not ret:
			log.warning(f"Failed to load file {file_path}, ignoring request")
			return
		else:
			self._config_file_picker_model.set_highlight_using_index(index)

	@catch_show_exception_in_popup_decorator
	def load_config_from_queue(self, queue_item_id : int) -> bool:
		"""
		Sets the current configuration to the configuration of the queue item with the provided id. If the queue item
		does not exist, raises a KeyError. If queue-item had no valid Configuration-instance, raises a ValueError.

		Args:
			queue_item_id (int): The id of the config we should attemt to load from the current RunQueue
		"""
		#Check if undo stack is clean, if not -> ask user if they want to save
		if self._configuration_model.undo_stack and not self._configuration_model.undo_stack.isClean():
			if not self._ask_overwrite_unsaved_changes():
				log.info("User chose not to overwrite unsaved changes, ignoring request to load config from queue")
				return False

		if queue_item_id == -1:
			log.warning("Queue item id is -1, ignoring request to set current config to queue item")
			raise KeyError("Queue item id is -1, ignoring request to set current config to queue item")

		new_config = self._run_queue.get_item_config(queue_item_id)
		if new_config is None or not isinstance(new_config, Configuration):
			raise ValueError(f"Queue item with id {queue_item_id} did not return a Configuration. Instead, returned "
		    	f"{type(new_config)}.")

		self._configuration_model.set_configuration_data(new_config, validate_after_setting=True)
		if self._configuration_model.undo_stack: #Reset undo stack
			self._configuration_model.undo_stack.clear()

		#========= Update source ===========
		self._queue_source_id = queue_item_id
		self.ui.saveToQueueItemBtn.setHidden(False) #Show the save to queue button
		self._cur_source = OptionsSource.QUEUE

		#========= Update the file picker view ===========
		self._config_file_picker_model.reset_highlight() #Reset the hightlight

		return True

	def set_source(self, new_source : OptionsSource) -> None:
		"""
		Sets the current source of the configuration (self._cur_source).
		If the source changed, the ui will be updated to reflect the new source
		(e.g. show load-to-queue-button, clear any highlights in other source etc.)

		Args:
			new_source (OptionsSource): The new source
		"""
		if new_source == self._cur_source:
			return

		self._cur_source = new_source
		self._cur_file_path = None
		self.ui.saveToQueueItemBtn.setHidden(new_source != OptionsSource.QUEUE) #Show the save button if item from queue

		if new_source == OptionsSource.FILE:
			#Clear highlight from RunQueue
			self.run_queue_table_model.set_highligh_by_id(-1)
		elif new_source == OptionsSource.QUEUE:
			self._config_file_picker_model.reset_highlight() #Reset the hightlight

		# self._config_file_picker_model.reset_highlight()

	def update_ui_by_connection_state(self, new_connection_state : bool) -> None:
		"""Updates the UI based on the connection state (disabled certain buttons, etc).
		Should only be called when runmode is set to network. When running locally - disconnects cannot happen.
		TODO: also put a "reconnect" button in front of the UI?

		Args:
			new_connection_state (bool): The new connection
		"""

		if not new_connection_state:
			self.ui.runQueueOverlayWidget.set_overlay_hidden(False)
			self.ui.ConsoleOverlayWidget.set_overlay_hidden(False)
		else:
			self.ui.runQueueOverlayWidget.set_overlay_hidden(True)
			self.ui.ConsoleOverlayWidget.set_overlay_hidden(True)

	def initial_run_queue_load(self) -> None:
		"""
		Should be called just after setting workspace.
		Tries to load the RunQueue contents from a file according to the filename that is used when the close-event is
		called. If the file does not exist, nothing happens.

		NOTE: In the case of RunQueueClient-based run-mode, this method should probably not be called, as it tries to
			overwrite the run-queue, which might not be desireable in the case of a running server.

		TODO: also move loading settings here?
		"""
		if os.path.exists(os.path.join(self._workspace_path, WORKSPACE_RUN_QUEUE_SAVE_NAME)):
			cur_items = self._run_queue.get_all_items_dict_snapshot_copy()
			if len(cur_items.keys()) > 0:
				#Create a popup that asks the user to select a path, if a path is selected, we will attempt to load the
				#Use one-liner
				warning_box = QtWidgets.QMessageBox.question(self.window, "Load run queue?",
					("Trying to reload run-queue from the workspace, but the current run-queue is not empty. Do you want "
					"to load the run-queue from the last session anyway?"),
					QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
				if warning_box == QtWidgets.QMessageBox.StandardButton.No:
					return

			path = os.path.join(self._workspace_path, WORKSPACE_RUN_QUEUE_SAVE_NAME)
			self.run_queue_table_model.load_from_file(path, allow_load_running_items="allow")
			# self.ui.runQueueWidget.load_from_file_popup
		else:
			log.info(f"No RunQueue save file found at {os.path.join(self._workspace_path, WORKSPACE_RUN_QUEUE_SAVE_NAME)}"
					", continuing with an empty run-queue.")



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
			QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self._config_save_path))

	@staticmethod
	def _ask_overwrite_unsaved_changes() -> bool:
		"""Can be used when the configuration has unsaved changes. Asks the user if they want to overwrite the current
		config with a new one. Returns True if the user wants to overwrite, False otherwise.

		Returns:
			bool: Whether the user wants to overwrite the current config with a new one
		"""
		new_msgbox = QtWidgets.QMessageBox()
		new_msgbox.setWindowTitle("Warning")
		new_msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
		new_msgbox.setText(
			"The current config has unsaved changed, do you want to overwrite them with the selected config?"
		)
		new_msgbox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
		new_msgbox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
		new_msgbox.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)
		ret = new_msgbox.exec()
		if ret == QtWidgets.QMessageBox.StandardButton.Yes:
			return True
		return False

	def new_configuration(self, ignore_modified_window : bool=False) -> None:
		"""
		Create a new configuration with default values. If the current config has unsaved changes, a dialog will be
		shown to ask the user if they want to save the current config first, unless ignore_modified_window is set to
		True.

		Args:
			ignore_modified_window (bool, optional): Whether to ignore the current modified window state. If true,
				overwrites the current config without asking the user. Defaults to False.
		"""
		if self.window.isWindowModified() and not ignore_modified_window:
			if not self._ask_overwrite_unsaved_changes():
				return

			self._config_file_picker_model.set_highlight_using_path(self._cur_file_path) #Hightlight path -> original
			return

		self.window.setWindowModified(False)
		self._cur_file_path = None
		self._config_file_picker_model.reset_highlight()
		self._configuration_model.reset_configuration_data_to_default()

	def load_from_file(self,
				new_path : str | None,
				show_dialog_on_problem=True,
				ignore_modified = False
			) -> bool:
		"""Loads the config from a file

		Args:
			new_path (str): The new path from which to load the config
			show_dialog_on_problem (bool, optional): Whether to show a dialog when there are problems. Defaults to True.
			ignore_modified (bool, optional): Whether to ignore the current modified window state. If true,
				overwrites the current config without asking the user. Defaults to False (ask user if modified).

		Returns:
			bool: Whether loading a config was succesful NOTE: still returns True if the passed file was already loaded,
			  also return True if there were problems, returns false if an unhandled exception occurs during loading
		"""
		if new_path is None or not os.path.isfile(new_path):
			return False

		if new_path == self._cur_file_path and self._cur_source == OptionsSource.FILE: #If file is already loaded
			if self._config_file_picker_model.get_highlight_path() != new_path:
				self._config_file_picker_model.set_highlight_using_path(self._cur_file_path) #Do update the highlight path
			return True #Ignore -> but action was successful

		if self.window.isWindowModified() and not ignore_modified:
			msg = QtWidgets.QMessageBox()
			msg.setWindowTitle("Warning")
			msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
			msg.setText("The current config has unsaved changed, do you want to overwrite them with this new config?")
			msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
			msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
			msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)
			ret = msg.exec()
			if ret == QtWidgets.QMessageBox.StandardButton.No:
				return False

		self._cur_file_path = new_path
		self.set_source(OptionsSource.FILE)
		self._config_file_picker_model.set_highlight_using_path(self._cur_file_path) #Also update the highlight path
		try:
			if new_path:
				problem_dict = {}
				try: #First try loading using class-type keys that are inside the json file
					problem_dict = self._configuration_model.load_json_from(new_path)
				except (UnkownOptionClassError, NoClassTypesError) as exception:

					msg = QtWidgets.QMessageBox()
					txt = ""
					button_discard = None
					if isinstance(exception, NoClassTypesError):
						txt += ("No class types were found in the file. We can try to to deduce the dataclass-types "
							"by using the option-names and automatic type-deduction. <br><br>")
						txt += ("<br>This could be the "
								"result of a change in the settings format, dataclass module- or class-names, or due to "
								"file corruption.")
					elif isinstance(exception, UnkownOptionClassError):
						txt = "<ul>"
						for option_name, exception_list in exception.args[-1].items():
							txt += f"<b>{option_name}:</b>"
							for exception in exception_list:
								txt += f"<li><b>{type(exception).__name__}</b>:<br>{exception}</li>"
						txt += "</ul>"
						txt += ("<br>There was a problem loading the option dataclass-types from file. This could be the "
								"result of a change in the settings format, dataclass module- or class-names, or due to "
								"file corruption.")
						txt += ("<br><br> We can discard the unknown dataclass-types or try to deduce the "
							"actual dataclass types by using the option-names and automatic type-deduction. <br><br>")

						button_discard = msg.addButton("Discard", QtWidgets.QMessageBox.ButtonRole.NoRole)


					msg.setWindowTitle("Warning")
					msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
					msg.setText(f"Could not immediately load dataclass-types from {new_path}:")
					msg.setInformativeText(txt)

					#TODO: order of buttons is determined by buttonrole, so they seem a bit arbitrary...
					button_deduce = msg.addButton("Deduce", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
					msg.addButton("Cancel", QtWidgets.QMessageBox.ButtonRole.RejectRole)
					msg.setDetailedText(str(exception.args[-1]))


					msg.exec()
					if msg.clickedButton() == button_deduce: #Deduce
						problem_dict = self._configuration_model.load_json_from(new_path, load_using_classtypes_key=False)
					elif msg.clickedButton() == button_discard: #Discard
						problem_dict = self._configuration_model.load_json_from(new_path, ignore_unknown_option_types=True)
					else:
						#Reset settings
						self.new_configuration(ignore_modified_window=True) #If loading failed -> reset to default config
						return False

				if len(problem_dict) > 0 and show_dialog_on_problem:
					msg = QtWidgets.QMessageBox()
					msg.setIcon(QtWidgets.QMessageBox.Icon.Warning) #type: ignore
					msg.setText(
						f"The following problems were encountered while loading the settings from path <a href={new_path}></a>:")
					msg.setWindowTitle("Warning")
					txt =""
					for option_name, exception_list in problem_dict.items():
						txt += f"<b>{option_name}:</b>"
						txt += "<ul>"
						for exception in exception_list:
							txt += f"<li><b>{type(exception).__name__}</b>: {exception}</li>"
						txt += "</ul><br>"

					txt += ("The settings have been loaded anyway, but running them as-is might result in"
						"unexpected behaviour. This could be the result of a change in the settings format, or due to"
						"file corruption.")
					msg.setInformativeText(txt)
					msg.setDetailedText(str(problem_dict))
					msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok) #type: ignore
					msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok) #type: ignore
					msg.exec()

				try:
					self._configuration_model.validate_current_configuration()
				except OptionTypesMismatch as exception:
					msg = QtWidgets.QMessageBox()
					msg.setWindowTitle("Warning")
					msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
					msg.setText(f"The loaded configuration from <tt>{new_path}</tt> is not stable.")
					replaced_exception = str(exception).replace("\n", "<br>")
					print("kaas", replaced_exception)
					print("frikandel", exception)
					msg.setInformativeText((f"<b>{type(exception).__name__}:</b> {replaced_exception}<br><br>"
			     			"This could be the result of a change in the settings format, the type-deducer, "
							"the option-names, or due to file corruption. <br>"
							"You can continue using the configuration, but any changes to the config will overwrite the "
							" option-subgroup(s) mentioned above.<br>"))
					msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
					msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)
					msg.exec()

				self._config_file_picker_model.set_highlight_using_path(new_path)
				return True
		except Exception as exception: #pylint: disable=broad-except #Allow broad-exception, catch all and display
			msg = QtWidgets.QMessageBox()
			msg.setWindowTitle("Error")
			msg.setIcon(QtWidgets.QMessageBox.Icon.Critical) #type: ignore
			msg.setText(f"Could not load config from {new_path}")
			msg.setInformativeText(f"{type(exception).__name__}: {exception}")
			msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok) #type: ignore
			msg.exec()
			log.error(f"Could not load config from {new_path}. Error: {exception}")
			self._cur_file_path = None
			self._config_file_picker_model.reset_highlight()
		return False




	def close_event(self, event : QtGui.QCloseEvent) -> None:
		"""Overload default close event for a confirmation
		"""
		# ConfirmationBox = QtGui.QMessageBox()
		if self.window.isWindowModified():
			quit_msg = "There are unsaved changes. Do you want to save & quit or discard changes before closing?"
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
					if not self.save_config_triggered(): #If save was canceled, or failed, stop closing
						event.ignore()
						return
				except Exception as exception: #pylint: disable=broad-except
					log.error(f"Could not save config: {exception}")
					event.ignore() #If save failed - do not close
					return
			elif ret == QtWidgets.QMessageBox.StandardButton.Discard:
				log.info("Discarding changes...")
			else:
				event.ignore()
				return

		if not self.check_if_running_ask_stop_items_before_close(): #Check if user is okay with stopping the queue
			event.ignore()
			return

		save_dict = self._run_queue.get_queue_contents_dict(save_running_as_stopped=True)
		run_queue_contents_path = os.path.join(self._workspace_path, WORKSPACE_RUN_QUEUE_SAVE_NAME)
		with open(run_queue_contents_path, "wb") as file:
			dill.dump(save_dict, file)

		self._save_settings()

		if os.path.isfile(os.path.join(self._workspace_path, WORKSPACE_LOCK_FILE_NAME)): #Clean up lock-file
			os.remove(os.path.join(self._workspace_path, WORKSPACE_LOCK_FILE_NAME))
		event.accept()

	def check_if_running_ask_stop_items_before_close(self) -> bool:
		"""Checks if the queue is running an item. If so, asks the user if they want to stop the queue and close anyway.
		Uses a separate function because this function should not cancel the running processes in the case of a
		client-server app.
		"""
		#Check whether queue is running an item - if so, ask for confirmation
		if self._run_queue.get_running_configuration_count() > 0:
			quit_msg = "<b>The queue is currently running an item. Do you want to stop the queue and close anyway?</b>"
			#Create a window with a "quit", "save and quit" and "cancel" button
			win = QtWidgets.QMessageBox()
			win.setWindowTitle("Queue is running")
			win.setText(quit_msg)
			win.setInformativeText("If you choose to stop the queue, all currently running items will be marked as 'stopped'.")
			win.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
			win.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Yes)
			win.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)
			win.setIcon(QtWidgets.QMessageBox.Icon.Warning)
			ret = win.exec()

			if ret == QtWidgets.QMessageBox.StandardButton.Yes:
				self._run_queue.force_stop_all_running(
					stop_msg="User stopped the RunQueueue when closing the application."
				)
			else:
				return False

		return True



	def get_base_name(self) -> str:
		"""
		Generates a base name for the config file based on the current main-settings
		"""
		if self._cur_file_path:
			# return os.path.basename(self._cur_file_path) #If already saved, use the save-name
			return os.path.basename(self._cur_file_path).rsplit(".", 1)[0] #If already saved, use the save-name

		if hasattr(self._configuration_model, "experiment_name"): #If experiment name is set -> use that
			return self._configuration_model.experiment_name

		# name = ""
		# name += ("_" + self._config_model.data_class) if self._config_model.data_class else ""
		# name += ("_" + self._config_model.task) if self._config_model.task else ""
		# name += ("_" + self._config_model.model) if self._config_model.model else ""
		return "new_config"

	@catch_show_exception_in_popup_decorator
	def add_to_queue_triggered(self):
		"""
		Triggered when the "add to queue" button is clicked. Adds the current config to the queue.
		"""
		log.debug("Add to queue triggered")
		name = self.get_base_name()
		#Ask for user input for the name
		name, ok_clicked = QtWidgets.QInputDialog.getText(self.window, "Add to queue", "Enter a name for the config",
					    QtWidgets.QLineEdit.EchoMode.Normal, name)
		if ok_clicked:
			# self.ml_queue.add_to_queue(name, self._options.get_options_data_copy())
			self.run_queue_table_model.add_to_queue(name, self._configuration_model.get_configuration_data_copy())

	def undo_triggered(self):
		"""
		Triggered when undo is clicked. Undoes the last change to the options
		"""
		log.info("Undo triggered")
		if self._configuration_model.undo_stack:
			self._configuration_model.undo_stack.undo()

	def redo_triggered(self):
		"""
		Triggered when redo is clicked. Redoes the last change to the options
		"""

		log.info("Redo triggered")
		if self._configuration_model.undo_stack:
			self._configuration_model.undo_stack.redo()

	def save_config_triggered(self) -> bool:
		"""Save the config to the current file path. If no file path is set, calls save_config_as_triggered instead.

		Returns:
			bool: Whether the save was successful
		"""
		log.info("Save triggered")
		if self._cur_file_path is None or (self._cur_source != OptionsSource.FILE) or not os.path.isfile(self._cur_file_path):
			ret = self.save_config_as_triggered() #Already cleans undo-stack if successful
		else:
			ret = self._configuration_model.save_json_to(self._cur_file_path)
			if ret and self._configuration_model.undo_stack: #If save was successful -> set clean state
				self._configuration_model.undo_stack.setClean()
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
		start_path = self._config_save_path
		if self._cur_file_path is not None\
				and self._cur_source == OptionsSource.FILE\
				and os.path.isfile(self._cur_file_path): #If already saved -> use the current file as start path
			start_path = self._cur_file_path

		file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
			None, "Save config", start_path, "JSON (*.json)") #type:ignore
		if file_path:
			self._cur_file_path = file_path #If source is file -> this sets current file path
			self._config_file_picker_model.set_highlight_using_path(self._cur_file_path) #Also update the highlighted path
			ret = self._configuration_model.save_json_to(file_path)
			log.info(f"Save as returned {ret}")
			if ret and self._configuration_model.undo_stack: #If save was successful -> set clean state
				self._configuration_model.undo_stack.setClean()
				self.window.setWindowModified(False)
		else:
			log.info("No Save Path Selected")
		return ret
			#TODO: set selection to current file


def run_example_app():
	"""Runs the example app"""
	from configurun.examples.example_run_function import example_run_function #pylint: disable=import-outside-toplevel
	app = QtWidgets.QApplication([])
	main_window = QtWidgets.QMainWindow()
	workspace_path = os.path.join(os.path.expanduser("~"), APP_NAME)
	if not os.path.isdir(workspace_path):
		os.makedirs(workspace_path)

	#Set Qt workspace path
	QtCore.QDir.setCurrent(workspace_path) #Set the current working directory to the workspace path


	queue = RunQueue(
			target_function=example_run_function,
		  	log_location= os.path.join(workspace_path, "logs"),
			log_location_make_dirs=True #Create dir if it does not exist
	)
	config_model = ConfigurationModel(
		option_type_deduction_function=example_deduce_new_option_classes
	)
	MainWindow(
		configuration_model=config_model,
		run_queue=queue,
		window=main_window,
		workspace_path=workspace_path

	)

	main_window.show()
	app.exec()

if __name__ == "__main__":
	from configurun.examples.example_configuration import example_deduce_new_option_classes
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
