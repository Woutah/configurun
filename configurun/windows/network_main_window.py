"""
Network-equivalent of main_window.py
Contains everything neccesary to run the UI in client-mode, enabling the user to connect to a remotely running
RunQueueServer (see MLQueue.classes.RunQueueServer) and run machine learning tasks on it.
"""

import logging
import typing

from PySide6 import QtCore, QtGui, QtWidgets
from pyside6_utils.utility.catch_show_exception_in_popup_decorator import \
    catch_show_exception_in_popup_decorator

from configurun.classes.run_queue_client import RunQueueClient
from configurun.configuration.configuration_model import ConfigurationModel
from configurun.windows.main_window import MainWindow
from configurun.windows.widgets.network_login_widget import NetworkLoginWidget

log = logging.getLogger(__name__)

class NetworkMainWindow(MainWindow):
	"""
	The main QT window for this app which provides the user with several tools to edit/manage/run machine learning
	settings.


	This is the Networked-equivalent of main_window.py and implements some extra functionality to connect to a remote
	RunQueueServer (see classes.RunQueueServer) and run machine learning tasks on it.

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
				run_queue_client : RunQueueClient,
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
		super().__init__(
			configuration_model=configuration_model,
			run_queue=run_queue_client,
			window=window,
			workspace_path=workspace_path,
			settings_in_workspace_path=settings_in_workspace_path
		)

		# assert(type(self._run_queue) == RunQueueClient) #Make sure we're using the right type of queue
		self._run_queue : RunQueueClient = self._run_queue #For Type hinting
		assert(isinstance(self._run_queue, RunQueueClient)) #Make sure we're using the right type of queue

		#=================== Network UI ======================
		self.reconnect_button_1, self._task_queue_overlay_msg = self.get_connection_overlay_ui()
		self.reconnect_button_2, self._console_overlay_msg = self.get_connection_overlay_ui()


		self.ml_overlay_widget = self.ui.runQueueOverlayWidget
		self.console_overlay_widget = self.ui.ConsoleOverlayWidget

		self.ml_overlay_widget.set_overlay_widget(self._task_queue_overlay_msg)
		self.console_overlay_widget.set_overlay_widget(self._console_overlay_msg)

		self.console_overlay_widget.set_overlay_hidden(False)
		self.ml_overlay_widget.set_overlay_hidden(False)

		#================== Network-specific menu ================

		self.menubar = self.ui.menubar
		self.connection_menu = QtWidgets.QMenu(self.menubar)
		self.connection_menu.setTitle("Connection")
		self.menubar.addAction(self.connection_menu.menuAction())
		self.open_connection_action = QtGui.QAction("Connection Settings", self.connection_menu)
		self.open_connection_action.setIcon(QtGui.QIcon(":/Icons/icons/places/network-workgroup.png"))
		self.connection_menu.addAction(self.open_connection_action)


		#=========== Connect/Disconnect window ==============
		self.connection_window = QtWidgets.QMainWindow(self.window)
		self.connection_window.setWindowTitle("Connection")
		self.connection_window.setWindowIcon(self.window.windowIcon())

		self.network_connection_parent = QtWidgets.QWidget()
		self.network_connection_widget = NetworkLoginWidget(self.network_connection_parent, self._settings)
		self.connection_window.setCentralWidget(self.network_connection_parent)
		self.server_connection_state_changed(self._run_queue.is_connected_and_authenticated()) #Set initial state


		#=========== Link connection view buttons to connection window ==============
		self._run_queue.authenConnectionStateChanged.connect(self.server_connection_state_changed)
		self.network_connection_widget.connectClicked.connect(self.connect_to_server)
		self.network_connection_widget.disconnectClicked.connect(self.disconnect_from_server)
		self.network_connection_widget.cancelClicked.connect(lambda *_: self.connection_window.close())
		self.network_connection_widget.cancelClicked.connect(lambda *_: self.network_connection_widget.save_histories())

		self.network_connection_widget.connectClicked.connect(
			lambda *_: self.network_connection_widget.save_histories()
		)

		self.reconnect_button_1.clicked.connect(self.connection_window.show)
		self.reconnect_button_2.clicked.connect(self.connection_window.show)
		#Also move window to front
		self.reconnect_button_1.clicked.connect(lambda *_: self.connection_window.activateWindow())
		self.reconnect_button_2.clicked.connect(lambda *_: self.connection_window.activateWindow())
		self.open_connection_action.triggered.connect(self.connection_window.show)



	def initial_run_queue_load(self) -> None:
		"""Since this is a client, don't load any RunQueue on startup."""

	def check_if_running_ask_stop_items_before_close(self) -> bool:
		"""Overloads the main_window function. Normally, the user shuts down the running items before closing the
		app. For clients this is not neccesary.
		"""
		return True

	@catch_show_exception_in_popup_decorator
	def connect_to_server(self, server_ip : str, server_port : str, server_password : str) -> None:
		"""
		Wrapper around the connect function of the run_queue which displays a message box when encountering an exception
		Args:
			server_ip (str): The ip of the server to connect to
			server_port (str): The port of the server to connect to
			server_password (str): The password to use for authentication
		"""
		self._run_queue.connect_to_server(server_ip=server_ip, server_port=int(server_port), password=server_password)
		print("Connected to server!")

	@catch_show_exception_in_popup_decorator
	def disconnect_from_server(self) -> None:
		"""
		Wrapper around the disconnect function of the run_queue which displays a message box on thrown exceptions.
		"""
		self._run_queue.disconnect_clean_server()

	def server_connection_state_changed(self, connected : bool) -> None:
		"""Update the UI to reflect the connection state, e.g. grey-out the task queue on disconnect as to
		indicate to the user that connection has been lost.

		Args:
			connected (bool): The new connection state (true=Authenticated connection)
		"""
		log.info(f"Connection state changed to {connected}, now updating UI...")
		#=========== hide blocking overlays when connected ==========
		self.console_overlay_widget.set_overlay_hidden(connected)
		self.ml_overlay_widget.set_overlay_hidden(connected)


		#Update the connection window
		if connected:
			cur_ip, cur_port, cur_pw = self._run_queue.get_connection_info()
			self.network_connection_widget.client_connected(cur_ip, str(cur_port), cur_pw)
			self.connection_window.close()

			self.run_queue_table_model.reset_model() #Re-request all data from the server
			self.window.statusBar().showMessage(f"Connected to {cur_ip}:{cur_port}", timeout=0) #Show message until next msg

		else:
			self.network_connection_widget.client_disconnected()
			self.connection_window.activateWindow()
			self.connection_window.show()
			self.window.statusBar().showMessage("Not Connected", timeout=0) #Show message until next msg




	def close_event(self, event: QtGui.QCloseEvent) -> None:
		self.network_connection_widget.save_histories() #Also save file-edit history
		self.disconnect_from_server() #Disconnect from server
		return super().close_event(event)


	@staticmethod
	def get_connection_overlay_ui() -> typing.Tuple[QtWidgets.QPushButton, QtWidgets.QWidget]:
		"Create a simple ui with a button to reconnect"
		overlay_widget = QtWidgets.QWidget()
		overlay_widget.setLayout(QtWidgets.QVBoxLayout())
		overlay_widget.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
		overlay_widget.layout().setContentsMargins(0,0,0,0)
		overlay_widget.layout().setSpacing(0)
		overlay_widget.layout().addWidget(QtWidgets.QLabel("No (authenticated) connection to server..."))
		reconnect_btn = QtWidgets.QPushButton("(Re)connect")
		overlay_widget.layout().addWidget(reconnect_btn)
		return reconnect_btn, overlay_widget


def run_example_network_app(log_level : int = logging.INFO) -> None:
	"""
	Runs an example-client that can connect to a running server. Uses the example_deduce_new_option_classes to
	generate example options for the client
	"""

	#pylint: disable=import-outside-toplevel
	import os
	import tempfile
	from configurun.create import client
	from configurun.examples import example_deduce_new_option_classes
	from configurun.windows.main_window import APP_NAME

	tempdir = tempfile.gettempdir()
	workspace_path = os.path.join(tempdir, APP_NAME, "Configurun-Client-App-Example")

	client(
		options_source=example_deduce_new_option_classes,
		workspace_path=workspace_path,
		log_level=log_level
	)


if __name__ == "__main__":
	run_example_network_app(log_level=logging.DEBUG)
