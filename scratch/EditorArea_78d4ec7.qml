import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15

Rectangle {
    id: editorAreaRoot
    color: theme.bgEditor

    signal fileContentModified(string filePath, string content)
    signal requestRadialMenu(real posX, real posY)
    signal saveAsRequested()
    signal cursorPositionChanged(int line, int col)
    signal openWorkspaceRequested()
    signal openFileRequested()

    property string currentFilePath: ""
    property string currentFileName: ""
    property bool welcomeVisible: openTabsModel.count === 0
    property bool suppressEditorChange: false
    property bool completionTriggeredByDot: false
    property bool isModified: false
    property int editorFontSize: theme.editorFontSize || 14
    property bool findBarVisible: false

    // Expose text property and textarea directly
    property alias text: codeTextArea.text
    property alias textAreaItem: codeTextArea

    // ─── Multi-Tab Model ───
    ListModel {
        id: openTabsModel
        // Start like a real IDE: no file is open until the user opens one.
    }
    property int activeTabIndex: 0

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ═══════════════════════════════════════════════════════════════
        // 1. Multi-File Tab Bar
        // ═══════════════════════════════════════════════════════════════
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            color: theme.bgHeader

            RowLayout {
                anchors.fill: parent
                spacing: 0

                // Scrollable tab list
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                    ScrollBar.vertical.policy: ScrollBar.AlwaysOff
                    clip: true

                    Row {
                        height: 34
                        spacing: 1

                        Repeater {
                            model: openTabsModel

                            delegate: Rectangle {
                                id: tabDelegate
                                height: 34
                                width: Math.min(220, Math.max(112, tabDelegateTitle.implicitWidth + 52))
                                color: (editorAreaRoot.activeTabIndex === index) ? theme.tabActiveBg : (tabMouse.containsMouse ? theme.tabHoverBg : theme.tabInactiveBg)

                                Behavior on color { ColorAnimation { duration: theme.animFast } }

                                // Active top accent line
                                Rectangle {
                                    width: parent.width
                                    height: 1
                                    color: (editorAreaRoot.activeTabIndex === index) ? theme.accentColor : "transparent"
                                    anchors.top: parent.top
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 9
                                    anchors.rightMargin: 7
                                    spacing: 6

                                    // File type icon
                                    Text {
                                        text: getTabFileIcon(model.fileName)
                                        font.pixelSize: 11
                                        color: (editorAreaRoot.activeTabIndex === index) ? theme.accentColor : theme.textMuted
                                    }

                                    // Tab Title
                                    Text {
                                        id: tabDelegateTitle
                                        text: model.fileName
                                        color: (editorAreaRoot.activeTabIndex === index) ? theme.textPrimary : theme.textSecondary
                                        font.pixelSize: 11
                                        font.family: theme.uiFont
                                        font.bold: (editorAreaRoot.activeTabIndex === index)
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }

                                    // Unsaved modified indicator dot
                                    Rectangle {
                                        width: 7
                                        height: 7
                                        radius: 3.5
                                        color: theme.accentWarning
                                        visible: model.isModified
                                    }

                                    // Close Tab Button
                                    Rectangle {
                                        width: 18
                                        height: 18
                                        radius: 3
                                        color: closeTabMouse.containsMouse ? theme.bgHover : "transparent"

                                        Text {
                                            text: "✕"
                                            color: closeTabMouse.containsMouse ? theme.accentError : theme.textMuted
                                            font.pixelSize: 9
                                            anchors.centerIn: parent
                                        }

                                        MouseArea {
                                            id: closeTabMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                editorAreaRoot.closeTab(index)
                                            }
                                        }
                                    }
                                }

                                // Click to select tab
                                MouseArea {
                                    id: tabMouse
                                    anchors.fill: parent
                                    anchors.rightMargin: 24
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        editorAreaRoot.switchToTab(index)
                                    }
                                }

                            }
                        }

                        // Add new blank tab button
                        Rectangle {
                            width: 28
                        height: 26
                        radius: 3
                            anchors.verticalCenter: parent.verticalCenter
                            color: newTabMouse.containsMouse ? theme.bgHover : "transparent"

                            Text {
                                text: "+"
                                color: theme.textSecondary
                                font.pixelSize: 14
                                font.bold: true
                                anchors.centerIn: parent
                            }

                            MouseArea {
                                id: newTabMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: editorAreaRoot.newBlankTab()
                            }
                        }
                    }
                }
            }

            // Tab Bar Bottom Divider
            Rectangle {
                color: theme.borderSubtle
                height: 1
                width: parent.width
                anchors.bottom: parent.bottom
            }
        }

        // ═══════════════════════════════════════════════════════════════
        // 2. Inline Find & Replace Bar (Ctrl+F)
        // ═══════════════════════════════════════════════════════════════
        Rectangle {
            id: findReplaceBar
            Layout.fillWidth: true
            Layout.preferredHeight: findBarVisible ? 36 : 0
            visible: findBarVisible
            color: theme.bgCard
            clip: true

            Behavior on Layout.preferredHeight {
                NumberAnimation { duration: theme.animFast; easing.type: Easing.OutCubic }
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                Text {
                    text: "🔍"
                    font.pixelSize: 11
                }

                TextField {
                    id: findInput
                    placeholderText: "Find in file..."
                    placeholderTextColor: theme.textMuted
                    color: theme.textPrimary
                    font.family: theme.monoFont
                    font.pixelSize: 11
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 26
                    selectByMouse: true
                    background: Rectangle {
                        color: theme.bgInput
                        border.color: findInput.activeFocus ? theme.accentColor : theme.borderSubtle
                        radius: 4
                    }
                    onTextChanged: editorAreaRoot.executeFind(findInput.text, true)
                    onAccepted: editorAreaRoot.executeFindNext()
                }

                TextField {
                    id: replaceInput
                    placeholderText: "Replace with..."
                    placeholderTextColor: theme.textMuted
                    color: theme.textPrimary
                    font.family: theme.monoFont
                    font.pixelSize: 11
                    Layout.preferredWidth: 180
                    Layout.preferredHeight: 26
                    selectByMouse: true
                    background: Rectangle {
                        color: theme.bgInput
                        border.color: replaceInput.activeFocus ? theme.accentColor : theme.borderSubtle
                        radius: 4
                    }
                    onAccepted: editorAreaRoot.executeReplace()
                }

                // Match count badge
                Text {
                    id: matchCountLabel
                    text: editorAreaRoot.findMatchCount > 0 ? (editorAreaRoot.currentMatchIdx + 1) + "/" + editorAreaRoot.findMatchCount : (findInput.text.length > 0 ? "No match" : "")
                    color: editorAreaRoot.findMatchCount > 0 ? theme.accentColor : theme.textMuted
                    font.pixelSize: 10
                    font.family: theme.monoFont
                }

                // Prev Match Button
                Rectangle {
                    width: 22
                    height: 22
                    radius: 3
                    color: prevFindMouse.containsMouse ? theme.bgHover : "transparent"
                    Text { text: "▲"; color: theme.textSecondary; font.pixelSize: 9; anchors.centerIn: parent }
                    MouseArea {
                        id: prevFindMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: editorAreaRoot.executeFindPrev()
                    }
                }

                // Next Match Button
                Rectangle {
                    width: 22
                    height: 22
                    radius: 3
                    color: nextFindMouse.containsMouse ? theme.bgHover : "transparent"
                    Text { text: "▼"; color: theme.textSecondary; font.pixelSize: 9; anchors.centerIn: parent }
                    MouseArea {
                        id: nextFindMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: editorAreaRoot.executeFindNext()
                    }
                }

                // Replace Single Button
                Button {
                    text: "Replace"
                    Layout.preferredHeight: 24
                    onClicked: editorAreaRoot.executeReplace()
                    background: Rectangle {
                        color: parent.hovered ? theme.bgHover : theme.bgInput
                        border.color: theme.borderSubtle
                        radius: 3
                    }
                    contentItem: Text {
                        text: parent.text
                        color: theme.textPrimary
                        font.pixelSize: 10
                        font.family: theme.uiFont
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                // Replace All Button
                Button {
                    text: "Replace All"
                    Layout.preferredHeight: 24
                    onClicked: editorAreaRoot.executeReplaceAll()
                    background: Rectangle {
                        color: parent.hovered ? theme.bgHover : theme.bgInput
                        border.color: theme.borderSubtle
                        radius: 3
                    }
                    contentItem: Text {
                        text: parent.text
                        color: theme.textPrimary
                        font.pixelSize: 10
                        font.family: theme.uiFont
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Item { Layout.fillWidth: true }

                // Close Find Bar
                Rectangle {
                    width: 22
                    height: 22
                    radius: 3
                    color: closeFindMouse.containsMouse ? theme.bgHover : "transparent"
                    Text { text: "✕"; color: theme.textSecondary; font.pixelSize: 10; anchors.centerIn: parent }
                    MouseArea {
                        id: closeFindMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: editorAreaRoot.toggleFindBar()
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

        // ═══════════════════════════════════════════════════════════════
        // ═══════════════════════════════════════════════════════════════
        // 3. Editor Body (Gutter + TextArea + Optional Minimap)
        // ═══════════════════════════════════════════════════════════════
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: theme.bgEditor

            RowLayout {
                anchors.fill: parent
                spacing: 0

                // ────────────────────────────────────────────────────────
                // Line-number gutter
                // ────────────────────────────────────────────────────────
                Rectangle {
                    id: lineSidebar

                    Layout.preferredWidth: Math.max(
                        48,
                        (codeTextArea.lineCount.toString().length * 10) + 24
                    )
                    Layout.fillHeight: true
                    color: theme.gutterBg
                    clip: true

                    Item {


                        id: lineNumbersContent


                        anchors.left: parent.left


                        anchors.right: parent.right


                        y: -editorFlickable.contentY


                        height: codeTextArea.contentHeight


                        clip: false



                        // Use the editor's own content coordinates instead of a separate


                        // ListView. This keeps numbering locked to the text while scrolling,


                        // including when new lines are added at the bottom.


                        Item {


                            x: 0


                            y: 0


                            width: parent.width


                            height: codeTextArea.contentHeight



                            Repeater {


                                model: Math.max(1, codeTextArea.lineCount)



                                delegate: Text {


                                    width: lineNumbersContent.width - 10


                                    height: fontMetrics.height


                                    y: codeTextArea.topPadding + (index * fontMetrics.height)


                                    text: index + 1


                                    color: index === codeTextArea.currentLineIndex


                                           ? theme.accentColor


                                           : theme.gutterText


                                    font.family: theme.monoFont


                                    font.pixelSize: editorAreaRoot.editorFontSize


                                    font.bold: index === codeTextArea.currentLineIndex


                                    horizontalAlignment: Text.AlignRight


                                    verticalAlignment: Text.AlignVCenter


                                }


                            }


                        }



                    }



                    FontMetrics {
                        id: fontMetrics
                        font.family: theme.monoFont
                        font.pixelSize: editorAreaRoot.editorFontSize
                    }

                    // Intentionally no divider here.
                    // The editor should read as one clean surface.
                }

                // ────────────────────────────────────────────────────────
                // Real scrollable editor
                // ────────────────────────────────────────────────────────
                Flickable {
                    id: editorFlickable

                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    clip: true
                    interactive: true
                    boundsBehavior: Flickable.StopAtBounds

                    contentWidth: width
                    contentHeight: Math.max(
                        height,
                        codeTextArea.height
                    )

                    ScrollBar.vertical: ScrollBar {
                        id: vScrollBar
                        policy: editorFlickable.contentHeight > editorFlickable.height
                                ? ScrollBar.AsNeeded
                                : ScrollBar.AlwaysOff

                        contentItem: Rectangle {
                            implicitWidth: 7
                            radius: 3.5
                            color: theme.scrollThumb
                        }
                    }

                    ScrollBar.horizontal: ScrollBar {
                        policy: editorFlickable.contentWidth > editorFlickable.width
                                ? ScrollBar.AsNeeded
                                : ScrollBar.AlwaysOff

                        contentItem: Rectangle {
                            implicitHeight: 7
                            radius: 3.5
                            color: theme.scrollThumb
                        }
                    }

                    TextArea {
                        id: codeTextArea

                        x: 0
                        y: 0
                        width: editorFlickable.width

                        // The TextArea itself becomes as tall as its text.
                        // This gives the Flickable real content to scroll.
                        height: Math.max(
                            editorFlickable.height,
                            contentHeight + topPadding + bottomPadding
                        )

                        font.family: theme.monoFont
                        font.pixelSize: editorAreaRoot.editorFontSize

                        color: theme.textPrimary
                        selectionColor: theme.selectionBg
                        selectedTextColor: theme.textPrimary

                        background: Rectangle {
                            color: "transparent"
                        }

                        tabStopDistance: editorAreaRoot.editorFontSize * 4
                        selectByMouse: true

                        wrapMode: theme.wordWrap
                                   ? TextArea.Wrap
                                   : TextArea.NoWrap

                        leftPadding: 16
                        rightPadding: 16
                        topPadding: 12
                        bottomPadding: 40

                        property int currentLineIndex: 0

                        Rectangle {
                            id: activeLineHighlight

                            x: 0
                            width: parent.width
                            height: fontMetrics.height

                            y: codeTextArea.topPadding
                               + (codeTextArea.currentLineIndex
                                  * fontMetrics.height)

                            color: theme.currentLineBg
                            visible: codeTextArea.activeFocus
                            z: -1
                        }

                        Component.onCompleted: {
                            backend.register_text_area(codeTextArea)
                            codeTextArea.text = ""
                        }

                        onCursorPositionChanged: {
                            let textUpToCursor =
                                codeTextArea.text.substring(
                                    0,
                                    codeTextArea.cursorPosition
                                )

                            let lines = textUpToCursor.split("\n")

                            codeTextArea.currentLineIndex =
                                lines.length - 1

                            let col =
                                lines[lines.length - 1].length + 1

                            editorAreaRoot.cursorPositionChanged(
                                lines.length,
                                col
                            )
                        }

                        // Normal mouse wheel scrolling.
                        // This bypasses TextArea's own wheel handling.
                        WheelHandler {
                            id: editorWheelHandler
                            acceptedModifiers: Qt.NoModifier

                            onWheel: wheel => {
                                let delta = wheel.angleDelta.y

                                let maxY = Math.max(
                                    0,
                                    editorFlickable.contentHeight
                                    - editorFlickable.height
                                )

                                editorFlickable.contentY =
                                    Math.max(
                                        0,
                                        Math.min(
                                            maxY,
                                            editorFlickable.contentY
                                            - delta * 0.5
                                        )
                                    )

                                wheel.accepted = true
                            }
                        }

                        // Ctrl + wheel = editor zoom.
                        WheelHandler {
                            id: editorZoomHandler
                            acceptedModifiers: Qt.ControlModifier

                            onWheel: wheel => {
                                if (wheel.angleDelta.y < 0) {
                                    if (editorAreaRoot.editorFontSize > 9)
                                        editorAreaRoot.editorFontSize -= 1
                                } else if (wheel.angleDelta.y > 0) {
                                    if (editorAreaRoot.editorFontSize < 36)
                                        editorAreaRoot.editorFontSize += 1
                                }

                                wheel.accepted = true
                            }
                        }

                        onTextChanged: {
                            if (editorAreaRoot.suppressEditorChange)
                                return

                            if (
                                editorAreaRoot.activeTabIndex >= 0 &&
                                editorAreaRoot.activeTabIndex <
                                openTabsModel.count
                            ) {
                                openTabsModel.setProperty(
                                    editorAreaRoot.activeTabIndex,
                                    "content",
                                    codeTextArea.text
                                )

                                openTabsModel.setProperty(
                                    editorAreaRoot.activeTabIndex,
                                    "isModified",
                                    true
                                )

                                editorAreaRoot.isModified = true

                                if (
                                    editorAreaRoot.currentFilePath.length > 0
                                ) {
                                    backend.notify_change(
                                        editorAreaRoot.currentFilePath,
                                        codeTextArea.text
                                    )
                                }
                            }
                        }

                        Timer {
                            id: completionTimer
                            interval: 180
                            repeat: false

                            onTriggered: {
                                if (
                                    editorAreaRoot.suppressEditorChange ||
                                    !codeTextArea.activeFocus ||
                                    editorAreaRoot.currentFilePath.length === 0
                                )
                                    return

                                let textUpToCursor =
                                    codeTextArea.text.substring(
                                        0,
                                        codeTextArea.cursorPosition
                                    )

                                let linesArray =
                                    textUpToCursor.split("\n")

                                let currentLine =
                                    linesArray[linesArray.length - 1]

                                if (
                                    !editorAreaRoot.completionTriggeredByDot &&
                                    !/[a-zA-Z0-9_]$/.test(currentLine)
                                )
                                    return

                                backend.request_completion(
                                    editorAreaRoot.currentFilePath,
                                    linesArray.length - 1,
                                    currentLine.length,
                                    codeTextArea.text
                                )
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.RightButton
                            propagateComposedEvents: true

                            onClicked: mouse => {
                                if (mouse.button === Qt.RightButton) {
                                    editorAreaRoot.requestRadialMenu(
                                        mouse.x + lineSidebar.width,
                                        mouse.y + 36
                                    )
                                }
                            }
                        }

                        Keys.onPressed: function(event) {
                            // Save As: handle this at the TextArea because
                            // it receives the key event before main.qml Shortcut.
                            if (event.key === Qt.Key_S &&
                                (event.modifiers & Qt.ControlModifier) &&
                                (event.modifiers & Qt.ShiftModifier)) {
                                console.log("DGX SAVE AS: emitting saveAsRequested")
                                editorAreaRoot.saveAsRequested()
                                event.accepted = true
                                return
                            }

                            if (completionPopup.visible) {
                                if (event.key === Qt.Key_Down) {
                                    listView.currentIndex =
                                        Math.min(
                                            listView.currentIndex + 1,
                                            listView.count - 1
                                        )
                                    event.accepted = true
                                    return
                                }

                                if (event.key === Qt.Key_Up) {
                                    listView.currentIndex =
                                        Math.max(
                                            listView.currentIndex - 1,
                                            0
                                        )
                                    event.accepted = true
                                    return
                                }

                                if (
                                    event.key === Qt.Key_Return ||
                                    event.key === Qt.Key_Enter ||
                                    event.key === Qt.Key_Tab
                                ) {
                                    if (listView.count > 0) {
                                        editorAreaRoot.acceptCompletion(
                                            listView.currentIndex
                                        )
                                        event.accepted = true
                                        return
                                    }
                                }

                                if (event.key === Qt.Key_Escape) {
                                    completionPopup.close()
                                    event.accepted = true
                                    return
                                }
                            }

                            if (/^[a-zA-Z0-9_]$/.test(event.text)) {
                                editorAreaRoot.completionTriggeredByDot = false
                                completionTimer.restart()
                            } else if (event.text === ".") {
                                editorAreaRoot.completionTriggeredByDot = true
                                completionTimer.restart()
                            } else if (
                                event.text &&
                                !event.text.match(/^[\s]$/)
                            ) {
                                completionPopup.close()
                            }

                            // Language-aware indentation. Keep the current
                            // line's indentation on Enter, then add one level
                            // when the line opens a block.
                            if (
                                event.key === Qt.Key_Return ||
                                event.key === Qt.Key_Enter
                            ) {
                                let pos = codeTextArea.cursorPosition
                                let beforeCursor = codeTextArea.text.substring(0, pos)
                                let lineStart = beforeCursor.lastIndexOf("\n") + 1
                                let currentLine = beforeCursor.substring(lineStart)
                                let indentMatch = currentLine.match(/^[ \t]*/)
                                let indent = indentMatch ? indentMatch[0] : ""

                                // Normalize tabs in indentation to 4 spaces.
                                indent = indent.replace(/\t/g, "    ")

                                let contentOnly = currentLine.substring(
                                    indentMatch ? indentMatch[0].length : 0
                                )
                                let trimmed = contentOnly.replace(/\s+$/, "")
                                let extraIndent = ""
                                let path = editorAreaRoot.currentFilePath.toLowerCase()

                                // Python blocks use ':'; brace languages use '{'.
                                if (path.endsWith(".py") || path.endsWith(".pyw")) {
                                    if (trimmed.endsWith(":"))
                                        extraIndent = "    "
                                } else if (trimmed.endsWith("{")) {
                                    extraIndent = "    "
                                }

                                event.accepted = true
                                codeTextArea.insert(
                                    pos,
                                    "\n" + indent + extraIndent
                                )
                                codeTextArea.cursorPosition =
                                    pos + 1 + indent.length + extraIndent.length
                                return
                            }

                            // Always use spaces for editor indentation. At the
                            // start of a line, move to the next 4-space stop;
                            // elsewhere insert one indentation level.
                            if (event.key === Qt.Key_Tab) {
                                event.accepted = true
                                let pos = codeTextArea.cursorPosition
                                let beforeCursor = codeTextArea.text.substring(0, pos)
                                let lineStart = beforeCursor.lastIndexOf("\n") + 1
                                let currentLine = beforeCursor.substring(lineStart)
                                let leading = currentLine.match(/^[ \t]*/)[0]

                                if (leading.length === currentLine.length) {
                                    let spaces = leading.replace(/\t/g, "    ").length
                                    let nextStop = 4 - (spaces % 4)
                                    if (nextStop === 0) nextStop = 4
                                    codeTextArea.insert(pos, " ".repeat(nextStop))
                                    codeTextArea.cursorPosition = pos + nextStop
                                } else {
                                    codeTextArea.insert(pos, "    ")
                                    codeTextArea.cursorPosition = pos + 4
                                }
                                return
                            }

                            if (theme.bracketMatching) {
                                const pairs = {
                                    "{": "{}",
                                    "(": "()",
                                    "[": "[]",
                                    "'": "''",
                                    '"': '""'
                                }

                                if (pairs[event.text]) {
                                    let pos =
                                        codeTextArea.cursorPosition

                                    codeTextArea.insert(
                                        pos,
                                        pairs[event.text]
                                    )

                                    codeTextArea.cursorPosition =
                                        pos + 1

                                    event.accepted = true
                                    return
                                }
                            }
                        }
                    }
                }

                // ────────────────────────────────────────────────────────
                // Optional minimap
                // ────────────────────────────────────────────────────────
                Rectangle {
                    Layout.preferredWidth:
                        theme.minimapVisible ? 64 : 0

                    Layout.fillHeight: true
                    visible: theme.minimapVisible
                    color: theme.gutterBg

                    Text {
                        anchors.fill: parent
                        anchors.margins: 4
                        text: codeTextArea.text
                        color: theme.textMuted
                        font.family: theme.monoFont
                        font.pixelSize: 3
                        wrapMode: Text.NoWrap
                        clip: true
                    }

                    // No extra divider — keep the workspace visually quiet.
                }
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // 4. Welcome / No-File State
    // ═══════════════════════════════════════════════════════════════
    Rectangle {
        id: welcomePage
        anchors.fill: parent
        visible: openTabsModel.count === 0
        z: 50
        color: theme.bgEditor

        Column {
            anchors.centerIn: parent
            width: Math.min(520, parent.width - 48)
            spacing: 18

            Text {
                text: "DGX Studio"
                color: theme.textPrimary
                font.family: theme.uiFont
                font.pixelSize: 30
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                width: parent.width
            }

            Text {
                text: "Open a folder or a file to start coding."
                color: theme.textSecondary
                font.family: theme.uiFont
                font.pixelSize: 13
                horizontalAlignment: Text.AlignHCenter
                width: parent.width
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 10

                Button {
                    text: "Open Folder"
                    onClicked: editorAreaRoot.openWorkspaceRequested()
                }

                Button {
                    text: "New File"
                    onClicked: editorAreaRoot.newBlankTab()
                }
            }

            Text {
                text: "Ctrl+Shift+O  Open Folder     •     Ctrl+O  Open File     •     Ctrl+N  New File"
                color: theme.textMuted
                font.family: theme.monoFont
                font.pixelSize: 10
                horizontalAlignment: Text.AlignHCenter
                width: parent.width
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // 4. Autocomplete Popup
    // ═══════════════════════════════════════════════════════════════
    Popup {
        id: completionPopup
        z: 9999
        parent: Overlay.overlay
        width: 280
        height: Math.min(listView.contentHeight + 8, 220)
        padding: 4
        focus: false

        background: Rectangle {
            color: theme.bgCard
            border.color: theme.borderSubtle
            border.width: 1
            radius: 6
        }

        contentItem: ListView {
            id: listView
            model: ListModel { id: suggestionsModel }
            clip: true
            currentIndex: 0

            delegate: Rectangle {
                width: listView.width
                height: 26
                radius: 4
                color: (listView.currentIndex === index) ? theme.bgHover : "transparent"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 6

                    Text {
                        text: (modelData.type === 3) ? "λ" : "▪"
                        color: (modelData.type === 3) ? theme.accentSecondary : theme.accentColor
                        font.pixelSize: 11
                        font.bold: true
                    }

                    Text {
                        text: modelData.label
                        color: (listView.currentIndex === index) ? theme.textPrimary : theme.textSecondary
                        font.pixelSize: 11
                        font.family: theme.monoFont
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        listView.currentIndex = index
                        let itemData = suggestionsModel.get(index).modelData
                        let chosenItem = itemData.insertText || itemData.label
                        let pos = codeTextArea.cursorPosition
                        let before = codeTextArea.text.substring(0, pos)
                        let match = before.match(/[a-zA-Z0-9_]+$/)
                        if (match) {
                            let startPos = pos - match[0].length
                            codeTextArea.remove(startPos, pos)
                            codeTextArea.insert(startPos, chosenItem)
                            codeTextArea.cursorPosition = startPos + chosenItem.length
                        } else {
                            codeTextArea.insert(pos, chosenItem)
                            codeTextArea.cursorPosition = pos + chosenItem.length
                        }
                        completionPopup.close()
                    }
                }
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // 5. Helper Methods & Tab Management
    // ═══════════════════════════════════════════════════════════════
    property var findMatchPositions: []
    property int findMatchCount: 0
    property int currentMatchIdx: 0

    function toggleFindBar() {
        findBarVisible = !findBarVisible
        if (findBarVisible) {
            findInput.forceActiveFocus()
            if (codeTextArea.selectedText.length > 0) {
                findInput.text = codeTextArea.selectedText
            }
        } else {
            codeTextArea.forceActiveFocus()
        }
    }

    function executeFind(query, selectFirst) {
        findMatchPositions = []
        findMatchCount = 0
        currentMatchIdx = 0
        if (!query || query.length === 0) return

        var src = codeTextArea.text
        var pos = src.indexOf(query, 0)
        while (pos !== -1) {
            findMatchPositions.push(pos)
            pos = src.indexOf(query, pos + query.length)
        }
        findMatchCount = findMatchPositions.length
        if (findMatchCount > 0 && selectFirst) {
            codeTextArea.select(findMatchPositions[0], findMatchPositions[0] + query.length)
            codeTextArea.cursorPosition = findMatchPositions[0] + query.length
        }
    }

    function executeFindNext() {
        if (findMatchCount === 0) return
        currentMatchIdx = (currentMatchIdx + 1) % findMatchCount
        var p = findMatchPositions[currentMatchIdx]
        codeTextArea.select(p, p + findInput.text.length)
        codeTextArea.cursorPosition = p + findInput.text.length
    }

    function executeFindPrev() {
        if (findMatchCount === 0) return
        currentMatchIdx = (currentMatchIdx - 1 + findMatchCount) % findMatchCount
        var p = findMatchPositions[currentMatchIdx]
        codeTextArea.select(p, p + findInput.text.length)
        codeTextArea.cursorPosition = p + findInput.text.length
    }

    function executeReplace() {
        if (findMatchCount === 0) return
        var q = findInput.text
        var repl = replaceInput.text
        if (codeTextArea.selectedText === q) {
            var st = codeTextArea.selectionStart
            codeTextArea.remove(st, codeTextArea.selectionEnd)
            codeTextArea.insert(st, repl)
            executeFind(q, false)
            executeFindNext()
        } else {
            executeFindNext()
        }
    }

    function executeReplaceAll() {
        var q = findInput.text
        var repl = replaceInput.text
        if (!q || q.length === 0) return
        codeTextArea.text = codeTextArea.text.split(q).join(repl)
        executeFind(q, false)
    }

    function acceptCompletion(index) {
        if (index < 0 || index >= suggestionsModel.count) return
        var itemData = suggestionsModel.get(index).modelData
        var chosenItem = itemData.insertText || itemData.label || ""
        if (!chosenItem) return

        var pos = codeTextArea.cursorPosition
        var before = codeTextArea.text.substring(0, pos)
        var match = before.match(/[a-zA-Z0-9_]+$/)
        var startPos = match ? pos - match[0].length : pos

        if (itemData.type === 3 && !chosenItem.endsWith("()"))
            chosenItem += "()"

        editorAreaRoot.suppressEditorChange = true
        codeTextArea.remove(startPos, pos)
        codeTextArea.insert(startPos, chosenItem)
        codeTextArea.cursorPosition = chosenItem.endsWith("()") ? startPos + chosenItem.length - 1 : startPos + chosenItem.length
        editorAreaRoot.suppressEditorChange = false
        completionPopup.close()
        codeTextArea.forceActiveFocus()
    }

    function localCompletions(prefix) {
        var words = [
            // Python built-ins
            "print", "input", "len", "range", "str", "int", "float",
            "bool", "list", "dict", "set", "tuple", "open", "enumerate",
            "zip", "map", "filter", "sum", "min", "max", "abs", "round",
            "sorted", "reversed", "type", "isinstance", "super", "self",
            // Python keywords / common constructs
            "def", "class", "import", "from", "as", "return", "if", "elif",
            "else", "for", "while", "in", "is", "not", "and", "or",
            "try", "except", "finally", "with", "lambda", "yield",
            "async", "await", "True", "False", "None"
        ]

        var result = []
        var p = String(prefix || "").toLowerCase()

        if (!p)
            return result

        for (var i = 0; i < words.length; i++) {
            if (words[i].toLowerCase().indexOf(p) === 0)
                result.push({
                    label: words[i],
                    insertText: words[i],
                    type: 0
                })
        }

        return result
    }

    function showCompletions(suggestions) {
        if (editorAreaRoot.currentFilePath.length === 0) {
            completionPopup.close()
            return
        }

        if (!suggestions)
            suggestions = []

        var before = codeTextArea.text.substring(0, codeTextArea.cursorPosition)
        var currentLine = before.substring(before.lastIndexOf("\n") + 1)
        var match = currentLine.match(/[a-zA-Z0-9_]+$/)
        var prefix = match ? match[0].toLowerCase() : ""

        var mergedSuggestions = []
        var seenLabels = {}

        var local = localCompletions(prefix)
        for (var li = 0; li < local.length; li++) {
            var localLabel = String(local[li].label)
            seenLabels[localLabel.toLowerCase()] = true
            mergedSuggestions.push(local[li])
        }

        for (var si = 0; si < suggestions.length; si++) {
            var serverItem = suggestions[si]
            var serverLabel = String(serverItem.label || serverItem.insertText || "")
            var key = serverLabel.toLowerCase()
            if (!key || seenLabels[key])
                continue
            seenLabels[key] = true
            mergedSuggestions.push(serverItem)
        }

        if (mergedSuggestions.length === 0) {
            completionPopup.close()
            return
        }

        suggestionsModel.clear()
        for (var i = 0; i < mergedSuggestions.length; i++) {
            var item = mergedSuggestions[i]
            var label = String(item.label || item.insertText || "")
            var insertText = String(item.insertText || label)
            if (prefix.length > 0 && !label.toLowerCase().startsWith(prefix) && !insertText.toLowerCase().startsWith(prefix))
                continue
            suggestionsModel.append({ modelData: item })
            if (suggestionsModel.count >= 12) break
        }

        if (suggestionsModel.count === 0) {
            completionPopup.close()
            return
        }

        var cursorRect = codeTextArea.cursorRectangle
        var overlay = Overlay.overlay
        var absolutePos = codeTextArea.mapToItem(overlay, cursorRect.x, cursorRect.y)
        completionPopup.x = Math.max(8, Math.min(absolutePos.x, mainWindow.width - completionPopup.width - 8))
        completionPopup.y = Math.max(8, absolutePos.y + cursorRect.height + 4)
        listView.currentIndex = 0
        completionPopup.open()
    }

    function loadFile(filePath, content) {
        var fName = filePath.split("/").pop().split("\\").pop()

        // Check if tab is already open
        for (var i = 0; i < openTabsModel.count; i++) {
            if (openTabsModel.get(i).filePath === filePath) {
                switchToTab(i)
                return
            }
        }

        // Add new tab
        openTabsModel.append({
            filePath: filePath,
            fileName: fName,
            content: content,
            isModified: false,
            cursorPos: 0
        })

        switchToTab(openTabsModel.count - 1)
    }

    function switchToTab(index) {
        if (index < 0 || index >= openTabsModel.count) return
        activeTabIndex = index
        var tab = openTabsModel.get(index)
        completionPopup.close()
        completionTimer.stop()
        editorAreaRoot.suppressEditorChange = true
        editorAreaRoot.currentFilePath = tab.filePath
        editorAreaRoot.currentFileName = tab.fileName
        codeTextArea.text = tab.content
        codeTextArea.cursorPosition = Math.min(tab.cursorPos || 0, codeTextArea.length)
        editorAreaRoot.isModified = tab.isModified
        editorAreaRoot.suppressEditorChange = false
    }

    function closeTab(index) {
        if (openTabsModel.count <= 1) {
            openTabsModel.clear()
            activeTabIndex = -1
            currentFilePath = ""
            currentFileName = ""
            isModified = false
            suppressEditorChange = true
            codeTextArea.clear()
            suppressEditorChange = false
            completionPopup.close()
            return
        }

        openTabsModel.remove(index)
        if (activeTabIndex >= openTabsModel.count) {
            switchToTab(openTabsModel.count - 1)
        } else {
            switchToTab(activeTabIndex)
        }
    }

    function newBlankTab() {
        var count = openTabsModel.count + 1
        openTabsModel.append({
            filePath: "untitled_" + count + ".py",
            fileName: "untitled_" + count + ".py",
            content: "",
            isModified: false,
            cursorPos: 0
        })
        switchToTab(openTabsModel.count - 1)
    }

    function saveCurrentFile() {
        if (editorAreaRoot.currentFilePath.length === 0) return
        backend.save_file(editorAreaRoot.currentFilePath, codeTextArea.text)
        if (activeTabIndex >= 0 && activeTabIndex < openTabsModel.count) {
            openTabsModel.setProperty(activeTabIndex, "isModified", false)
        }
        editorAreaRoot.isModified = false
    }

    // Called by the Save As dialog in main.qml after the user chooses a path.
    function saveAsCurrentFile(filePath) {
        if (!filePath || String(filePath).length === 0) return false

        var newPath = String(filePath)
        if (newPath.indexOf("file:///") === 0) {
            newPath = newPath.substring(8)
            newPath = decodeURIComponent(newPath)
            // On Windows, file:///C:/... becomes /C:/... in QML.
            if (newPath.length >= 3 && newPath.charAt(0) === "/" && newPath.charAt(2) === ":")
                newPath = newPath.substring(1)
        }

        var parts = newPath.replace(/\\/g, "/").split("/")
        var newName = parts[parts.length - 1] || "untitled.py"

        backend.save_file(newPath, codeTextArea.text)

        editorAreaRoot.currentFilePath = newPath
        editorAreaRoot.currentFileName = newName

        if (activeTabIndex >= 0 && activeTabIndex < openTabsModel.count) {
            openTabsModel.setProperty(activeTabIndex, "filePath", newPath)
            openTabsModel.setProperty(activeTabIndex, "fileName", newName)
            openTabsModel.setProperty(activeTabIndex, "content", codeTextArea.text)
            openTabsModel.setProperty(activeTabIndex, "isModified", false)
        }

        editorAreaRoot.isModified = false
        return true
    }

    function getTabFileIcon(fileName) {
        var ext = fileName.split(".").pop().toLowerCase()
        switch (ext) {
            case "py": return "🐍"
            case "js": case "ts": case "jsx": case "tsx": return "📜"
            case "cpp": case "c": case "h": case "hpp": return "⚙️"
            case "html": case "htm": return "🌐"
            case "css": case "scss": return "🎨"
            case "json": case "yaml": case "yml": case "toml": return "📋"
            case "md": return "📝"
            case "qml": return "💠"
            case "rs": return "🦀"
            case "go": return "🔷"
            case "sql": return "🗄️"
            default: return "📄"
        }
    }
}
