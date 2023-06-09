import typing
from PySide6 import QtWidgets, QtCore, QtGui
import os
from enum import Enum
from MLQueue.NetworkLoginWidget.NetworkLoginWidget_ui import Ui_NetworkLoginWidget
from dataclasses import dataclass

@dataclass
class NetworkState(QtCore.QObject):
	stateChanged = QtCore.Signal()

	connected : bool = False
	connected_ip : str = ""
	connected_port : str = ""





class NetworkLoginWidget(QtWidgets.QWidget):
	#A controller to manage the machine learning window
	disconnectClicked = QtCore.Signal()
	connectClicked = QtCore.Signal(str, str, str) #IP, port, password
	cancelClicked = QtCore.Signal()


	def __init__(self, widget : QtWidgets.QWidget, settings : QtCore.QSettings) -> None:
		super().__init__()
		self._ui = Ui_NetworkLoginWidget()
		self._ui.setupUi(widget)
		self._settings = settings

		self.server_ip_history : list[str] = self._settings.value("server_ip_history", []) # type: ignore
		self.server_port_history : list[str] = self._settings.value("server_port_history", []) # type: ignore

		self._ui.serverIPComboBox.addItems(self.server_ip_history)
		self._ui.serverPortComboBox.addItems(self.server_port_history)

		#Set password-input to be a password input
		self._ui.serverPasswordLineEdit.setEchoMode(QtWidgets.QLineEdit.Password)

		self._history_max_count = 10
		self._ui.disconnectBtn.clicked.connect(self.disconnectClicked)
		self._ui.connectBtn.clicked.connect(lambda : self.connectClicked.emit(
			self._ui.serverIPComboBox.lineEdit().text(),
			self._ui.serverPortComboBox.lineEdit().text(),
			self._ui.serverPasswordLineEdit.text()
		))

		#Updates the history of the combobox (keeps max_count in account as well as duplicates)
		self._ui.serverIPComboBox.lineEdit().editingFinished.connect(lambda : self.comboBoxTextChanged(self._ui.serverIPComboBox, self.server_ip_history))
		self._ui.serverPortComboBox.lineEdit().editingFinished.connect(lambda : self.comboBoxTextChanged(self._ui.serverPortComboBox, self.server_port_history))
		
		self._ui.cancelBtn.clicked.connect(self.cancelClicked)

	#Pyqt slot that accept a triplet of strings (ip, port, password)
	@QtCore.Slot(str, str, str)
	def client_connected(self, ip : str, port : str, password : str) -> None:
		self._ui.serverIPComboBox.lineEdit().setText(ip)
		self._ui.serverPortComboBox.lineEdit().setText(port)
		self._ui.serverPasswordLineEdit.setText(password) #NOTE: we should probably put some nonsense here and use hash
		
		self._ui.serverIPComboBox.setEnabled(False)
		self._ui.serverPortComboBox.setEnabled(False)
		self._ui.serverPasswordLineEdit.setEnabled(False)
		
		self._ui.connectBtn.setEnabled(False)
		self._ui.disconnectBtn.setEnabled(True)

	@QtCore.Slot()
	def client_disconnected(self) -> None:
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


	def save_histories(self) -> None:
		self._settings.setValue("server_ip_history", self.server_ip_history)
		self._settings.setValue("server_port_history", self.server_port_history)

	def comboBoxTextChanged(self, combobox : QtWidgets.QComboBox, history_list : list):
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
	window = QtWidgets.QMainWindow()
	widget = QtWidgets.QWidget()
	loging_widget = NetworkLoginWidget(widget, QtCore.QSettings())
	loging_widget.client_connected("connectedip", "connectedport", "connectedpassword")
	window.setCentralWidget(widget)
	window.show()
	sys.exit(app.exec())