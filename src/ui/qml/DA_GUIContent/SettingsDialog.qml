import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material

Dialog {
    id: root
    width: Math.min(820, parent ? parent.width - 80 : 820)
    height: Math.min(700, parent ? parent.height - 60 : 700)
    modal: true
    focus: true
    padding: 0
    closePolicy: Popup.CloseOnEscape

    required property QtObject docController
    property color cardColor: "#b0000000"
    property color mutedText: "#a8b0c2"

    function loadValues() {
        const values = docController.getSettings()
        hostField.text = values.ollamaHost || ""
        modelField.text = values.ollamaModel || ""
        healthTimeoutField.value = values.healthTimeout || 5
        requestTimeoutField.value = values.requestTimeout || 300
        promptsField.text = values.promptsPath || ""
        spreadsheetField.text = values.spreadsheetId || ""
        sheetField.text = values.sheetName || ""
        folderField.text = values.targetFolderName || ""
        statusLabel.text = ""
    }

    onOpened: loadValues()

    background: Rectangle {
        color: "#151d30"
        radius: 25
        border.color: "#245A9690"
        border.width: 1
    }

    header: Item {
        implicitHeight: 82

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 28
            anchors.rightMargin: 20

            ColumnLayout {
                spacing: 3

                Label {
                    text: "系統設定"
                    font.pixelSize: 24
                    font.bold: true
                }

                Label {
                    text: "管理 AI 分析服務與雲端同步參數"
                    color: root.mutedText
                    font.pixelSize: 13
                }
            }

            Item { Layout.fillWidth: true }

            RoundButton {
                text: "×"
                flat: true
                font.pixelSize: 24
                onClicked: root.close()
            }
        }

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: "#15ffffff"
        }
    }

    contentItem: ScrollView {
        id: scrollView
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: scrollView.availableWidth
            spacing: 18

            Item { Layout.preferredHeight: 4 }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                implicitHeight: aiColumn.implicitHeight + 40
                color: root.cardColor
                radius: 20

                ColumnLayout {
                    id: aiColumn
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 13

                    Label {
                        text: "AI 服務"
                        font.pixelSize: 18
                        font.bold: true
                    }

                    Label {
                        text: "分析前會先確認 Ollama 可連線且指定模型已安裝。"
                        color: root.mutedText
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 14
                        rowSpacing: 8

                        TextField {
                            id: hostField
                            Layout.fillWidth: true
                            placeholderText: "http://127.0.0.1:11434"
                        }

                        TextField {
                            id: modelField
                            Layout.fillWidth: true
                            placeholderText: "模型名稱，例如 qwen3.5:9b"
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3

                            Label {
                                text: "可用性確認逾時"
                                color: root.mutedText
                                font.pixelSize: 12
                            }

                            SpinBox {
                                id: healthTimeoutField
                                Layout.fillWidth: true
                                from: 1
                                to: 120
                                editable: true
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3

                            Label {
                                text: "分析請求逾時"
                                color: root.mutedText
                                font.pixelSize: 12
                            }

                            SpinBox {
                                id: requestTimeoutField
                                Layout.fillWidth: true
                                from: 1
                                to: 3600
                                editable: true
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        TextField {
                            id: promptsField
                            Layout.fillWidth: true
                            placeholderText: "提示詞設定檔（prompts.json）"
                        }

                        RoundButton {
                            text: "瀏覽"
                            highlighted: true
                            onClicked: {
                                const selected = docController.selectPromptsFile()
                                if (selected)
                                    promptsField.text = selected
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                implicitHeight: googleColumn.implicitHeight + 40
                color: root.cardColor
                radius: 20

                ColumnLayout {
                    id: googleColumn
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 12

                    Label {
                        text: "Google Workspace"
                        font.pixelSize: 18
                        font.bold: true
                    }

                    Label {
                        text: "留空時維持本機儲存，不影響 AI 文件分析。"
                        color: root.mutedText
                    }

                    TextField {
                        id: spreadsheetField
                        Layout.fillWidth: true
                        placeholderText: "試算表 ID"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14

                        TextField {
                            id: sheetField
                            Layout.fillWidth: true
                            placeholderText: "工作表名稱"
                        }

                        TextField {
                            id: folderField
                            Layout.fillWidth: true
                            placeholderText: "Drive 目標資料夾"
                        }
                    }
                }
            }

            Item { Layout.preferredHeight: 4 }
        }
    }

    footer: Item {
        implicitHeight: 82

        Rectangle {
            width: parent.width
            height: 1
            color: "#15ffffff"
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 28
            anchors.rightMargin: 24

            Label {
                id: statusLabel
                Layout.fillWidth: true
                color: Material.accentColor
                elide: Text.ElideRight
            }

            Button {
                text: "取消"
                flat: true
                onClicked: root.close()
            }

            RoundButton {
                text: "儲存設定"
                highlighted: true
                leftPadding: 22
                rightPadding: 22
                onClicked: {
                    const result = docController.saveSettings({
                        ollamaHost: hostField.text,
                        ollamaModel: modelField.text,
                        healthTimeout: healthTimeoutField.value,
                        requestTimeout: requestTimeoutField.value,
                        promptsPath: promptsField.text,
                        spreadsheetId: spreadsheetField.text,
                        sheetName: sheetField.text,
                        targetFolderName: folderField.text
                    })
                    statusLabel.text = result.message
                    if (result.success)
                        closeTimer.start()
                }
            }
        }
    }

    Timer {
        id: closeTimer
        interval: 700
        onTriggered: root.close()
    }
}
