# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MLQueueWidget.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QHeaderView, QPushButton,
    QSizePolicy, QSpacerItem, QToolButton, QVBoxLayout,
    QWidget)

from MLQueue.windows.views.RunQueueTreeView import RunQueueTreeView
from PySide6Widgets.Widgets.SquareFrame import SquareFrame
import app_resources_rc

class Ui_MLQueueWidget(object):
    def setupUi(self, MLQueueWidget):
        if not MLQueueWidget.objectName():
            MLQueueWidget.setObjectName(u"MLQueueWidget")
        MLQueueWidget.resize(647, 548)
        self.verticalLayout = QVBoxLayout(MLQueueWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.squareFrame_3 = SquareFrame(MLQueueWidget)
        self.squareFrame_3.setObjectName(u"squareFrame_3")
        self.verticalLayout_5 = QVBoxLayout(self.squareFrame_3)
        self.verticalLayout_5.setSpacing(0)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.MoveUpInQueueBtn = QPushButton(self.squareFrame_3)
        self.MoveUpInQueueBtn.setObjectName(u"MoveUpInQueueBtn")
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.MoveUpInQueueBtn.sizePolicy().hasHeightForWidth())
        self.MoveUpInQueueBtn.setSizePolicy(sizePolicy)
        self.MoveUpInQueueBtn.setMinimumSize(QSize(50, 50))
        self.MoveUpInQueueBtn.setSizeIncrement(QSize(1, 1))
        icon = QIcon()
        icon.addFile(u":/Icons/icons/Tango Icons/32x32/actions/go-up.png", QSize(), QIcon.Normal, QIcon.Off)
        self.MoveUpInQueueBtn.setIcon(icon)
        self.MoveUpInQueueBtn.setIconSize(QSize(25, 25))

        self.verticalLayout_5.addWidget(self.MoveUpInQueueBtn)


        self.horizontalLayout.addWidget(self.squareFrame_3)

        self.squareFrame_4 = SquareFrame(MLQueueWidget)
        self.squareFrame_4.setObjectName(u"squareFrame_4")
        self.verticalLayout_6 = QVBoxLayout(self.squareFrame_4)
        self.verticalLayout_6.setSpacing(0)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.MoveDownInQueueBtn = QPushButton(self.squareFrame_4)
        self.MoveDownInQueueBtn.setObjectName(u"MoveDownInQueueBtn")
        sizePolicy.setHeightForWidth(self.MoveDownInQueueBtn.sizePolicy().hasHeightForWidth())
        self.MoveDownInQueueBtn.setSizePolicy(sizePolicy)
        self.MoveDownInQueueBtn.setMinimumSize(QSize(50, 50))
        self.MoveDownInQueueBtn.setSizeIncrement(QSize(1, 1))
        icon1 = QIcon()
        icon1.addFile(u":/Icons/icons/Tango Icons/32x32/actions/go-down.png", QSize(), QIcon.Normal, QIcon.Off)
        self.MoveDownInQueueBtn.setIcon(icon1)
        self.MoveDownInQueueBtn.setIconSize(QSize(25, 25))

        self.verticalLayout_6.addWidget(self.MoveDownInQueueBtn)


        self.horizontalLayout.addWidget(self.squareFrame_4)

        self.squareFrame_5 = SquareFrame(MLQueueWidget)
        self.squareFrame_5.setObjectName(u"squareFrame_5")
        self.verticalLayout_7 = QVBoxLayout(self.squareFrame_5)
        self.verticalLayout_7.setSpacing(0)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.CancelStopButton = QPushButton(self.squareFrame_5)
        self.CancelStopButton.setObjectName(u"CancelStopButton")
        sizePolicy.setHeightForWidth(self.CancelStopButton.sizePolicy().hasHeightForWidth())
        self.CancelStopButton.setSizePolicy(sizePolicy)
        self.CancelStopButton.setMinimumSize(QSize(50, 50))
        self.CancelStopButton.setSizeIncrement(QSize(1, 1))
        icon2 = QIcon()
        icon2.addFile(u":/Icons/icons/Tango Icons/32x32/actions/process-stop.png", QSize(), QIcon.Normal, QIcon.Off)
        self.CancelStopButton.setIcon(icon2)
        self.CancelStopButton.setIconSize(QSize(25, 25))

        self.verticalLayout_7.addWidget(self.CancelStopButton)


        self.horizontalLayout.addWidget(self.squareFrame_5)

        self.squareFrame_6 = SquareFrame(MLQueueWidget)
        self.squareFrame_6.setObjectName(u"squareFrame_6")
        self.verticalLayout_8 = QVBoxLayout(self.squareFrame_6)
        self.verticalLayout_8.setSpacing(0)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.DeleteButton = QPushButton(self.squareFrame_6)
        self.DeleteButton.setObjectName(u"DeleteButton")
        sizePolicy.setHeightForWidth(self.DeleteButton.sizePolicy().hasHeightForWidth())
        self.DeleteButton.setSizePolicy(sizePolicy)
        self.DeleteButton.setMinimumSize(QSize(50, 50))
        self.DeleteButton.setSizeIncrement(QSize(1, 1))
        icon3 = QIcon()
        icon3.addFile(u":/Icons/icons/Tango Icons/32x32/places/user-trash.png", QSize(), QIcon.Normal, QIcon.Off)
        self.DeleteButton.setIcon(icon3)
        self.DeleteButton.setIconSize(QSize(25, 25))

        self.verticalLayout_8.addWidget(self.DeleteButton)


        self.horizontalLayout.addWidget(self.squareFrame_6)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.squareFrame = SquareFrame(MLQueueWidget)
        self.squareFrame.setObjectName(u"squareFrame")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.squareFrame.sizePolicy().hasHeightForWidth())
        self.squareFrame.setSizePolicy(sizePolicy1)
        self.verticalLayout_3 = QVBoxLayout(self.squareFrame)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.StartRunningQueueBtn = QPushButton(self.squareFrame)
        self.StartRunningQueueBtn.setObjectName(u"StartRunningQueueBtn")
        sizePolicy2 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.StartRunningQueueBtn.sizePolicy().hasHeightForWidth())
        self.StartRunningQueueBtn.setSizePolicy(sizePolicy2)
        self.StartRunningQueueBtn.setMinimumSize(QSize(50, 50))
        icon4 = QIcon()
        icon4.addFile(u":/Icons/icons/Tango Icons/32x32/actions/media-playback-start.png", QSize(), QIcon.Normal, QIcon.Off)
        icon4.addFile(u":/Icons/icons/media-playback-started.png", QSize(), QIcon.Normal, QIcon.On)
        self.StartRunningQueueBtn.setIcon(icon4)
        self.StartRunningQueueBtn.setIconSize(QSize(25, 25))
        self.StartRunningQueueBtn.setCheckable(True)

        self.verticalLayout_3.addWidget(self.StartRunningQueueBtn)


        self.horizontalLayout.addWidget(self.squareFrame)

        self.squareFrame_2 = SquareFrame(MLQueueWidget)
        self.squareFrame_2.setObjectName(u"squareFrame_2")
        self.verticalLayout_4 = QVBoxLayout(self.squareFrame_2)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.toolButton_2 = QToolButton(self.squareFrame_2)
        self.toolButton_2.setObjectName(u"toolButton_2")
        sizePolicy2.setHeightForWidth(self.toolButton_2.sizePolicy().hasHeightForWidth())
        self.toolButton_2.setSizePolicy(sizePolicy2)
        self.toolButton_2.setSizeIncrement(QSize(25, 25))
        self.toolButton_2.setBaseSize(QSize(25, 25))
        icon5 = QIcon()
        icon5.addFile(u":/Icons/icons/Tango Icons/32x32/categories/preferences-system.png", QSize(), QIcon.Normal, QIcon.Off)
        self.toolButton_2.setIcon(icon5)
        self.toolButton_2.setIconSize(QSize(25, 25))

        self.verticalLayout_4.addWidget(self.toolButton_2)


        self.horizontalLayout.addWidget(self.squareFrame_2)


        self.horizontalLayout_2.addLayout(self.horizontalLayout)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.QueueViewLayout = QVBoxLayout()
        self.QueueViewLayout.setObjectName(u"QueueViewLayout")
        self.queueView = RunQueueTreeView(MLQueueWidget)
        self.queueView.setObjectName(u"queueView")

        self.QueueViewLayout.addWidget(self.queueView)


        self.verticalLayout.addLayout(self.QueueViewLayout)

        self.verticalLayout.setStretch(1, 1)

        self.retranslateUi(MLQueueWidget)

        QMetaObject.connectSlotsByName(MLQueueWidget)
    # setupUi

    def retranslateUi(self, MLQueueWidget):
        MLQueueWidget.setWindowTitle(QCoreApplication.translate("MLQueueWidget", u"Form", None))
