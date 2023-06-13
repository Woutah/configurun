# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ApplyMachineLearningWindow.ui'
##
## Created by: Qt User Interface Compiler version 6.5.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QDockWidget, QGridLayout, QHBoxLayout,
    QHeaderView, QMainWindow, QMdiArea, QMenu,
    QMenuBar, QPushButton, QSizePolicy, QStatusBar,
    QToolButton, QUndoView, QVBoxLayout, QWidget)

from PySide6Widgets.Widgets.ConsoleWidget import ConsoleWidget
from PySide6Widgets.Widgets.FileExplorerView import FileExplorerView
from PySide6Widgets.Widgets.OverlayWidget import OverlayWidget
from PySide6Widgets.Widgets.SquareFrame import SquareFrame
import app_resources_rc

class Ui_ApplyMachineLearningWindow(object):
    def setupUi(self, ApplyMachineLearningWindow):
        if not ApplyMachineLearningWindow.objectName():
            ApplyMachineLearningWindow.setObjectName(u"ApplyMachineLearningWindow")
        ApplyMachineLearningWindow.resize(2112, 1141)
        icon = QIcon()
        icon.addFile(u":/Icons/icons/Tango Icons/32x32/categories/preferences-desktop.png", QSize(), QIcon.Normal, QIcon.Off)
        ApplyMachineLearningWindow.setWindowIcon(icon)
        self.actionUndo = QAction(ApplyMachineLearningWindow)
        self.actionUndo.setObjectName(u"actionUndo")
        icon1 = QIcon()
        icon1.addFile(u":/Icons/icons/Tango Icons/32x32/actions/edit-undo.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionUndo.setIcon(icon1)
        self.actionRedo = QAction(ApplyMachineLearningWindow)
        self.actionRedo.setObjectName(u"actionRedo")
        icon2 = QIcon()
        icon2.addFile(u":/Icons/icons/Tango Icons/32x32/actions/edit-redo.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionRedo.setIcon(icon2)
        self.actionIncreaseFontSize = QAction(ApplyMachineLearningWindow)
        self.actionIncreaseFontSize.setObjectName(u"actionIncreaseFontSize")
        icon3 = QIcon()
        icon3.addFile(u":/Icons/icons/Tango Icons/32x32/actions/list-add.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionIncreaseFontSize.setIcon(icon3)
        self.actionDefaultFontSize = QAction(ApplyMachineLearningWindow)
        self.actionDefaultFontSize.setObjectName(u"actionDefaultFontSize")
        icon4 = QIcon()
        icon4.addFile(u":/Icons/icons/Tango Icons/32x32/actions/view-refresh.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionDefaultFontSize.setIcon(icon4)
        self.actionDecreaseFontSize = QAction(ApplyMachineLearningWindow)
        self.actionDecreaseFontSize.setObjectName(u"actionDecreaseFontSize")
        icon5 = QIcon()
        icon5.addFile(u":/Icons/icons/Tango Icons/32x32/actions/list-remove.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionDecreaseFontSize.setIcon(icon5)
        self.actionSave = QAction(ApplyMachineLearningWindow)
        self.actionSave.setObjectName(u"actionSave")
        icon6 = QIcon()
        icon6.addFile(u":/Icons/icons/Tango Icons/32x32/actions/document-save.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionSave.setIcon(icon6)
        self.actionSave_As = QAction(ApplyMachineLearningWindow)
        self.actionSave_As.setObjectName(u"actionSave_As")
        icon7 = QIcon()
        icon7.addFile(u":/Icons/icons/Tango Icons/32x32/actions/document-save-as.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionSave_As.setIcon(icon7)
        self.actionReset_Splitters = QAction(ApplyMachineLearningWindow)
        self.actionReset_Splitters.setObjectName(u"actionReset_Splitters")
        self.actionReset_Splitters.setIcon(icon4)
        self.actionSetLocalRunMode = QAction(ApplyMachineLearningWindow)
        self.actionSetLocalRunMode.setObjectName(u"actionSetLocalRunMode")
        self.actionSetLocalRunMode.setCheckable(True)
        self.actionSetLocalRunMode.setChecked(True)
        self.actionSetLocalRunMode.setEnabled(True)
        icon8 = QIcon()
        icon8.addFile(u":/Icons/icons/Tango Icons/32x32/actions/go-home.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionSetLocalRunMode.setIcon(icon8)
        self.actionSetNetworkRunMode = QAction(ApplyMachineLearningWindow)
        self.actionSetNetworkRunMode.setObjectName(u"actionSetNetworkRunMode")
        self.actionSetNetworkRunMode.setCheckable(True)
        icon9 = QIcon()
        icon9.addFile(u":/Icons/icons/Tango Icons/32x32/apps/internet-web-browser.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionSetNetworkRunMode.setIcon(icon9)
        self.actionNewConfig = QAction(ApplyMachineLearningWindow)
        self.actionNewConfig.setObjectName(u"actionNewConfig")
        self.centralwidget = QWidget(ApplyMachineLearningWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(9, 0, 0, 0)
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, -1, -1, -1)
        self.ConfigurationMdiArea = QMdiArea(self.centralwidget)
        self.ConfigurationMdiArea.setObjectName(u"ConfigurationMdiArea")

        self.verticalLayout_2.addWidget(self.ConfigurationMdiArea)

        self.addToQueueButton = QPushButton(self.centralwidget)
        self.addToQueueButton.setObjectName(u"addToQueueButton")
        icon10 = QIcon()
        icon10.addFile(u":/Icons/icons/Tango Icons/32x32/actions/format-indent-more.png", QSize(), QIcon.Normal, QIcon.Off)
        self.addToQueueButton.setIcon(icon10)

        self.verticalLayout_2.addWidget(self.addToQueueButton)


        self.verticalLayout.addLayout(self.verticalLayout_2)

        ApplyMachineLearningWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(ApplyMachineLearningWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 2112, 22))
        self.menuasdf = QMenu(self.menubar)
        self.menuasdf.setObjectName(u"menuasdf")
        self.menusource = QMenu(self.menubar)
        self.menusource.setObjectName(u"menusource")
        self.menusource.setEnabled(True)
        self.menuview = QMenu(self.menubar)
        self.menuview.setObjectName(u"menuview")
        self.menuSet_Font_Size = QMenu(self.menuview)
        self.menuSet_Font_Size.setObjectName(u"menuSet_Font_Size")
        icon11 = QIcon()
        icon11.addFile(u":/Icons/icons/Tango Icons/32x32/apps/preferences-desktop-font.png", QSize(), QIcon.Normal, QIcon.Off)
        self.menuSet_Font_Size.setIcon(icon11)
        ApplyMachineLearningWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(ApplyMachineLearningWindow)
        self.statusbar.setObjectName(u"statusbar")
        ApplyMachineLearningWindow.setStatusBar(self.statusbar)
        self.dockWidget = QDockWidget(ApplyMachineLearningWindow)
        self.dockWidget.setObjectName(u"dockWidget")
        icon12 = QIcon()
        icon12.addFile(u":/Icons/icons/savesymbol.png", QSize(), QIcon.Normal, QIcon.Off)
        self.dockWidget.setWindowIcon(icon12)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.gridLayout = QGridLayout(self.dockWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.saveCurrentConfigBtn = QPushButton(self.dockWidgetContents)
        self.saveCurrentConfigBtn.setObjectName(u"saveCurrentConfigBtn")
        self.saveCurrentConfigBtn.setIcon(icon6)

        self.horizontalLayout_6.addWidget(self.saveCurrentConfigBtn)

        self.saveCurrentConfigAsBtn = QPushButton(self.dockWidgetContents)
        self.saveCurrentConfigAsBtn.setObjectName(u"saveCurrentConfigAsBtn")
        self.saveCurrentConfigAsBtn.setIcon(icon7)

        self.horizontalLayout_6.addWidget(self.saveCurrentConfigAsBtn)

        self.squareFrame = SquareFrame(self.dockWidgetContents)
        self.squareFrame.setObjectName(u"squareFrame")
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.squareFrame.sizePolicy().hasHeightForWidth())
        self.squareFrame.setSizePolicy(sizePolicy)
        self.verticalLayout_13 = QVBoxLayout(self.squareFrame)
        self.verticalLayout_13.setSpacing(0)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.OpenFileLocationBtn = QToolButton(self.squareFrame)
        self.OpenFileLocationBtn.setObjectName(u"OpenFileLocationBtn")
        sizePolicy.setHeightForWidth(self.OpenFileLocationBtn.sizePolicy().hasHeightForWidth())
        self.OpenFileLocationBtn.setSizePolicy(sizePolicy)
        self.OpenFileLocationBtn.setMinimumSize(QSize(24, 24))
        icon13 = QIcon()
        icon13.addFile(u":/Icons/icons/Tango Icons/32x32/actions/document-open.png", QSize(), QIcon.Normal, QIcon.Off)
        self.OpenFileLocationBtn.setIcon(icon13)

        self.verticalLayout_13.addWidget(self.OpenFileLocationBtn)


        self.horizontalLayout_6.addWidget(self.squareFrame)

        self.horizontalLayout_6.setStretch(0, 100)
        self.horizontalLayout_6.setStretch(1, 100)

        self.verticalLayout_5.addLayout(self.horizontalLayout_6)

        self.ConfigFilePickerView = FileExplorerView(self.dockWidgetContents)
        self.ConfigFilePickerView.setObjectName(u"ConfigFilePickerView")

        self.verticalLayout_5.addWidget(self.ConfigFilePickerView)


        self.gridLayout.addLayout(self.verticalLayout_5, 0, 0, 1, 1)

        self.dockWidget.setWidget(self.dockWidgetContents)
        ApplyMachineLearningWindow.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget)
        self.dockWidget_3 = QDockWidget(ApplyMachineLearningWindow)
        self.dockWidget_3.setObjectName(u"dockWidget_3")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.dockWidget_3.sizePolicy().hasHeightForWidth())
        self.dockWidget_3.setSizePolicy(sizePolicy1)
        icon14 = QIcon()
        icon14.addFile(u":/Icons/icons/Tango Icons/32x32/categories/applications-development.png", QSize(), QIcon.Normal, QIcon.Off)
        self.dockWidget_3.setWindowIcon(icon14)
        self.dockWidgetContents_3 = QWidget()
        self.dockWidgetContents_3.setObjectName(u"dockWidgetContents_3")
        self.verticalLayout_4 = QVBoxLayout(self.dockWidgetContents_3)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.MLQueueWidget = OverlayWidget(self.dockWidgetContents_3)
        self.MLQueueWidget.setObjectName(u"MLQueueWidget")
        self.MLQueueWidget.setProperty("overlayHidden", True)

        self.verticalLayout_4.addWidget(self.MLQueueWidget)

        self.dockWidget_3.setWidget(self.dockWidgetContents_3)
        ApplyMachineLearningWindow.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget_3)
        self.UndoStack = QDockWidget(ApplyMachineLearningWindow)
        self.UndoStack.setObjectName(u"UndoStack")
        self.UndoStack.setWindowIcon(icon1)
        self.dockWidgetContents_4 = QWidget()
        self.dockWidgetContents_4.setObjectName(u"dockWidgetContents_4")
        self.gridLayout_2 = QGridLayout(self.dockWidgetContents_4)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.undoView = QUndoView(self.dockWidgetContents_4)
        self.undoView.setObjectName(u"undoView")

        self.gridLayout_2.addWidget(self.undoView, 0, 0, 1, 1)

        self.UndoStack.setWidget(self.dockWidgetContents_4)
        ApplyMachineLearningWindow.addDockWidget(Qt.RightDockWidgetArea, self.UndoStack)
        self.ConsoleDockWidget = QDockWidget(ApplyMachineLearningWindow)
        self.ConsoleDockWidget.setObjectName(u"ConsoleDockWidget")
        self.dockWidgetContents_2 = QWidget()
        self.dockWidgetContents_2.setObjectName(u"dockWidgetContents_2")
        self.horizontalLayout = QHBoxLayout(self.dockWidgetContents_2)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.ConsoleOverlayWidget = OverlayWidget(self.dockWidgetContents_2)
        self.ConsoleOverlayWidget.setObjectName(u"ConsoleOverlayWidget")
        self.ConsoleOverlayWidget.setProperty("overlayHidden", True)
        self.verticalLayout_15 = QVBoxLayout(self.ConsoleOverlayWidget)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(-1, 0, -1, 0)
        self.verticalLayout_14 = QVBoxLayout()
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.consoleWidget = ConsoleWidget(self.ConsoleOverlayWidget)
        self.consoleWidget.setObjectName(u"consoleWidget")
        self.consoleWidget.setProperty("ConsoleWidthPercentage", 88)

        self.verticalLayout_14.addWidget(self.consoleWidget)


        self.verticalLayout_15.addLayout(self.verticalLayout_14)


        self.horizontalLayout.addWidget(self.ConsoleOverlayWidget)

        self.ConsoleDockWidget.setWidget(self.dockWidgetContents_2)
        ApplyMachineLearningWindow.addDockWidget(Qt.BottomDockWidgetArea, self.ConsoleDockWidget)

        self.menubar.addAction(self.menuasdf.menuAction())
        self.menubar.addAction(self.menuview.menuAction())
        self.menubar.addAction(self.menusource.menuAction())
        self.menuasdf.addAction(self.actionNewConfig)
        self.menuasdf.addAction(self.actionUndo)
        self.menuasdf.addAction(self.actionRedo)
        self.menuasdf.addSeparator()
        self.menuasdf.addAction(self.actionSave)
        self.menuasdf.addAction(self.actionSave_As)
        self.menusource.addAction(self.actionSetLocalRunMode)
        self.menusource.addAction(self.actionSetNetworkRunMode)
        self.menuview.addAction(self.menuSet_Font_Size.menuAction())
        self.menuview.addAction(self.actionReset_Splitters)
        self.menuSet_Font_Size.addAction(self.actionIncreaseFontSize)
        self.menuSet_Font_Size.addAction(self.actionDefaultFontSize)
        self.menuSet_Font_Size.addAction(self.actionDecreaseFontSize)

        self.retranslateUi(ApplyMachineLearningWindow)

        QMetaObject.connectSlotsByName(ApplyMachineLearningWindow)
    # setupUi

    def retranslateUi(self, ApplyMachineLearningWindow):
        ApplyMachineLearningWindow.setWindowTitle(QCoreApplication.translate("ApplyMachineLearningWindow", u"ML Task Scheduler[*]", None))
        self.actionUndo.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Undo", None))
#if QT_CONFIG(tooltip)
        self.actionUndo.setToolTip(QCoreApplication.translate("ApplyMachineLearningWindow", u"Undo the last edit to the settings", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionUndo.setShortcut(QCoreApplication.translate("ApplyMachineLearningWindow", u"Ctrl+Z", None))
#endif // QT_CONFIG(shortcut)
        self.actionRedo.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Redo", None))
#if QT_CONFIG(shortcut)
        self.actionRedo.setShortcut(QCoreApplication.translate("ApplyMachineLearningWindow", u"Ctrl+Y", None))
#endif // QT_CONFIG(shortcut)
        self.actionIncreaseFontSize.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Increase Size", None))
#if QT_CONFIG(shortcut)
        self.actionIncreaseFontSize.setShortcut(QCoreApplication.translate("ApplyMachineLearningWindow", u"Ctrl+=", None))
#endif // QT_CONFIG(shortcut)
        self.actionDefaultFontSize.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Default Size", None))
        self.actionDecreaseFontSize.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Decrease Size", None))
#if QT_CONFIG(shortcut)
        self.actionDecreaseFontSize.setShortcut(QCoreApplication.translate("ApplyMachineLearningWindow", u"Ctrl+-", None))
#endif // QT_CONFIG(shortcut)
        self.actionSave.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Save...", None))
#if QT_CONFIG(shortcut)
        self.actionSave.setShortcut(QCoreApplication.translate("ApplyMachineLearningWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionSave_As.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Save As...", None))
#if QT_CONFIG(shortcut)
        self.actionSave_As.setShortcut(QCoreApplication.translate("ApplyMachineLearningWindow", u"Ctrl+Shift+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionReset_Splitters.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Reset Splitters", None))
        self.actionSetLocalRunMode.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Local", None))
        self.actionSetNetworkRunMode.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Network", None))
        self.actionNewConfig.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"New Config...", None))
        self.addToQueueButton.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Add to Queue", None))
        self.menuasdf.setTitle(QCoreApplication.translate("ApplyMachineLearningWindow", u"File...", None))
        self.menusource.setTitle(QCoreApplication.translate("ApplyMachineLearningWindow", u"Mode...", None))
        self.menuview.setTitle(QCoreApplication.translate("ApplyMachineLearningWindow", u"View", None))
        self.menuSet_Font_Size.setTitle(QCoreApplication.translate("ApplyMachineLearningWindow", u"Font Size", None))
        self.dockWidget.setWindowTitle(QCoreApplication.translate("ApplyMachineLearningWindow", u"File Overview", None))
        self.saveCurrentConfigBtn.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Save", None))
        self.saveCurrentConfigAsBtn.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"Save As...", None))
        self.OpenFileLocationBtn.setText(QCoreApplication.translate("ApplyMachineLearningWindow", u"...", None))
        self.dockWidget_3.setWindowTitle(QCoreApplication.translate("ApplyMachineLearningWindow", u"Task Queue", None))
        self.UndoStack.setWindowTitle(QCoreApplication.translate("ApplyMachineLearningWindow", u"Undo Stack", None))
        self.ConsoleDockWidget.setWindowTitle(QCoreApplication.translate("ApplyMachineLearningWindow", u"Command-Line Output", None))
    # retranslateUi

