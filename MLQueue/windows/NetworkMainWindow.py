"""
Network-equivalent of main_window.py
Contains everything neccesary to run the UI in client-mode, enabling the user to connect to a remotely running
RunQueueServer (see MLQueue.classes.RunQueueServer) and run machine learning tasks on it.
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

#pylint: disable=wrong-import-position
import typing

from PySide6 import QtCore, QtGui, QtWidgets
from pyside6_utils.utility.catchExceptionInMsgBoxDecorator import \
    catch_show_exception_in_popup_decorator

from MLQueue.classes.RunQueueClient import RunQueueClient
from MLQueue.configuration.ConfigurationModel import ConfigurationModel
from MLQueue.windows.MainWindow import MainWindow
from MLQueue.windows.widgets.NetworkLoginWidget import NetworkLoginWidget


class NetworkMainWindow(MainWindow):
	"""
	UI for networking differs somewhat from the local-running UI - for ease of use, we separate the code.
	"""

	def __init__(self,
				configuration_model : ConfigurationModel,
				run_queue_client : RunQueueClient,
				window : QtWidgets.QMainWindow
			) -> None:
		super().__init__(configuration_model=configuration_model, run_queue=run_queue_client, window=window)
		# assert(type(self._run_queue) == RunQueueClient) #Make sure we're using the right type of queue
		self._run_queue : RunQueueClient = self._run_queue #For Type hinting

		#=================== Network UI ======================
		self.reconnect_button_1, self._task_queue_overlay_msg = self.get_connection_overlay_ui()
		self.reconnect_button_2, self._console_overlay_msg = self.get_connection_overlay_ui()


		self.ml_overlay_widget = self.ui.MLQueueWidget
		self.console_overlay_widget = self.ui.ConsoleOverlayWidget

		self.ml_overlay_widget.set_overlay_widget(self._task_queue_overlay_msg)
		self.console_overlay_widget.set_overlay_widget(self._console_overlay_msg)

		self.console_overlay_widget.set_overlay_hidden(False)
		self.ml_overlay_widget.set_overlay_hidden(False)

		#================== Network-specific menu ================

		self.menubar = self.ui.menubar
		self.connection_menu = QtWidgets.QMenu(self.menubar)
		self.connection_menu.setTitle("Connection...")
		self.menubar.addAction(self.connection_menu.menuAction())
		self.open_connection_action = QtGui.QAction("Connection Settings", self.connection_menu)
		self.connection_menu.addAction(self.open_connection_action)


		#=========== Connect/Disconnect window ==============
		self.connection_window = QtWidgets.QMainWindow()
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
		print(f"Connection state changed to {connected}, now updating UI...")
		log.info(f"Connection state changed to {connected}, now updating UI...")
		#=========== hide blocking overlays when connected ==========
		self.console_overlay_widget.set_overlay_hidden(connected)
		self.ml_overlay_widget.set_overlay_hidden(connected)


		#Update the connection window
		if connected:
			cur_ip, cur_port, cur_pw = self._run_queue.get_connection_info()
			self.network_connection_widget.client_connected(cur_ip, str(cur_port), cur_pw)
			self.connection_window.close()

			self.ml_queue_model.reset_model() #Re-request all data from the server
			self.window.statusBar().showMessage(f"Connected to {cur_ip}:{cur_port}", timeout=0) #Show message until next msg

		else:
			self.network_connection_widget.client_disconnected()
			self.connection_window.show()
			self.window.statusBar().showMessage("Not Connected", timeout=0) #Show message until next msg




	def close_event(self, event: QtGui.QCloseEvent) -> None:
		self.network_connection_widget.save_histories() #Also save file-edit history
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



if __name__ == "__main__":
	# Run Small tests using runqueue-client and example options
	from MLQueue.examples.ExampleConfiguration import \
	    deduce_new_option_class_types
	formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}] {levelname:<7s}   {message}", style='{')
	log.propagate = False
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logging.basicConfig(
		handlers=[handler],
		level=logging.DEBUG) #Without time
	app = QtWidgets.QApplication([])

	test_window = QtWidgets.QMainWindow()
	test_runqueue_client = RunQueueClient()
	test_configuration_model = ConfigurationModel(
		option_type_deduction_function=deduce_new_option_class_types
	)
	ml_window = NetworkMainWindow(
		configuration_model=test_configuration_model,
		run_queue_client=test_runqueue_client,
		window=test_window
	)
	test_window.show()
	app.exec()
