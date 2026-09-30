import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property string currentLanguage: "Plain Text"
    property int cursorLine: 1
    property int cursorColumn: 1

    signal languageSelected(string lang)
    signal settingsRequested()
    signal themeSelected(string themeName)

    height: 22
    color: theme ? theme.bgHeader : "#181818"

    // Single 1px top border line separating workspace from status bar
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: theme ? theme.borderSubtle : "#282828"
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 14

        // 1. Language Pill / Selector
        Rectangle {
            height: 18
            width: langText.contentWidth + 8
            radius: 2
            color: langMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

            Text {
                id: langText
                anchors.centerIn: parent
                text: root.currentLanguage
                color: theme ? theme.textPrimary : "#cccccc"
                font.pixelSize: 11
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
            }

            MouseArea {
                id: langMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: langMenu.open()
            }

            Menu {
                id: langMenu
                y: -contentHeight - 2
                background: Rectangle {
                    implicitWidth: 150
                    color: theme ? theme.bgPopup : "#252526"
                    border.color: theme ? theme.borderNormal : "#333333"
                    radius: theme ? theme.radiusSm : 3
                }

                Action { text: "Python"; onTriggered: root.languageSelected("Python") }
                Action { text: "JavaScript"; onTriggered: root.languageSelected("JavaScript") }
                Action { text: "TypeScript"; onTriggered: root.languageSelected("TypeScript") }
                Action { text: "C++"; onTriggered: root.languageSelected("C++") }
                Action { text: "C"; onTriggered: root.languageSelected("C") }
                Action { text: "HTML"; onTriggered: root.languageSelected("HTML") }
                Action { text: "CSS"; onTriggered: root.languageSelected("CSS") }
                Action { text: "JSON"; onTriggered: root.languageSelected("JSON") }
                Action { text: "QML"; onTriggered: root.languageSelected("QML") }
                Action { text: "Plain Text"; onTriggered: root.languageSelected("Plain Text") }

                delegate: MenuItem {
                    id: langItm
                    implicitHeight: 24
                    contentItem: Text {
                        text: langItm.text
                        color: langItm.highlighted ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                        font.pixelSize: 11
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: 6
                    }
                    background: Rectangle {
                        color: langItm.highlighted ? (theme ? theme.bgSelected : "#04395e") : "transparent"
                    }
                }
            }
        }

        // 2. Cursor Position
        Text {
            text: "Ln " + root.cursorLine + ", Col " + root.cursorColumn
            color: theme ? theme.textSecondary : "#858585"
            font.pixelSize: 11
            font.family: theme ? theme.fontFamilyUi : "sans-serif"
        }

        // 3. Encoding & Spaces
        Text {
            text: "UTF-8"
            color: theme ? theme.textMuted : "#656565"
            font.pixelSize: 11
            font.family: theme ? theme.fontFamilyUi : "sans-serif"
        }

        Text {
            text: "Spaces: " + (theme ? theme.tabSize : 4)
            color: theme ? theme.textMuted : "#656565"
            font.pixelSize: 11
            font.family: theme ? theme.fontFamilyUi : "sans-serif"
        }

        Item {
            Layout.fillWidth: true
        }

        // 4. Quick Notification / Ready State
        RowLayout {
            spacing: 4

            Rectangle {
                width: 6
                height: 6
                radius: 3
                color: theme ? theme.success : "#4ec9b0"
            }

            Text {
                text: "Ready"
                color: theme ? theme.textMuted : "#656565"
                font.pixelSize: 11
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
            }
        }
    }
}
