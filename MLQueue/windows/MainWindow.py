"""
Contains the main window class, which is a window which provides the user with several tools to
edit/manage/run machine learning settings.

Also contains OptionsSource, which is used to determine if the current file should be saved to a file or to the queue.
"""
import logging
import os
import typing
from enum import Enum

import PySide6Widgets.Models.FileExplorerModel
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6Widgets.Utility.catchExceptionInMsgBoxDecorator import \
    catchExceptionInMsgBoxDecorator
from PySide6Widgets.Widgets.FramelessMdiWindow import FramelessMdiWindow
from PySide6Widgets.Utility.DataClassEditorsDelegate import DataClassEditorsDelegate
import importlib.util

from MLQueue.classes.RunQueue import RunQueue
from MLQueue.configuration.ConfigurationModel import ConfigurationModel
from MLQueue.examples.FrameworkExample import FrameworkConfigurationModel
from MLQueue.windows.models.RunQueueConsoleModel import RunQueueConsoleModel
from MLQueue.windows.models.RunQueueTableModel import RunQueueTableModel
from MLQueue.windows.ui.ApplyMachineLearningWindow_ui import \
    Ui_ApplyMachineLearningWindow
from MLQueue.windows.widgets.MLQueueWidget import MLQueueWidget
from MLQueue.configuration.ConfigurationModel import UnkownOptionClassError, NoClassTypesError


log = logging.getLogger(__name__)
if __name__ == "__main__":
	logging.getLogger('matplotlib').setLevel(logging.INFO)
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}] {levelname:<7s}   {message}", style='{')
	log.propagate = False
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.DEBUG
	) #Without time

SETTINGS_PATH_MACHINE_LEARNING_WINDOW = "/Settings/MachineLearning"

class OptionsSource(Enum):
	"""
	Source of the options. Used to determine whether the options should be saved to a file or to the queue.
	"""
	FILE = 0
	QUEUE = 1


