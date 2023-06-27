"""
Implements a widget for logging in to a server
"""


from PySide6 import QtCore, QtWidgets

from configurun.windows.ui.network_login_widget_ui import Ui_NetworkLoginWidget



class NetworkLoginWidget(QtWidgets.QWidget):
	"""A widget to control connection to a server:
		Input-fields: IP, port, password
		Buttons: connect, disconnect, cancel
	"""
	#A controller to manage the machine learning window
	disconnectClicked = QtCore.Signal()
	connectClicked = QtCore.Signal(str, str, str) #IP, port, password
	cancelClicked = QtCore.Signal()


	def __init__(self, widget : QtWidgets.QWidget, settings : QtCore.QSettings) -> None:
		super().__init__()
		self._ui = Ui_NetworkLoginWidget()
		self._ui.setupUi(widget)
		self._settings = settings

		self.server_ip_history : list[str] = self._settings.value("server_ip_history", None) # type: ignore
		self.server_port_history : list[str] = self._settings.value("server_port_history", None) # type: ignore
		if self.server_ip_history is None:
			self.server_ip_history = []
		if self.server_port_history is None:
			self.server_port_history = []
		assert isinstance(self.server_ip_history, list)
		assert isinstance(self.server_port_history, list)

		self._ui.serverIPComboBox.addItems(self.server_ip_history)
		self._ui.serverPortComboBox.addItems(self.server_port_history)

		#Set password-input to be a password input
		self._ui.serverPasswordLineEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

		self._history_max_count = 10
		self._ui.disconnectBtn.clicked.connect(self.disconnectClicked)
		self._ui.connectBtn.clicked.connect(lambda : self.connectClicked.emit(
			self._ui.serverIPComboBox.lineEdit().text(),
			self._ui.serverPortComboBox.lineEdit().text(),
			self._ui.serverPasswordLineEdit.text()
		))

		#Updates the history of the combobox (keeps max_count in account as well as duplicates)
		self._ui.serverIPComboBox.lineEdit().editingFinished.connect(
			lambda : self.combo_box_txt_changed(self._ui.serverIPComboBox, self.server_ip_history))
		self._ui.serverPortComboBox.lineEdit().editingFinished.connect(
			lambda : self.combo_box_txt_changed(self._ui.serverPortComboBox, self.server_port_history))

		self._ui.cancelBtn.clicked.connect(self.cancelClicked)

	#Pyqt slot that accept a triplet of strings (ip, port, password)
	@QtCore.Slot(str, str, str)
	def client_connected(self, server_ip : str, server_port : str, server_password : str) -> None:
		"""Disable the connect button and inputs and enable the disconnect button"""

		self._ui.serverIPComboBox.lineEdit().setText(server_ip)
		self._ui.serverPortComboBox.lineEdit().setText(server_port)
		self._ui.serverPasswordLineEdit.setText(server_password)

		self._ui.serverIPComboBox.setEnabled(False)
		self._ui.serverPortComboBox.setEnabled(False)
		self._ui.serverPasswordLineEdit.setEnabled(False)

		self._ui.connectBtn.setEnabled(False)
		self._ui.disconnectBtn.setEnabled(True)
		self._ui.cancelBtn.setDefault(True)

	@QtCore.Slot()
	def client_disconnected(self) -> None:
		"""Disable the disconnect button and enable the connect button and inputs"""
		self._ui.connectBtn.setEnabled(True)
		self._ui.disconnectBtn.setEnabled(False)

		self._ui.serverIPComboBox.setEnabled(True)
		self._ui.serverPortComboBox.setEnabled(True)
		self._ui.serverPasswordLineEdit.setEnabled(True)

		self._ui.serverIPComboBox.lineEdit().setText(
			self.server_ip_history[0] if len(self.server_ip_history) > 0 else ""
		)
		self._ui.serverPortComboBox.lineEdit().setText(
			self.server_port_history[0] if len(self.server_port_history) > 0 else ""
		)
		#Set connect button to be the default button
		self._ui.connectBtn.setDefault(True)


	def save_histories(self) -> None:
		"""Save the history of the comboboxes to the settings"""
		if len(self.server_ip_history) == 1: #TODO: somehow loading settings goes wrong if only 1 item in list
			self.server_ip_history.append('')
		if len(self.server_port_history) == 1:
			self.server_port_history.append('')

		self._settings.setValue("server_ip_history", self.server_ip_history)
		self._settings.setValue("server_port_history", self.server_port_history)

	def combo_box_txt_changed(self, combobox : QtWidgets.QComboBox, history_list : list):
		"""When the text in a combobox is changed, update the history list and the combobox

		Args:
			combobox (QtWidgets.QComboBox): The combobox that was changed
			history_list (list): The history list to update
		"""
		text = combobox.lineEdit().text()
		if text in history_list:
			history_list.remove(text)
		history_list.insert(0, text)
		if len(history_list) > self._history_max_count:
			history_list.pop(-1)

		combobox.clear()
		for address in history_list:
			combobox.addItem(address)


if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication(sys.argv)
	test_window = QtWidgets.QMainWindow()
	test_widget = QtWidgets.QWidget()
	loging_widget = NetworkLoginWidget(test_widget, QtCore.QSettings())
	loging_widget.client_connected("connectedip", "connectedport", "connectedpassword")
	test_window.setCentralWidget(test_widget)
	test_window.show()
	sys.exit(app.exec())
