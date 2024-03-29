# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
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
    QHeaderView, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QStatusBar, QToolButton,
    QUndoView, QVBoxLayout, QWidget)

from configurun.app.widgets.run_queue_widget import RunQueueWidget
from pyside6_utils.widgets.console_widget import ConsoleWidget
from pyside6_utils.widgets.extended_mdi_area import ExtendedMdiArea
from pyside6_utils.widgets.file_explorer_view import FileExplorerView
from pyside6_utils.widgets.overlay_widget import OverlayWidget
from pyside6_utils.widgets.square_frame import SquareFrame
import configurun.res.app_resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(2112, 1141)
        icon = QIcon()
        icon.addFile(u":/Icons/icons/apps/utilities-system-monitor.png", QSize(), QIcon.Normal, QIcon.Off)
        MainWindow.setWindowIcon(icon)
        self.actionUndo = QAction(MainWindow)
        self.actionUndo.setObjectName(u"actionUndo")
        icon1 = QIcon()
        icon1.addFile(u":/Icons/icons/actions/edit-undo.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionUndo.setIcon(icon1)
        self.actionRedo = QAction(MainWindow)
        self.actionRedo.setObjectName(u"actionRedo")
        icon2 = QIcon()
        icon2.addFile(u":/Icons/icons/actions/edit-redo.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionRedo.setIcon(icon2)
        self.actionIncreaseFontSize = QAction(MainWindow)
        self.actionIncreaseFontSize.setObjectName(u"actionIncreaseFontSize")
        icon3 = QIcon()
        icon3.addFile(u":/Icons/icons/actions/list-add.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionIncreaseFontSize.setIcon(icon3)
        self.actionDefaultFontSize = QAction(MainWindow)
        self.actionDefaultFontSize.setObjectName(u"actionDefaultFontSize")
        icon4 = QIcon()
        icon4.addFile(u":/Icons/icons/actions/view-refresh.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionDefaultFontSize.setIcon(icon4)
        self.actionDecreaseFontSize = QAction(MainWindow)
        self.actionDecreaseFontSize.setObjectName(u"actionDecreaseFontSize")
        icon5 = QIcon()
        icon5.addFile(u":/Icons/icons/actions/list-remove.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionDecreaseFontSize.setIcon(icon5)
        self.actionSave = QAction(MainWindow)
        self.actionSave.setObjectName(u"actionSave")
        icon6 = QIcon()
        icon6.addFile(u":/Icons/icons/actions/document-save.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionSave.setIcon(icon6)
        self.actionSave_As = QAction(MainWindow)
        self.actionSave_As.setObjectName(u"actionSave_As")
        icon7 = QIcon()
        icon7.addFile(u":/Icons/icons/actions/document-save-as.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionSave_As.setIcon(icon7)
        self.actionReset_Splitters = QAction(MainWindow)
        self.actionReset_Splitters.setObjectName(u"actionReset_Splitters")
        icon8 = QIcon()
        icon8.addFile(u":/Icons/icons/Tango Icons/32x32/actions/view-refresh.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionReset_Splitters.setIcon(icon8)
        self.actionSetLocalRunMode = QAction(MainWindow)
        self.actionSetLocalRunMode.setObjectName(u"actionSetLocalRunMode")
        self.actionSetLocalRunMode.setCheckable(True)
        self.actionSetLocalRunMode.setChecked(True)
        self.actionSetLocalRunMode.setEnabled(True)
        icon9 = QIcon()
        icon9.addFile(u":/Icons/icons/Tango Icons/32x32/actions/go-home.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionSetLocalRunMode.setIcon(icon9)
        self.actionSetNetworkRunMode = QAction(MainWindow)
        self.actionSetNetworkRunMode.setObjectName(u"actionSetNetworkRunMode")
        self.actionSetNetworkRunMode.setCheckable(True)
        icon10 = QIcon()
        icon10.addFile(u":/Icons/icons/Tango Icons/32x32/apps/internet-web-browser.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionSetNetworkRunMode.setIcon(icon10)
        self.actionNewConfig = QAction(MainWindow)
        self.actionNewConfig.setObjectName(u"actionNewConfig")
        icon11 = QIcon()
        icon11.addFile(u":/Icons/icons/actions/document-new.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionNewConfig.setIcon(icon11)
        self.actionNone = QAction(MainWindow)
        self.actionNone.setObjectName(u"actionNone")
        self.actionNone.setEnabled(False)
        self.actionReset_Splitters_2 = QAction(MainWindow)
        self.actionReset_Splitters_2.setObjectName(u"actionReset_Splitters_2")
        icon12 = QIcon()
        icon12.addFile(u":/Icons/icons/mimetypes/x-office-document-template.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionReset_Splitters_2.setIcon(icon12)
        self.actionBackupRunQueue = QAction(MainWindow)
        self.actionBackupRunQueue.setObjectName(u"actionBackupRunQueue")
        self.actionLoadRunQueue = QAction(MainWindow)
        self.actionLoadRunQueue.setObjectName(u"actionLoadRunQueue")
        self.action_None = QAction(MainWindow)
        self.action_None.setObjectName(u"action_None")
        self.actionOpenConfig = QAction(MainWindow)
        self.actionOpenConfig.setObjectName(u"actionOpenConfig")
        icon13 = QIcon()
        icon13.addFile(u":/Icons/icons/actions/document-open.png", QSize(), QIcon.Normal, QIcon.Off)
        self.actionOpenConfig.setIcon(icon13)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(9, 0, 0, 0)
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, -1, -1, -1)
        self.ConfigurationMdiArea = ExtendedMdiArea(self.centralwidget)
        self.ConfigurationMdiArea.setObjectName(u"ConfigurationMdiArea")

        self.verticalLayout_2.addWidget(self.ConfigurationMdiArea)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.addToQueueButton = QPushButton(self.centralwidget)
        self.addToQueueButton.setObjectName(u"addToQueueButton")
        icon14 = QIcon()
        icon14.addFile(u":/Icons/icons/actions/format-indent-more.png", QSize(), QIcon.Normal, QIcon.Off)
        self.addToQueueButton.setIcon(icon14)

        self.horizontalLayout_2.addWidget(self.addToQueueButton)

        self.saveToQueueItemBtn = QPushButton(self.centralwidget)
        self.saveToQueueItemBtn.setObjectName(u"saveToQueueItemBtn")
        icon15 = QIcon()
        icon15.addFile(u":/Icons/icons/actions/savesymbol.png", QSize(), QIcon.Normal, QIcon.Off)
        self.saveToQueueItemBtn.setIcon(icon15)

        self.horizontalLayout_2.addWidget(self.saveToQueueItemBtn)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)


        self.verticalLayout.addLayout(self.verticalLayout_2)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 2112, 22))
        self.menuasdf = QMenu(self.menubar)
        self.menuasdf.setObjectName(u"menuasdf")
        self.menuview = QMenu(self.menubar)
        self.menuview.setObjectName(u"menuview")
        self.menuSet_Font_Size = QMenu(self.menuview)
        self.menuSet_Font_Size.setObjectName(u"menuSet_Font_Size")
        self.menuSet_Font_Size.setGeometry(QRect(0, 0, 144, 122))
        icon16 = QIcon()
        icon16.addFile(u":/Icons/icons/apps/preferences-desktop-font.png", QSize(), QIcon.Normal, QIcon.Off)
        self.menuSet_Font_Size.setIcon(icon16)
        self.menuMDI_Area = QMenu(self.menuview)
        self.menuMDI_Area.setObjectName(u"menuMDI_Area")
        self.menuMDI_Area.setEnabled(True)
        icon17 = QIcon()
        icon17.addFile(u":/Icons/icons/apps/preferences-system-windows.png", QSize(), QIcon.Normal, QIcon.Off)
        self.menuMDI_Area.setIcon(icon17)
        self.menuRun_Queue = QMenu(self.menubar)
        self.menuRun_Queue.setObjectName(u"menuRun_Queue")
        self.actionViewRunQueueFilter = QMenu(self.menuRun_Queue)
        self.actionViewRunQueueFilter.setObjectName(u"actionViewRunQueueFilter")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.dockWidget = QDockWidget(MainWindow)
        self.dockWidget.setObjectName(u"dockWidget")
        icon18 = QIcon()
        icon18.addFile(u":/Icons/icons/savesymbol.png", QSize(), QIcon.Normal, QIcon.Off)
        self.dockWidget.setWindowIcon(icon18)
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
        icon19 = QIcon()
        icon19.addFile(u":/Icons/icons/actions/folder-new.png", QSize(), QIcon.Normal, QIcon.Off)
        self.OpenFileLocationBtn.setIcon(icon19)

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
        MainWindow.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget)
        self.dockWidget_3 = QDockWidget(MainWindow)
        self.dockWidget_3.setObjectName(u"dockWidget_3")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.dockWidget_3.sizePolicy().hasHeightForWidth())
        self.dockWidget_3.setSizePolicy(sizePolicy1)
        icon20 = QIcon()
        icon20.addFile(u":/Icons/icons/Tango Icons/32x32/categories/applications-development.png", QSize(), QIcon.Normal, QIcon.Off)
        self.dockWidget_3.setWindowIcon(icon20)
        self.dockWidgetContents_3 = QWidget()
        self.dockWidgetContents_3.setObjectName(u"dockWidgetContents_3")
        self.verticalLayout_4 = QVBoxLayout(self.dockWidgetContents_3)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.runQueueOverlayWidget = OverlayWidget(self.dockWidgetContents_3)
        self.runQueueOverlayWidget.setObjectName(u"runQueueOverlayWidget")
        sizePolicy.setHeightForWidth(self.runQueueOverlayWidget.sizePolicy().hasHeightForWidth())
        self.runQueueOverlayWidget.setSizePolicy(sizePolicy)
        self.runQueueOverlayWidget.setProperty("overlayHidden", True)
        self.runQueueWidget = RunQueueWidget(self.runQueueOverlayWidget)
        self.runQueueWidget.setObjectName(u"runQueueWidget")
        self.runQueueWidget.setGeometry(QRect(1, 1, 18, 18))
        sizePolicy.setHeightForWidth(self.runQueueWidget.sizePolicy().hasHeightForWidth())
        self.runQueueWidget.setSizePolicy(sizePolicy)
        self.verticalLayout_6 = QVBoxLayout(self.runQueueWidget)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")

        self.verticalLayout_4.addWidget(self.runQueueOverlayWidget)

        self.dockWidget_3.setWidget(self.dockWidgetContents_3)
        MainWindow.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget_3)
        self.UndoStack = QDockWidget(MainWindow)
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
        MainWindow.addDockWidget(Qt.RightDockWidgetArea, self.UndoStack)
        self.ConsoleDockWidget = QDockWidget(MainWindow)
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
        MainWindow.addDockWidget(Qt.BottomDockWidgetArea, self.ConsoleDockWidget)

        self.menubar.addAction(self.menuasdf.menuAction())
        self.menubar.addAction(self.menuRun_Queue.menuAction())
        self.menubar.addAction(self.menuview.menuAction())
        self.menuasdf.addAction(self.actionNewConfig)
        self.menuasdf.addAction(self.actionOpenConfig)
        self.menuasdf.addSeparator()
        self.menuasdf.addAction(self.actionSave)
        self.menuasdf.addAction(self.actionSave_As)
        self.menuasdf.addSeparator()
        self.menuasdf.addAction(self.actionUndo)
        self.menuasdf.addAction(self.actionRedo)
        self.menuview.addAction(self.menuSet_Font_Size.menuAction())
        self.menuview.addAction(self.menuMDI_Area.menuAction())
        self.menuSet_Font_Size.addAction(self.actionIncreaseFontSize)
        self.menuSet_Font_Size.addAction(self.actionDefaultFontSize)
        self.menuSet_Font_Size.addAction(self.actionDecreaseFontSize)
        self.menuMDI_Area.addAction(self.actionNone)
        self.menuRun_Queue.addAction(self.actionViewRunQueueFilter.menuAction())
        self.menuRun_Queue.addSeparator()
        self.actionViewRunQueueFilter.addAction(self.action_None)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Configurun[*]", None))
        self.actionUndo.setText(QCoreApplication.translate("MainWindow", u"Undo", None))
#if QT_CONFIG(tooltip)
        self.actionUndo.setToolTip(QCoreApplication.translate("MainWindow", u"Undo the last edit to the settings", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionUndo.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Z", None))
#endif // QT_CONFIG(shortcut)
        self.actionRedo.setText(QCoreApplication.translate("MainWindow", u"Redo", None))
#if QT_CONFIG(shortcut)
        self.actionRedo.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Y", None))
#endif // QT_CONFIG(shortcut)
        self.actionIncreaseFontSize.setText(QCoreApplication.translate("MainWindow", u"Increase Size", None))
#if QT_CONFIG(shortcut)
        self.actionIncreaseFontSize.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+=", None))
#endif // QT_CONFIG(shortcut)
        self.actionDefaultFontSize.setText(QCoreApplication.translate("MainWindow", u"Default Size", None))
        self.actionDecreaseFontSize.setText(QCoreApplication.translate("MainWindow", u"Decrease Size", None))
#if QT_CONFIG(shortcut)
        self.actionDecreaseFontSize.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+-", None))
#endif // QT_CONFIG(shortcut)
        self.actionSave.setText(QCoreApplication.translate("MainWindow", u"Save...", None))
#if QT_CONFIG(shortcut)
        self.actionSave.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionSave_As.setText(QCoreApplication.translate("MainWindow", u"Save As...", None))
#if QT_CONFIG(shortcut)
        self.actionSave_As.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionReset_Splitters.setText(QCoreApplication.translate("MainWindow", u"Reset Splitters", None))
        self.actionSetLocalRunMode.setText(QCoreApplication.translate("MainWindow", u"Local", None))
        self.actionSetNetworkRunMode.setText(QCoreApplication.translate("MainWindow", u"Network", None))
        self.actionNewConfig.setText(QCoreApplication.translate("MainWindow", u"New Config...", None))
#if QT_CONFIG(shortcut)
        self.actionNewConfig.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+N", None))
#endif // QT_CONFIG(shortcut)
        self.actionNone.setText(QCoreApplication.translate("MainWindow", u"None", None))
        self.actionReset_Splitters_2.setText(QCoreApplication.translate("MainWindow", u"Reset Splitters", None))
        self.actionBackupRunQueue.setText(QCoreApplication.translate("MainWindow", u"Backup...", None))
        self.actionLoadRunQueue.setText(QCoreApplication.translate("MainWindow", u"Load...", None))
        self.action_None.setText(QCoreApplication.translate("MainWindow", u"(None)", None))
        self.actionOpenConfig.setText(QCoreApplication.translate("MainWindow", u"Open...", None))
        self.addToQueueButton.setText(QCoreApplication.translate("MainWindow", u"Append to Queue", None))
        self.saveToQueueItemBtn.setText(QCoreApplication.translate("MainWindow", u"Save to Queue-Item", None))
        self.menuasdf.setTitle(QCoreApplication.translate("MainWindow", u"Configuration", None))
        self.menuview.setTitle(QCoreApplication.translate("MainWindow", u"View", None))
        self.menuSet_Font_Size.setTitle(QCoreApplication.translate("MainWindow", u"Font Size", None))
        self.menuMDI_Area.setTitle(QCoreApplication.translate("MainWindow", u"MDI Area", None))
        self.menuRun_Queue.setTitle(QCoreApplication.translate("MainWindow", u"Run Queue", None))
        self.actionViewRunQueueFilter.setTitle(QCoreApplication.translate("MainWindow", u"(built during runtime)", None))
        self.dockWidget.setWindowTitle(QCoreApplication.translate("MainWindow", u"File Overview", None))
        self.saveCurrentConfigBtn.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.saveCurrentConfigAsBtn.setText(QCoreApplication.translate("MainWindow", u"Save As...", None))
        self.OpenFileLocationBtn.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.dockWidget_3.setWindowTitle(QCoreApplication.translate("MainWindow", u"Run Queue", None))
        self.UndoStack.setWindowTitle(QCoreApplication.translate("MainWindow", u"Undo Stack", None))
        self.ConsoleDockWidget.setWindowTitle(QCoreApplication.translate("MainWindow", u"Command-Line Output", None))
    # retranslateUi

