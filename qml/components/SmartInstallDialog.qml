import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property bool isOpen: false
    property string toolName: ""
    property string toolType: "tool"
    property string executableName: ""
    property string descriptionText: ""
    property string proposedCommand: ""
    property string sourceKind: "recipe"
    property string retryAction: ""
    property string targetFilePath: ""
    property string targetLanguageId: ""

    property bool isInstalling: false
    property string statusMessage: ""
    property string installLogs: ""

    signal confirmed(string toolName, string command, string executable, string retryAction, string filePath)
    signal cancelled()
    signal retryRequested(string action, string filePath, string langId)

    anchors.fill: parent
    color: "#a0000000"
    visible: isOpen
    z: 9999

    // Consume all clicks so background isn't clicked through
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        onClicked: {}
    }

    Connections {
        target: typeof extensionManager !== "undefined" ? extensionManager : null
        ignoreUnknownSignals: true

        function onSmartInstallProgress(name, status, msg) {
            if (name === root.toolName || !root.toolName) {
                root.isInstalling = (status === "installing");
                root.statusMessage = msg;
                root.installLogs += (msg + "\n");
            }
        }

        function onSmartInstallCompleted(name, success, msg, retryAct) {
            root.isInstalling = false;
            root.statusMessage = msg;
            root.installLogs += (msg + "\n");

            if (success) {
                successTimer.restart();
            }
        }
    }

    Timer {
        id: successTimer
        interval: 1000
        repeat: false
        onTriggered: {
            var act = root.retryAction;
            var fp = root.targetFilePath;
            var lang = root.targetLanguageId;
            root.isOpen = false;
            root.retryRequested(act, fp, lang);
        }
    }

    Rectangle {
        id: modalCard
        width: Math.min(540, parent.width - 32)
        height: Math.min(420, parent.height - 48)
        anchors.centerIn: parent
        radius: 6
        color: theme ? theme.bgSurface : "#1e1e1e"
        border.color: theme ? theme.borderNormal : "#333333"
        border.width: 1
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            // 1. Header
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: 32
                    height: 32
                    radius: 16
                    color: (theme ? theme.accent : "#0078d4") + "25"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "download"
                        size: 16
                        color: theme ? theme.accent : "#0078d4"
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: "Smart Install Developer Tool"
                        color: theme ? theme.textBright : "#ffffff"
                        font.pixelSize: 14
                        font.bold: true
                        font.family: theme ? theme.fontFamilyUi : "Segoe UI, sans-serif"
                    }

                    Text {
                        text: "Automatic environment setup & dependency resolution"
                        color: theme ? theme.textMuted : "#888888"
                        font.pixelSize: 11
                        font.family: theme ? theme.fontFamilyUi : "Segoe UI, sans-serif"
                    }
                }

                // Close Button
                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: closeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "close"
                        size: 10
                        color: theme ? theme.textMuted : "#888888"
                    }

                    MouseArea {
                        id: closeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (!root.isInstalling) {
                                root.isOpen = false;
                                root.cancelled();
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: theme ? theme.borderSubtle : "#282828"
            }

            // 2. Tool Description / Notice
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: descCol.implicitHeight + 16
                radius: 4
                color: theme ? theme.bgPanel : "#141414"
                border.color: theme ? theme.borderSubtle : "#282828"
                border.width: 1

                ColumnLayout {
                    id: descCol
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 4

                    RowLayout {
                        spacing: 6
                        Text {
                            text: root.toolName || "Required Developer Tool"
                            color: theme ? theme.textBright : "#ffffff"
                            font.pixelSize: 12
                            font.bold: true
                        }

                        Rectangle {
                            height: 16
                            width: sourceBadgeText.implicitWidth + 8
                            radius: 8
                            color: root.sourceKind === "recipe" ? "#0284c725" : "#a855f725"
                            border.color: root.sourceKind === "recipe" ? "#0284c7" : "#a855f7"
                            border.width: 1

                            Text {
                                id: sourceBadgeText
                                anchors.centerIn: parent
                                text: root.sourceKind === "recipe" ? "Verified Recipe" : "AI Suggested"
                                color: root.sourceKind === "recipe" ? "#38bdf8" : "#c084fc"
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.descriptionText || "This tool is required to perform the requested operation."
                        color: theme ? theme.textSecondary : "#aaaaaa"
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                }
            }

            // 3. Proposed Command Display Box
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Text {
                    text: "Exact Proposed Command:"
                    color: theme ? theme.textSecondary : "#cccccc"
                    font.pixelSize: 11
                    font.bold: true
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 52
                    radius: 4
                    color: theme ? theme.bgInput : "#0d0d0d"
                    border.color: theme ? theme.borderNormal : "#333333"
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 6

                        Text {
                            Layout.fillWidth: true
                            text: root.proposedCommand || "No command generated"
                            color: theme ? theme.success : "#4ade80"
                            font.pixelSize: 11
                            font.family: theme ? theme.fontFamilyMono : "Consolas, monospace"
                            wrapMode: Text.WrapAnywhere
                            elide: Text.ElideMiddle
                        }

                        Rectangle {
                            width: 24
                            height: 24
                            radius: 3
                            color: copyMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                            VectorIcon {
                                anchors.centerIn: parent
                                name: "copy"
                                size: 11
                                color: theme ? theme.textSecondary : "#aaaaaa"
                            }

                            MouseArea {
                                id: copyMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (typeof extensionManager !== "undefined" && extensionManager) {
                                        extensionManager.copy_to_clipboard(root.proposedCommand);
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // 4. Execution Logs / Status
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 4
                color: theme ? theme.bgPanel : "#121212"
                border.color: theme ? theme.borderSubtle : "#252525"
                border.width: 1
                visible: root.isInstalling || root.installLogs.length > 0

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 6
                    clip: true

                    Text {
                        width: parent.width
                        text: root.installLogs || root.statusMessage
                        color: theme ? theme.textSecondary : "#aaaaaa"
                        font.pixelSize: 10
                        font.family: theme ? theme.fontFamilyMono : "monospace"
                        wrapMode: Text.WrapAnywhere
                    }
                }
            }

            // 5. Actions Footer
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Item { Layout.fillWidth: true }

                // Cancel Button
                Rectangle {
                    width: 80
                    height: 28
                    radius: 3
                    color: cancelMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                    border.color: theme ? theme.borderNormal : "#333333"
                    border.width: 1
                    enabled: !root.isInstalling

                    Text {
                        anchors.centerIn: parent
                        text: "Cancel"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 11
                    }

                    MouseArea {
                        id: cancelMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.isOpen = false;
                            root.cancelled();
                        }
                    }
                }

                // Smart Install Confirm Button
                Rectangle {
                    width: 120
                    height: 28
                    radius: 3
                    color: root.isInstalling ? (theme ? theme.bgSurfaceActive : "#444444") : (confirmMa.containsMouse ? (theme ? theme.accentHover : "#006cbd") : (theme ? theme.accent : "#0078d4"))
                    enabled: !root.isInstalling

                    Row {
                        anchors.centerIn: parent
                        spacing: 5

                        VectorIcon {
                            anchors.verticalCenter: parent.verticalCenter
                            name: "download"
                            size: 11
                            color: "#ffffff"
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.isInstalling ? "Installing..." : "Smart Install"
                            color: "#ffffff"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: confirmMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.isInstalling = true;
                            root.installLogs = "Starting Smart Install for " + root.toolName + "...\n";
                            if (typeof extensionManager !== "undefined" && extensionManager) {
                                extensionManager.execute_smart_install_command(
                                    root.toolName,
                                    root.proposedCommand,
                                    root.executableName,
                                    root.retryAction,
                                    root.targetFilePath
                                );
                            }
                            root.confirmed(root.toolName, root.proposedCommand, root.executableName, root.retryAction, root.targetFilePath);
                        }
                    }
                }
            }
        }
    }

    function openProposal(proposal) {
        if (!proposal) return;
        root.toolName = proposal.toolName || "";
        root.toolType = proposal.toolType || "tool";
        root.executableName = proposal.executable || "";
        root.descriptionText = proposal.description || "";
        root.proposedCommand = proposal.command || "";
        root.sourceKind = proposal.source || "recipe";
        root.retryAction = proposal.retryAction || "";
        root.targetFilePath = proposal.filePath || "";
        root.targetLanguageId = proposal.languageId || "";
        root.isInstalling = false;
        root.statusMessage = "";
        root.installLogs = "";
        root.isOpen = true;
    }
}
