import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    id: root

    property bool isOpen: false
    property string mode: "files" // "files" or "goto"
    property var filesList: []
    property int selectedIndex: 0

    signal fileSelected(string filePath)
    signal lineSelected(int lineNumber)
    signal closeRequested()

    anchors.fill: parent
    visible: isOpen
    z: 9999

    // Backdrop
    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    function openQuickOpen() {
        mode = "files";
        searchInput.text = "";
        selectedIndex = 0;
        updateFileList("");
        isOpen = true;
        searchInput.forceActiveFocus();
    }

    function openGotoLine(currentLine) {
        mode = "goto";
        searchInput.text = ":" + (currentLine !== undefined ? currentLine : "");
        selectedIndex = 0;
        isOpen = true;
        searchInput.forceActiveFocus();
        searchInput.selectAll();
    }

    function close() {
        isOpen = false;
        root.closeRequested();
    }

    function updateFileList(query) {
        if (typeof backend !== "undefined" && backend && backend.get_workspace_files) {
            filesList = backend.get_workspace_files(query) || [];
        } else {
            filesList = [];
        }
        selectedIndex = 0;
    }

    function handleAccept() {
        var query = searchInput.text.trim();
        if (query.startsWith(":") || mode === "goto") {
            var rawNum = query.startsWith(":") ? query.substring(1) : query;
            var parts = rawNum.split(":");
            var lineNum = parseInt(parts[0], 10);
            if (!isNaN(lineNum) && lineNum > 0) {
                root.lineSelected(lineNum);
                root.close();
            }
        } else {
            if (filesList && filesList.length > 0 && selectedIndex >= 0 && selectedIndex < filesList.length) {
                var selectedItem = filesList[selectedIndex];
                root.fileSelected(selectedItem.path);
                root.close();
            }
        }
    }

    // Modal Card
    Rectangle {
        id: paletteBox
        width: Math.min(parent.width - 48, 520)
        height: Math.min(parent.height - 80, (mode === "goto" || filesList.length === 0) ? 56 : Math.min(340, 56 + filesList.length * 30 + 10))
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 36
        radius: 6
        color: (typeof theme !== "undefined" && theme && theme.bgPopup) ? theme.bgPopup : "#1e1e24"
        border.color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#333338"
        border.width: 1

        // Elevation Glow
        Rectangle {
            anchors.fill: parent
            anchors.margins: -2
            radius: 8
            color: "transparent"
            border.color: "#000000"
            opacity: 0.35
            z: -1
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 6
            spacing: 4

            // Search Box Input
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                radius: 4
                color: (typeof theme !== "undefined" && theme && theme.bgEditor) ? theme.bgEditor : "#141417"
                border.color: searchInput.activeFocus ? ((typeof theme !== "undefined" && theme && theme.accent) ? theme.accent : "#0078d4") : ((typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#2b2b30")
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 6

                    VectorIcon {
                        name: root.mode === "goto" ? "zen" : "search"
                        size: 13
                        color: (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#71717a"
                    }

                    TextInput {
                        id: searchInput
                        Layout.fillWidth: true
                        color: (typeof theme !== "undefined" && theme && theme.textBright) ? theme.textBright : "#ffffff"
                        selectionColor: (typeof theme !== "undefined" && theme && theme.selectionBackground) ? theme.selectionBackground : "#264f78"
                        selectedTextColor: "#ffffff"
                        font.pixelSize: 12
                        font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyUi) ? theme.fontFamilyUi : "sans-serif"
                        clip: true

                        Text {
                            text: root.mode === "goto" ? "Type line number to navigate..." : "Search files by name (type : to go to line)..."
                            color: (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#52525b"
                            font.pixelSize: 11
                            font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyUi) ? theme.fontFamilyUi : "sans-serif"
                            visible: !searchInput.text && !searchInput.inputMethodComposing
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        onTextChanged: {
                            if (text.startsWith(":")) {
                                root.mode = "goto";
                            } else {
                                root.mode = "files";
                                root.updateFileList(text);
                            }
                        }

                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Escape) {
                                root.close();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                root.handleAccept();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Down) {
                                if (root.filesList.length > 0) {
                                    root.selectedIndex = (root.selectedIndex + 1) % root.filesList.length;
                                    fileListView.positionViewAtIndex(root.selectedIndex, ListView.Contain);
                                }
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Up) {
                                if (root.filesList.length > 0) {
                                    root.selectedIndex = (root.selectedIndex - 1 + root.filesList.length) % root.filesList.length;
                                    fileListView.positionViewAtIndex(root.selectedIndex, ListView.Contain);
                                }
                                event.accepted = true;
                            }
                        }
                    }
                }
            }

            // Results List
            ListView {
                id: fileListView
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.mode === "files" && root.filesList.length > 0
                clip: true
                model: root.filesList
                spacing: 1

                delegate: Rectangle {
                    width: fileListView.width
                    height: 28
                    radius: 3
                    color: index === root.selectedIndex ? ((typeof theme !== "undefined" && theme && theme.selectionBackground) ? theme.selectionBackground : "#094771") : (itemMouseArea.containsMouse ? ((typeof theme !== "undefined" && theme && theme.bgSurfaceHover) ? theme.bgSurfaceHover : "#24242a") : "transparent")

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8

                        VectorIcon {
                            name: {
                                var n = modelData.name.toLowerCase();
                                if (n.endsWith(".py")) return "code";
                                if (n.endsWith(".js") || n.endsWith(".ts")) return "code";
                                if (n.endsWith(".html")) return "file";
                                if (n.endsWith(".css")) return "sparkles";
                                if (n.endsWith(".cpp") || n.endsWith(".h")) return "code";
                                if (n.endsWith(".qml")) return "sparkles";
                                if (n.endsWith(".json")) return "settings";
                                return "file";
                            }
                            size: 13
                            color: index === root.selectedIndex ? "#ffffff" : ((typeof theme !== "undefined" && theme && theme.textSecondary) ? theme.textSecondary : "#a1a1aa")
                        }

                        Text {
                            text: modelData.name
                            color: index === root.selectedIndex ? "#ffffff" : ((typeof theme !== "undefined" && theme && theme.textPrimary) ? theme.textPrimary : "#e4e4e7")
                            font.pixelSize: 11
                            font.bold: index === root.selectedIndex
                            font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyUi) ? theme.fontFamilyUi : "sans-serif"
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData.relPath
                            color: index === root.selectedIndex ? "#cbd5e1" : ((typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#71717a")
                            font.pixelSize: 10
                            font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyUi) ? theme.fontFamilyUi : "sans-serif"
                            elide: Text.ElideMiddle
                        }
                    }

                    MouseArea {
                        id: itemMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.selectedIndex = index;
                            root.handleAccept();
                        }
                    }
                }
            }
        }
    }
}
