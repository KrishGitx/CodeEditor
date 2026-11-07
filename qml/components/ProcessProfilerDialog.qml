import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var stats: (typeof lspManager !== "undefined" && lspManager) ? lspManager.get_profiler_stats() : {
        "idePid": 0, "ideRamMb": 0, "lspRamMb": 0, "totalRamMb": 0,
        "activeLanguage": "csharp", "activeServerName": "Unity & C#", "activeServerRam": 0,
        "servers": []
    }
    property string freedNotification: ""

    anchors.fill: parent
    color: "#80000000"
    visible: false
    z: 9999

    // Click outside to dismiss
    MouseArea {
        anchors.fill: parent
        onClicked: root.visible = false
    }

    // Auto-refresh timer while dialog is visible
    Timer {
        interval: 1000
        running: root.visible
        repeat: true
        onTriggered: {
            if (typeof lspManager !== "undefined" && lspManager) {
                root.stats = lspManager.get_profiler_stats();
            }
        }
    }

    Connections {
        target: (typeof lspManager !== "undefined") ? lspManager : null
        function onProfilerStatsUpdated(newStats) {
            if (root.visible) {
                root.stats = newStats;
            }
        }
    }

    // Main Dialog Box
    Rectangle {
        id: dialogBox
        width: Math.min(620, parent.width - 40)
        height: Math.min(460, parent.height - 40)
        anchors.centerIn: parent
        color: (typeof theme !== "undefined" && theme) ? theme.bgSurface : "#18181b"
        border.color: (typeof theme !== "undefined" && theme) ? theme.borderSubtle : "#27272a"
        border.width: 1
        radius: 10
        clip: true

        MouseArea {
            anchors.fill: parent
            onClicked: {} // Prevent dismiss click inside
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 16

            // =================================================================
            // 1. HEADER
            // =================================================================
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Rectangle {
                    width: 32
                    height: 32
                    radius: 8
                    color: Qt.rgba(0.2, 0.7, 1.0, 0.15)
                    border.color: Qt.rgba(0.2, 0.7, 1.0, 0.3)
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "⚡"
                        font.pixelSize: 16
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Text {
                        text: "Raw RAM Resource Monitor"
                        color: (typeof theme !== "undefined" && theme) ? theme.textBright : "#ffffff"
                        font.pixelSize: 15
                        font.bold: true
                    }
                    Text {
                        text: "Live process Working Set memory footprint in Megabytes"
                        color: (typeof theme !== "undefined" && theme) ? theme.textMuted : "#a1a1aa"
                        font.pixelSize: 11
                    }
                }

                Item { Layout.fillWidth: true }

                // Close Button
                Rectangle {
                    width: 28
                    height: 28
                    radius: 6
                    color: closeMa.containsMouse ? "#ef4444" : "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: closeMa.containsMouse ? "#ffffff" : "#a1a1aa"
                        font.pixelSize: 13
                    }
                    MouseArea {
                        id: closeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.visible = false
                    }
                }
            }

            // =================================================================
            // 2. RAW RAM SUMMARY TILES
            // =================================================================
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                // Total Memory
                Rectangle {
                    Layout.fillWidth: true
                    height: 70
                    radius: 8
                    color: Qt.rgba(0.12, 0.12, 0.15, 0.7)
                    border.color: Qt.rgba(0.25, 0.25, 0.3, 0.5)

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 2
                        Text {
                            text: "TOTAL RAM USAGE"
                            color: "#71717a"
                            font.pixelSize: 9
                            font.bold: true
                        }
                        Text {
                            text: (root.stats.totalRamMb || 0).toFixed(1) + " MB"
                            color: "#38bdf8"
                            font.pixelSize: 20
                            font.bold: true
                        }
                        Text {
                            text: "Combined IDE + LSP"
                            color: "#a1a1aa"
                            font.pixelSize: 10
                        }
                    }
                }

                // Main IDE RAM
                Rectangle {
                    Layout.fillWidth: true
                    height: 70
                    radius: 8
                    color: Qt.rgba(0.12, 0.12, 0.15, 0.7)
                    border.color: Qt.rgba(0.25, 0.25, 0.3, 0.5)

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 2
                        Text {
                            text: "POD STUDIO GUI (PID " + (root.stats.idePid || "-") + ")"
                            color: "#71717a"
                            font.pixelSize: 9
                            font.bold: true
                        }
                        RowLayout {
                            spacing: 8
                            Text {
                                text: (root.stats.ideRamMb || 0).toFixed(1) + " MB"
                                color: "#f8fafc"
                                font.pixelSize: 20
                                font.bold: true
                            }
                            Item { Layout.fillWidth: true }
                            Rectangle {
                                width: gcText.contentWidth + 10
                                height: 20
                                radius: 4
                                color: gcMa.containsMouse ? "#3b82f6" : Qt.rgba(0.2, 0.5, 0.9, 0.2)
                                border.color: "#3b82f6"
                                Text {
                                    id: gcText
                                    anchors.centerIn: parent
                                    text: "Free RAM"
                                    color: "#ffffff"
                                    font.pixelSize: 10
                                    font.bold: true
                                }
                                MouseArea {
                                    id: gcMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (typeof lspManager !== "undefined" && lspManager) {
                                            var freed = lspManager.force_gc_collect();
                                            root.freedNotification = "Freed " + freed + " MB!";
                                            clearNotifyTimer.restart();
                                        }
                                    }
                                }
                            }
                        }
                        Text {
                            text: root.freedNotification ? root.freedNotification : "Main application process"
                            color: root.freedNotification ? "#10b981" : "#a1a1aa"
                            font.pixelSize: 10
                        }
                    }
                }

                // LSP Daemons RAM
                Rectangle {
                    Layout.fillWidth: true
                    height: 70
                    radius: 8
                    color: Qt.rgba(0.12, 0.12, 0.15, 0.7)
                    border.color: Qt.rgba(0.25, 0.25, 0.3, 0.5)

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 2
                        Text {
                            text: "LSP SERVICES RAM"
                            color: "#71717a"
                            font.pixelSize: 9
                            font.bold: true
                        }
                        Text {
                            text: (root.stats.lspRamMb || 0).toFixed(1) + " MB"
                            color: "#a855f7"
                            font.pixelSize: 20
                            font.bold: true
                        }
                        Text {
                            text: "Background language servers"
                            color: "#a1a1aa"
                            font.pixelSize: 10
                        }
                    }
                }
            }

            Timer {
                id: clearNotifyTimer
                interval: 3000
                onTriggered: root.freedNotification = ""
            }

            // =================================================================
            // 3. RAW PROCESS BREAKDOWN LIST
            // =================================================================
            Text {
                text: "RUNNING PROCESSES & RAW MEMORY BREAKDOWN"
                color: "#71717a"
                font.pixelSize: 11
                font.bold: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 8
                color: Qt.rgba(0.09, 0.09, 0.11, 0.7)
                border.color: Qt.rgba(0.25, 0.25, 0.3, 0.4)
                clip: true

                ListView {
                    id: processListView
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6

                    // Filter only running processes with memory
                    model: {
                        var list = [];
                        // 1. Pod Studio IDE GUI process
                        list.push({
                            "name": "Pod Studio IDE GUI",
                            "pid": root.stats.idePid || 0,
                            "type": "Main Application Engine",
                            "memoryMb": root.stats.ideRamMb || 0,
                            "isMain": true
                        });
                        // 2. Any running LSP server
                        var srvs = root.stats.servers || [];
                        for (var i = 0; i < srvs.length; i++) {
                            var s = srvs[i];
                            if (s.status === "RUNNING" || s.memoryMb > 0) {
                                list.push({
                                    "name": s.name || s.id,
                                    "pid": s.pid || 0,
                                    "type": "LSP Subprocess (" + (s.language || "") + ")",
                                    "memoryMb": s.memoryMb || 0,
                                    "isMain": false
                                });
                            }
                        }
                        return list;
                    }

                    delegate: Rectangle {
                        width: processListView.width
                        height: 52
                        radius: 6
                        color: Qt.rgba(0.14, 0.14, 0.18, 0.5)
                        border.color: Qt.rgba(0.25, 0.25, 0.3, 0.3)

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 12

                            // Process Icon / Bullet
                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: modelData.isMain ? "#38bdf8" : "#a855f7"
                            }

                            // Process Name & Type
                            ColumnLayout {
                                Layout.preferredWidth: 260
                                spacing: 2
                                Text {
                                    text: modelData.name
                                    color: "#f8fafc"
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                                Text {
                                    text: modelData.type + (modelData.pid ? " | PID " + modelData.pid : "")
                                    color: "#a1a1aa"
                                    font.pixelSize: 10
                                }
                            }

                            Item { Layout.fillWidth: true }

                            // Memory Meter Bar & Number
                            ColumnLayout {
                                Layout.preferredWidth: 200
                                spacing: 4
                                RowLayout {
                                    Text {
                                        text: "RAM Allocation"
                                        color: "#71717a"
                                        font.pixelSize: 10
                                    }
                                    Item { Layout.fillWidth: true }
                                    Text {
                                        text: (modelData.memoryMb || 0).toFixed(1) + " MB"
                                        color: modelData.isMain ? "#38bdf8" : "#a855f7"
                                        font.pixelSize: 12
                                        font.bold: true
                                    }
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 5
                                    radius: 2.5
                                    color: "#27272a"
                                    Rectangle {
                                        height: parent.height
                                        radius: 2.5
                                        width: Math.max(4, Math.min(parent.width, ((modelData.memoryMb || 0) / Math.max(1, (root.stats.totalRamMb || 100))) * parent.width))
                                        color: modelData.isMain ? "#38bdf8" : "#a855f7"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
