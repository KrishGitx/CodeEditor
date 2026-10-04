import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

Rectangle {
    id: root

    property string playbackState: "stopped" // "playing", "paused", "stopped"
    property string currentTitle: "Coding Focus Lo-Fi"
    property string currentArtist: "Deep Code Audio"
    property string currentVideoId: "demo_1"
    property string currentCoverUrl: "https://img.youtube.com/vi/3_g2un5M350/hqdefault.jpg"
    property real currentVolume: 0.8
    property string viewMode: "player" // "player" or "search"
    property bool showInfoCard: false

    // Playback Progress Tracking (in seconds)
    property int currentPositionSec: 0
    property int totalDurationSec: 225 // 3m 45s default

    // Responsive layout check
    readonly property bool isTallLayout: root.height >= 460

    signal closeRequested()

    color: theme ? theme.bgSidebar : "#181818"

    Component.onCompleted: {
        if (typeof settingsBackend !== "undefined" && settingsBackend) {
            var savedVol = settingsBackend.get_value("music_volume", "0.8");
            if (savedVol) {
                var v = parseFloat(savedVol);
                if (!isNaN(v)) {
                    root.currentVolume = v;
                    if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.set_volume) {
                        musicPlayer.set_volume(v);
                    }
                }
            }
        }
    }

    onCurrentVolumeChanged: {
        if (typeof settingsBackend !== "undefined" && settingsBackend) {
            settingsBackend.set_value("music_volume", "" + root.currentVolume);
        }
    }

    // Dreamy, Gloomy Animated Ambient Floating Gradient Background
    Item {
        anchors.fill: parent
        z: 0
        clip: true

        Canvas {
            id: dreamyBgCanvas
            anchors.fill: parent

            property real timePhase: 0.0

            Timer {
                interval: 40
                running: true
                repeat: true
                onTriggered: {
                    dreamyBgCanvas.timePhase += 0.007; // ultra-smooth, slow dreamy breathing speed
                    dreamyBgCanvas.requestPaint();
                }
            }

            onPaint: {
                var ctx = getContext("2d");
                ctx.reset();
                ctx.clearRect(0, 0, width, height);

                // Base vertical gloomy gradient: transparent at top -> moody deep dusk at bottom
                var baseGrad = ctx.createLinearGradient(0, 0, 0, height);
                baseGrad.addColorStop(0.0, "transparent");
                baseGrad.addColorStop(0.25, "transparent");
                baseGrad.addColorStop(0.6, "#150d2460");
                baseGrad.addColorStop(1.0, "#0c0817b0");
                ctx.fillStyle = baseGrad;
                ctx.fillRect(0, 0, width, height);

                // Floating Glowing Ambient Aurora Orbs (slow organic floating motion)
                var p = dreamyBgCanvas.timePhase;

                // Orb 1: Moody Deep Amethyst / Magenta Glowing Aura behind vinyl & controls
                var orb1X = width * (0.4 + 0.3 * Math.sin(p * 0.8));
                var orb1Y = height * (0.65 + 0.18 * Math.cos(p * 0.6));
                var orb1R = Math.max(140, width * 0.85);

                var grad1 = ctx.createRadialGradient(orb1X, orb1Y, 15, orb1X, orb1Y, orb1R);
                grad1.addColorStop(0.0, "#701a7575"); // Rich moody Magenta
                grad1.addColorStop(0.45, "#3b076445"); // Deep purple aura
                grad1.addColorStop(1.0, "transparent");
                ctx.fillStyle = grad1;
                ctx.beginPath();
                ctx.arc(orb1X, orb1Y, orb1R, 0, Math.PI * 2);
                ctx.fill();

                // Orb 2: Dreamy Twilight Teal / Ocean Glow
                var orb2X = width * (0.6 - 0.28 * Math.cos(p * 0.7));
                var orb2Y = height * (0.78 + 0.14 * Math.sin(p * 0.9));
                var orb2R = Math.max(150, width * 0.9);

                var grad2 = ctx.createRadialGradient(orb2X, orb2Y, 15, orb2X, orb2Y, orb2R);
                grad2.addColorStop(0.0, "#0891b265"); // Dreamy Deep Teal
                grad2.addColorStop(0.5, "#155e7535");
                grad2.addColorStop(1.0, "transparent");
                ctx.fillStyle = grad2;
                ctx.beginPath();
                ctx.arc(orb2X, orb2Y, orb2R, 0, Math.PI * 2);
                ctx.fill();

                // Orb 3: Soft subtle bottom indigo glow
                var orb3X = width * 0.5;
                var orb3Y = height * 0.92;
                var orb3R = width * 0.8;
                var grad3 = ctx.createRadialGradient(orb3X, orb3Y, 10, orb3X, orb3Y, orb3R);
                grad3.addColorStop(0.0, "#4338ca40");
                grad3.addColorStop(1.0, "transparent");
                ctx.fillStyle = grad3;
                ctx.beginPath();
                ctx.arc(orb3X, orb3Y, orb3R, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }

    Timer {
        id: playbackTimer
        interval: 1000
        running: root.playbackState === "playing"
        repeat: true
        onTriggered: {
            if (root.currentPositionSec < root.totalDurationSec) {
                root.currentPositionSec += 1;
            } else {
                root.playNextSong();
            }
        }
    }

    function formatTime(sec) {
        var m = Math.floor(sec / 60);
        var s = sec % 60;
        return (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s);
    }

    ListModel {
        id: songListModel

        Component.onCompleted: {
            append({ title: "Coding Focus Lo-Fi Flow", artist: "Deep Code Audio", videoId: "demo_1", duration: 225 });
            append({ title: "Midnight Ambient Beats", artist: "Studio Soundscapes", videoId: "demo_2", duration: 198 });
            append({ title: "Deep Synthwave Rhythm", artist: "Cyber Pulse", videoId: "demo_3", duration: 264 });
            append({ title: "Chill Coffeehouse Acoustic", artist: "Acoustic Vibes", videoId: "demo_4", duration: 180 });
        }
    }

    Connections {
        target: typeof musicPlayer !== "undefined" ? musicPlayer : null
        ignoreUnknownSignals: true

        function onSearchResults(songs) {
            songListModel.clear();
            if (!songs || songs.length === 0) return;
            for (var i = 0; i < songs.length; i++) {
                songListModel.append(songs[i]);
            }
        }

        function onPlaybackStateChanged(state) {
            root.playbackState = state;
            if (state === "playing") {
                playbackTimer.restart();
            }
        }

        function onCurrentSongChanged(title, artist, videoId, duration) {
            root.currentTitle = title;
            root.currentArtist = artist;
            root.currentVideoId = videoId;
            root.totalDurationSec = duration || 210;
            root.currentPositionSec = 0;
            root.viewMode = "player";
            if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.coverUrl) {
                root.currentCoverUrl = musicPlayer.coverUrl;
            } else {
                root.currentCoverUrl = "https://img.youtube.com/vi/" + videoId + "/hqdefault.jpg";
            }
        }

        function onCoverUrlChanged(url) {
            if (url) {
                root.currentCoverUrl = url;
            }
        }

        function onSongFinished(videoId) {
            if (root.playbackState === "playing" && root.currentPositionSec >= Math.max(10, root.totalDurationSec - 5)) {
                root.playNextSong();
            }
        }

        function onVolumeChanged(vol) {
            root.currentVolume = vol;
            volumeKnob.value = vol;
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // =====================================================================
        // 1. HEADER (Back <, Title / Search Box, Close X)
        // =====================================================================
        Rectangle {
            Layout.fillWidth: true
            height: 34
            color: theme ? theme.bgHeader : "#181818"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6

                // Back Button (<) - Switch view mode in compact view
                Rectangle {
                    width: 22
                    height: 22
                    radius: 3
                    color: backMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                    visible: !root.isTallLayout

                    VectorIcon {
                        anchors.centerIn: parent
                        name: root.viewMode === "player" ? "back" : "disc"
                        size: 11
                        color: theme ? theme.textBright : "#ffffff"
                    }

                    MouseArea {
                        id: backMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.viewMode = (root.viewMode === "player") ? "search" : "player";
                        }
                    }
                }

                // Header Title or Search Toggle
                Text {
                    text: root.viewMode === "player" ? (root.currentTitle ? root.currentTitle : "Now Playing") : "Search Songs"
                    color: theme ? theme.textBright : "#ffffff"
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                // Switch to Search/List Button (when in Player mode)
                Rectangle {
                    width: 22
                    height: 22
                    radius: 3
                    color: modeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                    visible: !root.isTallLayout

                    VectorIcon {
                        anchors.centerIn: parent
                        name: root.viewMode === "player" ? "search" : "disc"
                        size: 11
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    MouseArea {
                        id: modeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.viewMode = (root.viewMode === "player") ? "search" : "player";
                        }
                    }
                }

                // Close Button (x)
                Rectangle {
                    width: 22
                    height: 22
                    radius: 3
                    color: closeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "close"
                        size: 9
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    MouseArea {
                        id: closeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.closeRequested()
                    }
                }
            }
        }

        // Header Divider
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: theme ? theme.borderSubtle : "#282828"
        }

        // =====================================================================
        // 2. NOW PLAYING HERO SECTION (Featured Vinyl + Progress Bar + Controls)
        // =====================================================================
        Rectangle {
            id: playerHeroSection
            Layout.fillWidth: true
            Layout.preferredHeight: (root.isTallLayout || root.viewMode === "player") ? (root.isTallLayout ? 260 : -1) : 0
            Layout.fillHeight: (!root.isTallLayout && root.viewMode === "player")
            visible: root.isTallLayout || root.viewMode === "player"
            color: "transparent"
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                // Center Spinning Vinyl Record (Large & Prominent)
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(130, Math.max(90, playerHeroSection.height - 140))
                    Layout.fillHeight: !root.isTallLayout

                    VinylRecord {
                        id: heroVinyl
                        anchors.centerIn: parent
                        size: Math.min(parent.height, 130)
                        isPlaying: root.playbackState === "playing"
                        trackTitle: root.currentTitle
                        trackArtist: root.currentArtist
                        coverUrl: (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.coverUrl) ? musicPlayer.coverUrl : (root.currentCoverUrl || "")
                    }
                }

                // Track Title & Artist Labels
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: root.currentTitle
                        color: theme ? theme.textBright : "#ffffff"
                        font.pixelSize: 12
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Text {
                        text: root.currentArtist
                        color: theme ? theme.textSecondary : "#858585"
                        font.pixelSize: 10
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                // Audio Frequency Style Gradient Visualizer & Progress Tracker
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    // Frequency Equalizer Wave Canvas with Radiant Gradient
                    Rectangle {
                        id: freqBox
                        Layout.fillWidth: true
                        height: 38
                        radius: 4
                        color: theme ? theme.bgSurface : "#202022"
                        border.color: theme ? theme.borderSubtle : "#282828"
                        border.width: 1
                        clip: true

                        Canvas {
                            id: freqCanvas
                            anchors.fill: parent
                            anchors.margins: 4
                            renderTarget: Canvas.Image

                            property real phase: 0.0
                            property bool isPlaying: root.playbackState === "playing"

                            Timer {
                                interval: 40
                                running: freqCanvas.isPlaying
                                repeat: true
                                onTriggered: {
                                    freqCanvas.phase += 0.15;
                                    freqCanvas.requestPaint();
                                }
                            }

                            onPaint: {
                                var ctx = getContext("2d");
                                ctx.reset();
                                ctx.clearRect(0, 0, width, height);

                                var barCount = 28;
                                var barSpacing = 2.5;
                                var totalSpacing = (barCount - 1) * barSpacing;
                                var barWidth = Math.max(2, (width - totalSpacing) / barCount);

                                var grad = ctx.createLinearGradient(0, 0, 0, height);
                                grad.addColorStop(0.0, "#4ec9b0"); // Teal/Cyan
                                grad.addColorStop(0.5, "#0078d4"); // Electric Blue
                                grad.addColorStop(1.0, "#a855f7"); // Vibrant Purple

                                ctx.fillStyle = grad;

                                var progressRatio = root.totalDurationSec > 0 ? (root.currentPositionSec / root.totalDurationSec) : 0;

                                for (var i = 0; i < barCount; i++) {
                                    var x = i * (barWidth + barSpacing);
                                    var baseFactor = Math.sin((i / barCount) * Math.PI); // arch curve

                                    var h = 4;
                                    if (freqCanvas.isPlaying) {
                                        var wave1 = Math.sin(freqCanvas.phase + i * 0.4);
                                        var wave2 = Math.cos(freqCanvas.phase * 0.7 + i * 0.6);
                                        var norm = (wave1 + wave2 + 2) / 4; // 0 to 1
                                        h = Math.max(4, (height - 4) * baseFactor * norm);
                                    } else {
                                        h = Math.max(4, (height * 0.35) * baseFactor);
                                    }

                                    var y = height - h;
                                    ctx.beginPath();
                                    ctx.rect(x, y, barWidth, h);
                                    ctx.fill();
                                }

                                // Subtle Progress Line at bottom
                                ctx.fillStyle = "#ffffff30";
                                ctx.fillRect(0, height - 1.5, width, 1.5);
                                ctx.fillStyle = "#0078d4";
                                ctx.fillRect(0, height - 1.5, width * progressRatio, 1.5);
                            }
                        }
                    }

                    // Duration Timestamps (e.g. 01:24 / 03:45) & Playing Indicator
                    RowLayout {
                        Layout.fillWidth: true

                        Text {
                            text: root.formatTime(root.currentPositionSec)
                            color: theme ? theme.accent : "#0078d4"
                            font.pixelSize: 9
                            font.bold: true
                            font.family: theme ? theme.fontFamilyMono : "monospace"
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: root.playbackState === "playing" ? "FREQUENCY EQ ON" : "STUDIO OFF"
                            color: root.playbackState === "playing" ? (theme ? theme.success : "#4ec9b0") : (theme ? theme.textMuted : "#656565")
                            font.pixelSize: 8
                            font.bold: true
                            font.letterSpacing: 0.5
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: root.formatTime(root.totalDurationSec)
                            color: theme ? theme.textMuted : "#656565"
                            font.pixelSize: 9
                            font.family: theme ? theme.fontFamilyMono : "monospace"
                        }
                    }
                }

                // Playback Controls Row (Prev, Play/Pause, Next, Stop, Rotary Volume, Info ⓘ)
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    // Previous Track Button
                    Rectangle {
                        width: 26
                        height: 26
                        radius: 13
                        color: prevMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                        border.color: theme ? theme.borderNormal : "#333333"
                        border.width: 1

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "undo"
                            size: 10
                            color: theme ? theme.textSecondary : "#858585"
                        }

                        ToolTip.visible: prevMa.containsMouse
                        ToolTip.text: "Previous Track"

                        MouseArea {
                            id: prevMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.playPrevSong()
                        }
                    }

                    // Play/Pause Button
                    Rectangle {
                        width: 32
                        height: 32
                        radius: 16
                        color: theme ? theme.accent : "#0078d4"

                        VectorIcon {
                            anchors.centerIn: parent
                            name: root.playbackState === "playing" ? "pause" : "play"
                            size: 13
                            color: "#ffffff"
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.togglePlayPause()
                        }
                    }

                    // Next Track Button
                    Rectangle {
                        width: 26
                        height: 26
                        radius: 13
                        color: nextMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                        border.color: theme ? theme.borderNormal : "#333333"
                        border.width: 1

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "redo"
                            size: 10
                            color: theme ? theme.textSecondary : "#858585"
                        }

                        ToolTip.visible: nextMa.containsMouse
                        ToolTip.text: "Next Track"

                        MouseArea {
                            id: nextMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.playNextSong()
                        }
                    }

                    // Stop Button
                    Rectangle {
                        width: 26
                        height: 26
                        radius: 13
                        color: stopMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                        border.color: theme ? theme.borderNormal : "#333333"
                        border.width: 1

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "stop"
                            size: 10
                            color: theme ? theme.textSecondary : "#858585"
                        }

                        MouseArea {
                            id: stopMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.stopPlayback()
                        }
                    }

                    Item { Layout.fillWidth: true }

                    // Rotary Volume Knob
                    VolumeKnob {
                        id: volumeKnob
                        size: 32
                        value: root.currentVolume
                        onMoved: function(val) {
                            root.setVolume(val);
                        }
                    }

                    // Info Button (ⓘ)
                    Rectangle {
                        width: 26
                        height: 26
                        radius: 13
                        color: (infoMa.containsMouse || root.showInfoCard) ? (theme ? theme.bgSurfaceActive : "#37373d") : "transparent"
                        border.color: root.showInfoCard ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderNormal : "#333333")
                        border.width: 1

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "info"
                            size: 12
                            color: root.showInfoCard ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textSecondary : "#858585")
                        }

                        MouseArea {
                            id: infoMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.showInfoCard = !root.showInfoCard
                        }
                    }
                }

                // Toggleable Track Info Card
                Rectangle {
                    Layout.fillWidth: true
                    height: root.showInfoCard ? 54 : 0
                    visible: height > 0
                    radius: 4
                    color: theme ? theme.bgSurface : "#252526"
                    border.color: theme ? theme.borderSubtle : "#282828"
                    border.width: 1
                    clip: true

                    Column {
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 2

                        Text {
                            text: "Track: " + root.currentTitle
                            color: theme ? theme.textPrimary : "#cccccc"
                            font.pixelSize: 10
                            font.bold: true
                            elide: Text.ElideRight
                            width: parent.width
                        }

                        Text {
                            text: "Artist: " + root.currentArtist
                            color: theme ? theme.textSecondary : "#858585"
                            font.pixelSize: 9
                            elide: Text.ElideRight
                            width: parent.width
                        }

                        Text {
                            text: "Bitrate: 320 kbps (High Quality PCM Audio Sink)"
                            color: theme ? theme.textMuted : "#656565"
                            font.pixelSize: 8
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }

                    Behavior on height {
                        NumberAnimation { duration: 150 }
                    }
                }
            }
        }

        // Divider between Hero Player and Song List (when tall layout)
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: theme ? theme.borderSubtle : "#282828"
            visible: root.isTallLayout
        }

        // =====================================================================
        // 3. SEARCH & TRACK LIST SECTION (Shown below player if tall, or as tab)
        // =====================================================================
        Rectangle {
            id: searchListSection
            Layout.fillWidth: true
            Layout.fillHeight: (root.isTallLayout || root.viewMode === "search")
            visible: root.isTallLayout || root.viewMode === "search"
            color: "transparent"

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // Search Input Field
                Rectangle {
                    Layout.fillWidth: true
                    height: 30
                    color: theme ? theme.bgPanel : "#181818"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 4

                        VectorIcon {
                            name: "search"
                            size: 11
                            color: theme ? theme.textMuted : "#656565"
                        }

                        TextInput {
                            id: musicSearchInput
                            Layout.fillWidth: true
                            verticalAlignment: TextInput.AlignVCenter
                            color: theme ? theme.textPrimary : "#cccccc"
                            font.pixelSize: 11
                            selectByMouse: true

                            Text {
                                anchors.fill: parent
                                verticalAlignment: Text.AlignVCenter
                                text: "Search songs / artists..."
                                color: theme ? theme.textMuted : "#656565"
                                font.pixelSize: 11
                                visible: !musicSearchInput.text && !musicSearchInput.activeFocus
                            }

                            onAccepted: root.searchMusic()
                        }
                    }
                }

                // Song List View
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ScrollView {
                        anchors.fill: parent
                        clip: true

                        ListView {
                            id: musicListView
                            anchors.fill: parent
                            model: songListModel
                            spacing: 1
                            boundsBehavior: Flickable.StopAtBounds

                            delegate: Rectangle {
                                width: musicListView.width
                                height: 36
                                color: model.videoId === root.currentVideoId ? (theme ? theme.bgSelected : "#04395e") : (songMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent")

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8
                                    spacing: 8

                                    // Track Cover Thumbnail / Icon
                                    Rectangle {
                                        width: 24
                                        height: 24
                                        radius: 3
                                        color: theme ? theme.bgSurface : "#202022"
                                        clip: true

                                        Image {
                                            anchors.fill: parent
                                            source: (model.coverUrl && model.coverUrl.length > 0) ? model.coverUrl : ("https://img.youtube.com/vi/" + model.videoId + "/hqdefault.jpg")
                                            fillMode: Image.PreserveAspectCrop
                                            asynchronous: true
                                            cache: true
                                            visible: status === Image.Ready
                                        }

                                        VectorIcon {
                                            anchors.centerIn: parent
                                            name: (model.videoId === root.currentVideoId && root.playbackState === "playing") ? "disc" : "play"
                                            size: 10
                                            color: model.videoId === root.currentVideoId ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565")
                                            visible: !model.coverUrl || model.coverUrl.length === 0
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1

                                        Text {
                                            text: model.title || "Track"
                                            color: model.videoId === root.currentVideoId ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                            font.pixelSize: 11
                                            font.bold: model.videoId === root.currentVideoId
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }

                                        Text {
                                            text: model.artist || "Artist"
                                            color: theme ? theme.textMuted : "#656565"
                                            font.pixelSize: 9
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                    }
                                }

                                MouseArea {
                                    id: songMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        root.playSong(model.videoId, model.title, model.artist, model.duration || 210);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    function searchMusic() {
        var q = musicSearchInput.text.trim();
        if (!q) return;
        if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.search_music) {
            musicPlayer.search_music(q);
        }
    }

    function playSong(vid, title, artist, dur) {
        root.currentVideoId = vid;
        root.currentTitle = title || "Track";
        root.currentArtist = artist || "Artist";
        root.totalDurationSec = dur || 210;
        root.currentPositionSec = 0;
        root.viewMode = "player";
        root.playbackState = "loading";

        if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.play_song) {
            musicPlayer.play_song(vid);
        } else {
            root.playbackState = "playing";
        }
    }

    function togglePlayPause() {
        if (root.playbackState === "stopped" && root.currentVideoId) {
            root.playSong(root.currentVideoId, root.currentTitle, root.currentArtist, root.totalDurationSec);
            return;
        }
        if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.toggle_play_pause) {
            musicPlayer.toggle_play_pause();
        } else {
            root.playbackState = (root.playbackState === "playing") ? "paused" : "playing";
        }
    }

    function stopPlayback() {
        if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.stop) {
            musicPlayer.stop();
        } else {
            root.playbackState = "stopped";
        }
    }

    function setVolume(vol) {
        root.currentVolume = vol;
        if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.volume_change) {
            musicPlayer.volume_change(vol);
        }
    }

    function playNextSong() {
        if (songListModel.count === 0) return;
        var curIdx = -1;
        for (var i = 0; i < songListModel.count; i++) {
            if (songListModel.get(i).videoId === root.currentVideoId) {
                curIdx = i;
                break;
            }
        }
        var nextIdx = curIdx + 1;
        if (nextIdx < songListModel.count) {
            var nextSong = songListModel.get(nextIdx);
            root.playSong(nextSong.videoId, nextSong.title, nextSong.artist, nextSong.duration || 210);
        } else {
            // Reached end of playlist/search list -> loop or stop
            if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.get_value("music_loop", "false") === "true") {
                var firstSong = songListModel.get(0);
                root.playSong(firstSong.videoId, firstSong.title, firstSong.artist, firstSong.duration || 210);
            } else {
                root.stopPlayback();
            }
        }
    }

    function playPrevSong() {
        if (songListModel.count === 0) return;
        var curIdx = -1;
        for (var i = 0; i < songListModel.count; i++) {
            if (songListModel.get(i).videoId === root.currentVideoId) {
                curIdx = i;
                break;
            }
        }
        var prevIdx = curIdx - 1;
        if (prevIdx >= 0) {
            var prevSong = songListModel.get(prevIdx);
            root.playSong(prevSong.videoId, prevSong.title, prevSong.artist, prevSong.duration || 210);
        } else {
            var lastSong = songListModel.get(songListModel.count - 1);
            root.playSong(lastSong.videoId, lastSong.title, lastSong.artist, lastSong.duration || 210);
        }
    }
}
