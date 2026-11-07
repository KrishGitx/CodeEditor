import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property var extensionData: null
    signal closeRequested()

    color: (typeof theme !== "undefined" && theme) ? theme.bgEditor : "#1e1e1e"

    readonly property string extId: extensionData ? (extensionData.id || extensionData.name || "") : ""
    readonly property string extName: extensionData ? (extensionData.name || extensionData.id || "Extension") : "Extension"
    readonly property string extVersion: extensionData ? ("v" + (extensionData.version || "1.0.0")) : "v1.0.0"
    readonly property string extAuthor: extensionData ? (extensionData.author || "DGX Studio") : "DGX Studio"
    readonly property string extDescription: extensionData ? (extensionData.description || "Provides language support, syntax highlighting, and formatting tools.") : ""
    property bool installedOverride: false
    property bool enabledOverride: false
    property bool hasOverride: false

    onExtensionDataChanged: {
        hasOverride = false;
        installedOverride = false;
        enabledOverride = false;
        isInstalling = false;
    }

    function checkInstalled(targetId) {
        if (!targetId) return false;
        if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.is_extension_installed) {
            return extensionManager.is_extension_installed(targetId);
        }
        return false;
    }

    property bool isInstalled: hasOverride ? installedOverride : (checkInstalled(root.extId) || Boolean(extensionData && extensionData.installed))
    readonly property bool isEnabled: hasOverride ? enabledOverride : (extensionData ? Boolean(extensionData.enabled) : true)
    readonly property bool isMarketplaceUninstalled: Boolean(extensionData && extensionData.is_marketplace && !root.isInstalled)
    property bool isInstalling: false

    Connections {
        target: (typeof extensionManager !== "undefined" && extensionManager) ? extensionManager : null
        function onOpenVsxInstallProgress(extId, status, message) {
            if (root.extId.toLowerCase() === (extId || "").toLowerCase()) {
                if (status === "downloading" || status === "extracting") {
                    root.isInstalling = true;
                } else if (status === "done") {
                    root.isInstalling = false;
                    root.hasOverride = true;
                    root.installedOverride = true;
                    root.enabledOverride = true;
                    if (typeof theme !== "undefined" && theme && theme.refreshAvailableThemes) {
                        theme.refreshAvailableThemes();
                    }
                } else if (status === "error") {
                    root.isInstalling = false;
                }
            }
        }
        function onExtensionsChanged() {
            if (!root.hasOverride) {
                root.isInstalled = root.checkInstalled(root.extId) || Boolean(root.extensionData && root.extensionData.installed);
            }
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: Math.min(840, parent.width - 64)
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 32
            spacing: 24

            // Top Header: Icon + Info + Action Buttons
            RowLayout {
                Layout.fillWidth: true
                spacing: 24

                // Large Extension Icon
                Rectangle {
                    Layout.preferredWidth: 72
                    Layout.preferredHeight: 72
                    radius: 8
                    color: {
                        var n = (root.extName).toLowerCase();
                        if (n.indexOf("react") !== -1) return "#087ea4";
                        if (n.indexOf("astro") !== -1) return "#bc52ee";
                        if (n.indexOf("unity") !== -1) return "#222c37";
                        if (n.indexOf("godot") !== -1) return "#478cbf";
                        if (n.indexOf("rust") !== -1) return "#b7410e";
                        if (n.indexOf("python") !== -1) return "#3572A5";
                        if (n.indexOf("c++") !== -1 || n.indexOf("c/") !== -1) return "#00599C";
                        if (n.indexOf("java") !== -1) return "#b07219";
                        return (typeof theme !== "undefined" && theme) ? theme.bgSurface : "#2a2d2e";
                    }
                    border.color: (typeof theme !== "undefined" && theme) ? theme.borderSubtle : "#3c3c3c"
                    border.width: 1

                    Image {
                        id: detailsAvatarImg
                        anchors.centerIn: parent
                        width: 52
                        height: 52
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true
                        source: (root.extensionData && (root.extensionData.iconUrl || root.extensionData.icon)) ? (root.extensionData.iconUrl || root.extensionData.icon) : ""
                        visible: status === Image.Ready
                    }

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "puzzle"
                        size: 36
                        color: "#ffffff"
                        visible: !detailsAvatarImg.visible
                    }
                }

                // Extension Title & Meta
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    RowLayout {
                        spacing: 12
                        Text {
                            text: root.extName
                            font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                            font.pixelSize: 22
                            font.bold: true
                            color: (typeof theme !== "undefined" && theme) ? theme.textBright : "#ffffff"
                        }
                        Text {
                            text: root.extVersion
                            font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                            font.pixelSize: 13
                            color: (typeof theme !== "undefined" && theme) ? theme.textDisabled : "#757575"
                            Layout.alignment: Qt.AlignBaseline
                        }
                    }

                    Text {
                        text: root.extAuthor + "  •  " + root.extId
                        font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                        font.pixelSize: 12
                        color: (typeof theme !== "undefined" && theme) ? theme.textSecondary : "#858585"
                    }

                    // Action Buttons Row (Disable / Enable, Uninstall / Remove, Install, Settings)
                    RowLayout {
                        spacing: 10
                        Layout.topMargin: 8

                        // Install Button for marketplace extension
                        Rectangle {
                            visible: root.isMarketplaceUninstalled
                            Layout.preferredWidth: 96
                            Layout.preferredHeight: 28
                            radius: (typeof theme !== "undefined" && theme && theme.radiusSm) ? theme.radiusSm : 3
                            color: root.isInstalling ? "#444444" : (instMa.containsMouse ? ((typeof theme !== "undefined" && theme) ? theme.accentHover : "#106ebe") : ((typeof theme !== "undefined" && theme) ? theme.accent : "#0078d4"))
                            border.color: (typeof theme !== "undefined" && theme) ? theme.borderNormal : "#444444"
                            border.width: 1

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6

                                VectorIcon {
                                    name: root.isInstalling ? "refresh" : "install"
                                    size: 11
                                    color: "#ffffff"
                                }

                                Text {
                                    text: root.isInstalling ? "Installing…" : "Install"
                                    font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: "#ffffff"
                                }
                            }

                            MouseArea {
                                id: instMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: root.isInstalling ? Qt.ArrowCursor : Qt.PointingHandCursor
                                onClicked: {
                                    if (root.isInstalling) return;
                                    root.isInstalling = true;
                                    if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.install_from_open_vsx) {
                                        extensionManager.install_from_open_vsx(root.extensionData.downloadUrl, root.extId, root.extName);
                                    }
                                }
                            }
                        }

                        // Enable / Disable Button
                        Rectangle {
                            visible: !root.isMarketplaceUninstalled
                            Layout.preferredWidth: 84
                            Layout.preferredHeight: 28
                            radius: (typeof theme !== "undefined" && theme && theme.radiusSm) ? theme.radiusSm : 3
                            color: root.isEnabled
                                   ? (disMa.containsMouse ? ((typeof theme !== "undefined" && theme) ? theme.bgSurfaceHover : "#3a3a3a") : ((typeof theme !== "undefined" && theme) ? theme.bgSurface : "#2d2d2d"))
                                   : (disMa.containsMouse ? ((typeof theme !== "undefined" && theme) ? theme.accentHover : "#106ebe") : ((typeof theme !== "undefined" && theme) ? theme.accent : "#0078d4"))
                            border.color: (typeof theme !== "undefined" && theme) ? theme.borderNormal : "#444444"
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: root.isEnabled ? "Disable" : "Enable"
                                font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                                font.pixelSize: 12
                                font.bold: true
                                color: root.isEnabled ? ((typeof theme !== "undefined" && theme) ? theme.textBright : "#ffffff") : "#ffffff"
                            }

                            MouseArea {
                                id: disMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    var newSt = !root.isEnabled;
                                    if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.toggle_extension) {
                                        extensionManager.toggle_extension(root.extId, newSt);
                                    } else if (typeof backend !== "undefined" && backend && backend.toggle_extension) {
                                        backend.toggle_extension(root.extId, newSt);
                                    }
                                    root.hasOverride = true;
                                    root.enabledOverride = newSt;
                                    if (root.extensionData) {
                                        root.extensionData.enabled = newSt;
                                    }
                                }
                            }
                        }

                        // Uninstall / Remove Button
                        Rectangle {
                            visible: !root.isMarketplaceUninstalled
                            Layout.preferredWidth: 84
                            Layout.preferredHeight: 28
                            radius: (typeof theme !== "undefined" && theme && theme.radiusSm) ? theme.radiusSm : 3
                            color: unMa.containsMouse ? "#451a1a" : ((typeof theme !== "undefined" && theme) ? theme.bgSurface : "#2d2d2d")
                            border.color: unMa.containsMouse ? "#dc2626" : ((typeof theme !== "undefined" && theme) ? theme.borderNormal : "#444444")
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "Uninstall"
                                font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                                font.pixelSize: 12
                                color: unMa.containsMouse ? "#ef4444" : ((typeof theme !== "undefined" && theme) ? theme.textPrimary : "#cccccc")
                            }

                            MouseArea {
                                id: unMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.uninstall_extension) {
                                        extensionManager.uninstall_extension(root.extId);
                                    } else if (typeof backend !== "undefined" && backend && backend.uninstall_extension) {
                                        backend.uninstall_extension(root.extId);
                                    }
                                    root.closeRequested();
                                }
                            }
                        }

                        // Status Badge
                        Rectangle {
                            Layout.preferredHeight: 28
                            Layout.preferredWidth: chipText.implicitWidth + 24
                            radius: (typeof theme !== "undefined" && theme && theme.radiusSm) ? theme.radiusSm : 3
                            color: root.isMarketplaceUninstalled
                                   ? (root.isInstalling ? "#1a2a3a" : "#222222")
                                   : (root.isEnabled ? "#152d1d" : "#302213")
                            border.color: root.isMarketplaceUninstalled
                                         ? (root.isInstalling ? "#38bdf8" : "#444444")
                                         : (root.isEnabled ? "#166534" : "#854d0e")
                            border.width: 1
                            Layout.alignment: Qt.AlignVCenter

                            Text {
                                id: chipText
                                anchors.centerIn: parent
                                text: root.isMarketplaceUninstalled
                                      ? (root.isInstalling ? "Installing…" : "Not Installed")
                                      : (root.isEnabled ? "Enabled" : "Disabled")
                                font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                                font.pixelSize: 11
                                font.bold: true
                                color: root.isMarketplaceUninstalled
                                       ? (root.isInstalling ? "#38bdf8" : "#999999")
                                       : (root.isEnabled ? "#4ade80" : "#fde047")
                            }
                        }
                    }
                }
            }

            // Divider Line
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: (typeof theme !== "undefined" && theme) ? theme.borderSubtle : "#282828"
            }

            // Description Section
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    text: "Overview"
                    font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                    font.pixelSize: 15
                    font.bold: true
                    color: (typeof theme !== "undefined" && theme) ? theme.textBright : "#ffffff"
                }

                Text {
                    text: root.extDescription
                    font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                    font.pixelSize: 13
                    lineHeight: 1.4
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    color: (typeof theme !== "undefined" && theme) ? theme.textPrimary : "#cccccc"
                }
            }

            // Technical Details & Properties Card
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: detailsCol.height + 32
                radius: 6
                color: (typeof theme !== "undefined" && theme) ? theme.bgSurface : "#252526"
                border.color: (typeof theme !== "undefined" && theme) ? theme.borderSubtle : "#333333"
                border.width: 1

                ColumnLayout {
                    id: detailsCol
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 16
                    spacing: 12

                    Text {
                        text: "Extension Details"
                        font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                        font.pixelSize: 13
                        font.bold: true
                        color: (typeof theme !== "undefined" && theme) ? theme.textBright : "#ffffff"
                    }

                    GridLayout {
                        columns: 2
                        columnSpacing: 24
                        rowSpacing: 8
                        Layout.fillWidth: true

                        Text { text: "Identifier"; font.pixelSize: 12; color: (typeof theme !== "undefined" && theme) ? theme.textSecondary : "#858585" }
                        Text { text: root.extId; font.pixelSize: 12; font.bold: true; color: (typeof theme !== "undefined" && theme) ? theme.textBright : "#ffffff" }

                        Text { text: "Version"; font.pixelSize: 12; color: (typeof theme !== "undefined" && theme) ? theme.textSecondary : "#858585" }
                        Text { text: root.extVersion; font.pixelSize: 12; color: (typeof theme !== "undefined" && theme) ? theme.textPrimary : "#cccccc" }

                        Text { text: "Publisher"; font.pixelSize: 12; color: (typeof theme !== "undefined" && theme) ? theme.textSecondary : "#858585" }
                        Text { text: root.extAuthor; font.pixelSize: 12; color: (typeof theme !== "undefined" && theme) ? theme.textPrimary : "#cccccc" }

                        Text { text: "Status"; font.pixelSize: 12; color: (typeof theme !== "undefined" && theme) ? theme.textSecondary : "#858585" }
                        Text {
                            text: root.isMarketplaceUninstalled ? "Not Installed" : (root.isEnabled ? "Active & Installed" : "Disabled")
                            font.pixelSize: 12
                            color: root.isMarketplaceUninstalled ? ((typeof theme !== "undefined" && theme) ? theme.textDisabled : "#858585") : (root.isEnabled ? "#4ade80" : "#eab308")
                        }
                    }
                }
            }
        }
    }
}

