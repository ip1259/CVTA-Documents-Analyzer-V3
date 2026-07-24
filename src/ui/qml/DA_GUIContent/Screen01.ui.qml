
/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import QtQuick.Controls
import DA_GUI
import QtQuick.Layouts
import QtQuick.Controls.Material
import Qt.labs.qmlmodels

Rectangle {
    id: root
    width: 1440
    height: 810
    color: "transparent"
    Layout.minimumWidth: 1400
    Layout.minimumHeight: 810
    scale: 1

    // 💡 1. 暴露 TableView 的 model 與選取狀態，讓 App.qml 處理綁定
    property alias tableModel: tableView.model
    property alias selectedRow: tableView.selectedRow

    // 💡 2. 暴露各個輸入框的 text 屬性（使用別名最方便）
    property alias unitText: textFrom.text
    property alias dateText: textDate.text
    property alias officerText: textOfficer.text
    property alias categoryText: textCategory.text
    property alias numberText: textNumber.text
    property alias classText: textClass.text
    property alias keyPointText: textKeyPoint.text

    // 💡 3. 暴露圖片的 source
    property alias imageSource: img.source

    // 💡 4. 定義按鈕被點擊的訊號，讓 App.qml 去接
    signal addClicked
    signal analyzeClicked
    signal uploadClicked
    signal openClicked
    signal saveClicked
    signal resetClicked
    signal settingsClicked

    Pane {
        id: pane
        anchors.fill: parent

        RowLayout {
            id: rowLayout
            x: 13
            y: 13
            anchors.fill: parent
            spacing: 15
            anchors.rightMargin: 25
            anchors.leftMargin: 25
            anchors.bottomMargin: 25
            anchors.topMargin: 25

            Rectangle {
                id: rectangle
                width: 200
                height: 200
                color: "#b0000000"
                radius: 25
                Layout.fillWidth: true
                Layout.margins: 0
                Layout.preferredHeight: 1
                Layout.fillHeight: true

                Flickable {
                    id: flickable
                    anchors.fill: parent
                    flickDeceleration: 2500
                    contentWidth: imageContainer.width
                    contentHeight: imageContainer.height
                    clip: true

                    PinchArea {
                        id: pinchArea
                        width: Math.max(flickable.width, imageContainer.width)
                        height: Math.max(flickable.height,
                                         imageContainer.height)

                        property real currentScale: 1.0
                        property real minScale: 0.5
                        property real maxScale: 5.0
                        readonly property real baseSizeWidth: img.sourceSize.width / 4
                        readonly property real baseSizeHeight: img.sourceSize.height / 4
                        Item {
                            id: imageContainer
                            width: pinchArea.baseSizeWidth
                            height: pinchArea.baseSizeHeight

                            // 讓縮放後的內容始終置中（如果小於視窗的話）
                            anchors.centerIn: parent

                            Image {
                                id: img
                                x: 15
                                y: 15
                                anchors.fill: parent
                                asynchronous: true
                                anchors.rightMargin: 15
                                anchors.leftMargin: 15
                                anchors.bottomMargin: 15
                                anchors.topMargin: 15
                                fillMode: Image.PreserveAspectFit
                            }
                        }

                        Connections {
                            target: pinchArea
                            onPinchStarted: flickable.interactive = false
                            onPinchUpdated: pinch => {
                                                // 計算縮放比例
                                                let newScale = currentScale * pinch.scale
                                                if (newScale < minScale)
                                                newScale = minScale
                                                if (newScale > maxScale)
                                                newScale = maxScale

                                                // 動態調整容器的寬高來達到縮放效果（比直接改 scale 更不易變形且與 Flickable 相容性好）
                                                imageContainer.width
                                                = pinchArea.baseSizeWidth * newScale
                                                imageContainer.height
                                                = pinchArea.baseSizeHeight * newScale
                                            }
                            onPinchFinished: pinch => {
                                                 currentScale = imageContainer.width
                                                 / pinchArea.baseSizeWidth
                                                 flickable.interactive = true // 縮放結束，重新啟用拖曳
                                             }
                        }

                        MouseArea {
                            id: mouseArea
                            anchors.fill: parent
                            acceptedButtons: Qt.AllButtons
                            propagateComposedEvents: true

                            Connections {
                                target: mouseArea
                                onClicked: mouse => mouse.accepted = false
                                onPressed: mouse => mouse.accepted = false
                                onWheel: wheel => {
                                             if (wheel.modifiers & Qt.ControlModifier) {
                                                 let zoomFactor = wheel.angleDelta.y > 0 ? 1.1 : 0.9
                                                 let newScale = pinchArea.currentScale * zoomFactor

                                                 if (newScale >= pinchArea.minScale
                                                     && newScale <= pinchArea.maxScale) {
                                                     pinchArea.currentScale = newScale
                                                     imageContainer.width
                                                     = pinchArea.baseSizeWidth * newScale
                                                     imageContainer.height
                                                     = pinchArea.baseSizeHeight * newScale
                                                 }
                                                 wheel.accepted = true
                                             } else {
                                                 wheel.accepted
                                                 = false // 如果沒按 Ctrl，把滾輪事件傳給 Flickable
                                             }
                                         }
                            }
                        }
                    }

                    PropertyAnimation {
                        id: propertyAnimation
                        target: flickable
                        property: "contentX"
                        easing.bezierCurve: [0.455, 0.03, 0.515, 0.955, 1, 1]
                        duration: 400
                    }

                    PropertyAnimation {
                        id: propertyAnimation1
                        target: flickable
                        property: "contentY"
                        easing.bezierCurve: [0.455, 0.03, 0.515, 0.955, 1, 1]
                        duration: 400
                    }

                    PropertyAnimation {
                        id: animWidth
                        target: imageContainer
                        property: "width"
                        easing.bezierCurve: [0.455, 0.03, 0.515, 0.955, 1, 1]
                        duration: 400
                    }

                    PropertyAnimation {
                        id: animHeight
                        target: imageContainer
                        property: "height"
                        easing.bezierCurve: [0.455, 0.03, 0.515, 0.955, 1, 1]
                        duration: 400
                    }
                }
            }

            ColumnLayout {
                id: columnLayout
                width: 100
                height: 100
                spacing: 20
                Layout.preferredHeight: 1
                Layout.fillHeight: true
                Layout.fillWidth: true

                Rectangle {
                    id: rectangle1
                    width: 200
                    height: 200
                    color: "#b0000000"
                    radius: 25
                    Layout.preferredHeight: 1
                    Layout.fillHeight: true
                    Layout.fillWidth: true

                    RowLayout {
                        id: rowLayout1
                        anchors.fill: parent

                        RoundButton {
                            id: prevButton
                            text: ""
                            Layout.preferredWidth: 1
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            flat: true
                            highlighted: true
                            icon.source: "images/arrow_back.svg"
                            display: AbstractButton.IconOnly

                            Connections {
                                target: prevButton
                                onClicked: () => {
                                               if (tableView.model.rowCount()) {
                                                   if (tableView.selectedRow > 0) {
                                                       tableView.selectedRow -= 1
                                                   } else {
                                                       tableView.selectedRow = tableView.rows - 1
                                                   }
                                                   // 滾動到選取列
                                                   let targetY = 0
                                                   for (var i = 0; i < tableView.selectedRow; i++) {
                                                       let h = tableView.rowHeight(
                                                           i)
                                                       targetY += (h > 0 ? h : 45)
                                                       + tableView.rowSpacing
                                                   }
                                                   let rowH = tableView.rowHeight(
                                                       tableView.selectedRow)
                                                   rowH = rowH > 0 ? rowH : 45
                                                   // 若選取列在可視區域之上，滾動到該列頂部
                                                   if (targetY < tableView.contentY) {
                                                       tableView.contentY = targetY
                                                   } else // 若選取列在可視區域之下，滾動到該列底部對齊視窗底部
                                                   if (targetY + rowH > tableView.contentY
                                                       + tableView.height) {
                                                       tableView.contentY = targetY
                                                       + rowH - tableView.height
                                                   }
                                               }
                                           }
                            }
                        }
                        GridLayout {
                            id: gridLayout
                            width: 100
                            height: 100
                            columns: 2
                            rows: 5
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredWidth: 5

                            TextField {
                                id: textFrom
                                placeholderTextColor: enabled
                                                      && activeFocus ? Material.accentColor : "#b0ffffff"
                                Layout.fillHeight: false
                                Layout.fillWidth: true
                                Layout.rowSpan: 1
                                Layout.columnSpan: 2
                                placeholderText: qsTr("發文單位")

                                Connections {
                                    target: textFrom
                                    onFocusChanged: () => {
                                                        if (textFrom.focus) {
                                                            animWidth.to
                                                            = pinchArea.baseSizeWidth * 1.8
                                                            animHeight.to
                                                            = pinchArea.baseSizeHeight * 1.8
                                                            propertyAnimation.to = 220
                                                            propertyAnimation1.to = 0
                                                            animWidth.start()
                                                            animHeight.start()
                                                            propertyAnimation.start()
                                                            propertyAnimation1.start()
                                                        }
                                                    }
                                }
                            }

                            TextField {
                                id: textDate
                                placeholderTextColor: enabled
                                                      && activeFocus ? Material.accentColor : "#b0ffffff"
                                Layout.fillHeight: false
                                Layout.fillWidth: true
                                placeholderText: qsTr("發文日期")

                                Connections {
                                    target: textDate
                                    onFocusChanged: () => {
                                                        if (textDate.focus) {
                                                            animWidth.to
                                                            = pinchArea.baseSizeWidth * 2.5
                                                            animHeight.to
                                                            = pinchArea.baseSizeHeight * 2.5
                                                            propertyAnimation.to = 220
                                                            propertyAnimation1.to = 280
                                                            animWidth.start()
                                                            animHeight.start()
                                                            propertyAnimation.start()
                                                            propertyAnimation1.start()
                                                        }
                                                    }
                                }
                            }

                            TextField {
                                id: textOfficer
                                placeholderTextColor: enabled
                                                      && activeFocus ? Material.accentColor : "#b0ffffff"
                                Layout.fillHeight: false
                                Layout.fillWidth: true
                                placeholderText: qsTr("承辦人")
                                Connections {
                                    target: textOfficer
                                    onFocusChanged: () => {
                                                        if (textOfficer.focus) {
                                                            animWidth.to
                                                            = pinchArea.baseSizeWidth * 2.5
                                                            animHeight.to
                                                            = pinchArea.baseSizeHeight * 2.5
                                                            propertyAnimation.to = 600
                                                            propertyAnimation1.to = 0
                                                            animWidth.start()
                                                            animHeight.start()
                                                            propertyAnimation.start()
                                                            propertyAnimation1.start()
                                                        }
                                                    }
                                }
                            }

                            TextField {
                                id: textCategory
                                placeholderTextColor: enabled
                                                      && activeFocus ? Material.accentColor : "#b0ffffff"
                                Layout.fillHeight: false
                                Layout.fillWidth: true
                                placeholderText: qsTr("發文字")
                                Connections {
                                    target: textCategory
                                    onFocusChanged: () => {
                                                        if (textCategory.focus) {
                                                            animWidth.to
                                                            = pinchArea.baseSizeWidth * 2.5
                                                            animHeight.to
                                                            = pinchArea.baseSizeHeight * 2.5
                                                            propertyAnimation.to = 220
                                                            propertyAnimation1.to = 280
                                                            animWidth.start()
                                                            animHeight.start()
                                                            propertyAnimation.start()
                                                            propertyAnimation1.start()
                                                        }
                                                    }
                                }
                            }

                            TextField {
                                id: textNumber
                                placeholderTextColor: enabled
                                                      && activeFocus ? Material.accentColor : "#b0ffffff"
                                Layout.fillHeight: false
                                Layout.fillWidth: true
                                placeholderText: qsTr("發文號")
                                Connections {
                                    target: textNumber
                                    onFocusChanged: () => {
                                                        if (textNumber.focus) {
                                                            animWidth.to
                                                            = pinchArea.baseSizeWidth * 2.5
                                                            animHeight.to
                                                            = pinchArea.baseSizeHeight * 2.5
                                                            propertyAnimation.to = 220
                                                            propertyAnimation1.to = 280
                                                            animWidth.start()
                                                            animHeight.start()
                                                            propertyAnimation.start()
                                                            propertyAnimation1.start()
                                                        }
                                                    }
                                }
                            }

                            TextField {
                                id: textClass
                                placeholderTextColor: enabled
                                                      && activeFocus ? Material.accentColor : "#b0ffffff"
                                Layout.columnSpan: 2
                                Layout.fillHeight: false
                                Layout.fillWidth: true
                                placeholderText: qsTr("班級")
                                Connections {
                                    target: textClass
                                    onFocusChanged: () => {
                                                        if (textClass.focus) {
                                                            animWidth.to
                                                            = pinchArea.baseSizeWidth * 1.35
                                                            animHeight.to
                                                            = pinchArea.baseSizeHeight * 1.35
                                                            propertyAnimation.to = 90
                                                            propertyAnimation1.to = 100
                                                            animWidth.start()
                                                            animHeight.start()
                                                            propertyAnimation.start()
                                                            propertyAnimation1.start()
                                                        }
                                                    }
                                }
                            }

                            TextField {
                                id: textKeyPoint
                                placeholderTextColor: enabled
                                                      && activeFocus ? Material.accentColor : "#b0ffffff"
                                Layout.columnSpan: 2
                                Layout.fillHeight: false
                                Layout.fillWidth: true
                                placeholderText: qsTr("事由")
                                Connections {
                                    target: textKeyPoint
                                    onFocusChanged: () => {
                                                        if (textKeyPoint.focus) {
                                                            animWidth.to
                                                            = pinchArea.baseSizeWidth * 1.35
                                                            animHeight.to
                                                            = pinchArea.baseSizeHeight * 1.35
                                                            propertyAnimation.to = 90
                                                            propertyAnimation1.to = 100
                                                            animWidth.start()
                                                            animHeight.start()
                                                            propertyAnimation.start()
                                                            propertyAnimation1.start()
                                                        }
                                                    }
                                }
                            }
                        }

                        RoundButton {
                            id: nextButton
                            text: ""
                            highlighted: true
                            icon.source: "images/arrow_forward.svg"
                            Layout.preferredWidth: 1
                            Layout.fillWidth: true
                            flat: true
                            display: AbstractButton.IconOnly
                            Layout.fillHeight: true

                            Connections {
                                target: nextButton
                                onClicked: () => {
                                               if (tableView.model.rowCount()) {
                                                   if (tableView.selectedRow < tableView.rows - 1) {
                                                       tableView.selectedRow += 1
                                                   } else {
                                                       tableView.selectedRow = 0
                                                   }
                                                   // 滾動到選取列
                                                   let targetY = 0
                                                   for (var i = 0; i < tableView.selectedRow; i++) {
                                                       let h = tableView.rowHeight(
                                                           i)
                                                       targetY += (h > 0 ? h : 45)
                                                       + tableView.rowSpacing
                                                   }
                                                   let rowH = tableView.rowHeight(
                                                       tableView.selectedRow)
                                                   rowH = rowH > 0 ? rowH : 45
                                                   if (targetY < tableView.contentY) {
                                                       tableView.contentY = targetY
                                                   } else if (targetY + rowH > tableView.contentY
                                                              + tableView.height) {
                                                       tableView.contentY = targetY
                                                       + rowH - tableView.height
                                                   }
                                               }
                                           }
                            }
                        }
                    }
                }

                Rectangle {
                    id: rectangle2
                    width: 200
                    height: 200
                    color: "#b0000000"
                    radius: 25
                    Layout.preferredHeight: 1
                    Layout.fillHeight: true
                    Layout.fillWidth: true

                    ColumnLayout {
                        id: columnLayout1
                        anchors.fill: parent

                        RowLayout {
                            id: rowLayout2
                            width: 100
                            height: 100
                            Layout.margins: 10
                            Layout.leftMargin: 10
                            Layout.bottomMargin: 10
                            Layout.topMargin: 10
                            Layout.preferredHeight: 52
                            Layout.fillWidth: true
                            Layout.fillHeight: false

                            RoundButton {
                                id: addButton
                                text: "新增公文"
                                rightPadding: 20
                                leftPadding: 20
                                padding: 12
                                spacing: 5
                                font.bold: true
                                icon.source: "images/add_circle.svg"
                                highlighted: true
                                display: AbstractButton.TextBesideIcon

                                Connections {
                                    target: addButton
                                    onClicked: root.addClicked()
                                }
                            }

                            RoundButton {
                                id: analyzeButton
                                text: "開始分析"
                                spacing: 5
                                highlighted: true
                                icon.source: "images/scan_75dp_000000_FILL0_wght400_GRAD0_opsz48.svg"
                                font.bold: true
                                padding: 12
                                leftPadding: 20
                                display: AbstractButton.TextBesideIcon
                                rightPadding: 20

                                Connections {
                                    target: analyzeButton
                                    onClicked: root.analyzeClicked()
                                }
                            }

                            RoundButton {
                                id: uploadButton
                                text: "開始上傳"
                                spacing: 5
                                highlighted: true
                                icon.source: "images/upload_75dp_000000_FILL0_wght400_GRAD0_opsz48.svg"
                                font.bold: true
                                padding: 12
                                leftPadding: 20
                                display: AbstractButton.TextBesideIcon
                                rightPadding: 20

                                Connections {
                                    target: uploadButton
                                    onClicked: root.uploadClicked()
                                }
                            }

                            Item {
                                id: spacer
                                width: 200
                                height: 200
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                            }

                            RoundButton {
                                id: openButton
                                text: ""
                                flat: true
                                icon.source: "images/file_open_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg"
                                highlighted: true
                                display: AbstractButton.IconOnly
                                ToolTip.visible: hovered
                                ToolTip.text: "開啟存檔"
                                ToolTip.delay: 500
                                ToolTip.timeout: 3000

                                Connections {
                                    target: openButton
                                    onClicked: root.openClicked()
                                }
                            }

                            RoundButton {
                                id: saveButton
                                text: ""
                                flat: true
                                icon.source: "images/file_save_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg"
                                highlighted: true
                                display: AbstractButton.IconOnly
                                ToolTip.visible: hovered
                                ToolTip.text: "儲存"
                                ToolTip.delay: 500
                                ToolTip.timeout: 3000

                                Connections {
                                    target: saveButton
                                    onClicked: root.saveClicked()
                                }
                            }

                            RoundButton {
                                id: resetButton
                                text: "+"
                                flat: true
                                icon.source: "images/delete_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg"
                                highlighted: true
                                display: AbstractButton.IconOnly
                                ToolTip.visible: hovered
                                ToolTip.text: "清除"
                                ToolTip.delay: 500
                                ToolTip.timeout: 3000

                                Connections {
                                    target: resetButton
                                    onClicked: root.resetClicked()
                                }
                            }

                            RoundButton {
                                id: settingsButton
                                text: "+"
                                flat: true
                                icon.source: "images/settings_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg"
                                highlighted: true
                                display: AbstractButton.IconOnly
                                ToolTip.visible: hovered
                                ToolTip.text: "設定"
                                ToolTip.delay: 500
                                ToolTip.timeout: 3000

                                Connections {
                                    target: settingsButton
                                    onClicked: () => {
                                                   root.settingsClicked()
                                               }
                                }
                            }
                        }

                        HorizontalHeaderView {
                            id: horizontalHeader
                            syncView: tableView
                            Layout.fillWidth: true
                            clip: true

                            delegate: Rectangle {
                                required property int column
                                required property string display

                                implicitWidth: (column === 0) ? 80 : 150
                                implicitHeight: 45
                                color: "#20ffffff"

                                Rectangle {
                                    height: 1
                                    color: "#15ffffff"
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                }
                                Rectangle {
                                    width: 1
                                    color: "#15ffffff"
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                }

                                Text {
                                    text: model.display
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    color: Material.foreground
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: (column === 0) ? Text.AlignHCenter : Text.AlignLeft
                                    font.pointSize: 11
                                    font.bold: true
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        TableView {
                            id: tableView
                            property int selectedRow: -1
                            property int hoveredRow: -1

                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            columnSpacing: 1
                            rowSpacing: 1
                            clip: true

                            MouseArea {
                                id: tableWheelArea
                                anchors.fill: parent
                                acceptedButtons: Qt.NoButton

                                Connections {
                                    target: tableWheelArea
                                    onWheel: wheel => {
                                                 let notches = wheel.angleDelta.y / Math.abs(
                                                     wheel.angleDelta.y) * 1
                                                 if (wheel.modifiers & Qt.ShiftModifier) {
                                                     // 左右：動態取得欄位寬度，若目標未渲染則使用當前欄位寬度作為基準
                                                     if (notches < 0) {
                                                         // 往右滾動
                                                         let w = tableView.columnWidth(
                                                             tableView.leftColumn)
                                                         w = (w > 0 ? w : 150)
                                                         + tableView.columnSpacing
                                                         tableView.contentX = Math.min(
                                                             tableView.contentX + w,
                                                             Math.max(
                                                                 0,
                                                                 tableView.contentWidth
                                                                 - tableView.width))
                                                     } else {
                                                         // 往左滾動
                                                         let prevCol = Math.max(
                                                             0,
                                                             tableView.leftColumn - 1)
                                                         let w = tableView.columnWidth(
                                                             prevCol)
                                                         if (w <= 0)
                                                         w = tableView.columnWidth(
                                                             tableView.leftColumn)
                                                         w = (w > 0 ? w : 150)
                                                         + tableView.columnSpacing
                                                         tableView.contentX = Math.max(
                                                             0,
                                                             tableView.contentX - w)
                                                     }
                                                 } else {
                                                     // 上下：動態取得列高度，若目標未渲染則使用當前列高度作為基準
                                                     if (notches < 0) {
                                                         // 往下滾動
                                                         let h = tableView.rowHeight(
                                                             tableView.topRow)
                                                         h = (h > 0 ? h : 45) + tableView.rowSpacing
                                                         tableView.contentY = Math.min(
                                                             tableView.contentY + h,
                                                             Math.max(
                                                                 0,
                                                                 tableView.contentHeight
                                                                 - tableView.height))
                                                     } else {
                                                         // 往上滾動
                                                         let prevRow = Math.max(
                                                             0,
                                                             tableView.topRow - 1)
                                                         let h = tableView.rowHeight(
                                                             prevRow)
                                                         if (h <= 0)
                                                         h = tableView.rowHeight(
                                                             tableView.topRow)
                                                         h = (h > 0 ? h : 45) + tableView.rowSpacing
                                                         tableView.contentY = Math.max(
                                                             0,
                                                             tableView.contentY - h)
                                                     }
                                                 }
                                                 wheel.accepted = true
                                             }
                                }
                            }

                            // 💡 符合 Design Studio 規範的 Delegate
                            delegate: Rectangle {
                                id: cellRectangle

                                // Design Studio 規範：使用 required property 接收 TableView 的內建索引
                                required property int row
                                required property int column

                                // 接收來自 model 的資料（由外部或系統注入）
                                property string cellText: display
                                property bool isSelected: tableView.selectedRow === row
                                property bool isHovered: tableView.hoveredRow === row

                                property color cellBackgroundColor: isSelected ? "#30b87f4d" : isHovered ? "#15ffffff" : ((row % 2 === 0) ? "transparent" : "#05ffffff")

                                implicitWidth: (column === 0) ? 80 : 150
                                implicitHeight: 45
                                color: cellBackgroundColor

                                // 分隔線
                                Rectangle {
                                    height: 1
                                    color: "#15ffffff" // 改為半透明白以符合深色主題
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                }
                                Rectangle {
                                    width: 1
                                    color: "#15ffffff"
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                }

                                // 點擊與懸停偵測 (使用 Connections 遵守 Design Studio 規範)
                                TapHandler {
                                    id: tapHandler
                                }
                                Connections {
                                    target: tapHandler
                                    onTapped: () => {
                                                  tableView.selectedRow = cellRectangle.row
                                              }
                                }

                                HoverHandler {
                                    id: hoverHandler
                                }
                                Connections {
                                    target: hoverHandler
                                    onHoveredChanged: () => {
                                                          if (hoverHandler.hovered) {
                                                              tableView.hoveredRow
                                                              = cellRectangle.row
                                                          } else if (tableView.hoveredRow
                                                                     === cellRectangle.row) {
                                                              tableView.hoveredRow = -1
                                                          }
                                                      }
                                }

                                Text {
                                    text: cellRectangle.cellText // 綁定到自訂屬性
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    color: (cellRectangle.column === 0) ? Material.accentColor : Material.foreground // 第0欄使用 Accent color，其餘用淺灰色
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: (cellRectangle.column === 0) ? Text.AlignHCenter : Text.AlignLeft
                                    font.pointSize: 11
                                    font.bold: (cellRectangle.column === 0)
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
