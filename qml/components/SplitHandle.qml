import QtQuick 2.15

Item {
    id: root

    // Orientation: Qt.Horizontal (divides left/right, drags X) or Qt.Vertical (divides top/bottom, drags Y)
    property int orientation: Qt.Horizontal
    property real thickness: 4
    property color dividerLineColor: theme ? theme.borderSubtle : "#282828"
    property color hoverColor: theme ? theme.accent : "#0078d4"

    signal moved(real delta)
    property bool enabled: true

    width: orientation === Qt.Horizontal ? thickness : undefined
    height: orientation === Qt.Vertical ? thickness : undefined

    // Exact 1px divider line
    Rectangle {
        id: line
        anchors.centerIn: parent
        width: root.orientation === Qt.Horizontal ? 1 : parent.width
        height: root.orientation === Qt.Vertical ? 1 : parent.height
        color: (mouseArea.containsMouse || mouseArea.pressed) ? root.hoverColor : root.dividerLineColor
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: root.enabled
        enabled: root.enabled
        cursorShape: root.orientation === Qt.Horizontal ? Qt.SplitHCursor : Qt.SplitVCursor

        property real startPos: 0

        onPressed: function(mouse) {
            startPos = (root.orientation === Qt.Horizontal) ? mouse.x : mouse.y;
        }

        onPositionChanged: function(mouse) {
            if (pressed) {
                var currentPos = (root.orientation === Qt.Horizontal) ? mouse.x : mouse.y;
                var delta = currentPos - startPos;
                if (Math.abs(delta) > 0.5) {
                    root.moved(delta);
                }
            }
        }
    }
}
