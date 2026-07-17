import QtQuick; import Qt.labs.qmlmodels; Item { TableModel { id: m; TableModelColumn { display: c1 } }; Component.onCompleted: { console.log(has headerData:, typeof m.headerData !== undefined) } }
