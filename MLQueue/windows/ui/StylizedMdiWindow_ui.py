# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'StylizedMdiWindow.ui'
##
## Created by: Qt User Interface Compiler version 6.5.0
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)
import app_resources_rc

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(981, 655)
        self.verticalLayout_2 = QVBoxLayout(Form)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.titleBarFrame = QFrame(Form)
        self.titleBarFrame.setObjectName(u"titleBarFrame")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.titleBarFrame.sizePolicy().hasHeightForWidth())
        self.titleBarFrame.setSizePolicy(sizePolicy)
        self.titleBarFrame.setFrameShape(QFrame.StyledPanel)
        self.titleBarFrame.setFrameShadow(QFrame.Sunken)
        self.titleBarFrame.setLineWidth(3)
        self.verticalLayout_4 = QVBoxLayout(self.titleBarFrame)
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.titleLabel = QLabel(self.titleBarFrame)
        self.titleLabel.setObjectName(u"titleLabel")
        font = QFont()
        font.setBold(True)
        self.titleLabel.setFont(font)

        self.horizontalLayout.addWidget(self.titleLabel)

        self.MinimizeButton = QPushButton(self.titleBarFrame)
        self.MinimizeButton.setObjectName(u"MinimizeButton")
        sizePolicy1 = QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.MinimizeButton.sizePolicy().hasHeightForWidth())
        self.MinimizeButton.setSizePolicy(sizePolicy1)
        icon = QIcon()
        icon.addFile(u":/Icons/icons/actions/list-remove.png", QSize(), QIcon.Normal, QIcon.Off)
        self.MinimizeButton.setIcon(icon)
        self.MinimizeButton.setIconSize(QSize(15, 15))
        self.MinimizeButton.setFlat(True)

        self.horizontalLayout.addWidget(self.MinimizeButton)

        self.zoomButton = QPushButton(self.titleBarFrame)
        self.zoomButton.setObjectName(u"zoomButton")
        sizePolicy1.setHeightForWidth(self.zoomButton.sizePolicy().hasHeightForWidth())
        self.zoomButton.setSizePolicy(sizePolicy1)
        icon1 = QIcon()
        icon1.addFile(u":/Icons/icons/actions/system-search.png", QSize(), QIcon.Normal, QIcon.Off)
        self.zoomButton.setIcon(icon1)
        self.zoomButton.setIconSize(QSize(15, 15))
        self.zoomButton.setFlat(True)

        self.horizontalLayout.addWidget(self.zoomButton)

        self.horizontalLayout.setStretch(0, 1)

        self.verticalLayout_4.addLayout(self.horizontalLayout)


        self.verticalLayout.addWidget(self.titleBarFrame)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)


        self.verticalLayout.addLayout(self.verticalLayout_3)

        self.verticalLayout.setStretch(1, 1)

        self.verticalLayout_2.addLayout(self.verticalLayout)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.titleLabel.setText(QCoreApplication.translate("Form", u"WindowTitle", None))
        self.MinimizeButton.setText("")
        self.zoomButton.setText("")
    # retranslateUi

