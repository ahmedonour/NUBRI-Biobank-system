from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QMessageBox, QDialogButtonBox
)
from PyQt5.QtCore import Qt
from ..database.models import ColumnDefinition


class AddColumnDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Column")
        self.setModal(True)
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Freezer Row, Box Number, ...")
        layout.addRow("Column Name:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["TEXT", "NUMBER", "DATE"])
        layout.addRow("Type:", self.type_combo)

        self.required_check = QCheckBox("Required field")
        layout.addRow("", self.required_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "type": self.type_combo.currentText(),
            "required": self.required_check.isChecked()
        }


class SchemaManagerWidget(QWidget):
    schema_changed = object()

    def __init__(self, db=None):
        super().__init__()
        self.db = db
        self.column_def = ColumnDefinition(self.db)
        self._setup_ui()
        self._load_columns()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Manage Custom Columns")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4da6ff; margin-bottom: 10px;")
        layout.addWidget(title)

        info = QLabel("Add, edit, or remove columns. Changes apply to all new labels.")
        info.setStyleSheet("color: #9e9e9e; margin-bottom: 10px;")
        layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Column Name", "Type", "Required", "Order"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("+ Add Column")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff; color: white; padding: 10px 20px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3d8bd4; }
        """)
        self.add_btn.clicked.connect(self._add_column)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #555; color: #e0e0e0; padding: 10px 20px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #666; }
        """)
        self.edit_btn.clicked.connect(self._edit_column)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef5350; color: white; padding: 10px 20px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #e53935; }
        """)
        self.delete_btn.clicked.connect(self._delete_column)
        btn_layout.addWidget(self.delete_btn)

        self.move_up_btn = QPushButton("Move Up")
        self.move_up_btn.setStyleSheet("""
            QPushButton {
                background-color: #555; color: #e0e0e0; padding: 10px 20px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #666; }
        """)
        self.move_up_btn.clicked.connect(self._move_up)
        btn_layout.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("Move Down")
        self.move_down_btn.setStyleSheet("""
            QPushButton {
                background-color: #555; color: #e0e0e0; padding: 10px 20px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #666; }
        """)
        self.move_down_btn.clicked.connect(self._move_down)
        btn_layout.addWidget(self.move_down_btn)

        layout.addLayout(btn_layout)

    def _load_columns(self):
        columns = self.column_def.get_all()
        self.table.setRowCount(len(columns))

        for row, col in enumerate(columns):
            self.table.setItem(row, 0, QTableWidgetItem(col["column_name"]))
            self.table.setItem(row, 1, QTableWidgetItem(col["column_type"]))
            self.table.setItem(row, 2, QTableWidgetItem("Yes" if col["is_required"] else "No"))
            order_item = QTableWidgetItem(str(col["display_order"]))
            order_item.setData(Qt.UserRole, col["id"])
            self.table.setItem(row, 3, order_item)

    def _add_column(self):
        dialog = AddColumnDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Error", "Column name is required.")
                return
            try:
                self.column_def.add(data["name"], data["type"], data["required"])
                self._load_columns()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add column: {str(e)}")

    def _edit_column(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Please select a column to edit.")
            return

        col_id = self.table.item(row, 3).data(Qt.UserRole)
        current_name = self.table.item(row, 0).text()
        current_type = self.table.item(row, 1).text()
        current_required = self.table.item(row, 2).text() == "Yes"

        dialog = AddColumnDialog(self)
        dialog.name_edit.setText(current_name)
        dialog.type_combo.setCurrentText(current_type)
        dialog.required_check.setChecked(current_required)
        dialog.setWindowTitle("Edit Column")

        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Error", "Column name is required.")
                return
            try:
                self.column_def.update(col_id, data["name"], data["type"], data["required"])
                self._load_columns()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update column: {str(e)}")

    def _delete_column(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Please select a column to delete.")
            return

        col_name = self.table.item(row, 0).text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete column '{col_name}'?\nExisting data for this field will be preserved but hidden.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            col_id = self.table.item(row, 3).data(Qt.UserRole)
            try:
                self.column_def.delete(col_id)
                self._load_columns()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete column: {str(e)}")

    def _move_up(self):
        row = self.table.currentRow()
        if row <= 0:
            return
        ids = [self.table.item(r, 3).data(Qt.UserRole) for r in range(self.table.rowCount())]
        ids[row], ids[row - 1] = ids[row - 1], ids[row]
        self.column_def.reorder(ids)
        self._load_columns()
        self.table.selectRow(row - 1)

    def _move_down(self):
        row = self.table.currentRow()
        if row < 0 or row >= self.table.rowCount() - 1:
            return
        ids = [self.table.item(r, 3).data(Qt.UserRole) for r in range(self.table.rowCount())]
        ids[row], ids[row + 1] = ids[row + 1], ids[row]
        self.column_def.reorder(ids)
        self._load_columns()
        self.table.selectRow(row + 1)
