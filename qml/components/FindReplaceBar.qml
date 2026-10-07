import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property bool isReplaceMode: false
    property string findText: findInput.text
    property string replaceText: replaceInput.text
    property bool matchCase: false
    property bool matchWholeWord: false
    property int currentMatchIndex: 0
    property int totalMatches: 0

    signal findNextRequested()
    signal findPrevRequested()
    signal replaceRequested()
    signal replaceAllRequested()
    signal closeRequested()
    function focusInput() {
        findInput.forceActiveFocus();
        findInput.selectAll();
    }

    function setFindText(t) {
        findInput.text = t;
    }

    onFindTextChanged: {
        root.findNextRequested();
    }

    width: 380
    height: isReplaceMode ? 76 : 38
    radius: theme ? theme.radiusMd : 6
    color: theme ? theme.bgPopup : "#151824"
    border.color: theme ? theme.borderNormal : "#2a3145"
    border.width: 1

    Behavior on height {
        NumberAnimation { duration: theme ? theme.animationDurationFast : 120 }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 4

        // 1. Find Row
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            // Toggle Replace Arrow
            Rectangle {
                width: 22
                height: 22
                radius: 4
                color: expandMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#202536") : "transparent"

                VectorIcon {
                    anchors.centerIn: parent
                    name: root.isReplaceMode ? "chevron-down" : "chevron-right"
                    size: 11
                    color: theme ? theme.textSecondary : "#94a3b8"
                }

                MouseArea {
                    id: expandMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.isReplaceMode = !root.isReplaceMode
                }
            }

            // Find Input
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 4
                color: theme ? theme.bgInput : "#0e1017"
                border.color: findInput.activeFocus ? (theme ? theme.borderFocus : "#3b82f6") : (theme ? theme.borderSubtle : "#1f2433")

                TextInput {
                    id: findInput
                    objectName: "findInput"
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 6
                    verticalAlignment: TextInput.AlignVCenter
                    color: theme ? theme.textPrimary : "#f1f5f9"
                    font.pixelSize: 12
                    font.family: theme ? theme.fontFamilyMono : "monospace"
                    selectByMouse: true

                    Text {
                        anchors.fill: parent
                        verticalAlignment: Text.AlignVCenter
                        text: "Find..."
                        color: theme ? theme.textMuted : "#64748b"
                        font.pixelSize: 12
                        visible: !findInput.text && !findInput.activeFocus
                    }

                    onAccepted: root.findNextRequested()

                    Keys.onEscapePressed: root.closeRequested()
                    Keys.onPressed: function(event) {
                        if (event.key === Qt.Key_F3) {
                            if (event.modifiers & Qt.ShiftModifier) {
                                root.findPrevRequested();
                            } else {
                                root.findNextRequested();
                            }
                            event.accepted = true;
                        }
                    }
                }
            }

            // Match Count
            Text {
                text: root.findText.length > 0 ? (root.totalMatches > 0 ? (root.currentMatchIndex + 1) + " of " + root.totalMatches : "No results") : ""
                color: root.totalMatches > 0 ? (theme ? theme.textSecondary : "#94a3b8") : (theme ? theme.error : "#ef4444")
                font.pixelSize: 11
                Layout.preferredWidth: 60
            }

            // Previous Button
            Rectangle {
                width: 22
                height: 22
                radius: 4
                color: prevMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#202536") : "transparent"

                VectorIcon {
                    anchors.centerIn: parent
                    name: "prev"
                    size: 10
                    color: theme ? theme.textSecondary : "#94a3b8"
                }

                ToolTip.visible: prevMa.containsMouse
                ToolTip.text: "Previous Match (Shift+F3)"

                MouseArea {
                    id: prevMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.findPrevRequested()
                }
            }

            // Next Button
            Rectangle {
                width: 22
                height: 22
                radius: 4
                color: nextMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#202536") : "transparent"

                VectorIcon {
                    anchors.centerIn: parent
                    name: "next"
                    size: 10
                    color: theme ? theme.textSecondary : "#94a3b8"
                }

                ToolTip.visible: nextMa.containsMouse
                ToolTip.text: "Next Match (F3)"

                MouseArea {
                    id: nextMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.findNextRequested()
                }
            }

            // Match Case Toggle Button (Aa)
            Rectangle {
                width: 24
                height: 22
                radius: 4
                color: root.matchCase ? (theme ? theme.accentMuted : "#3b82f630") : (caseMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#202536") : "transparent")
                border.color: root.matchCase ? (theme ? theme.borderFocus : "#3b82f6") : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "Aa"
                    font.pixelSize: 11
                    font.bold: root.matchCase
                    color: root.matchCase ? (theme ? theme.accent : "#3b82f6") : (theme ? theme.textSecondary : "#94a3b8")
                }

                ToolTip.visible: caseMa.containsMouse
                ToolTip.text: "Match Case"

                MouseArea {
                    id: caseMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.matchCase = !root.matchCase
                }
            }

            // Close Button
            Rectangle {
                width: 22
                height: 22
                radius: 4
                color: closeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#202536") : "transparent"

                VectorIcon {
                    anchors.centerIn: parent
                    name: "close"
                    size: 10
                    color: closeMa.containsMouse ? (theme ? theme.error : "#ef4444") : (theme ? theme.textSecondary : "#94a3b8")
                }

                MouseArea {
                    id: closeMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.closeRequested()
                }
            }
        }

        // 2. Replace Row (visible when isReplaceMode)
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            visible: root.isReplaceMode

            Item {
                width: 22
                height: 22
            }

            // Replace Input
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 4
                color: theme ? theme.bgInput : "#0e1017"
                border.color: replaceInput.activeFocus ? (theme ? theme.borderFocus : "#3b82f6") : (theme ? theme.borderSubtle : "#1f2433")

                TextInput {
                    id: replaceInput
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 6
                    verticalAlignment: TextInput.AlignVCenter
                    color: theme ? theme.textPrimary : "#f1f5f9"
                    font.pixelSize: 12
                    font.family: theme ? theme.fontFamilyMono : "monospace"
                    selectByMouse: true

                    Text {
                        anchors.fill: parent
                        verticalAlignment: Text.AlignVCenter
                        text: "Replace with..."
                        color: theme ? theme.textMuted : "#64748b"
                        font.pixelSize: 12
                        visible: !replaceInput.text && !replaceInput.activeFocus
                    }

                    onAccepted: root.replaceRequested()
                }
            }

            // Replace Button
            Rectangle {
                width: 60
                height: 22
                radius: 4
                color: repMa.containsMouse ? (theme ? theme.bgSurfaceActive : "#282f44") : (theme ? theme.bgSurface : "#181c28")
                border.color: theme ? theme.borderSubtle : "#1f2433"

                Text {
                    anchors.centerIn: parent
                    text: "Replace"
                    color: theme ? theme.textPrimary : "#f1f5f9"
                    font.pixelSize: 11
                }

                MouseArea {
                    id: repMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.replaceRequested()
                }
            }

            // Replace All Button
            Rectangle {
                width: 70
                height: 22
                radius: 4
                color: repAllMa.containsMouse ? (theme ? theme.bgSurfaceActive : "#282f44") : (theme ? theme.bgSurface : "#181c28")
                border.color: theme ? theme.borderSubtle : "#1f2433"

                Text {
                    anchors.centerIn: parent
                    text: "Replace All"
                    color: theme ? theme.textPrimary : "#f1f5f9"
                    font.pixelSize: 11
                }

                MouseArea {
                    id: repAllMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.replaceAllRequested()
                }
            }
        }
    }

    function focusFind() {
        findInput.forceActiveFocus()
        findInput.selectAll()
    }
}
