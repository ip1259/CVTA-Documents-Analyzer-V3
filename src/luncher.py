from PySide6.QtWidgets import QApplication
import sys
import os
from pathlib import Path
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl

# 你的 controller
from ui.doc_controller import DocController

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 設定 Material Style
    os.environ["QT_QUICK_CONTROLS_CONF"] = str(
        Path(__file__).parent / "ui" / "qml" / "qtquickcontrols2.conf"
    )

    engine = QQmlApplicationEngine()

    # ★ 關鍵：加入 QML import path，讓引擎找到 DA_GUI 模組
    qml_dir = Path(__file__).parent / "ui" / "qml"
    engine.addImportPath(str(qml_dir))

    # 建立 controller 實例
    controller = DocController(app)

    # 載入主 QML（App.qml）
    qml_file = qml_dir / "DA_GUIContent" / "App.qml"

    # ★ 將 docController 傳入 QML（對應 App.qml 的 required property）
    engine.setInitialProperties({"docController": controller})

    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())
