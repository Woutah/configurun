

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


import typing

from MLQueue.windows.ApplyMachineLearningWindow import ApplyMachineLearningWindow
from gui.NetworkLoginWidget.NetworkLoginWidget import NetworkLoginWidget
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6Widgets.Utility.catchExceptionInMsgBoxDecorator import \
    catchExceptionInMsgBoxDecorator
from PySide6Widgets.Utility.DataClassEditorsDelegate import \
    DataClassEditorsDelegate
# from MachineLearning.framework.
from res import Paths

from MLQueue.classes.RunQueue import RunQueue
from MLQueue.classes.RunQueueClient import RunQueueClient
from MLQueue.windows.models.MLQueueModel import MLQueueModel
# from gui.ApplyMachineLearningWindow.ApplyMachineLearningWindow_ui import Ui_ApplyMachineLearningWindow
from MLQueue.windows.ui.ApplyMachineLearningWindow_ui import \
    Ui_ApplyMachineLearningWindow
from MLQueue.windows.widgets.MLQueueWidget import MLQueueWidget


class NetworkApplyMachineLearningWindow(ApplyMachineLearningWindow):
	"""
	UI for networking differs somewhat from the local-running UI - for ease of use, we separate the code.
	"""

	def __init__(self, run_queue_client : RunQueueClient, window: QtWidgets.QMainWindow) -> None:
		super().__init__(run_queue=run_queue_client, window=window)
		assert(type(self._run_queue) == RunQueueClient) #Make sure we're using the right type of queue
		self._run_queue : RunQueueClient = self._run_queue #For Type hinting

		#=================== Network UI ======================
		self.reconnect_button_1, self._task_queue_overlay_msg = self.get_connection_overlay_ui()
		self.reconnect_button_2, self._console_overlay_msg = self.get_connection_overlay_ui()


		self.ml_overlay_widget = self.ui.MLQueueWidget
		self.console_overlay_widget = self.ui.ConsoleOverlayWidget

		self.ml_overlay_widget.setOverlayWidget(self._task_queue_overlay_msg)
		self.console_overlay_widget.setOverlayWidget(self._console_overlay_msg)

		self.console_overlay_widget.setOverlayHidden(False)
		self.ml_overlay_widget.setOverlayHidden(False)


		# self.ui.menubar.removeEventFilter(self.ui.menusource)
		self.ui.menubar.removeAction(self.ui.actionSetLocalRunMode)
		self.ui.menubar.removeAction(self.ui.actionSetNetworkRunMode)
		self.ui.actionSetLocalRunMode.deleteLater()
		self.ui.actionSetNetworkRunMode.deleteLater()
		self.ui.menusource.deleteLater()

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
		# self.connection_window.setCentralWidget(self.network_connection_widget)
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


	@catchExceptionInMsgBoxDecorator
	def connect_to_server(self, ip : str, port : str, password : str) -> None:
		self._run_queue.connect_to_server(server_ip=ip, server_port=int(port), password=password)
		print("Connected to server!")

	@catchExceptionInMsgBoxDecorator
	def disconnect_from_server(self) -> None:
		self._run_queue.disconnect_clean_server()
		# raise NotImplementedError("Disconnecting from server not implemented yet...")

	def server_connection_state_changed(self, connected : bool) -> None:
		print(f"Connection state changed to {connected}, now updating UI...")
		log.info(f"Connection state changed to {connected}, now updating UI...")
		#=========== hide blocking overlays when connected ==========
		self.console_overlay_widget.setOverlayHidden(connected)
		self.ml_overlay_widget.setOverlayHidden(connected)

		
		#Update the connection window
		if connected:
			ip, port, pw = self._run_queue.get_connection_info()
			self.network_connection_widget.client_connected(ip, str(port), pw)
			self.connection_window.close()

			self.ml_queue_model.reset_model() #Re-request all data from the server
			self.window.statusBar().showMessage(f"Connected to {ip}:{port}", timeout=0) #Show message until next msg

		else:
			self.network_connection_widget.client_disconnected()
			self.connection_window.show()
			self.window.statusBar().showMessage("Not Connected", timeout=0) #Show message until next msg




	def closeEvent(self, event: QtGui.QCloseEvent) -> None:
		self.network_connection_widget.save_histories() #Also save file-edit history
		return super().closeEvent(event)


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
	
	# formatter = logging.Formatter("[{pathname:>90s}:{lineno:<4}] {levelname:<7s}   {message}", style='{')
	# log.propagate = False
	# handler = logging.StreamHandler()
	# handler.setFormatter(formatter)
	# logging.basicConfig(
	# 	handlers=[handler],
	# 	level=logging.DEBUG) #Without time
	app = QtWidgets.QApplication([])

	window = QtWidgets.QMainWindow()
	runqueue_client = RunQueueClient()
	ml_window = NetworkApplyMachineLearningWindow(runqueue_client, window)
	# window = QtWidgets.QWidget()
	window.show()
	app.exec()

