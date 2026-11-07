import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

Rectangle {
    id: root

    property string playbackState: "stopped" // "playing", "paused", "stopped"
    property string currentTitle: "No Track Selected"
    property string currentArtist: "Ready to Play"
    property string currentVideoId: ""
    property string currentCoverUrl: ""
    property real currentVolume: 0.8
    property string viewMode: "search" // "player" or "search"
    property string activeCategory: "search" // "search", "liked", "recommended"
    property bool showInfoCard: false
    property bool isCurrentLiked: false

    // Playback Progress Tracking (in seconds)
    property int currentPositionSec: 0
    property int totalDurationSec: 225 // 3m 45s default

    // Responsive layout check
    // readonly property bool isTallLayout (disabled to prevent stacking)

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
        if (typeof musicPlayer !== "undefined" && musicPlayer) {
            root.playbackState = musicPlayer.playbackState || "stopped";
            if (musicPlayer.currentVideoId) {
                root.currentVideoId = musicPlayer.currentVideoId;
                root.currentTitle = musicPlayer.currentTitle || "No Track Selected";
                root.currentArtist = musicPlayer.currentArtist || "Ready to Play";
                root.totalDurationSec = musicPlayer.currentDuration || 210;
                root.isCurrentLiked = musicPlayer.is_liked ? musicPlayer.is_liked(root.currentVideoId) : false;
            }
        }
    }

    onCurrentVolumeChanged: {
        if (typeof settingsBackend !== "undefined" && settingsBackend) {
            settingsBackend.set_value("music_volume", "" + root.currentVolume);
        }
    }

    // Dreamy, Gloomy Animated Ambient Floating Green Aura Background
    Item {
        anchors.fill: parent
        z: 0
        clip: true

        Canvas {
            id: dreamyBgCanvas
            anchors.fill: parent

            property real timePhase: 0.0

            Timer {
                interval: 35
                running: true
                repeat: true
                onTriggered: {
                    dreamyBgCanvas.timePhase += 0.008; // slow organic dreamy float
                    dreamyBgCanvas.requestPaint();
                }
            }

            onPaint: {
                var ctx = getContext("2d");
                ctx.reset();
                ctx.clearRect(0, 0, width, height);

                // Base background color
                var baseColor = (typeof theme !== "undefined" && theme && theme.bgSidebar) ? theme.bgSidebar : "#181818";
                ctx.fillStyle = baseColor;
                ctx.fillRect(0, 0, width, height);

                // Determine CD vinyl center if available
                var vinylCx = width * 0.5;
                var vinylCy = height * 0.62;
                if (root.viewMode === "player" && heroVinyl && heroVinyl.visible) {
                    try {
                        var pt = heroVinyl.mapToItem(dreamyBgCanvas, heroVinyl.width * 0.5, heroVinyl.height * 0.5);
                        if (pt && pt.y > 0 && pt.y < height) {
                            vinylCx = pt.x;
                            vinylCy = pt.y;
                        }
                    } catch (e) {}
                }

                var p = dreamyBgCanvas.timePhase;
                var extraHeight = Math.max(0, height - 380);

                // Subtle deep moody gradient: dark at top, richer dusky tint toward bottom
                var baseGrad = ctx.createLinearGradient(0, 0, 0, height);
                baseGrad.addColorStop(0.0, "transparent");
                baseGrad.addColorStop(0.4, "#06130e40");
                baseGrad.addColorStop(0.8, "#091e1630");
                baseGrad.addColorStop(1.0, "#050b0850");
                ctx.fillStyle = baseGrad;
                ctx.fillRect(0, 0, width, height);

                // =================================================================
                // 1. Core Floaty Green Aura directly behind the CD Vinyl
                // =================================================================
                var drift1X = vinylCx + (14 * Math.sin(p * 0.8));
                var drift1Y = vinylCy + (10 * Math.cos(p * 0.6));
                // Green aura radius increases with height!
                var orb1R = Math.max(130, Math.min(width * 1.05, 135 + extraHeight * 0.38));

                var grad1 = ctx.createRadialGradient(drift1X, drift1Y, 15, drift1X, drift1Y, orb1R);
                grad1.addColorStop(0.0, "#1e523e38");  // Soft, muted moss / sage glow
                grad1.addColorStop(0.40, "#143d2e25"); // Deep gloomy forest tone
                grad1.addColorStop(0.75, "#0b261d12"); // Subtle ambient fade
                grad1.addColorStop(1.0, "transparent");
                ctx.fillStyle = grad1;
                ctx.beginPath();
                ctx.arc(drift1X, drift1Y, orb1R, 0, Math.PI * 2);
                ctx.fill();

                // =================================================================
                // 2. Rising / Increasing Floaty Green Aura into the spacious upper zone
                //    (Expands and increases when panel is tall without AI panel)
                // =================================================================
                if (extraHeight > 15) {
                    var riseY = Math.max(height * 0.18, vinylCy - (90 + extraHeight * 0.42));
                    var drift2X = width * (0.5 + 0.16 * Math.cos(p * 0.7));
                    var drift2Y = riseY + (16 * Math.sin(p * 0.5));
                    var orb2R = Math.max(140, width * 0.9 + extraHeight * 0.40);

                    var grad2 = ctx.createRadialGradient(drift2X, drift2Y, 20, drift2X, drift2Y, orb2R);
                    grad2.addColorStop(0.0, "#285e4828");  // Soft atmospheric ambient mist
                    grad2.addColorStop(0.45, "#1640301a"); // Deep muted sage
                    grad2.addColorStop(0.80, "#0d261c10"); // Ethereal twilight fade
                    grad2.addColorStop(1.0, "transparent");
                    ctx.fillStyle = grad2;
                    ctx.beginPath();
                    ctx.arc(drift2X, drift2Y, orb2R, 0, Math.PI * 2);
                    ctx.fill();
                }

                // =================================================================
                // 3. Ethereal Cyan-Teal / Green Drift Pulse on the perimeter
                // =================================================================
                var orb3X = width * (0.55 - 0.22 * Math.sin(p * 0.65));
                var orb3Y = vinylCy - 20 + (12 * Math.sin(p * 0.9));
                var orb3R = Math.max(110, width * 0.75 + extraHeight * 0.18);

                var grad3 = ctx.createRadialGradient(orb3X, orb3Y, 15, orb3X, orb3Y, orb3R);
                grad3.addColorStop(0.0, "#16473d22");  // Subtle teal-forest tint
                grad3.addColorStop(0.60, "#0c2b2410");
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
    }

    Connections {
        target: typeof musicPlayer !== "undefined" ? musicPlayer : null
        ignoreUnknownSignals: true

        function onSearchResults(songs) {
            if (root.activeCategory !== "search") return;
            songListModel.clear();
            if (!songs || songs.length === 0) return;
            for (var i = 0; i < songs.length; i++) {
                songListModel.append(songs[i]);
            }
        }

        function onLikedSongsChanged(songs) {
            if (typeof musicPlayer !== "undefined" && musicPlayer && root.currentVideoId) {
                root.isCurrentLiked = musicPlayer.is_liked(root.currentVideoId);
            }
            if (root.activeCategory === "liked") {
                songListModel.clear();
                if (songs && songs.length > 0) {
                    for (var i = 0; i < songs.length; i++) {
                        songListModel.append(songs[i]);
                    }
                }
            }
        }

        function onRecommendationsReady(songs) {
            if (root.activeCategory === "recommended") {
                songListModel.clear();
                if (songs && songs.length > 0) {
                    for (var i = 0; i < songs.length; i++) {
                        songListModel.append(songs[i]);
                    }
                }
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
            if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.is_liked) {
                root.isCurrentLiked = musicPlayer.is_liked(videoId);
            }
            if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.coverUrl) {
                root.currentCoverUrl = musicPlayer.coverUrl;
            } else {
                root.currentCoverUrl = "";
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

                // Header Title
                Text {
                    text: root.viewMode === "player" ? (root.currentTitle ? root.currentTitle : "Now Playing") : "Search Songs"
                    color: theme ? theme.textBright : "#ffffff"
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                // View Mode Toggle (Disc for player, Search for song search)
                Rectangle {
                    width: 22
                    height: 22
                    radius: 3
                    color: modeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                    visible: true

                    VectorIcon {
                        anchors.centerIn: parent
                        name: root.viewMode === "player" ? "search" : "disc"
                        size: 11
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    ToolTip.visible: modeMa.containsMouse
                    ToolTip.text: root.viewMode === "player" ? "Search Songs" : "Now Playing"

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
            Layout.preferredHeight: (root.viewMode === "player") ? -1 : 0
            Layout.fillHeight: (root.viewMode === "player")
            visible: (root.viewMode === "player")
            color: "transparent"
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                anchors.topMargin: 8
                anchors.bottomMargin: 12
                spacing: 8

                // Top Atmosphere Spacer: absorbs tall panel height without AI panel and keeps CD down
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 8
                }

                // Center Spinning Vinyl Record (Kept down near track title and controls)
                Item {
                    id: vinylContainer
                    Layout.fillWidth: true
                    Layout.preferredHeight: heroVinyl.size + 14
                    Layout.alignment: Qt.AlignHCenter

                    VinylRecord {
                        id: heroVinyl
                        anchors.centerIn: parent
                        size: Math.min(156, Math.max(96, playerHeroSection.height > 520 ? 148 : (playerHeroSection.height > 380 ? 128 : 100)))
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
                                grad.addColorStop(0.0, "#38bdf880"); // Soft muted sky blue
                                grad.addColorStop(0.5, "#4338ca65"); // Deep indigo
                                grad.addColorStop(1.0, "#6366f150"); // Muted dusk violet

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
                                ctx.fillStyle = theme ? (theme.accentMuted || "#3b5e82") : "#3b5e82";
                                ctx.fillRect(0, height - 1.5, width * progressRatio, 1.5);
                            }
                        }
                    }

                    // Duration Timestamps (e.g. 01:24 / 03:45) & Playing Indicator
                    RowLayout {
                        Layout.fillWidth: true

                        Text {
                            text: root.formatTime(root.currentPositionSec)
                            color: theme ? theme.textSecondary : "#94a3b8"
                            font.pixelSize: 9
                            font.bold: true
                            font.family: theme ? theme.fontFamilyMono : "monospace"
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: root.playbackState === "playing" ? "FREQUENCY EQ ON" : "STUDIO OFF"
                            color: root.playbackState === "playing" ? (theme ? (theme.successMuted || "#5e817a") : "#5e817a") : (theme ? theme.textMuted : "#656565")
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
                        color: playMa.containsMouse ? (theme ? (theme.accentHover || "#3d5e7d") : "#3d5e7d") : (theme ? (theme.accentMuted || "#2e4a62") : "#2e4a62")

                        VectorIcon {
                            anchors.centerIn: parent
                            name: root.playbackState === "playing" ? "pause" : "play"
                            size: 13
                            color: "#ffffff"
                        }

                        MouseArea {
                            id: playMa
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

                    // Like / Love Button
                    Rectangle {
                        width: 26
                        height: 26
                        radius: 13
                        color: likeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                        border.color: root.isCurrentLiked ? "#9e4a57" : (theme ? theme.borderNormal : "#333333")
                        border.width: 1

                        VectorIcon {
                            anchors.centerIn: parent
                            name: root.isCurrentLiked ? "heart-filled" : "heart"
                            size: 11
                            color: root.isCurrentLiked ? "#b85d6e" : (theme ? theme.textSecondary : "#858585")
                        }

                        ToolTip.visible: likeMa.containsMouse
                        ToolTip.text: root.isCurrentLiked ? "Liked Song (Click to Unlike)" : "Like Song"

                        MouseArea {
                            id: likeMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.toggleCurrentLike()
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
                        border.color: root.showInfoCard ? (theme ? (theme.accentMuted || "#4b6a8a") : "#4b6a8a") : (theme ? theme.borderNormal : "#333333")
                        border.width: 1

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "info"
                            size: 12
                            color: root.showInfoCard ? (theme ? (theme.accentMuted || "#4b6a8a") : "#4b6a8a") : (theme ? theme.textSecondary : "#858585")
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
            visible: false
        }

        // =====================================================================
        // 3. SEARCH & TRACK LIST SECTION (Shown below player if tall, or as tab)
        // =====================================================================
        Rectangle {
            id: searchListSection
            Layout.fillWidth: true
            Layout.fillHeight: (root.viewMode === "search")
            visible: (root.viewMode === "search")
            color: "transparent"

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // Category Selector Bar (Search / Liked / Recommended)
                Rectangle {
                    Layout.fillWidth: true
                    height: 26
                    color: theme ? theme.bgHeader : "#141414"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 2
                        spacing: 2

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 2
                            color: root.activeCategory === "search" ? (theme ? theme.bgSurfaceActive : "#2a2d2e") : "transparent"

                            Text {
                                anchors.centerIn: parent
                                text: "Search"
                                color: root.activeCategory === "search" ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#888888")
                                font.pixelSize: 10
                                font.bold: root.activeCategory === "search"
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeCategory = "search"
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 2
                            color: root.activeCategory === "liked" ? (theme ? theme.bgSurfaceActive : "#2a2d2e") : "transparent"

                            Row {
                                anchors.centerIn: parent
                                spacing: 4

                                VectorIcon {
                                    name: "heart-filled"
                                    size: 8
                                    color: root.activeCategory === "liked" ? "#b85d6e" : (theme ? theme.textMuted : "#888888")
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: "Liked"
                                    color: root.activeCategory === "liked" ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#888888")
                                    font.pixelSize: 10
                                    font.bold: root.activeCategory === "liked"
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.activeCategory = "liked";
                                    root.loadLikedSongs();
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 2
                            color: root.activeCategory === "recommended" ? (theme ? theme.bgSurfaceActive : "#2a2d2e") : "transparent"

                            Text {
                                anchors.centerIn: parent
                                text: "Recommended"
                                color: root.activeCategory === "recommended" ? (theme ? theme.accent : "#38bdf8") : (theme ? theme.textMuted : "#888888")
                                font.pixelSize: 10
                                font.bold: root.activeCategory === "recommended"
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.activeCategory = "recommended";
                                    root.loadRecommendations();
                                }
                            }
                        }
                    }
                }

                // Search Input Field (Visible in search category)
                Rectangle {
                    Layout.fillWidth: true
                    height: 28
                    radius: theme ? theme.radiusSm : 3
                    color: theme ? theme.bgInput : "#1e1e1e"
                    border.color: musicSearchInput.activeFocus ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderSubtle : "#282828")
                    border.width: 1
                    visible: root.activeCategory === "search"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 6

                        VectorIcon {
                            name: "search"
                            size: 11
                            color: musicSearchInput.activeFocus ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565")
                        }

                        TextInput {
                            id: musicSearchInput
                            Layout.fillWidth: true
                            verticalAlignment: TextInput.AlignVCenter
                            color: theme ? theme.textBright : "#ffffff"
                            font.pixelSize: 11
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            selectByMouse: true

                            Text {
                                anchors.fill: parent
                                verticalAlignment: Text.AlignVCenter
                                text: "Search songs / artists..."
                                color: theme ? theme.textMuted : "#656565"
                                font.pixelSize: 11
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
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

                    // Empty state indicator
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width - 24
                        height: 80
                        color: "transparent"
                        visible: songListModel.count === 0

                        Column {
                            anchors.centerIn: parent
                            spacing: 6

                            VectorIcon {
                                anchors.horizontalCenter: parent.horizontalCenter
                                name: root.activeCategory === "liked" ? "heart" : (root.activeCategory === "recommended" ? "sparkles" : "music")
                                size: 18
                                color: theme ? theme.textMuted : "#555555"
                            }

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: root.activeCategory === "liked" ? "No liked songs yet" : (root.activeCategory === "recommended" ? "Finding recommendations..." : "No songs yet")
                                color: theme ? theme.textSecondary : "#888888"
                                font.pixelSize: 11
                                font.bold: true
                            }

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: root.activeCategory === "liked" ? "Click the heart button to save favorite tracks." : (root.activeCategory === "recommended" ? "Signals based on your loved tracks and artists." : "Type above to search online tracks.")
                                color: theme ? theme.textMuted : "#666666"
                                font.pixelSize: 9
                            }
                        }
                    }

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
                                            source: (model.coverUrl && model.coverUrl.length > 0) ? model.coverUrl : ""
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

                                    // Like indicator in list item
                                    VectorIcon {
                                        name: "heart-filled"
                                        size: 9
                                        color: "#b85d6e"
                                        visible: (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.is_liked) ? musicPlayer.is_liked(model.videoId) : false
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

                // Compact Now-Playing Bar at bottom of search view
                Rectangle {
                    Layout.fillWidth: true
                    height: (root.currentVideoId !== "") ? 42 : 0
                    visible: height > 0
                    color: theme ? theme.bgSurface : "#202022"
                    border.color: theme ? theme.borderSubtle : "#282828"
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8

                        // Mini Cover or Disc Icon
                        Rectangle {
                            width: 26
                            height: 26
                            radius: 13
                            color: theme ? theme.bgHeader : "#181818"
                            border.color: theme ? theme.borderNormal : "#333333"
                            border.width: 1

                            VectorIcon {
                                anchors.centerIn: parent
                                name: root.playbackState === "playing" ? "disc" : "music"
                                size: 12
                                color: theme ? (theme.accentMuted || "#4b6a8a") : "#4b6a8a"
                            }
                        }

                        // Track title & artist
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1

                            Text {
                                text: root.currentTitle
                                color: theme ? theme.textBright : "#ffffff"
                                font.pixelSize: 10
                                font.bold: true
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            Text {
                                text: root.currentArtist
                                color: theme ? theme.textMuted : "#858585"
                                font.pixelSize: 9
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }

                        // Mini Play / Pause
                        Rectangle {
                            width: 24
                            height: 24
                            radius: 12
                            color: miniPlayMa.containsMouse ? (theme ? (theme.accentHover || "#3d5e7d") : "#3d5e7d") : (theme ? (theme.accentMuted || "#2e4a62") : "#2e4a62")

                            VectorIcon {
                                anchors.centerIn: parent
                                name: root.playbackState === "playing" ? "pause" : "play"
                                size: 10
                                color: "#ffffff"
                            }

                            MouseArea {
                                id: miniPlayMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.togglePlayPause()
                            }
                        }

                        // Open Player View Button
                        Rectangle {
                            width: 24
                            height: 24
                            radius: 4
                            color: expandMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                            VectorIcon {
                                anchors.centerIn: parent
                                name: "disc"
                                size: 11
                                color: theme ? theme.textSecondary : "#858585"
                            }

                            ToolTip.visible: expandMa.containsMouse
                            ToolTip.text: "Open Vinyl Player"

                            MouseArea {
                                id: expandMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.viewMode = "player"
                            }
                        }
                    }

                    // Click area on bar to open full player
                    MouseArea {
                        anchors.fill: parent
                        anchors.rightMargin: 60
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.viewMode = "player"
                    }
                }
            }
        }
    }

    function toggleCurrentLike() {
        if (!root.currentVideoId) return;
        if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.toggle_like) {
            root.isCurrentLiked = musicPlayer.toggle_like(
                root.currentVideoId,
                root.currentTitle,
                root.currentArtist,
                root.totalDurationSec,
                root.currentCoverUrl
            );
        }
    }

    function loadLikedSongs() {
        songListModel.clear();
        if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.get_liked_songs) {
            var liked = musicPlayer.get_liked_songs();
            if (liked && liked.length > 0) {
                for (var i = 0; i < liked.length; i++) {
                    songListModel.append(liked[i]);
                }
            }
        }
    }

    function loadRecommendations() {
        songListModel.clear();
        if (typeof musicPlayer !== "undefined" && musicPlayer && musicPlayer.fetch_recommendations) {
            musicPlayer.fetch_recommendations();
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
