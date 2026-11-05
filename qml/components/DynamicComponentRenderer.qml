import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var componentData: null
    signal actionTriggered(string componentId, string actionName, var payload)

    implicitWidth: contentLoader.item ? contentLoader.item.implicitWidth : 0
    implicitHeight: contentLoader.item ? contentLoader.item.implicitHeight : 0

    Loader {
        id: contentLoader
        anchors.fill: parent
        sourceComponent: getComponentForType(root.componentData ? root.componentData.type : "")
    }

    function getComponentForType(typeStr) {
        switch (typeStr) {
            case "row": return rowComponent;
            case "column": return colComponent;
            case "grid": return gridComponent;
            case "card": return cardComponent;
            case "box": return boxComponent;
            case "scrollview": return scrollComponent;
            case "text": return textComponent;
            case "header": return headerComponent;
            case "badge": return badgeComponent;
            case "progressbar": return progressComponent;
            case "button": return buttonComponent;
            case "iconbutton": return iconButtonComponent;
            case "textinput": return inputComponent;
            case "textarea": return textAreaComponent;
            case "checkbox": return checkboxComponent;
            case "switch": return switchComponent;
            case "select": return selectComponent;
            case "slider": return sliderComponent;
            case "colorpicker": return colorPickerComponent;
            case "image": return imageComponent;
            case "spritesheet": return spriteSheetComponent;
            case "video": return videoComponent;
            case "canvas": return canvasComponent;
            case "codeeditor": return codeEditorComponent;
            case "markdown": return markdownComponent;
            case "spacer": return spacerComponent;
            case "divider": return dividerComponent;
            default: return emptyComponent;
        }
    }

    Component { id: emptyComponent; Item {} }

    Component {
        id: childDelegateRow
        Loader {
            id: clRow
            source: "DynamicComponentRenderer.qml"
            onLoaded: {
                if (item) {
                    item.componentData = modelData;
                    item.actionTriggered.connect(function(componentId, actionName, payload) {
                        root.actionTriggered(componentId, actionName, payload);
                    });
                }
            }
            Binding {
                target: clRow.item
                property: "componentData"
                value: modelData
                when: clRow.status === Loader.Ready
            }
        }
    }

    Component {
        id: childDelegateFill
        Loader {
            id: clFill
            Layout.fillWidth: true
            source: "DynamicComponentRenderer.qml"
            onLoaded: {
                if (item) {
                    item.componentData = modelData;
                    item.actionTriggered.connect(function(componentId, actionName, payload) {
                        root.actionTriggered(componentId, actionName, payload);
                    });
                }
            }
            Binding {
                target: clFill.item
                property: "componentData"
                value: modelData
                when: clFill.status === Loader.Ready
            }
        }
    }

    // 1. ROW LAYOUT
    Component {
        id: rowComponent
        RowLayout {
            spacing: (root.componentData && root.componentData.props && root.componentData.props.spacing !== undefined) ? root.componentData.props.spacing : 8
            Repeater {
                model: (root.componentData && root.componentData.children) ? root.componentData.children : []
                delegate: childDelegateRow
            }
        }
    }

    // 2. COLUMN LAYOUT
    Component {
        id: colComponent
        ColumnLayout {
            spacing: (root.componentData && root.componentData.props && root.componentData.props.spacing !== undefined) ? root.componentData.props.spacing : 8
            Repeater {
                model: (root.componentData && root.componentData.children) ? root.componentData.children : []
                delegate: childDelegateFill
            }
        }
    }

    // 3. GRID LAYOUT
    Component {
        id: gridComponent
        GridLayout {
            columns: (root.componentData && root.componentData.props && root.componentData.props.columns) ? root.componentData.props.columns : 2
            rowSpacing: (root.componentData && root.componentData.props && root.componentData.props.spacing !== undefined) ? root.componentData.props.spacing : 8
            columnSpacing: rowSpacing
            Repeater {
                model: (root.componentData && root.componentData.children) ? root.componentData.children : []
                delegate: childDelegateFill
            }
        }
    }

    // 4. CARD CONTAINER
    Component {
        id: cardComponent
        Rectangle {
            implicitWidth: cardCol.implicitWidth + 24
            implicitHeight: cardCol.implicitHeight + 24
            radius: (root.componentData && root.componentData.props && root.componentData.props.border_radius !== undefined) ? root.componentData.props.border_radius : 6
            color: (root.componentData && root.componentData.props && root.componentData.props.background) ? root.componentData.props.background : (theme ? theme.bgSurface : "#252526")
            border.color: (root.componentData && root.componentData.props && root.componentData.props.border_color) ? root.componentData.props.border_color : (theme ? theme.borderSubtle : "#333333")
            border.width: 1

            ColumnLayout {
                id: cardCol
                anchors.fill: parent
                anchors.margins: (root.componentData && root.componentData.props && root.componentData.props.padding !== undefined) ? root.componentData.props.padding : 12
                spacing: 8

                Text {
                    text: (root.componentData && root.componentData.props) ? (root.componentData.props.title || "") : ""
                    visible: text.length > 0
                    font.bold: true
                    font.pixelSize: 13
                    color: theme ? theme.textBright : "#ffffff"
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                Text {
                    text: (root.componentData && root.componentData.props) ? (root.componentData.props.subtitle || "") : ""
                    visible: text.length > 0
                    font.pixelSize: 11
                    color: theme ? theme.textSecondary : "#858585"
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                Repeater {
                    model: (root.componentData && root.componentData.children) ? root.componentData.children : []
                    delegate: childDelegateFill
                }
            }
        }
    }

    // 5. BOX CONTAINER
    Component {
        id: boxComponent
        Rectangle {
            implicitWidth: (root.componentData && root.componentData.props && root.componentData.props.width) ? root.componentData.props.width : boxCol.implicitWidth
            implicitHeight: (root.componentData && root.componentData.props && root.componentData.props.height) ? root.componentData.props.height : boxCol.implicitHeight
            radius: (root.componentData && root.componentData.props && root.componentData.props.border_radius) ? root.componentData.props.border_radius : 0
            color: (root.componentData && root.componentData.props && root.componentData.props.background) ? root.componentData.props.background : "transparent"

            ColumnLayout {
                id: boxCol
                anchors.fill: parent
                anchors.margins: (root.componentData && root.componentData.props && root.componentData.props.padding) ? root.componentData.props.padding : 0
                spacing: 6
                Repeater {
                    model: (root.componentData && root.componentData.children) ? root.componentData.children : []
                    delegate: childDelegateFill
                }
            }
        }
    }

    // 6. SCROLLVIEW
    Component {
        id: scrollComponent
        ScrollView {
            clip: true
            implicitHeight: (root.componentData && root.componentData.props && root.componentData.props.height) ? root.componentData.props.height : 200
            ScrollBar.vertical.policy: ScrollBar.AsNeeded
            ScrollBar.horizontal.policy: (root.componentData && root.componentData.props && root.componentData.props.scroll_x) ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff

            ColumnLayout {
                width: parent.width
                spacing: 6
                Repeater {
                    model: (root.componentData && root.componentData.children) ? root.componentData.children : []
                    delegate: childDelegateFill
                }
            }
        }
    }

    // 7. TEXT
    Component {
        id: textComponent
        Text {
            text: (root.componentData && root.componentData.props) ? (root.componentData.props.text || "") : ""
            font.pixelSize: (root.componentData && root.componentData.props && root.componentData.props.size) ? root.componentData.props.size : 12
            font.bold: Boolean(root.componentData && root.componentData.props && root.componentData.props.bold)
            font.italic: Boolean(root.componentData && root.componentData.props && root.componentData.props.italic)
            color: (root.componentData && root.componentData.props && root.componentData.props.color) ? root.componentData.props.color : (theme ? theme.textPrimary : "#cccccc")
            wrapMode: (root.componentData && root.componentData.props && root.componentData.props.wrap === false) ? Text.NoWrap : Text.WordWrap
            font.family: theme ? theme.fontFamilyUi : "sans-serif"
        }
    }

    // 8. HEADER
    Component {
        id: headerComponent
        ColumnLayout {
            spacing: 2
            Text {
                text: (root.componentData && root.componentData.props) ? (root.componentData.props.title || "") : ""
                font.pixelSize: (root.componentData && root.componentData.props && root.componentData.props.size) ? root.componentData.props.size : 16
                font.bold: true
                color: theme ? theme.textBright : "#ffffff"
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
            }
            Text {
                text: (root.componentData && root.componentData.props) ? (root.componentData.props.subtitle || "") : ""
                visible: text.length > 0
                font.pixelSize: 11
                color: theme ? theme.textSecondary : "#858585"
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
            }
        }
    }

    // 9. BADGE
    Component {
        id: badgeComponent
        Rectangle {
            implicitWidth: badgeText.width + 12
            implicitHeight: 20
            radius: (root.componentData && root.componentData.props && root.componentData.props.border_radius) ? root.componentData.props.border_radius : 3
            color: (root.componentData && root.componentData.props && root.componentData.props.background) ? root.componentData.props.background : (theme ? theme.accent : "#0078d4")

            Text {
                id: badgeText
                anchors.centerIn: parent
                text: (root.componentData && root.componentData.props) ? (root.componentData.props.text || "") : ""
                font.pixelSize: 10
                font.bold: true
                color: (root.componentData && root.componentData.props && root.componentData.props.color) ? root.componentData.props.color : "#ffffff"
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
            }
        }
    }

    // 10. PROGRESS BAR
    Component {
        id: progressComponent
        ColumnLayout {
            spacing: 4
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: (root.componentData && root.componentData.props) ? (root.componentData.props.label || "") : ""
                    font.pixelSize: 11
                    color: theme ? theme.textSecondary : "#858585"
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: Math.round(((root.componentData && root.componentData.props && root.componentData.props.value) ? root.componentData.props.value : 0)) + "%"
                    font.pixelSize: 11
                    font.bold: true
                    color: theme ? theme.textBright : "#ffffff"
                }
            }
            Rectangle {
                Layout.fillWidth: true
                height: 6
                radius: 3
                color: theme ? theme.bgSurface : "#2a2a2a"

                Rectangle {
                    height: parent.height
                    radius: 3
                    width: parent.width * Math.max(0, Math.min(1.0, ((root.componentData && root.componentData.props && root.componentData.props.value) ? root.componentData.props.value : 0) / 100.0))
                    color: (root.componentData && root.componentData.props && root.componentData.props.color) ? root.componentData.props.color : (theme ? theme.accent : "#0078d4")
                }
            }
        }
    }

    // 11. BUTTON
    Component {
        id: buttonComponent
        Rectangle {
            implicitWidth: (root.componentData && root.componentData.props && root.componentData.props.width) ? root.componentData.props.width : btnRow.implicitWidth + 24
            implicitHeight: 28
            radius: 4
            property bool isPrimary: !root.componentData || !root.componentData.props || root.componentData.props.variant === "primary"
            property bool isDanger: Boolean(root.componentData && root.componentData.props && root.componentData.props.variant === "danger")

            color: isDanger
                ? (btnMa.containsMouse ? "#dc2626" : "#b91c1c")
                : (isPrimary
                    ? (btnMa.containsMouse ? (theme ? theme.accentHover : "#1084d8") : (theme ? theme.accent : "#0078d4"))
                    : (btnMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : (theme ? theme.bgSurface : "#252526")))
            border.color: (!isPrimary && !isDanger) ? (theme ? theme.borderNormal : "#383838") : "transparent"
            border.width: 1

            RowLayout {
                id: btnRow
                anchors.centerIn: parent
                spacing: 6

                VectorIcon {
                    name: (root.componentData && root.componentData.props && root.componentData.props.icon) ? root.componentData.props.icon : ""
                    size: 12
                    visible: name.length > 0
                    color: "#ffffff"
                }

                Text {
                    text: (root.componentData && root.componentData.props) ? (root.componentData.props.label || "") : ""
                    font.pixelSize: 11
                    font.bold: true
                    color: "#ffffff"
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }
            }

            MouseArea {
                id: btnMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.componentData) {
                        root.actionTriggered(root.componentData.id, "click", null)
                    }
                }
            }
        }
    }

    // 12. ICON BUTTON
    Component {
        id: iconButtonComponent
        Rectangle {
            implicitWidth: 26
            implicitHeight: 26
            radius: 4
            color: iconBtnMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

            VectorIcon {
                anchors.centerIn: parent
                name: (root.componentData && root.componentData.props && root.componentData.props.icon) ? root.componentData.props.icon : "sparkles"
                size: (root.componentData && root.componentData.props && root.componentData.props.size) ? root.componentData.props.size : 13
                color: iconBtnMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textSecondary : "#858585")
            }

            MouseArea {
                id: iconBtnMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.componentData) {
                        root.actionTriggered(root.componentData.id, "click", null)
                    }
                }
            }
        }
    }

    // 13. TEXT INPUT
    Component {
        id: inputComponent
        Rectangle {
            implicitWidth: 220
            implicitHeight: 28
            radius: 4
            color: theme ? theme.bgSurface : "#252526"
            border.color: innerInput.activeFocus ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderSubtle : "#383838")
            border.width: 1

            TextInput {
                id: innerInput
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                verticalAlignment: Text.AlignVCenter
                text: (root.componentData && root.componentData.props) ? (root.componentData.props.text || "") : ""
                echoMode: (root.componentData && root.componentData.props && root.componentData.props.password) ? TextInput.Password : TextInput.Normal
                color: theme ? theme.textBright : "#ffffff"
                font.pixelSize: 11
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                selectByMouse: true
                clip: true

                Text {
                    anchors.fill: parent
                    verticalAlignment: Text.AlignVCenter
                    text: (root.componentData && root.componentData.props) ? (root.componentData.props.placeholder || "") : ""
                    color: theme ? theme.textMuted : "#656565"
                    font.pixelSize: 11
                    font.italic: true
                    visible: !innerInput.text && !innerInput.activeFocus
                }

                onTextChanged: {
                    if (root.componentData && text !== root.componentData.props.text) {
                        root.componentData.props.text = text;
                        root.actionTriggered(root.componentData.id, "change", text);
                    }
                }

                onAccepted: {
                    if (root.componentData) {
                        root.actionTriggered(root.componentData.id, "submit", text);
                    }
                }
            }
        }
    }

    // 14. TEXT AREA
    Component {
        id: textAreaComponent
        Rectangle {
            implicitWidth: 280
            implicitHeight: Math.max(60, ((root.componentData && root.componentData.props && root.componentData.props.lines) ? root.componentData.props.lines : 4) * 18)
            radius: 4
            color: theme ? theme.bgSurface : "#252526"
            border.color: innerArea.activeFocus ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderSubtle : "#383838")
            border.width: 1

            TextArea {
                id: innerArea
                anchors.fill: parent
                anchors.margins: 6
                text: (root.componentData && root.componentData.props) ? (root.componentData.props.text || "") : ""
                color: theme ? theme.textBright : "#ffffff"
                font.pixelSize: 11
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                selectByMouse: true
                wrapMode: TextArea.Wrap

                onTextChanged: {
                    if (root.componentData && text !== root.componentData.props.text) {
                        root.componentData.props.text = text;
                        root.actionTriggered(root.componentData.id, "change", text);
                    }
                }
            }
        }
    }

    // 15. CHECKBOX
    Component {
        id: checkboxComponent
        RowLayout {
            spacing: 8
            Rectangle {
                width: 16
                height: 16
                radius: 3
                color: (root.componentData && root.componentData.props && root.componentData.props.checked) ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgSurface : "#252526")
                border.color: theme ? theme.borderNormal : "#3e3e42"
                border.width: 1

                VectorIcon {
                    anchors.centerIn: parent
                    name: "check"
                    size: 9
                    color: "#ffffff"
                    visible: Boolean(root.componentData && root.componentData.props && root.componentData.props.checked)
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.componentData && root.componentData.props) {
                            var newVal = !root.componentData.props.checked;
                            root.componentData.props.checked = newVal;
                            root.actionTriggered(root.componentData.id, "change", newVal);
                        }
                    }
                }
            }

            Text {
                text: (root.componentData && root.componentData.props) ? (root.componentData.props.label || "") : ""
                font.pixelSize: 12
                color: theme ? theme.textPrimary : "#cccccc"
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
            }
        }
    }

    // 16. SWITCH
    Component {
        id: switchComponent
        RowLayout {
            spacing: 10
            Rectangle {
                width: 32
                height: 18
                radius: 9
                color: (root.componentData && root.componentData.props && root.componentData.props.checked) ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderNormal : "#444444")

                Behavior on color { ColorAnimation { duration: 120 } }

                Rectangle {
                    width: 14
                    height: 14
                    radius: 7
                    color: "#ffffff"
                    y: 2
                    x: (root.componentData && root.componentData.props && root.componentData.props.checked) ? 16 : 2
                    Behavior on x { NumberAnimation { duration: 120 } }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.componentData && root.componentData.props) {
                            var newVal = !root.componentData.props.checked;
                            root.componentData.props.checked = newVal;
                            root.actionTriggered(root.componentData.id, "change", newVal);
                        }
                    }
                }
            }

            Text {
                text: (root.componentData && root.componentData.props) ? (root.componentData.props.label || "") : ""
                font.pixelSize: 12
                color: theme ? theme.textPrimary : "#cccccc"
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
            }
        }
    }

    // 17. SELECT / DROPDOWN
    Component {
        id: selectComponent
        RowLayout {
            spacing: 8
            Text {
                text: (root.componentData && root.componentData.props && root.componentData.props.label) ? root.componentData.props.label : ""
                font.pixelSize: 11
                color: theme ? theme.textSecondary : "#858585"
                visible: text.length > 0
            }

            ComboBox {
                model: (root.componentData && root.componentData.props && root.componentData.props.options) ? root.componentData.props.options : []
                currentIndex: Math.max(0, model.indexOf((root.componentData && root.componentData.props) ? root.componentData.props.selected : ""))
                onActivated: {
                    if (root.componentData && root.componentData.props) {
                        var val = currentText;
                        root.componentData.props.selected = val;
                        root.actionTriggered(root.componentData.id, "change", val);
                    }
                }
            }
        }
    }

    // 18. SLIDER
    Component {
        id: sliderComponent
        RowLayout {
            spacing: 8
            Text {
                text: (root.componentData && root.componentData.props && root.componentData.props.label) ? root.componentData.props.label : ""
                font.pixelSize: 11
                color: theme ? theme.textSecondary : "#858585"
                visible: text.length > 0
            }

            Slider {
                from: (root.componentData && root.componentData.props && root.componentData.props.min_value !== undefined) ? root.componentData.props.min_value : 0
                to: (root.componentData && root.componentData.props && root.componentData.props.max_value !== undefined) ? root.componentData.props.max_value : 100
                value: (root.componentData && root.componentData.props && root.componentData.props.value !== undefined) ? root.componentData.props.value : 50
                stepSize: (root.componentData && root.componentData.props && root.componentData.props.step !== undefined) ? root.componentData.props.step : 1
                onMoved: {
                    if (root.componentData && root.componentData.props) {
                        root.componentData.props.value = value;
                        root.actionTriggered(root.componentData.id, "change", value);
                    }
                }
            }

            Text {
                text: "" + Math.round(((root.componentData && root.componentData.props && root.componentData.props.value !== undefined) ? root.componentData.props.value : 0))
                font.pixelSize: 11
                font.bold: true
                color: theme ? theme.textBright : "#ffffff"
            }
        }
    }

    // 19. COLOR PICKER
    Component {
        id: colorPickerComponent
        RowLayout {
            spacing: 8
            Rectangle {
                width: 24
                height: 24
                radius: 4
                color: (root.componentData && root.componentData.props && root.componentData.props.color) ? root.componentData.props.color : "#0078d4"
                border.color: "#ffffff"
                border.width: 1
            }
            Text {
                text: (root.componentData && root.componentData.props && root.componentData.props.color) ? root.componentData.props.color : ""
                font.pixelSize: 11
                font.family: "Consolas, monospace"
                color: theme ? theme.textPrimary : "#cccccc"
            }
        }
    }

    // 20. IMAGE
    Component {
        id: imageComponent
        Image {
            source: (root.componentData && root.componentData.props && root.componentData.props.source) ? root.componentData.props.source : ""
            width: (root.componentData && root.componentData.props && root.componentData.props.width) ? root.componentData.props.width : undefined
            height: (root.componentData && root.componentData.props && root.componentData.props.height) ? root.componentData.props.height : undefined
            fillMode: Image.PreserveAspectFit
            asynchronous: true
        }
    }

    // 21. SPRITE SHEET
    Component {
        id: spriteSheetComponent
        Item {
            implicitWidth: (root.componentData && root.componentData.props && root.componentData.props.frame_width) ? root.componentData.props.frame_width : 32
            implicitHeight: (root.componentData && root.componentData.props && root.componentData.props.frame_height) ? root.componentData.props.frame_height : 32
            clip: true

            property int currentFrame: (root.componentData && root.componentData.props && root.componentData.props.current_frame) ? root.componentData.props.current_frame : 0
            property int totalFrames: (root.componentData && root.componentData.props && root.componentData.props.total_frames) ? root.componentData.props.total_frames : 1
            property int fps: (root.componentData && root.componentData.props && root.componentData.props.fps) ? root.componentData.props.fps : 12

            Image {
                source: (root.componentData && root.componentData.props && root.componentData.props.source) ? root.componentData.props.source : ""
                x: -currentFrame * parent.width
                y: 0
            }

            Timer {
                interval: Math.max(16, Math.floor(1000 / parent.fps))
                running: Boolean(root.componentData && root.componentData.props && root.componentData.props.playing)
                repeat: true
                onTriggered: {
                    parent.currentFrame = (parent.currentFrame + 1) % parent.totalFrames;
                }
            }
        }
    }

    // 22. VIDEO
    Component {
        id: videoComponent
        Rectangle {
            implicitWidth: (root.componentData && root.componentData.props && root.componentData.props.width) ? root.componentData.props.width : 320
            implicitHeight: (root.componentData && root.componentData.props && root.componentData.props.height) ? root.componentData.props.height : 180
            color: "#000000"
            radius: 4

            Text {
                anchors.centerIn: parent
                text: "🎬 Video: " + ((root.componentData && root.componentData.props) ? root.componentData.props.source : "")
                color: "#888888"
                font.pixelSize: 11
            }
        }
    }

    // 23. CANVAS
    Component {
        id: canvasComponent
        Canvas {
            implicitWidth: (root.componentData && root.componentData.props && root.componentData.props.width) ? root.componentData.props.width : 200
            implicitHeight: (root.componentData && root.componentData.props && root.componentData.props.height) ? root.componentData.props.height : 150

            onPaint: {
                var ctx = getContext("2d");
                ctx.clearRect(0, 0, width, height);
                var cmds = (root.componentData && root.componentData.props && root.componentData.props.commands) ? root.componentData.props.commands : [];
                for (var i = 0; i < cmds.length; i++) {
                    var c = cmds[i];
                    if (c.cmd === "line") {
                        ctx.strokeStyle = c.color || "#ffffff";
                        ctx.lineWidth = c.width || 1;
                        ctx.beginPath();
                        ctx.moveTo(c.x1, c.y1);
                        ctx.lineTo(c.x2, c.y2);
                        ctx.stroke();
                    } else if (c.cmd === "circle") {
                        ctx.beginPath();
                        ctx.arc(c.cx, c.cy, c.radius, 0, 2 * Math.PI);
                        if (c.fill) { ctx.fillStyle = c.fill; ctx.fill(); }
                        if (c.border) { ctx.strokeStyle = c.border; ctx.stroke(); }
                    } else if (c.cmd === "rect") {
                        if (c.fill) { ctx.fillStyle = c.fill; ctx.fillRect(c.x, c.y, c.w, c.h); }
                        if (c.border) { ctx.strokeStyle = c.border; ctx.strokeRect(c.x, c.y, c.w, c.h); }
                    } else if (c.cmd === "text") {
                        ctx.fillStyle = c.color || "#ffffff";
                        ctx.font = (c.bold ? "bold " : "") + (c.size || 12) + "px sans-serif";
                        ctx.fillText(c.text, c.x, c.y);
                    }
                }
            }
        }
    }

    // 24. CODE EDITOR
    Component {
        id: codeEditorComponent
        Rectangle {
            implicitWidth: 320
            implicitHeight: (root.componentData && root.componentData.props && root.componentData.props.height) ? root.componentData.props.height : 140
            color: theme ? theme.bgEditor : "#1e1e1e"
            radius: 4
            border.color: theme ? theme.borderNormal : "#333333"
            border.width: 1

            ScrollView {
                anchors.fill: parent
                anchors.margins: 4
                TextArea {
                    text: (root.componentData && root.componentData.props) ? (root.componentData.props.code || "") : ""
                    font.family: "Consolas, monospace"
                    font.pixelSize: 12
                    color: theme ? theme.textBright : "#ffffff"
                    readOnly: Boolean(root.componentData && root.componentData.props && root.componentData.props.read_only)
                }
            }
        }
    }

    // 25. MARKDOWN VIEWER
    Component {
        id: markdownComponent
        Text {
            text: (root.componentData && root.componentData.props) ? (root.componentData.props.content || "") : ""
            textFormat: Text.MarkdownText
            wrapMode: Text.WordWrap
            color: theme ? theme.textPrimary : "#cccccc"
            font.pixelSize: 12
            font.family: theme ? theme.fontFamilyUi : "sans-serif"
        }
    }

    // 26. SPACER
    Component {
        id: spacerComponent
        Item {
            implicitWidth: (root.componentData && root.componentData.props && root.componentData.props.size) ? root.componentData.props.size : 8
            implicitHeight: implicitWidth
            Layout.fillWidth: (!root.componentData || !root.componentData.props || root.componentData.props.size === undefined)
        }
    }

    // 27. DIVIDER
    Component {
        id: dividerComponent
        Rectangle {
            property bool isHoriz: !root.componentData || !root.componentData.props || root.componentData.props.orientation !== "vertical"
            Layout.fillWidth: isHoriz
            Layout.fillHeight: !isHoriz
            height: isHoriz ? 1 : undefined
            width: !isHoriz ? 1 : undefined
            color: (root.componentData && root.componentData.props && root.componentData.props.color) ? root.componentData.props.color : (theme ? theme.borderSubtle : "#333333")
        }
    }
}