#if QT_CONFIG(tooltip)
        self.MoveUpInQueueBtn.setToolTip(QCoreApplication.translate("MLQueueWidget", u"Move item up in Queue", None))
#endif // QT_CONFIG(tooltip)
        self.MoveUpInQueueBtn.setText("")
#if QT_CONFIG(tooltip)
        self.MoveDownInQueueBtn.setToolTip(QCoreApplication.translate("MLQueueWidget", u"Move item down in Queue", None))
#endif // QT_CONFIG(tooltip)
        self.MoveDownInQueueBtn.setText("")
#if QT_CONFIG(tooltip)
        self.CancelStopButton.setToolTip(QCoreApplication.translate("MLQueueWidget", u"Dequeue/Stop item", None))
#endif // QT_CONFIG(tooltip)
        self.CancelStopButton.setText("")
#if QT_CONFIG(tooltip)
        self.DeleteButton.setToolTip(QCoreApplication.translate("MLQueueWidget", u"Delete item", None))
#endif // QT_CONFIG(tooltip)
        self.DeleteButton.setText("")
#if QT_CONFIG(tooltip)
        self.StartRunningQueueBtn.setToolTip(QCoreApplication.translate("MLQueueWidget", u"Start automatic run-mode", None))
#endif // QT_CONFIG(tooltip)
        self.StartRunningQueueBtn.setText("")
        self.toolButton_2.setText(QCoreApplication.translate("MLQueueWidget", u"...", None))
    # retranslateUi

