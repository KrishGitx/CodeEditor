import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15

Rectangle {
    id: statusBarRoot
    height: 24
    color: theme.bgHeader

    signal toggleTerminal()
    signal toggleMusic()

    property int cursorLine: 1
    property int cursorCol: 1
    property string activeLanguage: "Python"
    property string currentSongTitle: "No Track Playing"
    property string musicPlaybackState: "stopped"

    Connections {
        target: backend
        function onCurrentLanguageChanged(lang) {
            statusBarRoot.activeLanguage = lang.charAt(0).toUpperCase() + lang.slice(1)
        }
    }

    Connections {
        target: musicPlayer
        function onCurrentSongChanged(title, artist, videoId) {
            statusBarRoot.currentSongTitle = title
        }
        function onPlaybackStateChanged(state) {
            statusBarRoot.musicPlaybackState = state
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        spacing: 10

        // Git Branch Indicator
        Row {
            spacing: 4
            Layout.alignment: Qt.AlignVCenter

            Text {
                text: "⎇"
                color: theme.accentColor
                font.pixelSize: 11
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "main"
                color: theme.textSecondary
                font.pixelSize: 10
                font.family: theme.monoFont
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Terminal Toggle Button
        Rectangle {
            width: termRow.implicitWidth + 12
            height: 18
            radius: 2
            color: termMouse.containsMouse ? theme.bgHover : "transparent"

            Row {
                id: termRow
                anchors.centerIn: parent
                spacing: 4

                Text {
                    text: "⌸"
                    color: theme.accentColor
                    font.pixelSize: 10
                }

                Text {
                    text: "Terminal"
                    color: theme.textSecondary
                    font.pixelSize: 10
                    font.family: theme.uiFont
                }
            }

            MouseArea {
                id: termMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: statusBarRoot.toggleTerminal()
            }
        }

        // Mini Music Widget with reactive equalizer
        Rectangle {
            width: Math.min(220, musicRow.implicitWidth + 16)
            height: 18
            radius: 2
            color: musicMouse.containsMouse ? theme.bgHover : "transparent"

            Row {
                id: musicRow
                anchors.centerIn: parent
                spacing: 6

                // Mini Animated Equalizer bars
                Row {
                    spacing: 2
                    anchors.verticalCenter: parent.verticalCenter
                    visible: statusBarRoot.musicPlaybackState === "playing"

                    Repeater {
                        model: 3
                        Rectangle {
                            width: 2
                            height: 6 + (index * 2)
                            color: theme.accentColor
                            radius: 1
                            SequentialAnimation on height {
                                running: statusBarRoot.musicPlaybackState === "playing" && theme.animationsEnabled
                                loops: Animation.Infinite
                                NumberAnimation { to: 10 - (index * 2); duration: 250 + (index * 80) }
                                NumberAnimation { to: 4 + (index * 2); duration: 250 + (index * 80) }
                            }
                        }
                    }
                }

                Text {
                    visible: statusBarRoot.musicPlaybackState !== "playing"
                    text: "💿"
                    font.pixelSize: 10
                }

                Text {
                    text: statusBarRoot.currentSongTitle
                    color: statusBarRoot.musicPlaybackState === "playing" ? theme.accentColor : theme.textMuted
                    font.pixelSize: 10
                    font.family: theme.uiFont
                    elide: Text.ElideRight
                    width: 140
                }
            }

            MouseArea {
                id: musicMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: statusBarRoot.toggleMusic()
            }
        }

        Item { Layout.fillWidth: true }

        // Cursor Position
        Text {
            text: "Ln " + statusBarRoot.cursorLine + ", Col " + statusBarRoot.cursorCol
            color: theme.textSecondary
            font.pixelSize: 10
            font.family: theme.monoFont
        }

        // Indentation
        Text {
            text: "Spaces: 4"
            color: theme.textSecondary
            font.pixelSize: 10
            font.family: theme.uiFont
        }

        // Encoding
        Text {
            text: "UTF-8"
            color: theme.textSecondary
            font.pixelSize: 10
            font.family: theme.uiFont
        }

        // Active Theme Indicator
        Rectangle {
            height: 16
            width: themeNameText.implicitWidth + 10
            radius: 3
            color: "transparent"

            Text {
                id: themeNameText
                text: theme.currentTheme
                color: theme.textSecondary
                font.pixelSize: 9
                font.family: theme.uiFont
                anchors.centerIn: parent
            }
        }

        // Language Selector Pill
        Rectangle {
            id: langPill
            height: 16
            width: langText.implicitWidth + 12
            radius: 2
            color: langMouse.containsMouse ? theme.bgActive : "transparent"

            Text {
                id: langText
                text: statusBarRoot.activeLanguage
                color: theme.accentColor
                font.pixelSize: 9
                font.bold: true
                font.family: theme.monoFont
                anchors.centerIn: parent
            }

            MouseArea {
                id: langMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: langMenu.open()
            }

            Menu {
                id: langMenu
                y: -contentHeight - 4
                background: Rectangle {
                    implicitWidth: 140
                    color: theme.bgCard
                    border.color: theme.borderSubtle
                    radius: 6
                }

                Repeater {
                    model: ["Python", "JavaScript", "TypeScript", "C++", "C", "Rust", "HTML", "CSS", "JSON", "Markdown", "QML", "Go", "SQL", "Shell"]
                    delegate: Action {
                        text: modelData
                        onTriggered: {
                            statusBarRoot.activeLanguage = modelData
                            backend.set_theme(theme.highlighterThemeName())
                        }
                    }
                }
            }
        }
    }

    // Top subtle divider
    Rectangle {
        color: theme.borderSubtle
        height: 1
        width: parent.width
        anchors.top: parent.top
    }
}
