import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtWebEngine 1.15
import "."

Rectangle {
    id: root

    property string htmlContent: ""
    property string sourcePath: ""
    property string activeUrl: "http://localhost:3000"
    property string previewMode: "desktop" // "desktop", "mobile"
    property bool isMarkdown: false

    signal closeRequested()

    color: theme ? theme.bgEditor : "#1e1e1e"
    clip: true

    onHtmlContentChanged: updatePreview()
    onSourcePathChanged: updatePreview()
    onIsMarkdownChanged: updatePreview()

    function setContent(content, isMd, path) {
        root.htmlContent = content || "";
        root.isMarkdown = !!isMd;
        if (path !== undefined) root.sourcePath = path;
        updatePreview();
    }

    function getBaseUrl() {
        if (root.sourcePath && root.sourcePath.indexOf("://") === -1) {
            var folder = root.sourcePath.replace(/\\/g, "/");
            var lastSlash = folder.lastIndexOf("/");
            if (lastSlash !== -1) {
                folder = folder.substring(0, lastSlash + 1);
            }
            return "file:///" + folder;
        }
        return "http://localhost/";
    }

    function getRenderHtml() {
        if (!root.htmlContent || root.htmlContent.trim().length === 0) {
            return "<!DOCTYPE html><html><head><meta charset='utf-8'><style>" +
                   "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #121212; color: #888; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }" +
                   "h2 { color: #fff; margin-bottom: 8px; font-size: 20px; font-weight: 600; }" +
                   "p { max-width: 420px; font-size: 13px; line-height: 1.6; color: #999; }" +
                   ".badge { background: #0078d420; color: #0078d4; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; border: 1px solid #0078d440; margin-bottom: 12px; }" +
                   "</style></head><body>" +
                   "<div class='badge'>Chromium Engine Active</div>" +
                   "<h2>Live Web & HTML Sandbox</h2>" +
                   "<p>Edit HTML, CSS, JavaScript, or Markdown to see instant pixel-perfect hot-reloading.</p>" +
                   "</body></html>";
        }
        if (root.isMarkdown) {
            var md = root.htmlContent;
            var formatted = md
                .replace(/^### (.*$)/gim, '<h3 style="color:#0078d4; margin-top:20px;">$1</h3>')
                .replace(/^## (.*$)/gim, '<h2 style="color:#0078d4; border-bottom:1px solid #e2e8f0; padding-bottom:6px; margin-top:24px;">$1</h2>')
                .replace(/^# (.*$)/gim, '<h1 style="color:#0f172a; border-bottom:2px solid #0078d4; padding-bottom:10px; margin-top:14px;">$1</h1>')
                .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
                .replace(/\*(.*)\*/gim, '<em>$1</em>')
                .replace(/`([^`]+)`/gim, '<code style="background:#f1f5f9; color:#e11d48; padding:2px 6px; border-radius:4px; font-family:monospace;">$1</code>')
                .replace(/\n/gim, '<br>');
            return "<!DOCTYPE html><html><head><meta charset='utf-8'><style>" +
                   "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #ffffff; color: #1e293b; padding: 24px; margin: 0; line-height: 1.6; font-size: 14px; }" +
                   "pre { background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; overflow-x: auto; }" +
                   "</style></head><body>" + formatted + "</body></html>";
        }
        return root.htmlContent;
    }

    function updatePreview() {
        if (typeof webEngineView !== "undefined" && webEngineView) {
            webEngineView.loadHtml(getRenderHtml(), getBaseUrl());
        }
    }

    function openInBrowser() {
        if (root.sourcePath && root.sourcePath.indexOf("://") === -1) {
            var cleanPath = root.sourcePath.replace(/\\/g, "/");
            Qt.openUrlExternally("file:///" + cleanPath);
        } else {
            Qt.openUrlExternally("http://localhost:3000");
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Navigation / Preview Toolbar Bar
        Rectangle {
            Layout.fillWidth: true
            height: 38
            color: theme ? theme.bgHeader : "#181818"
            border.color: theme ? theme.borderSubtle : "#282828"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 8

                VectorIcon {
                    name: "sparkles"
                    size: 13
                    color: theme ? theme.accent : "#0078d4"
                }

                Text {
                    text: root.isMarkdown ? "Live Markdown Preview" : "Live Web & HTML Preview (Chromium)"
                    color: theme ? theme.textBright : "#ffffff"
                    font.pixelSize: 11
                    font.bold: true
                }

                // URL / Status Bar
                Rectangle {
                    Layout.fillWidth: true
                    height: 24
                    radius: 3
                    color: theme ? theme.bgInput : "#252526"
                    border.color: theme ? theme.borderSubtle : "#333333"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8

                        Text {
                            text: root.isMarkdown ? "markdown://rendered-document" : (root.sourcePath ? ("file:///" + root.sourcePath.replace(/\\/g, "/")) : "live-sandbox://index.html")
                            color: theme ? theme.textSecondary : "#858585"
                            font.pixelSize: 10
                            font.family: theme ? theme.fontFamilyMono : "monospace"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }

                        Rectangle {
                            width: 6; height: 6; radius: 3
                            color: "#22c55e"
                        }
                    }
                }

                // Viewport device buttons & Open in Browser
                Row {
                    spacing: 4

                    // Open in Browser Button
                    Rectangle {
                        width: 24; height: 24; radius: 3
                        color: obMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                        VectorIcon { anchors.centerIn: parent; name: "code"; size: 11; color: theme ? theme.accent : "#0078d4" }
                        ToolTip.visible: obMa.containsMouse
                        ToolTip.text: "Open in Default Web Browser"
                        MouseArea {
                            id: obMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.openInBrowser()
                        }
                    }

                    Rectangle { width: 1; height: 16; anchors.verticalCenter: parent.verticalCenter; color: theme ? theme.borderSubtle : "#333333" }

                    // Desktop View
                    Rectangle {
                        width: 24; height: 24; radius: 3
                        color: root.previewMode === "desktop" ? (theme ? theme.bgSurfaceActive : "#37373d") : "transparent"
                        VectorIcon { anchors.centerIn: parent; name: "sparkles"; size: 11; color: root.previewMode === "desktop" ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565") }
                        ToolTip.visible: dtMa.containsMouse
                        ToolTip.text: "Desktop 100%"
                        MouseArea { id: dtMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.previewMode = "desktop" }
                    }

                    // Mobile View
                    Rectangle {
                        width: 24; height: 24; radius: 3
                        color: root.previewMode === "mobile" ? (theme ? theme.bgSurfaceActive : "#37373d") : "transparent"
                        VectorIcon { anchors.centerIn: parent; name: "settings"; size: 10; color: root.previewMode === "mobile" ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565") }
                        ToolTip.visible: mbMa.containsMouse
                        ToolTip.text: "Mobile View (375px)"
                        MouseArea { id: mbMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.previewMode = "mobile" }
                    }
                }

                Rectangle { width: 1; height: 16; color: theme ? theme.borderSubtle : "#333333" }

                // Close Preview Tab
                Rectangle {
                    width: 24; height: 24; radius: 3
                    color: closeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                    VectorIcon { anchors.centerIn: parent; name: "close"; size: 9; color: theme ? theme.textSecondary : "#858585" }
                    MouseArea { id: closeMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.closeRequested() }
                }
            }
        }

        // 2. High-Fidelity Chromium WebEngine Viewport
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Rectangle {
                anchors.fill: parent
                color: theme ? theme.bgRoot : "#121212"
            }

            Rectangle {
                id: viewportCard
                anchors.centerIn: parent
                width: root.previewMode === "mobile" ? 375 : parent.width
                height: root.previewMode === "mobile" ? Math.min(parent.height - 20, 667) : parent.height
                radius: root.previewMode === "mobile" ? 8 : 0
                color: "#ffffff"
                clip: true
                border.color: root.previewMode === "mobile" ? "#333333" : "transparent"
                border.width: root.previewMode === "mobile" ? 2 : 0

                WebEngineView {
                    id: webEngineView
                    anchors.fill: parent
                    Component.onCompleted: root.updatePreview()
                }
            }
        }
    }
}
