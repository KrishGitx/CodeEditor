import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property var tabModel: null
    property int activeIndex: 0
    property bool isSplit: false

    signal tabSelected(int index)
    signal tabClosed(int index)
    signal newTabRequested()
    signal splitEditorRequested()
    signal closeOtherTabsRequested(int index)
    signal closeTabsToTheRightRequested(int index)
    signal closeAllTabsRequested()
    signal closeSavedTabsRequested()
    signal copyTabPathRequested(int index)
    signal revealTabInExplorerRequested(int index)

    height: 30
    color: theme ? theme.bgHeader : "#181818"

    // Single bottom border line
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: theme ? theme.borderSubtle : "#282828"
    }

    ScrollView {
        id: tabScrollView
        anchors.left: parent.left
        anchors.right: actionsRow.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        ScrollBar.horizontal.policy: ScrollBar.AsNeeded
        ScrollBar.vertical.policy: ScrollBar.AlwaysOff
        clip: true

        Row {
            id: tabsRow
            height: parent.height
            spacing: 1

            Repeater {
                model: root.tabModel

                delegate: Rectangle {
                    id: tabItem
                    height: root.height - 1
                    width: Math.min(190, Math.max(90, tabTitleText.contentWidth + 46))
                    color: index === root.activeIndex ? (theme ? theme.bgEditor : "#1e1e1e") : (tabMa.containsMouse ? (theme ? theme.bgSurface : "#252526") : (theme ? theme.bgHeader : "#181818"))

                    readonly property bool isDirty: model.isDirty === true
                    readonly property bool isHovered: tabMa.containsMouse || closeTabMa.containsMouse

                    // Right tab divider line
                    Rectangle {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: 1
                        color: theme ? theme.borderSubtle : "#282828"
                    }

                    // Top active line
                    Rectangle {
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 2
                        color: theme ? theme.accent : "#0078d4"
                        visible: index === root.activeIndex
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 6
                        spacing: 6

                        // File Icon
                        VectorIcon {
                            name: (model.isWhiteboard || model.languageId === "whiteboard") ? "board" : ((model.isWebPreview || model.languageId === "webpreview") ? "sparkles" : "file")
                            size: 11
                            color: index === root.activeIndex ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565")
                        }

                        // Tab Title
                        Text {
                            id: tabTitleText
                            text: model.title || "Untitled"
                            color: index === root.activeIndex ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                            font.pixelSize: 12
                            font.family: theme ? theme.fontFamilyUi : "Segoe UI, sans-serif"
                            font.italic: tabItem.isDirty
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        // Close Button / Unsaved Dirty Dot Indicator (VS Code Style)
                        Rectangle {
                            width: 16
                            height: 16
                            radius: 2
                            color: closeTabMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                            // 1. Unsaved dirty circle indicator (shown when modified and not hovered)
                            Rectangle {
                                anchors.centerIn: parent
                                width: 7
                                height: 7
                                radius: 3.5
                                color: theme ? theme.textBright : "#ffffff"
                                opacity: 0.85
                                visible: tabItem.isDirty && !tabItem.isHovered
                            }

                            // 2. Close 'x' icon (shown when hovered or when file is clean)
                            VectorIcon {
                                anchors.centerIn: parent
                                name: "close"
                                size: 8
                                color: closeTabMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                                visible: !tabItem.isDirty || tabItem.isHovered
                            }

                            MouseArea {
                                id: closeTabMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.tabClosed(index);
                                }
                            }
                        }
                    }

                    MouseArea {
                        id: tabMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                        z: -1

                        onClicked: function(mouse) {
                            if (mouse.button === Qt.LeftButton) {
                                root.tabSelected(index);
                            } else if (mouse.button === Qt.MiddleButton) {
                                root.tabClosed(index);
                            } else if (mouse.button === Qt.RightButton) {
                                tabContextMenu.openAt(mouse.x, mouse.y, index, model.path || "", model.title || "", model.isDirty === true);
                            }
                        }
                    }
                }
            }
        }
    }

    // Action Buttons Row (New Tab + Split Editor)
    Row {
        id: actionsRow
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.rightMargin: 4
        spacing: 2

        // Split Editor Button
        Rectangle {
            id: splitBtn
            width: 24
            height: 24
            radius: 2
            color: root.isSplit ? (theme ? theme.bgSurfaceActive : "#37373d") : (splitMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent")

            VectorIcon {
                anchors.centerIn: parent
                name: "split-horizontal"
                size: 12
                color: root.isSplit ? (theme ? theme.accent : "#0078d4") : (splitMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textSecondary : "#858585"))
            }

            MouseArea {
                id: splitMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.splitEditorRequested()
            }
        }

        // New Tab Button (+)
        Rectangle {
            id: newTabBtn
            width: 24
            height: 24
            radius: 2
            color: newTabMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

            VectorIcon {
                anchors.centerIn: parent
                name: "new-file"
                size: 11
                color: newTabMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textSecondary : "#858585")
            }

            MouseArea {
                id: newTabMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.newTabRequested()
            }
        }
    }

    // =========================================================================
    // TAB RIGHT-CLICK CONTEXT MENU (VS Code Native Style)
    // =========================================================================
    Popup {
        id: tabContextMenu
        width: 180
        padding: 4
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        property int targetIndex: -1
        property string targetPath: ""
        property string targetTitle: ""
        property bool targetIsDirty: false

        background: Rectangle {
            color: (typeof theme !== "undefined" && theme && theme.bgSurface) ? theme.bgSurface : "#252526"
            border.color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#454545"
            border.width: 1
            radius: 4
        }

        function openAt(mouseX, mouseY, idx, path, title, isDirty) {
            targetIndex = idx;
            targetPath = path || "";
            targetTitle = title || "";
            targetIsDirty = isDirty || false;

            var globalPos = mapToItem(root, mouseX, mouseY);
            tabContextMenu.x = Math.max(4, Math.min(root.width - tabContextMenu.width - 6, mouseX + 10));
            tabContextMenu.y = Math.max(4, Math.min(root.height + 250, mouseY + 24));
            tabContextMenu.open();
        }

        contentItem: ColumnLayout {
            spacing: 2

            // 1. Close
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: closeMnuMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Close"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                    Text {
                        text: "Ctrl+W"
                        color: theme ? theme.textMuted : "#656565"
                        font.pixelSize: 11
                    }
                }
                MouseArea {
                    id: closeMnuMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        tabContextMenu.close();
                        root.tabClosed(tabContextMenu.targetIndex);
                    }
                }
            }

            // 2. Close Others
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                enabled: root.tabModel && root.tabModel.count > 1
                opacity: enabled ? 1.0 : 0.5
                color: closeOthMa.containsMouse && enabled ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Close Others"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: closeOthMa
                    anchors.fill: parent
                    hoverEnabled: parent.enabled
                    cursorShape: parent.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: {
                        tabContextMenu.close();
                        root.closeOtherTabsRequested(tabContextMenu.targetIndex);
                    }
                }
            }

            // 3. Close Tabs to the Right
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                enabled: root.tabModel && tabContextMenu.targetIndex < root.tabModel.count - 1
                opacity: enabled ? 1.0 : 0.5
                color: closeRightMa.containsMouse && enabled ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Close Tabs to the Right"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: closeRightMa
                    anchors.fill: parent
                    hoverEnabled: parent.enabled
                    cursorShape: parent.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: {
                        tabContextMenu.close();
                        root.closeTabsToTheRightRequested(tabContextMenu.targetIndex);
                    }
                }
            }

            // 4. Close Saved
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: closeSavedMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Close Saved"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: closeSavedMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        tabContextMenu.close();
                        root.closeSavedTabsRequested();
                    }
                }
            }

            // 5. Close All
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: closeAllMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Close All"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: closeAllMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        tabContextMenu.close();
                        root.closeAllTabsRequested();
                    }
                }
            }

            // Separator
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: theme ? theme.borderNormal : "#3c3c3c"
                Layout.topMargin: 2
                Layout.bottomMargin: 2
                visible: tabContextMenu.targetPath !== ""
            }

            // 6. Copy Path
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                visible: tabContextMenu.targetPath !== ""
                color: cpPathMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Copy Path"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: cpPathMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        tabContextMenu.close();
                        root.copyTabPathRequested(tabContextMenu.targetIndex);
                    }
                }
            }

            // 7. Reveal in File Explorer
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                visible: tabContextMenu.targetPath !== ""
                color: revTabMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Reveal in File Explorer"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: revTabMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        tabContextMenu.close();
                        root.revealTabInExplorerRequested(tabContextMenu.targetIndex);
                    }
                }
            }
        }
    }
}
