# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'NetworkLoginWidget.ui'
##
## Created by: Qt User Interface Compiler version 6.5.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_NetworkLoginWidget(object):
    def setupUi(self, NetworkLoginWidget):
        if not NetworkLoginWidget.objectName():
            NetworkLoginWidget.setObjectName(u"NetworkLoginWidget")
        NetworkLoginWidget.resize(452, 154)
        self.verticalLayout = QVBoxLayout(NetworkLoginWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.label = QLabel(NetworkLoginWidget)
        self.label.setObjectName(u"label")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)

        self.serverIPComboBox = QComboBox(NetworkLoginWidget)
        self.serverIPComboBox.setObjectName(u"serverIPComboBox")
        self.serverIPComboBox.setEditable(True)

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.serverIPComboBox)

        self.label_2 = QLabel(NetworkLoginWidget)
        self.label_2.setObjectName(u"label_2")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_2)

        self.serverPortComboBox = QComboBox(NetworkLoginWidget)
        self.serverPortComboBox.setObjectName(u"serverPortComboBox")
        self.serverPortComboBox.setEditable(True)

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.serverPortComboBox)

        self.label_3 = QLabel(NetworkLoginWidget)
        self.label_3.setObjectName(u"label_3")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.label_3)

        self.serverPasswordLineEdit = QLineEdit(NetworkLoginWidget)
        self.serverPasswordLineEdit.setObjectName(u"serverPasswordLineEdit")
        self.serverPasswordLineEdit.setEchoMode(QLineEdit.Normal)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.serverPasswordLineEdit)


        self.verticalLayout.addLayout(self.formLayout)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.cancelBtn = QPushButton(NetworkLoginWidget)
        self.cancelBtn.setObjectName(u"cancelBtn")

        self.horizontalLayout.addWidget(self.cancelBtn)

        self.disconnectBtn = QPushButton(NetworkLoginWidget)
        self.disconnectBtn.setObjectName(u"disconnectBtn")

        self.horizontalLayout.addWidget(self.disconnectBtn)

        self.connectBtn = QPushButton(NetworkLoginWidget)
        self.connectBtn.setObjectName(u"connectBtn")

        self.horizontalLayout.addWidget(self.connectBtn)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.verticalLayout.setStretch(0, 1)

        self.retranslateUi(NetworkLoginWidget)

        QMetaObject.connectSlotsByName(NetworkLoginWidget)
    # setupUi

    def retranslateUi(self, NetworkLoginWidget):
        NetworkLoginWidget.setWindowTitle(QCoreApplication.translate("NetworkLoginWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("NetworkLoginWidget", u"Server IP:", None))
        self.label_2.setText(QCoreApplication.translate("NetworkLoginWidget", u"Server Port:", None))
        self.label_3.setText(QCoreApplication.translate("NetworkLoginWidget", u"Password", None))
        self.cancelBtn.setText(QCoreApplication.translate("NetworkLoginWidget", u"Cancel", None))
        self.disconnectBtn.setText(QCoreApplication.translate("NetworkLoginWidget", u"Disconnect", None))
        self.connectBtn.setText(QCoreApplication.translate("NetworkLoginWidget", u"Connect", None))
    # retranslateUi

