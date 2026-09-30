import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    // Tools: "hand", "pen", "box", "sticky", "eraser"
    property string activeTool: "pen"
    property string activeColor: "#0078d4"
    property real strokeWidth: 2.5
    property var freehandPaths: [] // Array of { color: string, width: real, points: [{x, y}] }
    property var currentPathPoints: []

    // Pan and Zoom Transformation (Infinite Canvas)
    property real panX: 0.0
    property real panY: 0.0
    property real zoomScale: 1.0

    // Drag tracking for panning
    property real lastMouseX: 0.0
    property real lastMouseY: 0.0
    property bool isPanning: false

    // Eraser cursor position
    property real eraserScreenX: -100
    property real eraserScreenY: -100
    property real eraserRadius: 18

    signal closeRequested()

    color: theme ? theme.bgEditor : "#1e1e1e"
    clip: true

    // Photoshop-like Fit / Center View (Ctrl+0)
    function centerAndFitView() {
        var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        var hasContent = false;

        // Check freehand strokes
        for (var i = 0; i < root.freehandPaths.length; i++) {
            var pts = root.freehandPaths[i].points;
            if (!pts) continue;
            for (var j = 0; j < pts.length; j++) {
                minX = Math.min(minX, pts[j].x);
                minY = Math.min(minY, pts[j].y);
                maxX = Math.max(maxX, pts[j].x);
                maxY = Math.max(maxY, pts[j].y);
                hasContent = true;
            }
        }

        // Check architecture blocks & sticky notes
        for (var k = 0; k < nodeModel.count; k++) {
            var node = nodeModel.get(k);
            minX = Math.min(minX, node.nodeX);
            minY = Math.min(minY, node.nodeY);
            maxX = Math.max(maxX, node.nodeX + (node.nodeW || 180));
            maxY = Math.max(maxY, node.nodeY + (node.nodeH || 90));
            hasContent = true;
        }

        if (!hasContent) {
            root.panX = 0;
            root.panY = 0;
            root.zoomScale = 1.0;
        } else {
            var contentW = Math.max(120, maxX - minX);
            var contentH = Math.max(120, maxY - minY);
            var midX = (minX + maxX) / 2;
            var midY = (minY + maxY) / 2;

            var padding = 90;
            var viewW = Math.max(200, root.width - padding * 2);
            var viewH = Math.max(200, root.height - padding * 2);

            var scaleX = viewW / contentW;
            var scaleY = viewH / contentH;
            var targetZoom = Math.max(0.35, Math.min(1.4, Math.min(scaleX, scaleY)));

            root.zoomScale = targetZoom;
            root.panX = (root.width / 2) - (midX * targetZoom);
            root.panY = (root.height / 2) - (midY * targetZoom);
        }

        bgCanvas.requestPaint();
        drawCanvas.requestPaint();
    }

    // Photoshop Ctrl+0 Shortcut
    Shortcut {
        sequence: "Ctrl+0"
        onActivated: root.centerAndFitView()
    }
    Shortcut {
        sequence: "Ctrl+NumPad0"
        onActivated: root.centerAndFitView()
    }

    // Convert Screen coordinates to World Canvas coordinates
    function screenToWorld(sx, sy) {
        return {
            x: (sx - root.panX) / root.zoomScale,
            y: (sy - root.panY) / root.zoomScale
        };
    }

    // Convert World Canvas coordinates to Screen coordinates
    function worldToScreen(wx, wy) {
        return {
            x: (wx * root.zoomScale) + root.panX,
            y: (wy * root.zoomScale) + root.panY
        };
    }

    // Erase freehand strokes & nodes near world position (wx, wy)
    function eraseAt(wx, wy) {
        var radiusInWorld = (root.eraserRadius + 6) / root.zoomScale;
        var r2 = radiusInWorld * radiusInWorld;
        var changed = false;

        // 1. Erase freehand strokes
        for (var i = root.freehandPaths.length - 1; i >= 0; i--) {
            var path = root.freehandPaths[i];
            if (!path.points) continue;

            var hit = false;
            for (var j = 0; j < path.points.length; j++) {
                var dx = path.points[j].x - wx;
                var dy = path.points[j].y - wy;
                if ((dx * dx + dy * dy) <= r2) {
                    hit = true;
                    break;
                }
            }

            if (hit) {
                root.freehandPaths.splice(i, 1);
                changed = true;
            }
        }

        // 2. Erase architecture blocks & sticky notes if touched by eraser
        for (var k = nodeModel.count - 1; k >= 0; k--) {
            var n = nodeModel.get(k);
            var nx1 = n.nodeX - radiusInWorld;
            var nx2 = n.nodeX + (n.nodeW || 180) + radiusInWorld;
            var ny1 = n.nodeY - radiusInWorld;
            var ny2 = n.nodeY + (n.nodeH || 90) + radiusInWorld;

            if (wx >= nx1 && wx <= nx2 && wy >= ny1 && wy <= ny2) {
                nodeModel.remove(k);
            }
        }

        if (changed) {
            drawCanvas.requestPaint();
        }
    }

    // 1. Infinite Blueprint Dot Grid Background
    Canvas {
        id: bgCanvas
        anchors.fill: parent
        renderTarget: Canvas.Image

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.clearRect(0, 0, width, height);

            var dotColor = theme ? theme.borderSubtle : "#282828";
            ctx.fillStyle = dotColor;

            var rawStep = 24 * root.zoomScale;
            var step = Math.max(12, rawStep);

            var offsetX = (root.panX % step + step) % step;
            var offsetY = (root.panY % step + step) % step;

            var dotRadius = Math.max(0.8, 1.2 * Math.min(1.5, root.zoomScale));

            for (var x = offsetX; x < width; x += step) {
                for (var y = offsetY; y < height; y += step) {
                    ctx.beginPath();
                    ctx.arc(x, y, dotRadius, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
        }
    }

    // 2. Freehand Drawing Canvas (Transformed by pan & zoom)
    Canvas {
        id: drawCanvas
        anchors.fill: parent
        z: 2

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.clearRect(0, 0, width, height);

            ctx.save();
            ctx.translate(root.panX, root.panY);
            ctx.scale(root.zoomScale, root.zoomScale);

            ctx.lineCap = "round";
            ctx.lineJoin = "round";

            // Draw all saved paths with their own immutable frozen colors
            for (var i = 0; i < root.freehandPaths.length; i++) {
                var p = root.freehandPaths[i];
                if (!p.points || p.points.length < 2) continue;

                ctx.strokeStyle = "" + (p.color || "#0078d4");
                ctx.lineWidth = p.width || 2.5;
                ctx.beginPath();
                ctx.moveTo(p.points[0].x, p.points[0].y);

                for (var j = 1; j < p.points.length; j++) {
                    ctx.lineTo(p.points[j].x, p.points[j].y);
                }
                ctx.stroke();
            }

            // Draw current active path while dragging
            if (root.currentPathPoints.length > 1) {
                ctx.strokeStyle = "" + root.activeColor;
                ctx.lineWidth = root.strokeWidth;
                ctx.beginPath();
                ctx.moveTo(root.currentPathPoints[0].x, root.currentPathPoints[0].y);

                for (var k = 1; k < root.currentPathPoints.length; k++) {
                    ctx.lineTo(root.currentPathPoints[k].x, root.currentPathPoints[k].y);
                }
                ctx.stroke();
            }

            ctx.restore();
        }
    }

    // Model for Architecture Boxes and Sticky Notes
    ListModel {
        id: nodeModel
    }

    // 3. World Canvas Item for Pan & Scaled Architecture Nodes (High z-index for full interactivity)
    Item {
        id: nodeContainer
        x: root.panX
        y: root.panY
        scale: root.zoomScale
        transformOrigin: Item.TopLeft
        z: 20

        Repeater {
            model: nodeModel

            delegate: Item {
                id: nodeItem
                x: model.nodeX
                y: model.nodeY
                width: model.nodeW
                height: model.nodeH
                z: 25

                Rectangle {
                    anchors.fill: parent
                    radius: model.type === "sticky" ? 2 : 6
                    color: model.type === "sticky" ? model.bgColor : (theme ? theme.bgSurface : "#252526")
                    border.color: model.type === "sticky" ? "#ffffff20" : model.borderColor
                    border.width: model.type === "sticky" ? 1 : 2

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 4

                        // Node Title Header & Move Grip
                        Rectangle {
                            Layout.fillWidth: true
                            height: 24
                            color: "transparent"

                            RowLayout {
                                anchors.fill: parent
                                spacing: 6

                                Rectangle {
                                    width: 8
                                    height: 8
                                    radius: 4
                                    color: model.borderColor
                                    visible: model.type !== "sticky"
                                }

                                TextInput {
                                    id: titleInput
                                    text: model.title
                                    color: model.type === "sticky" ? "#1e1e1e" : (theme ? theme.textBright : "#ffffff")
                                    font.pixelSize: 12
                                    font.bold: true
                                    Layout.fillWidth: true
                                    selectByMouse: true
                                    cursorVisible: activeFocus
                                    onTextChanged: nodeModel.setProperty(index, "title", text)
                                }

                                // Delete / Close Node Button
                                Rectangle {
                                    width: 20
                                    height: 20
                                    radius: 3
                                    z: 30
                                    color: nodeCloseMa.containsMouse ? "#ff000040" : "transparent"

                                    VectorIcon {
                                        anchors.centerIn: parent
                                        name: "close"
                                        size: 9
                                        color: model.type === "sticky" ? "#444444" : (theme ? theme.textMuted : "#858585")
                                    }

                                    MouseArea {
                                        id: nodeCloseMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: nodeModel.remove(index)
                                    }
                                }
                            }

                            // Header Drag Grip
                            MouseArea {
                                anchors.fill: parent
                                anchors.rightMargin: 24
                                drag.target: nodeItem
                                drag.axis: Drag.XAndYAxis
                                cursorShape: Qt.SizeAllCursor
                                acceptedButtons: Qt.LeftButton
                                z: -1

                                onPositionChanged: function(mouse) {
                                    if (drag.active) {
                                        nodeModel.setProperty(index, "nodeX", nodeItem.x);
                                        nodeModel.setProperty(index, "nodeY", nodeItem.y);
                                    }
                                }
                            }
                        }

                        // Body Content / Code Notes (Directly Editable)
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            TextEdit {
                                id: bodyInput
                                width: parent.width
                                text: model.bodyText
                                color: model.type === "sticky" ? "#2a2a2a" : (theme ? theme.textPrimary : "#cccccc")
                                font.pixelSize: 11
                                font.family: model.type === "sticky" ? (theme ? theme.fontFamilyUi : "sans-serif") : (theme ? theme.fontFamilyMono : "monospace")
                                wrapMode: TextEdit.Wrap
                                selectByMouse: true
                                cursorVisible: activeFocus
                                onTextChanged: nodeModel.setProperty(index, "bodyText", text)
                            }
                        }
                    }

                    // Eraser Tool Hit Detector (When in Eraser mode, clicking anywhere deletes this node)
                    MouseArea {
                        anchors.fill: parent
                        visible: root.activeTool === "eraser"
                        z: 50
                        cursorShape: Qt.ForbiddenCursor
                        acceptedButtons: Qt.LeftButton

                        onPressed: function(mouse) {
                            nodeModel.remove(index);
                            mouse.accepted = true;
                        }
                    }
                }
            }
        }
    }

    // 4. Main Canvas Interaction MouseArea (Drawing, Panning, Canvas Erasing)
    MouseArea {
        id: drawArea
        anchors.fill: parent
        z: 5
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton

        cursorShape: {
            if (root.activeTool === "hand" || root.isPanning) {
                return pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor;
            } else if (root.activeTool === "eraser") {
                return Qt.BlankCursor; // custom eraser circle rendered below
            } else if (root.activeTool === "pen") {
                return Qt.CrossCursor;
            } else {
                return Qt.ArrowCursor;
            }
        }

        onWheel: function(wheel) {
            var oldZoom = root.zoomScale;
            var newZoom = oldZoom;

            if (wheel.angleDelta.y > 0) {
                newZoom = Math.min(3.0, oldZoom + 0.1);
            } else {
                newZoom = Math.max(0.3, oldZoom - 0.1);
            }

            if (newZoom !== oldZoom) {
                var mouseWorldX = (wheel.x - root.panX) / oldZoom;
                var mouseWorldY = (wheel.y - root.panY) / oldZoom;

                root.panX = wheel.x - (mouseWorldX * newZoom);
                root.panY = wheel.y - (mouseWorldY * newZoom);
                root.zoomScale = newZoom;

                bgCanvas.requestPaint();
                drawCanvas.requestPaint();
            }
        }

        onPressed: function(mouse) {
            root.lastMouseX = mouse.x;
            root.lastMouseY = mouse.y;

            if (mouse.button === Qt.MiddleButton || root.activeTool === "hand") {
                root.isPanning = true;
                return;
            }

            var wPos = root.screenToWorld(mouse.x, mouse.y);

            if (root.activeTool === "pen") {
                root.currentPathPoints = [{ x: wPos.x, y: wPos.y }];
                drawCanvas.requestPaint();
            } else if (root.activeTool === "eraser") {
                root.eraseAt(wPos.x, wPos.y);
            } else if (root.activeTool === "box") {
                nodeModel.append({
                    type: "box",
                    title: "Architecture Block",
                    bodyText: "// System component & APIs\n- API Gateway\n- Data Pipeline",
                    nodeX: wPos.x - 90,
                    nodeY: wPos.y - 45,
                    nodeW: 200,
                    nodeH: 110,
                    borderColor: "" + root.activeColor,
                    bgColor: "#252526"
                });
                root.activeTool = "pen";
            } else if (root.activeTool === "sticky") {
                nodeModel.append({
                    type: "sticky",
                    title: "PLAN / TODO",
                    bodyText: "• Build feature\n• Write unit tests\n• Verify performance",
                    nodeX: wPos.x - 80,
                    nodeY: wPos.y - 50,
                    nodeW: 170,
                    nodeH: 120,
                    borderColor: "#eab308",
                    bgColor: "#fef08a"
                });
                root.activeTool = "pen";
            }
        }

        onPositionChanged: function(mouse) {
            root.eraserScreenX = mouse.x;
            root.eraserScreenY = mouse.y;

            if (root.isPanning || (pressed && (mouse.buttons & Qt.MiddleButton || root.activeTool === "hand"))) {
                var dx = mouse.x - root.lastMouseX;
                var dy = mouse.y - root.lastMouseY;
                root.panX += dx;
                root.panY += dy;
                root.lastMouseX = mouse.x;
                root.lastMouseY = mouse.y;

                bgCanvas.requestPaint();
                drawCanvas.requestPaint();
                return;
            }

            if (pressed) {
                var wPos = root.screenToWorld(mouse.x, mouse.y);
                if (root.activeTool === "pen") {
                    root.currentPathPoints.push({ x: wPos.x, y: wPos.y });
                    drawCanvas.requestPaint();
                } else if (root.activeTool === "eraser") {
                    root.eraseAt(wPos.x, wPos.y);
                }
            }
        }

        onReleased: function(mouse) {
            root.isPanning = false;

            if (root.activeTool === "pen" && root.currentPathPoints.length > 1) {
                var copyPoints = [];
                for (var i = 0; i < root.currentPathPoints.length; i++) {
                    copyPoints.push({ x: root.currentPathPoints[i].x, y: root.currentPathPoints[i].y });
                }
                // Save stroke with immutable string color
                root.freehandPaths.push({
                    color: "" + root.activeColor,
                    width: root.strokeWidth,
                    points: copyPoints
                });
                root.currentPathPoints = [];
                drawCanvas.requestPaint();
            }
        }
    }

    // 5. Visual Eraser Circle Indicator
    Rectangle {
        id: eraserIndicator
        width: root.eraserRadius * 2
        height: root.eraserRadius * 2
        radius: root.eraserRadius
        x: root.eraserScreenX - root.eraserRadius
        y: root.eraserScreenY - root.eraserRadius
        color: "#f14c4c20"
        border.color: "#f14c4c"
        border.width: 1.5
        visible: root.activeTool === "eraser" && drawArea.containsMouse
        z: 40
    }

    // 6. Floating Glassmorphism Whiteboard Toolbar
    Rectangle {
        id: toolbar
        anchors.top: parent.top
        anchors.topMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
        width: toolbarLayout.implicitWidth + 24
        height: 42
        radius: 21
        z: 50
        color: theme ? theme.bgPopup : "#252526"
        border.color: theme ? theme.borderNormal : "#333333"
        border.width: 1

        RowLayout {
            id: toolbarLayout
            anchors.centerIn: parent
            spacing: 6

            // Pan / Hand Tool
            ToolBtn {
                iconName: "hand"
                toolTip: "Hand / Pan Tool (Drag canvas)"
                isSelected: root.activeTool === "hand"
                onClicked: root.activeTool = "hand"
            }

            // Pen Tool
            ToolBtn {
                iconName: "edit"
                toolTip: "Freehand Pen"
                isSelected: root.activeTool === "pen"
                onClicked: root.activeTool = "pen"
            }

            // Architecture Box / Node Tool
            ToolBtn {
                iconName: "code"
                toolTip: "Architecture Block"
                isSelected: root.activeTool === "box"
                onClicked: root.activeTool = "box"
            }

            // Sticky Note Tool
            ToolBtn {
                iconName: "file"
                toolTip: "Sticky Plan Note"
                isSelected: root.activeTool === "sticky"
                onClicked: root.activeTool = "sticky"
            }

            // Eraser Tool
            ToolBtn {
                iconName: "eraser"
                toolTip: "Eraser (Strokes & Nodes)"
                isSelected: root.activeTool === "eraser"
                onClicked: root.activeTool = "eraser"
            }

            Rectangle { width: 1; height: 18; color: theme ? theme.borderSubtle : "#333333" }

            // Color Palette for Pen & Nodes
            Row {
                spacing: 5
                Repeater {
                    model: ["#0078d4", "#4ec9b0", "#cca700", "#f14c4c", "#a855f7", "#ffffff"]
                    delegate: Rectangle {
                        width: 18
                        height: 18
                        radius: 9
                        color: modelData
                        border.color: root.activeColor === modelData ? "#ffffff" : "transparent"
                        border.width: 2

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.activeColor = "" + modelData;
                                if (root.activeTool === "eraser" || root.activeTool === "hand") {
                                    root.activeTool = "pen";
                                }
                            }
                        }
                    }
                }
            }

            Rectangle { width: 1; height: 18; color: theme ? theme.borderSubtle : "#333333" }

            // Photoshop-like Center / Fit View (Ctrl+0)
            ToolBtn {
                iconName: "focus"
                toolTip: "Fit / Center View (Ctrl+0)"
                onClicked: root.centerAndFitView()
            }

            // Clear Whiteboard Canvas
            ToolBtn {
                iconName: "trash"
                toolTip: "Clear Canvas"
                onClicked: {
                    root.freehandPaths = [];
                    root.currentPathPoints = [];
                    nodeModel.clear();
                    drawCanvas.requestPaint();
                }
            }

            Rectangle { width: 1; height: 18; color: theme ? theme.borderSubtle : "#333333" }

            // Close Tab
            ToolBtn {
                iconName: "close"
                toolTip: "Close Whiteboard Tab"
                onClicked: root.closeRequested()
            }
        }
    }

    // 7. Bottom-Right Navigation / Zoom Badge
    Rectangle {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 14
        height: 28
        width: 175
        radius: 14
        color: theme ? theme.bgPopup : "#252526"
        border.color: theme ? theme.borderSubtle : "#333333"
        border.width: 1
        z: 50

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            spacing: 4

            Text {
                text: Math.round(root.zoomScale * 100) + "%"
                color: theme ? theme.textSecondary : "#858585"
                font.pixelSize: 10
                font.family: theme ? theme.fontFamilyMono : "monospace"
                Layout.fillWidth: true
            }

            // Center / Reset View (Ctrl+0)
            Rectangle {
                width: 20
                height: 20
                radius: 10
                color: centerMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#37373d") : "transparent"

                VectorIcon {
                    anchors.centerIn: parent
                    name: "focus"
                    size: 10
                    color: theme ? theme.textPrimary : "#cccccc"
                }

                ToolTip.visible: centerMa.containsMouse
                ToolTip.text: "Center View (Ctrl+0)"

                MouseArea {
                    id: centerMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.centerAndFitView()
                }
            }

            // Zoom In (+)
            Rectangle {
                width: 18
                height: 18
                radius: 9
                color: zoomInMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#37373d") : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "+"
                    color: theme ? theme.textBright : "#ffffff"
                    font.pixelSize: 12
                    font.bold: true
                }

                MouseArea {
                    id: zoomInMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.zoomScale = Math.min(3.0, root.zoomScale + 0.15);
                        bgCanvas.requestPaint();
                        drawCanvas.requestPaint();
                    }
                }
            }

            // Zoom Out (-)
            Rectangle {
                width: 18
                height: 18
                radius: 9
                color: zoomOutMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#37373d") : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "−"
                    color: theme ? theme.textBright : "#ffffff"
                    font.pixelSize: 12
                    font.bold: true
                }

                MouseArea {
                    id: zoomOutMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.zoomScale = Math.max(0.3, root.zoomScale - 0.15);
                        bgCanvas.requestPaint();
                        drawCanvas.requestPaint();
                    }
                }
            }
        }
    }

    // Helper Component for Toolbar Buttons
    component ToolBtn: Rectangle {
        property string iconName: ""
        property string toolTip: ""
        property bool isSelected: false
        signal clicked()

        width: 28
        height: 28
        radius: 14
        color: isSelected ? (theme ? theme.accent : "#0078d4") : (btnMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#37373d") : "transparent")

        VectorIcon {
            anchors.centerIn: parent
            name: iconName
            size: 12
            color: isSelected ? "#ffffff" : (theme ? theme.textPrimary : "#cccccc")
        }

        ToolTip.visible: btnMa.containsMouse
        ToolTip.text: toolTip

        MouseArea {
            id: btnMa
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
        }
    }
}
