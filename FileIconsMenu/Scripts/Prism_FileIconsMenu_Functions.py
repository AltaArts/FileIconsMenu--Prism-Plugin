# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.
#
####################################################
#
#           FILE ICON MENU PLUGIN
#           by Joshua Breckeen
#                Alta Arts
#           josh@alta-arts.com
#
#   This PlugIn adds a sub-Menu to the Settings Menu to allow the
#   user to select icon images to associate with file types that 
#   are not part of a Prism DCC intergration.
#
####################################################


import os
import shutil
import json
import re

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_FileIconsMenu_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        #   Global Settings File
        pluginLocation = os.path.dirname(os.path.dirname(__file__))

        global settingsFile
        settingsFile = os.path.join(pluginLocation, "FileIconsMenu_Config.json")

        global iconDir
        iconDir = os.path.join(pluginLocation, "Icons")
        if not os.path.exists(iconDir):
            os.mkdir(iconDir)

        #   Callbacks
        self.core.registerCallback("userSettings_loadUI", self.userSettings_loadUI, plugin=self)
        self.core.registerCallback("getIconPathForFileType", self.getIconPathForFileType, plugin=self)


    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True
    

    #   Called with Callback
    @err_catcher(name=__name__)
    def userSettings_loadUI(self, origin):      #   ADDING "File Icons Menu" TO SETTINGS

        #   Loads Settings File
        fileIconList = self.loadSettings()
        headerLabels = ["File Type", "Icon Path", "Icon"]

        # Create a Widget
        origin.w_fileIcon = QWidget()
        origin.lo_fileIcon = QVBoxLayout(origin.w_fileIcon)

        #   Send To Menu UI List
        gb_fileIcon = QGroupBox("File Icon Associations")
        lo_fileIcon = QVBoxLayout()
        gb_fileIcon.setLayout(lo_fileIcon)

        tw_fileIcon = QTableWidget()
        tw_fileIcon.setColumnCount(len(headerLabels))
        tw_fileIcon.setHorizontalHeaderLabels(headerLabels)
        tw_fileIcon.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        tw_fileIcon.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        #   Set Intial Table Sizes
        tw_fileIcon.setMinimumHeight(300)  # Adjust the value as needed

        #   Adds Buttons
        w_fileIcon = QWidget()
        lo_fileIconButtons = QHBoxLayout()
        b_addFileIcon = QPushButton("Add")
        b_removeFileIcon = QPushButton("Remove")

        w_fileIcon.setLayout(lo_fileIconButtons)
        lo_fileIconButtons.addStretch()
        lo_fileIconButtons.addWidget(b_addFileIcon)
        lo_fileIconButtons.addWidget(b_removeFileIcon)

        lo_fileIcon.addWidget(tw_fileIcon)
        lo_fileIcon.addWidget(w_fileIcon)
        origin.lo_fileIcon.addWidget(gb_fileIcon)

        # Configure table options
        tw_fileIcon.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        tw_fileIcon.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tw_fileIcon.setSelectionBehavior(QTableWidget.SelectRows)
        tw_fileIcon.setSelectionMode(QTableWidget.SingleSelection)

        tip = "Icons associated with filetypes in Prism UI.\n\nFiles will be opened using Prism's default behavior."
        tw_fileIcon.setToolTip(tip)

        #   Executes button actions
        b_addFileIcon.clicked.connect(lambda: self.addFileIcon(origin, tw_fileIcon))
        b_removeFileIcon.clicked.connect(lambda: self.removeFileIcon(origin, tw_fileIcon))

        #   Populates lists from Settings File Data
        for item in fileIconList:
            row_position = tw_fileIcon.rowCount()
            tw_fileIcon.insertRow(row_position)
            tw_fileIcon.setItem(row_position, 0, QTableWidgetItem(item.get("File Type", "")))
            tw_fileIcon.setItem(row_position, 1, QTableWidgetItem(item.get("Icon Path", "")))

            # Add an example icon in the third column
            exampleIconPath = item.get("Icon Path", "")
            exampleIconItem = QTableWidgetItem()
            if exampleIconPath:
                pixmap = QPixmap(exampleIconPath)
                exampleIconItem.setIcon(QIcon(pixmap))
            tw_fileIcon.setItem(row_position, 2, exampleIconItem)

        # Add Tab to User Settings
        origin.addTab(origin.w_fileIcon, "File Icon Associations")


    @err_catcher(name=__name__)
    def addFileIcon(self, origin, tw_fileIcon):

        #   Calls Custom Dialog
        dialog = AddFileIconDialog(origin)

        #   Adds Name and Path to UI List
        if dialog.exec_() == QDialog.Accepted:
            name, path = dialog.getValues()

            if name and path:

                # Copy the icon file to Plugin Icon Dir
                newPath = os.path.join(iconDir, os.path.basename(path))
                # Handles case of icon already existing in location
                if os.path.abspath(newPath) != os.path.abspath(path):
                    shutil.copy2(path, newPath)

                # Adds new selection to UI list
                row_position = tw_fileIcon.rowCount()
                tw_fileIcon.insertRow(row_position)
                tw_fileIcon.setItem(row_position, 0, QTableWidgetItem(name))
                tw_fileIcon.setItem(row_position, 1, QTableWidgetItem(newPath))

                # Add an example icon in the third column of UI list
                exampleIconItem = QTableWidgetItem()
                if newPath:
                    pixmap = QPixmap(newPath)
                    exampleIconItem.setIcon(QIcon(pixmap))
                tw_fileIcon.setItem(row_position, 2, exampleIconItem)

            #   Saves UI List to JSON file
            self.saveSettings(tw_fileIcon)


    @err_catcher(name=__name__)
    def removeFileIcon(self, origin, tw_fileIcon):

        selectedRow = tw_fileIcon.currentRow()

        if selectedRow != -1:
            # Delete the associated file
            fileToDelete = tw_fileIcon.item(selectedRow, 1).text()
            if os.path.exists(fileToDelete):
                os.remove(fileToDelete)

            #   Remove Row from UI
            tw_fileIcon.removeRow(selectedRow)

            #   Saves UI List to JSON file
            self.saveSettings(tw_fileIcon)


    @err_catcher(name=__name__)
    def loadSettings(self):
        #   Loads Global Settings File JSON
        try:
            with open(settingsFile, "r") as json_file:
                data = json.load(json_file)
                return data
            
        except FileNotFoundError:
            return []


    @err_catcher(name=__name__)
    def saveSettings(self, tw_fileIcon):

        data = []

        #   Populates data[] from UI List
        for row in range(tw_fileIcon.rowCount()):
            nameItem = tw_fileIcon.item(row, 0)
            pathItem = tw_fileIcon.item(row, 1)

            if nameItem and pathItem:
                name = nameItem.text()
                location = pathItem.text()

                data.append({"File Type": name, "Icon Path": location})

        #   Saves to Global JSON File
        with open(settingsFile, "w") as json_file:
            json.dump(data, json_file, indent=4)


    @err_catcher(name=__name__)
    def getIconPathForFileType(self, extension):
        # Retrieves extension and associates icon from Global Settings Files    
        fileIconList = self.loadSettings()

        # Matches extension to icon path
        for association in fileIconList:
            if association["File Type"] == extension:
                icon = os.path.join(iconDir, association["Icon Path"])
                return icon

        return None


class AddFileIconDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        #   Sets up Custon File Selection UI
        self.setWindowTitle("Add Icon Association")

        self.l_name = QLabel("File Extension")
        self.le_name = QLineEdit()

        #   Tooltips
        tip = "File extension.  Examples:  .py .fspy  .xcf"
        self.l_name.setToolTip(tip)
        self.le_name.setToolTip(tip)
        # Set the initial text to include a period
        self.le_name.setText('.')

        self.l_location = QLabel("Icon Location:")
        self.but_location = QPushButton("Select Icon")
        self.but_location.clicked.connect(self.selectLocation)
        tip = "Choose icon file.  Allowed: .ico .png .jpg .bmp"
        self.l_location.setToolTip(tip)
        self.but_location.setToolTip(tip)

        self.but_ok = QPushButton("OK")
        self.but_ok.clicked.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(self.l_name)
        layout.addWidget(self.le_name)
        layout.addWidget(self.l_location)
        layout.addWidget(self.but_location)
        layout.addWidget(self.but_ok)

        self.setLayout(layout)
        self.setFixedWidth(300)


    def accept(self):
        # Check if name is a valid file extension
        name = self.le_name.text()
        if not re.match(r'^\.[a-zA-Z0-9]{1,6}$', name):     # max 6 characters
            warning_message = "Please enter a valid file extension.\n\nExamples: .png, .sni"
            QMessageBox.warning(self, "Invalid File Extension", warning_message)
            return
        
        # Check if the selected icon file has a valid extension
        icon_path = self.l_location.text()
        valid_extensions = ['.ico', '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.svg']
        if not any(icon_path.lower().endswith(ext) for ext in valid_extensions):
            warning_message = (
                "Please select a valid image file with one of the following extensions:\n"
                ".ico, .png, .jpg, .jpeg, .bmp, .gif, .svg"
            )
            QMessageBox.warning(self, "Invalid Image File", warning_message)
            return
        
        super().accept()


    def selectLocation(self):

        #   Calls native File Dialog
        windowTitle = "Select Icon"
        fileFilter = "Icon (*.ico;*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.svg);;All files (*)"
        selectedPath, _ = QFileDialog.getOpenFileName(self, windowTitle, "", fileFilter)

        if selectedPath:
            self.l_location.setText(selectedPath)

            # Dynamically adjust the width based on the length of the selected path
            currentWidth = self.width()
            pathLength = len(selectedPath)
            newWidth = max(300, currentWidth, pathLength * 8)  # Adjust the multiplier as needed
            self.setFixedWidth(newWidth)


    def getValues(self):
        name = self.le_name.text()
        location = self.l_location.text()

        return name, location