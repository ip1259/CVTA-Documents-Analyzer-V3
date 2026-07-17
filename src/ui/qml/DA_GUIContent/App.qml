import QtQuick
import DA_GUI
import QtQuick.Controls
import QtQuick.Controls.Material

Window {
    id: appWindow
    width: 1400
    height: 810

    visible: true
    title: "DA_GUI"
    Material.theme: Material.Dark
    Material.primary: "#5A9690"
    Material.accent: "#b87f4d"
    Material.background: "#151d30"
    required property QtObject docController

    Screen01 {
        id: mainScreen
        anchors.fill: parent

        tableModel: appWindow.docController.tableModel
        selectedRow: appWindow.docController.selectedRow

        unitText: appWindow.docController.currentUnit
        dateText: appWindow.docController.currentDate
        officerText: appWindow.docController.currentOfficer
        categoryText: appWindow.docController.currentCategory
        numberText: appWindow.docController.currentNumber
        classText: appWindow.docController.currentClass
        keyPointText: appWindow.docController.currentKeyPoint

        onUnitTextChanged: appWindow.docController.currentUnit = unitText
        onDateTextChanged: appWindow.docController.currentDate = dateText
        onOfficerTextChanged: appWindow.docController.currentOfficer = officerText
        onCategoryTextChanged: appWindow.docController.currentCategory = categoryText
        onNumberTextChanged: appWindow.docController.currentNumber = numberText
        onClassTextChanged: appWindow.docController.currentClass = classText
        onKeyPointTextChanged: appWindow.docController.currentKeyPoint = keyPointText

        imageSource: appWindow.docController.currentImageSource

        onSelectedRowChanged: {
            if (mainScreen.selectedRow !== -1) {
                appWindow.docController.handleRowChanged(mainScreen.selectedRow)
            }
        }

        onAddClicked: appWindow.docController.addDocument()
        onAnalyzeClicked: appWindow.docController.analyzeDocument()
        onUploadClicked: appWindow.docController.uploadDocument()
        onOpenClicked: appWindow.docController.openArchive()
        onSaveClicked: appWindow.docController.saveArchive()
        onResetClicked: appWindow.docController.clearAllData()
        onSettingsClicked: appWindow.docController.openSettings()
    }
}
