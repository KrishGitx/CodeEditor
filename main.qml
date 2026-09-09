import QtQuick 2.15
import QtQuick.Window
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15
import QtQuick.Dialogs

Window {
    Component.onCompleted: {
        throw new Error("QML IS RUNNING")
    }
    property string colorTheme: "transparent"
    id: mainWindow
    width: 1280
    height: 920
    visible: true
    title: qsTr("Hello World")
    flags: Qt.Window | Qt.FramelessWindowHint
    color: colorTheme
    // Place this inside your root component window scope
    Connections {
        target: backend

        function onCompletionsReceived(suggestions) {
            console.log("Opening popup at absolute position X:",
                        completionPopup.x, "Y:", completionPopup.y)
            if (!suggestions || suggestions.length === 0) {
                completionPopup.close()
                return
            }

            suggestionsModel.clear()
            for (var i = 0; i < suggestions.length; i++) {
                suggestionsModel.append({
                                            "modelData": suggestions[i]
                                        })
            }

            // 1. Grab local cursor dimensions
            let cursorRect = codeTextArea.cursorRectangle

            // 2. Map coordinates up to global viewport root
            let absolutePos = codeTextArea.mapToItem(Overlay.overlay,
                                                     cursorRect.x, cursorRect.y)
            console.log("Content height:", listView.contentHeight)
            // 3. Offset and apply positions
            completionPopup.x = absolutePos.x
            completionPopup.y = absolutePos.y + cursorRect.height + 4

            // 4. Reset selection index
            listView.currentIndex = 0

            // 5. Present popup cleanly without stripping active focus from text typing
            completionPopup.open()
        }

        function onFileOpened(path, content) {
            codeTextArea.text = content
        }

        function onExplorerContent(list, fPath) {
            explorerContent.currentPath = fPath
            explorerContent.model.clear()
            for (var x of list) {
                x.canSee = true
                explorerContent.model.append(x)
            }
        }
    }

    Connections {
        target: musicPlayer
        function onSearchResults(list) {
            songModel.clear()
            for (var x of list) {
                songModel.append(x)
            }
        }
    }

    Popup {
        id: completionPopup
        z: 9999
        // Crucial: Forces the popup to render on top of all text areas/backgrounds
        parent: Overlay.overlay

        width: 250
        height: Math.min(listView.contentHeight + 4, 200)
        padding: 1
        focus: false // Keep false so your cursor input doesn't get violently hijacked

        background: Rectangle {
            color: "#21252b"
            border.color: "#181a1f"
            border.width: 1
            radius: 4
        }

        contentItem: ListView {
            id: listView
            model: ListModel {
                id: suggestionsModel
            }
            clip: true
            currentIndex: 0

            delegate: ItemDelegate {
                width: listView.width
                height: 28
                // Use highlighted state to map selection
                highlighted: ListView.isCurrentItem

                contentItem: Text {
                    text: modelData.label
                    color: highlighted ? "#ffffff" : "#abb2bf"
                    font.pointSize: 10
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    leftPadding: 8
                }

                background: Rectangle {
                    color: highlighted ? "#2c313c" : "transparent"
                }
            }

            ScrollIndicator.vertical: ScrollIndicator {}
        }
    }

    //Main Container
    FileDialog {
        id: openFileDialog
        title: "Please choose a file"
        currentFolder: StandardPaths.writableLocation(
                           StandardPaths.DocumentsLocation)
        onAccepted: {
            console.log("Selected file: " + selectedFile)

            backend.open_file(selectedFile)
        }
        onRejected: {
            console.log("Canceled")
        }
    }

    Shortcut {
        sequence: "Ctrl+S"
        onActivated: openFileDialog.open()
    }

    FolderDialog {
        id: openWorkSpace
        title: "Please choose a folder"
        currentFolder: StandardPaths.writableLocation(
                           StandardPaths.DocumentsLocation)
        onAccepted: {

            backend.open_Workspace(selectedFolder)
        }
        onRejected: {
            console.log("Canceled")
        }
    }

    Shortcut {
        sequence: "Ctrl+O"
        onActivated: openWorkSpace.open()
    }

    Rectangle {
        width: parent.width
        height: parent.height
        color: "#aa1e1e1e"

        //Header
        Rectangle {
            id: header
            width: parent.width
            height: 20
            color: "#57697d"

            //DRAGING WINDOW
            MouseArea {
                anchors.fill: parent
                property variant clickPos: "1,1"

                onPressed: {
                    clickPos = Qt.point(mouse.x, mouse.y)
                }

                onPositionChanged: {
                    var delta = Qt.point(mouse.x - clickPos.x,
                                         mouse.y - clickPos.y)
                    var new_x = mainWindow.x + delta.x
                    var new_y = mainWindow.y + delta.y
                    if (new_y <= 0)
                        mainWindow.visibility = Window.Maximized
                    else {
                        if (mainWindow.visibility === Window.Maximized)
                            mainWindow.visibility = Window.Windowed
                        mainWindow.x = new_x
                        mainWindow.y = new_y
                    }
                }
            }

            ListView {
                id: headerContent
                width: contentWidth
                height: parent.height
                orientation: ListView.Horizontal
                interactive: false

                model: ListModel {
                    ListElement {
                        itemName: "File"
                    }
                    ListElement {
                        itemName: "Edit"
                    }
                    ListElement {
                        itemName: "Code"
                    }
                    ListElement {
                        itemName: "View"
                    }
                }

                delegate: Rectangle {
                    width: itemText.implicitWidth + 30
                    height: parent.height
                    color: colorTheme
                    Text {
                        id: itemText
                        anchors.centerIn: parent
                        text: itemName
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: parent.height
                color: colorTheme

                Text {
                    text: "X"
                    anchors.right: parent.right
                    rightPadding: 10

                    TapHandler {
                        onTapped: mainWindow.close()
                    }
                }
            }

            Rectangle {
                color: "#80899e"
                height: 1
                width: parent.width
                anchors.bottom: parent.bottom
            }
        }

        //Main Editor
        RowLayout {
            id: layout
            anchors.top: header.bottom
            anchors.bottom: parent.bottom // FIX 1: Safely locks container height inside boundaries
            width: parent.width
            spacing: 0

            // Left Sidebar
            Rectangle {
                id: leftBar
                Layout.preferredWidth: 300
                Layout.fillHeight: true
                color: "#181818" // Gave it a distinct deep gray background

                // Master column to cleanly separate Sidebar Title from File List
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    // Sidebar Section Header
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        color: colorTheme

                        Text {
                            text: "EXPLORER"
                            anchors.centerIn: parent
                            color: "#ffffff"
                            font.bold: true
                            font.pixelSize: 11
                        }

                        Rectangle {
                            color: "#80899e"
                            height: 1
                            width: parent.width
                            anchors.bottom: parent.bottom
                        }
                    }

                    // File List Layout
                    ListView {
                        id: explorerContent
                        Layout.fillWidth: true
                        property string currentPath: ""

                        Layout.fillHeight: true // Grab remaining sidebar space safely
                        clip: true
                        function isItemVisible(type, name) {

                            if (type === "Folder") {
                                for (var x = 0; x < explorerContent.model.count; x++) {
                                    if (explorerContent.model.get(
                                                x).parentId === name
                                            && explorerContent.model.get(
                                                x).canSee) {
                                        explorerContent.model.setProperty(
                                                    x, "canSee", false)
                                    } else {
                                        explorerContent.model.setProperty(
                                                    x, "canSee", true)
                                    }
                                }
                            }
                        }

                        function getPadding(index, parentId) {
                            var depth = 0

                            for (var x = index - 1; x >= 0; x--) {
                                if (explorerContent.model.get(
                                            x).name === parentId) {
                                    depth += 1 + getPadding(
                                                x, explorerContent.model.get(
                                                    x).parentId)
                                }
                            }
                            return depth
                        }

                        function openFile(index, parentId) {
                            var path = ""

                            for (var x = index - 1; x >= 0; x--) {
                                if (explorerContent.model.get(
                                            x).name === parentId) {
                                    path += openFile(
                                                x, explorerContent.model.get(
                                                    x).parentId) + explorerContent.model.get(
                                                x).name + "\\"
                                    console.log("PATHOO: ", path)
                                }
                            }
                            return path
                        }

                        model: ListModel {}

                        delegate: Rectangle {
                            width: explorerContent.width
                            height: visible ? 30 : 0
                            color: colorTheme

                            // FIX 2: Prevents default white boxes from blinding text!
                            visible: canSee
                            // Place this inside your ListView component
                            Row {
                                anchors.fill: parent
                                spacing: 8

                                // leftPadding: 15
                                leftPadding: 15 * (1 + explorerContent.getPadding(
                                                       index, parentId))

                                Image {
                                    id: fileIcon
                                    // FIX 3: Dynamic switching based on item data type
                                    source: "Icons/" + (type === "Folder" ? "folder-ico.png" : "file-ico.png")
                                    width: 16
                                    height: 16
                                    anchors.verticalCenter: parent.verticalCenter
                                    fillMode: Image.PreserveAspectFit
                                }

                                Text {
                                    id: fileText
                                    text: name
                                    color: "white"
                                    anchors.verticalCenter: parent.verticalCenter
                                    font.pixelSize: 13
                                }
                            }
                            TapHandler {
                                onTapped: {
                                    if (type === "Folder") {
                                        explorerContent.isItemVisible(type,
                                                                      name)
                                    } else {
                                        var path = explorerContent.currentPath
                                                + "\\" + explorerContent.openFile(
                                                    index, parentId) + name
                                        backend.open_file(path)
                                    }
                                }
                            }
                        }
                    }
                }

                // Sidebar Dividing Right Border
                Rectangle {
                    color: "#80899e"
                    width: 1
                    height: parent.height
                    anchors.right: parent.right
                }
            }

            //Code Area:
            // FIX 1: Change outer container to ColumnLayout so tabs stay on top of the editor
            ColumnLayout {
                id: mainEditorView
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0 // No gaps between tab bar and code area

                // --- 1. FILE TABS SECTION ---
                RowLayout {
                    Layout.fillWidth: true
                    height: 40 // Fixed tab bar height
                    spacing: 0

                    Rectangle {
                        Layout.preferredWidth: 150
                        height: 40
                        color: "#333552"

                        Text {
                            id: fileNameBar
                            text: "Main.py"
                            color: "white"
                            anchors.centerIn: parent
                        }

                        Text {
                            text: qsTr("X")
                            color: "#ff6b6b" // Subtle red for close button
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            rightPadding: 10

                            TapHandler {
                                onTapped: console.log("Close tab clicked")
                            }
                        }
                    }

                    // Spacer to push tabs to the left if needed
                    Item {
                        Layout.fillWidth: true
                    }
                }

                // --- 2. CODE EDITOR SECTION ---
                Rectangle {
                    // These tell the outer shell to fill your main window/sidebar space
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#1e1f29"

                    ScrollView {
                        id: editorScrollView
                        anchors.fill: parent
                        clip: true

                        RowLayout {
                            // CRITICAL FIX: Force the layout to match the visible window sizes!
                            width: editorScrollView.availableWidth
                            height: Math.max(editorScrollView.availableHeight,
                                             codeTextArea.implicitHeight + 30)
                            spacing: 0

                            // 1. LINE NUMBER SIDEBAR
                            Rectangle {
                                id: lineSidebar
                                Layout.preferredWidth: 40 // Fixed structural width for numbers
                                Layout.fillHeight: true // Stretches to match RowLayout height
                                color: "#14151a"

                                ListView {
                                    id: lineNumbersList
                                    anchors.fill: parent
                                    interactive: false
                                    clip: true
                                    model: codeTextArea.lineCount

                                    header: Item {
                                        width: parent.width
                                        height: codeTextArea.topPadding // Matches the text area's top gap perfectly
                                    }

                                    delegate: Text {

                                        width: lineSidebar.width
                                        height: (codeTextArea.implicitHeight
                                                 - codeTextArea.topPadding
                                                 - codeTextArea.bottomPadding)
                                                / codeTextArea.lineCount
                                        text: index + 1
                                        color: "#6272a4"
                                        font.family: codeTextArea.font.family
                                        font.pixelSize: codeTextArea.font.pixelSize
                                        horizontalAlignment: Text.AlignHCenter
                                    }

                                    contentY: codeTextArea.contentY
                                }
                            }
                            // 2. CODE TEXT AREA
                            TextArea {

                                property int fontSize: 14
                                id: codeTextArea

                                Rectangle {
                                    width: 1
                                    height: parent.height
                                    x: codeTextArea.leftPadding
                                    y: -codeTextArea.contentY
                                }

                                Layout.fillWidth: true // Forces text area to claim all remaining width
                                Layout.fillHeight: true // Forces text area to claim full vertical height

                                font.family: "Courier"
                                font.pixelSize: fontSize
                                background: Rectangle {
                                    color: "#1e1f29" // Your dark editor background color
                                    border.color: "#333552" // (Optional) Adds a subtle border ring around the text area
                                    border.width: 1
                                }
                                tabStopDistance: fontSize * 2

                                selectByMouse: true
                                wrapMode: TextArea.NoWrap
                                //bottomPadding: 15
                                leftPadding: 15
                                topPadding: 15

                                Component.onCompleted: {
                                    backend.register_text_area(codeTextArea)
                                }

                                WheelHandler {
                                    id: zoomhandler
                                    acceptedModifiers: Qt.ControlModifier

                                    onWheel: wheel => {
                                                 if (wheel.angleDelta.y < 0) {
                                                     if (codeTextArea.fontSize > 6) {
                                                         codeTextArea.fontSize -= 1
                                                     }
                                                 } else if (wheel.angleDelta.y > 0) {
                                                     if (codeTextArea.fontSize < 40) {
                                                         codeTextArea.fontSize += 1
                                                     }
                                                 }
                                             }
                                }
                                Timer {
                                    id: completionTimer
                                    interval: 150
                                    repeat: false

                                    onTriggered: {
                                        let textUpToCursor = codeTextArea.text.substring(
                                                0, codeTextArea.cursorPosition)

                                        let linesArray = textUpToCursor.split(
                                                "\n")

                                        backend.request_completion(
                                                    "C:/Users/amazi/OneDrive/Documents/DGX/test.py",
                                                    linesArray.length - 1,
                                                    linesArray[linesArray.length - 1].length,
                                                    codeTextArea.text)
                                    }
                                }

                                onTextChanged: {
                                    backend.notify_change(
                                                "C:/Users/amazi/OneDrive/Documents/DGX/test.py",
                                                codeTextArea.text)

                                    let textUpToCursor = codeTextArea.text.substring(
                                            0, codeTextArea.cursorPosition)

                                    let linesArray = textUpToCursor.split("\n")
                                    let calculatedLine = linesArray.length - 1
                                    let calculatedChar = linesArray[linesArray.length - 1].length
                                }
                                //Auto Compli
                                Keys.onPressed: function (event) {

                                    if (/^[a-zA-Z0-9_]$/.test(event.text)) {
                                        completionTimer.restart()
                                    }

                                    if (completionPopup.visible) {
                                        if (event.key === Qt.Key_Down) {
                                            if (listView.currentIndex < listView.count - 1) {
                                                listView.currentIndex++
                                            }
                                            event.accepted = true
                                            return
                                        }
                                        if (event.key === Qt.Key_Up) {
                                            if (listView.currentIndex > 0) {
                                                listView.currentIndex--
                                            }
                                            event.accepted = true
                                            return
                                        }

                                        if (completionPopup.visible
                                                && (event.key === Qt.Key_Return
                                                    || event.key === Qt.Key_Enter
                                                    || event.key === Qt.Key_Tab)) {

                                            event.accepted = true
                                            let chosenItem = suggestionsModel.get(
                                                    listView.currentIndex).modelData.insertText

                                            let pos = codeTextArea.cursorPosition

                                            let before = codeTextArea.text.substring(
                                                    0, pos)
                                            let match = before.match(
                                                    /[a-zA-Z0-9_]+$/)

                                            if (match) {
                                                let currentWord = match[0]

                                                let startPos = pos - currentWord.length

                                                codeTextArea.remove(
                                                            startPos,
                                                            startPos + currentWord.length)
                                                if (suggestionsModel.get(
                                                            listView.currentIndex).modelData.type
                                                        == 3) {
                                                    chosenItem += "()"
                                                }

                                                codeTextArea.insert(startPos,
                                                                    chosenItem)

                                                if (chosenItem.endsWith("()")) {
                                                    codeTextArea.cursorPosition
                                                            = startPos + chosenItem.length - 1
                                                } else {
                                                    codeTextArea.cursorPosition = startPos
                                                            + chosenItem.length
                                                }
                                            } else {
                                                if (suggestionsModel.get(
                                                            listView.currentIndex).modelData.type
                                                        == 3) {
                                                    chosenItem += "()"
                                                }
                                                codeTextArea.insert(
                                                            codeTextArea.cursorPosition,
                                                            chosenItem)
                                                if (chosenItem.endsWith("()")) {
                                                    codeTextArea.cursorPosition
                                                            = pos + chosenItem.length - 1
                                                } else {
                                                    codeTextArea.cursorPosition = pos
                                                            + chosenItem.length
                                                }
                                            }
                                            completionPopup.close()
                                            return
                                        }
                                        if (event.key === Qt.Key_Escape
                                                || event.key == Qt.Key_Space) {
                                            console.log("A")
                                            completionPopup.close()
                                            event.accepted = true
                                            return
                                        }
                                    }

                                    if (event.key === Qt.Key_Return
                                            || event.key === Qt.Key_Enter) {
                                        let pos = codeTextArea.cursorPosition

                                        if (pos > 0) {
                                            let lastChar = codeTextArea.text.charAt(
                                                    pos - 1)

                                            if (lastChar === '{'
                                                    || lastChar === ':') {
                                                // Stop standard enter behavior
                                                event.accepted = true

                                                // 1. Insert a literal newline and a raw hardware tab character (\t)
                                                codeTextArea.insert(pos, "\n\t")

                                                // 2. Explicitly advance the cursor by 2 positions (1 for \n, 1 for \t)
                                                codeTextArea.cursorPosition = pos + 2
                                                return
                                            }
                                        }
                                    }
                                    if (event.text === "{") {
                                        let pos = codeTextArea.cursorPosition

                                        // 1. Insert both braces together
                                        codeTextArea.insert(pos, "{}")

                                        // 2. Put the cursor right in the middle of them
                                        codeTextArea.cursorPosition = pos + 1

                                        // 3. Accept the event so QML doesn't type an extra duplicate "{"
                                        event.accepted = true
                                    } else if (event.text === "(") {
                                        let pos = codeTextArea.cursorPosition

                                        // 1. Insert both braces together
                                        codeTextArea.insert(pos, "()")

                                        // 2. Put the cursor right in the middle of them
                                        codeTextArea.cursorPosition = pos + 1

                                        // 3. Accept the event so QML doesn't type an extra duplicate "{"
                                        event.accepted = true
                                    } else if (event.text === "[") {
                                        let pos = codeTextArea.cursorPosition

                                        // 1. Insert both braces together
                                        codeTextArea.insert(pos, "[]")

                                        // 2. Put the cursor right in the middle of them
                                        codeTextArea.cursorPosition = pos + 1

                                        // 3. Accept the event so QML doesn't type an extra duplicate "{"
                                        event.accepted = true
                                    } else if (event.text === "'") {
                                        let pos = codeTextArea.cursorPosition

                                        // 1. Insert both braces together
                                        codeTextArea.insert(pos, "''")

                                        // 2. Put the cursor right in the middle of them
                                        codeTextArea.cursorPosition = pos + 1

                                        // 3. Accept the event so QML doesn't type an extra duplicate "{"
                                        event.accepted = true
                                    } else if (event.text === '"') {
                                        let pos = codeTextArea.cursorPosition

                                        // 1. Insert both braces together
                                        codeTextArea.insert(pos, '""')

                                        // 2. Put the cursor right in the middle of them
                                        codeTextArea.cursorPosition = pos + 1

                                        // 3. Accept the event so QML doesn't type an extra duplicate "{"
                                        event.accepted = true
                                    }

                                    if (event.text === ".") {
                                        console.log("Dot keyed! Synchronizing engine states...")

                                        // 1. Calculate target position (adding 1 accounts for the dot about to be typed)
                                        let textUpToCursor = codeTextArea.text.substring(
                                                0, codeTextArea.cursorPosition)
                                        let linesArray = textUpToCursor.split(
                                                "\n")
                                        let calculatedLine = linesArray.length - 1
                                        let calculatedChar = linesArray[linesArray.length
                                                                        - 1].length + 1

                                        // 2. We use a zero-interval runtime worker layout trick to break the execution
                                        // thread out of the keyboard event loop. This ensures notify_change runs FIRST.
                                        var delayObject = Qt.createQmlObject(
                                                    "import QtQml 2.0; Timer { interval: 10; repeat: false; }",
                                                    codeTextArea)
                                        delayObject.triggered.connect(
                                                    function () {
                                                        backend.request_completion(
                                                                    "C:/Users/amazi/OneDrive/Documents/DGX/test.py",
                                                                    calculatedLine,
                                                                    calculatedChar,
                                                                    codeTextArea.text)
                                                        delayObject.destroy()
                                                    })
                                        delayObject.start()
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.preferredWidth: 150
                Layout.fillHeight: true
                color: "#242c47"

                ColumnLayout {
                    anchors.fill: parent
                    Layout.alignment: Qt.AlignTop
                    spacing: 15
                    Rectangle {
                        color: "white"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 550
                        Text {
                            text: "fgsdfd"
                        }
                    }
                    Rectangle {
                        color: "gray"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 350

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 5
                            Layout.alignment: Qt.AlignTop
                            TextField {
                                id: searchField
                                Layout.fillWidth: true
                                Layout.preferredHeight: 40

                                placeholderText: "Search music..."

                                onAccepted: {
                                    musicPlayer.search_music(text)
                                }
                            }
                            Dial {
                                Layout.preferredWidth :50
                                Layout.preferredHeight:50
                                from: 0
                                to: 1

                                onValueChanged: {
                                    musicPlayer.volume_change(value)
                                }
                            }

                            ListView {
                                id: songResults

                                Layout.fillWidth: true
                                Layout.preferredHeight: 250

                                clip: true

                                model: ListModel
                                {
                                    id:songModel
                                }

                                delegate: Rectangle {
                                    width: songResults.width
                                    height: 20

                                    Text {
                                        text: title
                                    }

                                    TapHandler
                                    {
                                        onTapped:
                                        {
                                            console.log("Playing:", title,videoId)
                                            musicPlayer.play_song(videoId)
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
}
