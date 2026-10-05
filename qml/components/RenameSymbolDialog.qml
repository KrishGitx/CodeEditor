import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property bool isOpen: false
    property string currentSymbol: ""
    property int targetLine: 0
    property int targetCol: 0

    signal renameConfirmed(string oldName, string newName)
    signal closeRequested()

    visible: isOpen
    z: 9998
    width: 260
    height: 42
    radius: 6
    color: theme ? theme.bgPopup : "#151824"
    border.color: theme ? theme.accent : "#3b82f6"
    border.width: 1.5

    function openAt(targetX, targetY, symbolName, line, col) {
        currentSymbol = symbolName || "";
        targetLine = line;
        targetCol = col;
        renameInput.text = symbolName || "";
        x = Math.max(10, Math.min(parent ? (parent.width - width - 10) : 100, targetX));
        y = Math.max(10, targetY - height - 4);
        if (y < 10) {
            y = targetY + 22;
        }
        isOpen = true;
        renameInput.forceActiveFocus();
        renameInput.selectAll();
    }

    function close() {
        isOpen = false;
        root.closeRequested();
    }

    function confirm() {
        var newName = renameInput.text.trim();
        if (newName && newName !== currentSymbol) {
            root.renameConfirmed(currentSymbol, newName);
        }
        root.close();
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 4
        spacing: 6

        TextInput {
            id: renameInput
            Layout.fillWidth: true
            Layout.fillHeight: true
            verticalAlignment: TextInput.AlignVCenter
            color: theme ? theme.textPrimary : "#f1f5f9"
            selectionColor: theme ? theme.accent : "#3b82f6"
            selectedTextColor: "#ffffff"
            font.pixelSize: 12
            font.family: "Consolas, 'Courier New', monospace"
            leftPadding: 6

            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Escape) {
                    root.close();
                    event.accepted = true;
                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                    root.confirm();
                    event.accepted = true;
                }
            }
        }

        Rectangle {
            width: 26
            height: 26
            radius: 4
            color: confirmMa.containsMouse ? (theme ? theme.accent : "#3b82f6") : (theme ? theme.bgSurface : "#1e293b")

            VectorIcon {
                anchors.centerIn: parent
                name: "save"
                size: 12
                color: "#ffffff"
            }

            MouseArea {
                id: confirmMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.confirm()
            }
        }
    }
}
