from PySide6.QtWidgets import QApplication
import sys
import os
from pathlib import Path
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl

from src.ui.doc_controller import DocController
from src.infrastructure.logger import initialize_logging

if __name__ == "__main__":
    initialize_logging()
    app = QApplication(sys.argv)

    os.environ["QT_QUICK_CONTROLS_CONF"] = str(
        Path(__file__).parent / "ui" / "qml" / "qtquickcontrols2.conf"
    )

    engine = QQmlApplicationEngine()

    qml_dir = Path(__file__).parent / "ui" / "qml"
    engine.addImportPath(str(qml_dir))

    controller = DocController(app)

    qml_file = qml_dir / "DA_GUIContent" / "App.qml"

    engine.setInitialProperties({"docController": controller})

    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())
