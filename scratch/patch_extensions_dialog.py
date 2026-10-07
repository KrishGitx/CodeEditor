with open('qml/components/ExtensionsDialog.qml', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add ToolTip to Reload & Close buttons
old_reload_btn = '''                // Reload Button
                Rectangle {
                    width: 28
                    height: 26
                    radius: 4
                    color: reloadMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d30") : "transparent"
                    border.color: reloadMa.containsMouse ? (theme ? theme.borderSubtle : "#3e3e42") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "refresh"
                        size: 13
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    MouseArea {
                        id: reloadMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof extensionManager !== "undefined" && extensionManager) {
                                extensionManager.reload_extensions();
                            } else if (typeof backend !== "undefined" && backend && backend.reload_extensions) {
                                backend.reload_extensions();
                            }
                            root.refreshExtensions();
                        }
                    }
                }

                // Close Button
                Rectangle {
                    width: 28
                    height: 26
                    radius: 4
                    color: closeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d30") : "transparent"
                    border.color: closeMa.containsMouse ? (theme ? theme.borderSubtle : "#3e3e42") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "close"
                        size: 11
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    MouseArea {
                        id: closeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.closeRequested()
                    }
                }'''

new_reload_btn = '''                // Reload Button
                Rectangle {
                    width: 28
                    height: 26
                    radius: 4
                    color: reloadMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d30") : "transparent"
                    border.color: reloadMa.containsMouse ? (theme ? theme.borderSubtle : "#3e3e42") : "transparent"
                    ToolTip.visible: reloadMa.containsMouse
                    ToolTip.text: "Refresh Extensions"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "refresh"
                        size: 13
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    MouseArea {
                        id: reloadMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof extensionManager !== "undefined" && extensionManager) {
                                extensionManager.reload_extensions();
                            } else if (typeof backend !== "undefined" && backend && backend.reload_extensions) {
                                backend.reload_extensions();
                            }
                            root.refreshExtensions();
                        }
                    }
                }

                // Close Button
                Rectangle {
                    width: 28
                    height: 26
                    radius: 4
                    color: closeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d30") : "transparent"
                    border.color: closeMa.containsMouse ? (theme ? theme.borderSubtle : "#3e3e42") : "transparent"
                    ToolTip.visible: closeMa.containsMouse
                    ToolTip.text: "Close"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "close"
                        size: 11
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    MouseArea {
                        id: closeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.closeRequested()
                    }
                }'''

if old_reload_btn in content:
    content = content.replace(old_reload_btn, new_reload_btn, 1)
    print("Added ToolTips to ExtensionsDialog header buttons")
else:
    print("old_reload_btn not found")

# 2. Add subtle border around Extensions main body area
old_body = '''        // 2. Main Body Split Area
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true'''

new_body = '''        // 2. Main Body Split Area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"
            border.color: theme ? theme.borderSubtle : "#282828"
            border.width: 1'''

if old_body in content:
    content = content.replace(old_body, new_body, 1)
    print("Added subtle border to Extensions body area")
else:
    print("old_body not found")

with open('qml/components/ExtensionsDialog.qml', 'w', encoding='utf-8') as f:
    f.write(content)
print("ExtensionsDialog.qml patched")
