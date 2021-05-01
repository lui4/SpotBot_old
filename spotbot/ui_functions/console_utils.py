from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QTableWidgetItem


class ConsolePage:
    def __init__(self, parent, thread_id="/"):
        self.parent = parent
        self.thread_id = thread_id

    def add_message(self, status, message):
        """
        This function is used to enter a new message to the console page table
        :param status: Valid statuses: INFO, SUCCESS, ERROR
        :param message: Message to be displayed
        :return: None
        """

        row_position = self.parent.streaming_accounts_table.rowCount()
        self.parent.console_table.setColumnCount(3)
        self.parent.console_table.insertRow(row_position)

        self.parent.console_table.setItem(row_position, 0, QTableWidgetItem(""))

        item = QTableWidgetItem(str(self.thread_id))
        item.setTextAlignment(QtCore.Qt.AlignHCenter)
        self.parent.console_table.setItem(row_position, 1, item)

        self.parent.console_table.setItem(row_position, 2, QTableWidgetItem(message))
        if status == "INFO":
            self.parent.console_table.item(row_position, 0).setBackground(QtGui.QColor(255, 255, 255))
        elif status == "SUCCESS":
            self.parent.console_table.item(row_position, 0).setBackground(QtGui.QColor(12, 168, 12))
        elif status == "ERROR":
            self.parent.console_table.item(row_position, 0).setBackground(QtGui.QColor(237, 12, 12))
        else:
            raise ValueError("Invalid status selected (valid statuses: INFO, SUCCESS, ERROR)")