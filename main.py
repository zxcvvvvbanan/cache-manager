import datetime
import json
import os
import shutil
import time
from pathlib import Path
from multiprocessing.pool import ThreadPool

import hou

from PySide2.QtCore import Qt
from PySide2.QtGui import QBrush, QColor, QIcon, QPainter, QPen
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMessageBox, QHeaderView
)

class MainWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(False)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        painter.setPen(QPen(QColor(111, 111, 111, 150), 1, Qt.SolidLine))
        for i in range(self.topLevelItemCount()):
            self._draw_line_for_comment(painter, self.topLevelItem(i))

    def _draw_line_for_comment(self, painter, item):
        rect = self.visualItemRect(item)
        comment = item.text(1)
        if comment.strip():
            # Example: draw a line under the row if comment exists
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        for i in range(item.childCount()):
            self._draw_line_for_comment(painter, item.child(i))

class CacheManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowStaysOnTopHint)
        self._set_style()
        self.populate_tree()

    def refreshTree(self):
        self.tree_widget.clear()
        self.populate_tree()

    def populate_tree(self):
        start_time = time.time()
        current_directory = self.seq()
        try:
            self._populate_tree_with_pool(current_directory)
        except FileNotFoundError:
            Path(current_directory).mkdir(parents=True, exist_ok=True)
            self._populate_tree_with_pool(current_directory)
        self.searchMatchingVersion()
        print(f"Tree populated in {time.time() - start_time:.2f}s")

    def _populate_tree_with_pool(self, directory):
        pool = ThreadPool()
        pool.map(self.add_directory_to_tree_parallel, [(directory, self.tree_widget, directory)])
        pool.close()
        pool.join()

    def add_directory_to_tree_parallel(self, args):
        directory, parent_item, folder_path = args
        self.add_directory_to_tree(directory, parent_item, folder_path)

    def searchMatchingVersion(self):
        fileio_nodes = [
            node for node in hou.node("/obj").allSubChildren()
            if "filecache::2.0" in node.type().name()
        ]
        fileIO_dict = [
            {
                "version": node.parm("version").eval(),
                "basename": node.parm("basename").eval()
            }
            for node in fileio_nodes
        ]
        for entry in fileIO_dict:
            self.search_in_tree(self.tree_widget.invisibleRootItem(), entry)
        self.getCacheName(self.tree_widget.invisibleRootItem(), fileIO_dict)

    def getCacheName(self, item, entries):
        return [entry["basename"] for entry in entries]

    def search_in_tree(self, item, entry):
        for i in range(item.childCount()):
            child = item.child(i)
            try:
                elenm = child.parent().text(0)
                takev = child.parent().parent().text(0)
                elever = child.text(0)
                if (entry.get("takev") == takev and
                    entry.get("elenm") == elenm and
                    entry.get("elever") == elever):
                    child.setForeground(0, QBrush(QColor(255, 165, 0)))
            except Exception:
                pass
            self.search_in_tree(child, entry)

    def comment_retrieval(self, item_path):
        json_path = os.path.join(item_path, "cacheinfo.json")
        try:
            with open(json_path, "r") as file:
                data = json.load(file)
            return data.get("comment", "")
        except FileNotFoundError:
            return ""

    def protect_retrieval(self, item_path):
        json_path = os.path.join(item_path, "cacheinfo.json")
        try:
            with open(json_path, "r") as file:
                data = json.load(file)
            return data.get("cache_protect", 0)
        except FileNotFoundError:
            return 0

    def add_directory_to_tree(self, directory, parent_item, folder_path, depth=0):
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            item_name = os.path.basename(item_path)
            
            if os.path.isdir(item_path):
                size = self.get_directory_size(item_path)
                date = datetime.datetime.fromtimestamp(os.path.getmtime(item_path)).strftime('%m-%d  %H:%M')
                has_subdirs = any(os.path.isdir(os.path.join(item_path, d)) for d in os.listdir(item_path))
                comment = "" if has_subdirs else self.comment_retrieval(item_path)
                protect = 0 if has_subdirs else self.protect_retrieval(item_path)
                tree_item = QTreeWidgetItem(parent_item, [item_name, comment, self.format_size(size), date])
                if protect == 1:
                    tree_item.setIcon(0, QIcon("/stdrepo/PFX/TD/scripts/fx_cache_manager/lock.svg"))
                    tree_item.setFlags(tree_item.flags() & ~Qt.ItemIsSelectable)
                tree_item.setExpanded(True)
                tree_item.setData(0, Qt.UserRole, os.path.join(folder_path, item_name))
                self.add_directory_to_tree(item_path, tree_item, folder_path, depth + 1)

    def get_directory_size(self, path):
        total_size = 0
        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                total_size += os.path.getsize(file_path)
        return total_size

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:3.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def confirm_delete_selected_folder(self):
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "You have not selected any folder")
            return
        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete the selected folders?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            for item in selected_items:
                self.delCache(item)

    def delCache(self, item):
        path = []
        check = item
        while item is not None:
            path.insert(0, item.text(0))
            item = item.parent()
        cachepath = '/'.join(path)
        abspath = os.path.join(self.seq(), cachepath)
        if os.path.exists(abspath) and check.childCount() == 0:
            for col in range(check.columnCount()):
                check.setForeground(col, QBrush(QColor(111, 111, 111)))
            shutil.rmtree(abspath)
            self.tree_widget.clearSelection()
            self.tree_widget.takeTopLevelItem(self.tree_widget.indexOfTopLevelItem(check))
        elif check.childCount() != 0:
            self.foolProof()

    def foolProof(self):
        QMessageBox.critical(
            self, "Warning",
            "Subdirectory Found. This is Discouraged. Aborting job.",
            QMessageBox.Ok
        )

    def setCachePath(self):
        result = hou.ui.readInput("Enter the cache path for $CACHEPATH:", buttons=("OK", "Cancel"))
        if result[0] == 0:
            cache_path = result[1] + hou.hipFile.basename().split(".")[:-1][0]
            hou.hscript(f'set -g CACHEPATH = "{cache_path}"')
            hou.ui.displayMessage(f'$CACHEPATH has been set to:\n{cache_path}')
        else:
            hou.ui.displayMessage("Operation canceled. $CACHEPATH was not set.")

    def seq(self):
        aliassetcheck = hou.getenv("CACHEPATH")
        if not aliassetcheck:
            self.setCachePath()
            aliassetcheck = hou.getenv("CACHEPATH")
        return aliassetcheck

    def _set_style(self):
        self.setWindowTitle("Houdini Cache Manager by Yongjun Cho")
        self.setMinimumWidth(1400)
        self.setMinimumHeight(700)
        self.setMaximumWidth(1700)
        self.setMaximumHeight(1000)
        layout = QVBoxLayout(self)
        button_layout = QHBoxLayout()
        welcome_label = QLabel(f"Welcome, {os.environ.get('USERNAME', '')}")
        welcome_label.setAlignment(Qt.AlignLeft)
        welcome_label.setStyleSheet("font-size: 17px; font-weight: bold; margin-bottom: 1px; color: rgb(133,133,133)")
        layout.addWidget(welcome_label)
        welcome_label2 = QLabel(f"Target : {self.seq()}")
        welcome_label2.setAlignment(Qt.AlignLeft)
        welcome_label2.setStyleSheet("font-size: 22px; font-weight: bold; margin-bottom: 3px;")
        layout.addWidget(welcome_label2)
        self.tree_widget = MainWidget()
        self.tree_widget.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree_widget.setHeaderLabels(["name", "comment", "size", "date"])
        self.tree_widget.setStyleSheet("background-color: rgb(31,31,31);")
        header = self.tree_widget.header()
        for column in range(header.count()):
            header.setSectionResizeMode(column, QHeaderView.Stretch)
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.confirm_delete_selected_folder)
        self.refresh = QPushButton("Refresh")
        self.refresh.clicked.connect(self.refreshTree)
        layout.addWidget(self.tree_widget)
        self.tree_widget.setSortingEnabled(True)
        button_layout.addWidget(self.delete_button, 8)
        button_layout.addWidget(self.refresh, 2)
        layout.addLayout(button_layout)

dialog = CacheManager()
dialog.show()
