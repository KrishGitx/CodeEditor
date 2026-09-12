import QtQuick 2.15

// Minimal draggable workspace splitter.
// Public API preserved:
//   orientation
//   isHovered
//   isDragging
//   dragged(delta)

Rectangle {
    id: splitHandle

    property string orientation: "horizontal"
    property bool isHovered: hoverArea.containsMouse
    property bool isDragging: dragArea.pressed

    signal dragged(real delta)

    width: orientation === "horizontal" ? 6 : parent.width
    height: orientation === "vertical" ? 6 : parent.height

    // The splitter itself is transparent.
    // Only the single center line is visible.
    color: "transparent"

    readonly property bool horizontalDrag:
        orientation === "horizontal"

    // Invisible enlarged hit target.
    // This keeps resizing easy without making the UI look bulky.
    MouseArea {
        id: hoverArea

        anchors.fill: parent
        anchors.margins: -5

        hoverEnabled: true
        acceptedButtons: Qt.NoButton

        cursorShape: splitHandle.horizontalDrag
                     ? Qt.SplitHCursor
                     : Qt.SplitVCursor

        z: 1
    }

    // One subtle divider — no box, no grip, no second border.
    Rectangle {
        id: visualLine

        anchors.centerIn: parent

        width: splitHandle.horizontalDrag
               ? 0
               : Math.max(0, parent.width)

        height: splitHandle.horizontalDrag
                ? Math.max(0, parent.height)
                : 0

        color: splitHandle.isDragging
               ? theme.splitterHover
               : splitHandle.isHovered
                 ? Qt.lighter(theme.splitterLine, 1.25)
                 : theme.splitterLine

        opacity: splitHandle.isDragging
                 ? 1.0
                 : splitHandle.isHovered
                   ? 0.9
                   : 0.55

        Behavior on color {
            enabled: theme.animationsEnabled
            ColorAnimation {
                duration: theme.animFast
            }
        }

        Behavior on opacity {
            enabled: theme.animationsEnabled
            NumberAnimation {
                duration: theme.animFast
            }
        }
    }

    // Separate drag area so hover detection and dragging don't fight.
    MouseArea {
        id: dragArea

        anchors.fill: parent
        anchors.margins: -5

        cursorShape: splitHandle.horizontalDrag
                     ? Qt.SplitHCursor
                     : Qt.SplitVCursor

        preventStealing: true
        propagateComposedEvents: false

        property real lastGlobalPosition: 0

        onPressed: function(mouse) {
            var p = splitHandle.mapToItem(null, mouse.x, mouse.y)

            lastGlobalPosition =
                splitHandle.horizontalDrag ? p.x : p.y
        }

        onPositionChanged: function(mouse) {
            if (!pressed)
                return

            var p = splitHandle.mapToItem(null, mouse.x, mouse.y)

            var currentPosition =
                splitHandle.horizontalDrag ? p.x : p.y

            var delta =
                currentPosition - lastGlobalPosition

            if (Math.abs(delta) >= 0.5) {
                splitHandle.dragged(delta)
                lastGlobalPosition = currentPosition
            }
        }

        onReleased: {
            lastGlobalPosition = 0
        }

        onCanceled: {
            lastGlobalPosition = 0
        }
    }
}
