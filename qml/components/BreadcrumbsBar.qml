import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property string filePath: ""
    property string activeSymbol: ""
    property var symbolsList: []

    signal navigateToLine(int line)

    visible: (typeof theme !== "undefined" && theme && theme.enableBreadcrumbs !== undefined) ? theme.enableBreadcrumbs : true
    height: visible ? 20 : 0
    color: "transparent"
    border.width: 0
    clip: true

    function updateSymbols(sourceCode) {
        if (typeof backend !== "undefined" && backend && backend.get_document_symbols) {
            symbolsList = backend.get_document_symbols(filePath, sourceCode) || [];
        } else {
            symbolsList = [];
        }
    }

    function updateActiveSymbolForLine(line) {
        if (!symbolsList || symbolsList.length === 0) {
            activeSymbol = "";
            return;
        }
        var found = "";
        for (var i = 0; i < symbolsList.length; i++) {
            var sym = symbolsList[i];
            if (sym.line <= line) {
                found = (sym.container ? sym.container + " › " : "") + sym.name;
            }
        }
        activeSymbol = found;
    }

    // Segments calculation
    readonly property var pathSegments: {
        if (!filePath) return [];
        var clean = filePath.replace(/\\/g, "/");
        var parts = clean.split("/").filter(function(p) { return p.length > 0; });
        return parts.slice(Math.max(0, parts.length - 3));
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 8
        spacing: 4

        Repeater {
            model: root.pathSegments

            RowLayout {
                spacing: 4

                Text {
                    text: modelData
                    color: index === (root.pathSegments.length - 1) ? ((typeof theme !== "undefined" && theme && theme.textSecondary) ? theme.textSecondary : "#a1a1aa") : ((typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#71717a")
                    font.pixelSize: 10
                    font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyUi) ? theme.fontFamilyUi : "sans-serif"
                }

                Text {
                    text: "›"
                    color: (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#52525b"
                    font.pixelSize: 9
                }
            }
        }

        // Active Symbol in Current Scope
        Rectangle {
            visible: root.activeSymbol.length > 0 || (root.symbolsList && root.symbolsList.length > 0)
            height: 16
            radius: 3
            color: symbolMouseArea.containsMouse ? ((typeof theme !== "undefined" && theme && theme.bgSurfaceHover) ? theme.bgSurfaceHover : "#27272a") : "transparent"
            Layout.preferredWidth: symbolRow.width + 8

            RowLayout {
                id: symbolRow
                anchors.centerIn: parent
                spacing: 3

                Text {
                    text: root.activeSymbol || (root.symbolsList.length > 0 ? "outline" : "")
                    color: symbolMouseArea.containsMouse ? ((typeof theme !== "undefined" && theme && theme.textBright) ? theme.textBright : "#e4e4e7") : ((typeof theme !== "undefined" && theme && theme.textSecondary) ? theme.textSecondary : "#a1a1aa")
                    font.pixelSize: 10
                    font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyUi) ? theme.fontFamilyUi : "sans-serif"
                }

                Text {
                    text: "▾"
                    color: (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#52525b"
                    font.pixelSize: 8
                }
            }

            MouseArea {
                id: symbolMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: symbolPopup.open()
            }

            Popup {
                id: symbolPopup
                y: parent.height + 2
                width: 220
                height: Math.min(200, Math.max(36, root.symbolsList.length * 24 + 10))
                padding: 4
                background: Rectangle {
                    color: (typeof theme !== "undefined" && theme && theme.bgPopup) ? theme.bgPopup : "#18181b"
                    border.color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#27272a"
                    border.width: 1
                    radius: 4
                }

                ListView {
                    anchors.fill: parent
                    clip: true
                    model: root.symbolsList

                    delegate: Rectangle {
                        width: parent.width
                        height: 22
                        radius: 2
                        color: symDelegateMa.containsMouse ? ((typeof theme !== "undefined" && theme && theme.bgSurfaceHover) ? theme.bgSurfaceHover : "#27272a") : "transparent"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 6
                            anchors.rightMargin: 6
                            spacing: 6

                            VectorIcon {
                                name: modelData.kind === "class" ? "folder" : "code"
                                size: 10
                                color: (typeof theme !== "undefined" && theme && theme.textSecondary) ? theme.textSecondary : "#a1a1aa"
                            }

                            Text {
                                text: (modelData.container ? modelData.container + "." : "") + modelData.name
                                color: (typeof theme !== "undefined" && theme && theme.textPrimary) ? theme.textPrimary : "#e4e4e7"
                                font.pixelSize: 10
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Text {
                                text: ":" + modelData.line
                                color: (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#71717a"
                                font.pixelSize: 9
                            }
                        }

                        MouseArea {
                            id: symDelegateMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.navigateToLine(modelData.line);
                                symbolPopup.close();
                            }
                        }
                    }
                }
            }
        }

        Item { Layout.fillWidth: true }
    }
}
