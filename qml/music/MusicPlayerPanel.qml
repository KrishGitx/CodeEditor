import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15

Rectangle {
    id: musicPanelRoot
    color: theme.bgPanelRight

    signal closeRequested()
    property string currentSongTitle: "No Track Playing"
    property string currentArtist: "Search & Select a Song"
    property string currentVideoId: ""
    property string playbackState: "stopped" // "playing", "paused", "stopped"
    property real currentVolume: 0.8
    property bool compact: height < 360

    Connections {
        target: musicPlayer

        function onSearchResults(list) {
            songResultsModel.clear()
            for (var i = 0; i < list.length; i++) {
                songResultsModel.append(list[i])
            }
        }

        function onCurrentSongChanged(title, artist, videoId) {
            musicPanelRoot.currentSongTitle = title
            musicPanelRoot.currentArtist = artist
            musicPanelRoot.currentVideoId = videoId
        }

        function onPlaybackStateChanged(state) {
            musicPanelRoot.playbackState = state
        }

        function onVolumeChanged(val) {
            musicPanelRoot.currentVolume = val
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Music Header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            color: theme.bgHeader

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8

                Text {
                    text: "MUSIC PLAYER"
                    color: theme.textSecondary
                    font.bold: true
                    font.pixelSize: 11
                    font.family: theme.uiFont
                    font.letterSpacing: 1.0
                    Layout.fillWidth: true
                }

                Rectangle {
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    radius: 3
                    color: closeMusicMouse.containsMouse ? theme.bgHover : "transparent"

                    Text {
                        text: "×"
                        color: closeMusicMouse.containsMouse ? theme.textPrimary : theme.textMuted
                        font.pixelSize: 18
                        anchors.centerIn: parent
                    }

                    MouseArea {
                        id: closeMusicMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: musicPanelRoot.closeRequested()
                    }
                }

                // Vinyl icon
                Text {
                    text: "💿"
                    font.pixelSize: 12
                }
            }

            Rectangle {
                color: theme.borderSubtle
                height: 1
                width: parent.width
                anchors.bottom: parent.bottom
            }
        }

        // 2. Search Music Field
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            color: theme.bgPanelRight

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6

                TextField {
                    id: musicSearchInput
                    Layout.fillWidth: true
                    placeholderText: "Search YouTube songs..."
                    placeholderTextColor: theme.textMuted
                    color: theme.textPrimary
                    font.pixelSize: 11
                    font.family: theme.uiFont
                    selectByMouse: true

                    background: Rectangle {
                        color: theme.bgInput
                        border.color: musicSearchInput.activeFocus ? theme.accentColor : theme.borderSubtle
                        radius: 6
                    }

                    onAccepted: {
                        if (text.trim().length > 0) {
                            musicPlayer.search_music(text.trim())
                        }
                    }
                }

                // Search button
                Rectangle {
                    Layout.preferredWidth: 28
                    Layout.preferredHeight: 28
                    radius: 6
                    color: searchBtnMouse.containsMouse ? theme.accentColor : theme.bgHover

                    Text {
                        text: "🔍"
                        font.pixelSize: 11
                        anchors.centerIn: parent
                    }

                    MouseArea {
                        id: searchBtnMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (musicSearchInput.text.trim().length > 0) {
                                musicPlayer.search_music(musicSearchInput.text.trim())
                            }
                        }
                    }
                }
            }

            Rectangle {
                color: theme.borderSubtle
                height: 1
                width: parent.width
                anchors.bottom: parent.bottom
            }
        }

        // 3. Search Results List
        ListView {
            id: songResultsView
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 4
            clip: true

            model: ListModel {
                id: songResultsModel
            }

            Item {
                anchors.fill: parent
                visible: songResultsModel.count === 0

                Column {
                    anchors.centerIn: parent
                    width: parent.width - 36
                    spacing: 6

                    Text {
                        text: "Your queue is ready"
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        color: theme.textSecondary
                        font.pixelSize: 11
                        font.family: theme.uiFont
                    }
                    Text {
                        text: "Search for a track to start listening."
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        color: theme.textMuted
                        font.pixelSize: 10
                        font.family: theme.uiFont
                        wrapMode: Text.WordWrap
                    }
                }
            }

            delegate: Rectangle {
                width: songResultsView.width
                height: 38
                radius: theme.radiusSm
                color: (musicPanelRoot.currentVideoId === videoId) ? theme.bgActive : (songMouse.containsMouse ? theme.bgHover : "transparent")

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 8

                    // Playing indicator or number
                    Text {
                        text: (musicPanelRoot.currentVideoId === videoId && musicPanelRoot.playbackState === "playing") ? "▶" : "🎵"
                        color: (musicPanelRoot.currentVideoId === videoId) ? theme.accentColor : theme.textMuted
                        font.pixelSize: 11
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: title
                            color: (musicPanelRoot.currentVideoId === videoId) ? theme.accentColor : theme.textPrimary
                            font.pixelSize: 11
                            font.bold: (musicPanelRoot.currentVideoId === videoId)
                            font.family: theme.uiFont
                            elide: Text.ElideRight
                            width: parent.width
                        }

                        Text {
                            text: artist
                            color: theme.textMuted
                            font.pixelSize: 10
                            font.family: theme.uiFont
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }
                }

                MouseArea {
                    id: songMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        musicPanelRoot.currentSongTitle = title
                        musicPanelRoot.currentArtist = artist
                        musicPanelRoot.currentVideoId = videoId
                        musicPlayer.play_song(videoId)
                    }
                }
            }
        }

        // 4. Physical Playback Station (Vinyl + Track Details + Knob + Controls)
        Rectangle {
            Layout.fillWidth: true
            // The player must stay useful when AI and Music share a narrow
            // sidebar; a fixed 210px block made the queue disappear.
            Layout.preferredHeight: Math.min(190, Math.max(150, musicPanelRoot.height * 0.48))
            color: theme.bgCard

            Rectangle {
                color: theme.borderSubtle
                height: 1
                width: parent.width
                anchors.top: parent.top
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 4

                // Center Top-Down Vinyl Record & Volume Knob Row
                RowLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 12

                    // Rotary Volume Knob
                    Column {
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 4

                        RotaryKnob {
                            id: volumeKnob
                            value: musicPanelRoot.currentVolume
                            onValueModified: newVal => {
                                musicPlayer.volume_change(newVal)
                            }
                        }

                        Text {
                            text: Math.round(musicPanelRoot.currentVolume * 100) + "%"
                            color: theme.textMuted
                            font.pixelSize: 9
                            font.family: theme.uiFont
                            horizontalAlignment: Text.AlignHCenter
                            width: parent.width
                        }
                    }

                    // Top-Down Vinyl Record
                    VinylRecord {
                        id: vinylDisc
                        playbackState: musicPanelRoot.playbackState
                        Layout.preferredWidth: musicPanelRoot.compact ? 76 : 96
                        Layout.preferredHeight: musicPanelRoot.compact ? 76 : 96
                    }
                }

                // Track Metadata
                Column {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 2

                    Text {
                        text: musicPanelRoot.currentSongTitle
                        color: theme.textPrimary
                        font.pixelSize: 12
                        font.bold: true
                        font.family: theme.uiFont
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                        width: parent.width
                    }

                    Text {
                        text: musicPanelRoot.currentArtist
                        color: theme.textSecondary
                        font.pixelSize: 10
                        font.family: theme.uiFont
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                        width: parent.width
                    }
                }

                // Media Playback Controls
                PlaybackControls {
                    Layout.alignment: Qt.AlignHCenter
                    playbackState: musicPanelRoot.playbackState

                    onPlayPauseClicked: {
                        musicPlayer.toggle_play_pause()
                    }
                    onStopClicked: {
                        musicPlayer.stop()
                    }
                    onPrevClicked: {
                        // Previous track logic
                    }
                    onNextClicked: {
                        // Next track logic
                    }
                }
            }
        }
    }

    // Left border divider
    Rectangle {
        color: theme.borderSubtle
        width: 1
        height: parent.height
        anchors.left: parent.left
    }
}