class MainWindow():
	"""
	A QT window which provides the user with several tools to edit/manage/run machine learning settings.
	"""
	#A controller to manage the machine learning window
	def __init__(self, 
	      		configuration_model : ConfigurationModel,
				run_queue : RunQueue,
				window : QtWidgets.QMainWindow
			) -> None:
		self.ui = Ui_ApplyMachineLearningWindow() # pylint: disable=C0103
		self.ui.setupUi(window)

		self.window = window
		self._cur_source = None
		# self._default_splitter_states = {
		# 	splitter.objectName() : splitter.saveState() \
		# 		for splitter in self.ui.splitter.findChildren(QtWidgets.QSplitter)
		# } #Save all splitter states (to be able to reset them later)
		#====================== Base variables ===================
		self.set_run_queue(run_queue)
		self.ml_queue_widget = MLQueueWidget(self.ui.MLQueueWidget) #Create queue-interface with buttons

		self.ml_queue_widget.queue_view.setModel(self.ml_queue_model)

		# self._cur_path = None
		self._default_save_path = SETTINGS_PATH_MACHINE_LEARNING_WINDOW
		self._config_file_picker_model = PySide6Widgets.Models.FileExplorerModel.FileExplorerModel(
			allow_select_files_only=True)


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
		self._config_model = configuration_model

		self._mdi_area = self.ui.ConfigurationMdiArea
		self._cur_option_proxy_models : typing.Dict[str, QtCore.QSortFilterProxyModel]= {}
		self._cur_option_mdi_windows : typing.Dict[str, QtWidgets.QMdiSubWindow] = {}
		self._cur_option_tree_view : typing.Dict[str, QtWidgets.QTreeView] = {}
		self._cur_edited_signals : typing.Dict[str, typing.Callable] = {}

		self._config_model.proxyModelDictChanged.connect(self.option_proxy_models_changed)
		self.option_proxy_models_changed(self._config_model.get_proxy_model_dict()) #Initialize the mdi windows



		self._config_file_picker_model.setReadOnly(False)
		log.debug(f"Root path used for saving machine learning settings: {SETTINGS_PATH_MACHINE_LEARNING_WINDOW}")
		self._config_file_picker_model.setRootPath(QtCore.QDir.rootPath()) #Subscribe to changes in this path
		self.ui.ConfigFilePickerView.setModel(self._config_file_picker_model)
		self.ui.ConfigFilePickerView.setRootIndex(
			self._config_file_picker_model.index(SETTINGS_PATH_MACHINE_LEARNING_WINDOW)
		)

		self.ui.ConfigFilePickerView.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents) #type: ignore


		#======== Open a window which shows the undo/redo stack ========
		if self._config_model.undo_stack:
			self.ui.undoView.setStack(self._config_model.undo_stack)

		#Un undo-stack change, change the title of the window with a * to indicate that the file has been changed
		if self._config_model.undo_stack:
			self._config_model.undo_stack.cleanChanged.connect(
				lambda: self.window.setWindowModified(not self._config_model.undo_stack.isClean()) #type:ignore
			)

		#Link close-event to a confirmation box
		self.window.closeEvent = self.close_event


		self._hightlight_changed_signal = self._config_file_picker_model.highlightPathChanged.connect(
			self._config_file_picker_model_highlight_path_changed)

		#============= Post-load settings =============
		load_succesfully = self.load_from_file(self._cur_file_path, show_dialog_on_problem=False) #Attempt to load from file
		if not load_succesfully:
			self.new_configuration(ignore_modified_window=True) #If loading failed -> reset to default

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

		self.ui.actionNewConfig.triggered.connect(self.new_configuration) #Set
			#to empty config

		self.ui.menuMDI_Area.removeAction(self.ui.actionNone) #Remove the "none" action from the mdi menu
		self.ui.ConfigurationMdiArea.add_actions_to_menu(self.ui.menuMDI_Area)

	def set_config_by_path(self, 
			config_import_location : str
		):
		"""
		Set the config import using a path to a module. This will import the module under name specified by 
		CONFIGURATION_MODULE_NAME and then look for a class that is a subclass of ConfigurationModel. If no such class
		is found, a ValueError is raised.

		Args:
			config_import_location (str): the location to import configs from
		"""
		# module = importlib.import_module(config_import_location)
		spec = importlib.util.spec_from_file_location(CONFIGURATION_MODULE_NAME, config_import_location)
		assert spec, f"Could not import config import module at location {config_import_location} - spec is None"
		module = importlib.util.module_from_spec(spec)
		assert module, f"Could not import config import module at location {config_import_location} - module is None"
		if spec.name in sys.modules:
			log.warning(f"Module {spec.name} already in sys.modules when import Configuration module, overwriting it.")
		sys.modules[spec.name] = module #NOTE: this overwrites any existing module with the same name
		spec.loader.exec_module(module)

		#List classes in module
		classes = inspect.getmembers(module, inspect.isclass)
		for cur_class in classes:
			if issubclass(cur_class[1], ConfigurationModel):
				self._config_class = cur_class[1]
				return
		
		raise ValueError(f"Could not find a class in specified module {config_import_location} that is a subclass of \
			ConfigurationModel")

	def set_config_by_class(self, config_class : typing.Type[ConfigurationModel]):
		"""Sets the config import using a class type. This class should be a subclass of ConfigurationModel.
		
		Args:
			config_class (typing.Type[ConfigurationModel]): the class to use for importing configs, should be a subclass
				of ConfigurationModel. 
		"""
		assert issubclass(config_class, ConfigurationModel), f"Config class {config_class} is not a subclass of \
			ConfigurationModel"
		self._config_class = config_class


	def option_proxy_models_changed(self, dict_of_models : typing.Dict[str, QtCore.QSortFilterProxyModel]) -> None:
		"""Upon change of (one of) the dataclass editors -> update the console"""

		for option_name, option_model in dict_of_models.items():
			if option_name in self._cur_option_proxy_models:
				#check if the same model is used
				if self._cur_option_proxy_models[option_name] == option_model:
					log.debug(f"Model for {option_name} has not changed, not updating its model or window")
				else:
					self._cur_option_proxy_models[option_name] = option_model
					self._cur_option_tree_view[option_name].setModel(option_model)
			else: #Create a new mdi window
				self._cur_option_mdi_windows[option_name] = FramelessMdiWindow()
				# self._cur_option_mdi_windows[option_name].
				#TODO: add title to mdi window
				self._cur_option_proxy_models[option_name] = option_model
				self._cur_option_tree_view[option_name] = QtWidgets.QTreeView()
				self._cur_option_tree_view[option_name].setModel(option_model)
				self._cur_option_tree_view[option_name].setItemDelegate(DataClassEditorsDelegate())#Set custom delegate
				self._cur_option_mdi_windows[option_name].setWidget(self._cur_option_tree_view[option_name])
				self._mdi_area.addSubWindow(self._cur_option_mdi_windows[option_name])
				self._cur_option_mdi_windows[option_name].setWindowTitle(option_name.title().replace("_", " "))
				self._cur_option_mdi_windows[option_name].show()

				# self.


		#re-tile the mdi windows
		# for window in self._mdi_area.subWindowList():
		# 	window.show()
		# 	# window.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
		# 	# window.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
		# 	# window.setWindowFlags(QtCore.Qt.WindowType.CustomizeWindowHint | QtCore.Qt.WindowType.FramelessWindowHint)
		# 	window.setContentsMargins(0, 0, 0, 0)
		# self._mdi_area.tileSubWindows()

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
		self.ml_queue_model = RunQueueTableModel(self._run_queue)

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




	# def reset_splitter_states(self):
	# 	"""
	# 	Resets the state of all splitters to the default state
	# 	"""
	# 	for splitter in self.window.findChildren(QtWidgets.QSplitter):
	# 		if splitter.objectName() in self._default_splitter_states.keys():
	# 			splitter.restoreState(self._default_splitter_states[splitter.objectName()])

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
		# for tree_view_name, tree_view in self._treeviews.items():
		# 	self._settings.setValue(f"{tree_view_name}_geometry", tree_view.geometry())


		# for splitter in self.window.findChildren(QtWidgets.QSplitter): #Save the state of all splitters
		# 	self._settings.setValue(f"splitter_state_{splitter.objectName()}", splitter.saveState())




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
			new_msg = QtWidgets.QMessageBox()
			new_msg.setWindowTitle("Warning")
			new_msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
			new_msg.setText("The current config has unsaved changed, do you want to overwrite them with a new config?")
			new_msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
			new_msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
			new_msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)
			ret = new_msg.exec()
			if ret == QtWidgets.QMessageBox.StandardButton.No:
				self._config_file_picker_model.set_hightlight_using_path(self._cur_file_path) #Hightlight path -> original
				return

		self.window.setWindowModified(False)
		self._cur_file_path = None
		self._config_file_picker_model.reset_hightlight()
		self._config_model.reset_configuration_data_to_default()

		self.window.setWindowModified(False)
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
			if self._config_file_picker_model.get_hightlight_path() != new_path:
				self._config_file_picker_model.set_hightlight_using_path(self._cur_file_path) #Do update the highlight path
			return True #Ignore -> but action was successful

		if self.window.isWindowModified():
			msg = QtWidgets.QMessageBox()
			msg.setWindowTitle("Warning")
			msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
			msg.setText("The current config has unsaved changed, do you want to overwrite them with this new config?")
			msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
			msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
			msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)
			ret = msg.exec()
			if ret == QtWidgets.QMessageBox.StandardButton.No:
				self._config_file_picker_model.set_hightlight_using_path(self._cur_file_path) #Hightlight path -> original
				return False

		self._cur_file_path = new_path
		self._cur_source = OptionsSource.FILE
		self._config_file_picker_model.set_hightlight_using_path(self._cur_file_path) #Also update the highlight path
		log.debug(f"Started trying to load config from {new_path}")
		try:
			if new_path:
				problem_dict = {}
				try: #First try loading using class-type keys that are inside the json file
					problem_dict = self._config_model.load_json_from(new_path)
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
					button_cancel = msg.addButton("Cancel", QtWidgets.QMessageBox.ButtonRole.RejectRole)
					msg.setDetailedText(str(exception.args[-1]))


					msg.exec()
					if msg.clickedButton() == button_deduce: #Deduce
						problem_dict = self._config_model.load_json_from(new_path, load_using_classtypes_key=False)
					elif msg.clickedButton() == button_discard: #Discard
						problem_dict = self._config_model.load_json_from(new_path, ignore_unknown_option_types=True)
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
				self._config_file_picker_model.set_hightlight_using_path(new_path)
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
			self._config_file_picker_model.reset_hightlight()
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

		if hasattr(self._config_model, "experiment_name"): #If experiment name is set -> use that
			return self._config_model.experiment_name

		# name = ""
		# name += ("_" + self._config_model.data_class) if self._config_model.data_class else ""
		# name += ("_" + self._config_model.task) if self._config_model.task else ""
		# name += ("_" + self._config_model.model) if self._config_model.model else ""
		return "new_config"

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
			self.ml_queue_model.add_to_queue(name, self._config_model.get_configuration_data_copy())

	def undo_triggered(self):
		"""
		Triggered when undo is clicked. Undoes the last change to the options
		"""
		log.info("Undo triggered")
		if self._config_model.undo_stack:
			self._config_model.undo_stack.undo()

	def redo_triggered(self):
		"""
		Triggered when redo is clicked. Redoes the last change to the options
		"""

		log.info("Redo triggered")
		if self._config_model.undo_stack:
			self._config_model.undo_stack.redo()

	def save_config_triggered(self) -> bool:
		"""Save the config to the current file path. If no file path is set, calls save_config_as_triggered instead.

		Returns:
			bool: Whether the save was successful
		"""
		log.info("Save triggered")
		if self._cur_file_path is None or (self._cur_source != OptionsSource.FILE):
			ret = self.save_config_as_triggered() #Already cleans undo-stack if successful
		else:
			ret = self._config_model.save_json_to(self._cur_file_path)
			if ret and self._config_model.undo_stack: #If save was successful -> set clean state
				self._config_model.undo_stack.setClean()
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
			self._config_file_picker_model.set_hightlight_using_path(self._cur_file_path) #Also update the highlighted path
			ret = self._config_model.save_json_to(file_path)
			log.info(f"Save as returned {ret}")
			if ret and self._config_model.undo_stack: #If save was successful -> set clean state
				self._config_model.undo_stack.setClean()
				self.window.setWindowModified(False)
		else:
			log.info("No Save Path Selected")
		return ret
			#TODO: set selection to current file

if __name__ == "__main__":
	app = QtWidgets.QApplication([])
	main_window = QtWidgets.QMainWindow()
	queue = RunQueue()
	ml_window = MainWindow(run_queue=queue, window=main_window)
	main_window.show()
	app.exec()
