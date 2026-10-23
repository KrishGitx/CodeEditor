import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property bool isOpen: false
    property var installContext: null

    property string toolName: ""
    property string toolType: "tool"
    property string titleText: "Smart Install Developer Tool"
    property string executableName: ""
    property string descriptionText: ""
    property string diagnosisText: ""
    property string explanationText: ""
    property string proposedCommand: ""
    property var proposedSteps: []
    property string verifyCommand: ""
    property string sourceKind: "ai" // "ai", "built_in_recipe", "ai_unavailable"
    property string resolutionType: "single_command" // "single_command", "complex_setup", "cannot_resolve"
    property string retryAction: ""
    property string targetFilePath: ""
    property string targetLanguageId: ""
    property string failureReason: ""

    // Explicit states: "ready", "analyzing", "single_command", "complex_setup", "cannot_resolve", "ai_unavailable", "installing", "post_install_analyzing", "fix_available", "manual_installation_required", "retrying", "retry_failed", "success", "failed"
    property string dialogState: "ready"
    property bool isInstalling: false
    property string statusMessage: ""
    property string installLogs: ""

    // Post-install verification & AI fix state properties
    property string suggestedFixCommand: ""
    property string suggestedFixReason: ""
    property int fixAttemptCount: 0
    property bool installationSucceeded: false
    property bool verificationSucceeded: false
    property bool originalRetrySucceeded: false
    property string originalRetryError: ""

    signal confirmed(string toolName, string command, string executable, string retryAction, string filePath, string verifyCommand)
    signal cancelled()
    signal retryRequested(string action, string filePath, string langId)

    anchors.fill: parent
    color: "#a0000000"
    visible: isOpen
    z: 9999

    function setDialogState(newState) {
        var oldState = root.dialogState;
        if (oldState !== newState) {
            root.dialogState = newState;
            console.log("[SmartInstall] Dialog state transition: " + oldState + " -> " + newState);
        }
    }

    function reportRetryResult(success, errorMessage) {
        if (root.dialogState !== "retrying" && root.dialogState !== "installing" && root.dialogState !== "success") return;
        if (success) {
            root.originalRetrySucceeded = true;
            root.setDialogState("success");
            root.statusMessage = (root.toolName || "Tool") + " installed, verified, and operation completed successfully.";
            if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.report_retry_result) {
                extensionManager.report_retry_result(root.toolName, true, "");
            }
        } else {
            root.originalRetrySucceeded = false;
            root.originalRetryError = errorMessage || "Original operation failed.";
            root.statusMessage = "Operation failed: " + root.originalRetryError + "\nDiagnosing runtime compatibility...";
            root.setDialogState("analyzing");
            if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.diagnose_operation_failure) {
                extensionManager.diagnose_operation_failure(
                    root.toolName,
                    root.originalRetryError,
                    root.retryAction,
                    root.targetFilePath,
                    root.targetLanguageId
                );
            } else if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.report_retry_result) {
                extensionManager.report_retry_result(root.toolName, false, root.originalRetryError, root.retryAction, root.targetFilePath, root.targetLanguageId);
            } else {
                root.setDialogState("retry_failed");
            }
        }
    }

    // Consume all clicks so background isn't clicked through
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        onClicked: {}
    }

    Connections {
        target: typeof extensionManager !== "undefined" ? extensionManager : null
        ignoreUnknownSignals: true

        function onSmartInstallAnalysisStarted(name) {
            root.setDialogState("analyzing");
            root.statusMessage = "AI is investigating the failure and available environment...";
        }

        function onSmartInstallResolved(proposal) {
            if (!proposal) return;
            root.toolName = proposal.toolName || root.toolName;
            root.toolType = proposal.toolType || root.toolType;
            root.titleText = proposal.title || ("Install " + root.toolName);
            root.executableName = proposal.executable || root.executableName;
            root.descriptionText = proposal.description || proposal.explanation || "";
            root.diagnosisText = proposal.diagnosis || "";
            root.explanationText = proposal.explanation || proposal.description || "";
            root.proposedCommand = proposal.command || "";
            root.proposedSteps = proposal.steps || [];
            root.verifyCommand = proposal.verifyCommand || "";
            root.sourceKind = proposal.source || "ai";
            root.resolutionType = proposal.resolutionType || "single_command";
            root.retryAction = proposal.retryAction || root.retryAction;
            root.targetFilePath = proposal.filePath || root.targetFilePath;
            root.targetLanguageId = proposal.languageId || root.targetLanguageId;
            root.isInstalling = false;

            if (root.sourceKind === "ai_unavailable") {
                root.failureReason = root.explanationText || "AI provider unavailable";
                root.setDialogState("ai_unavailable");
            } else if (root.resolutionType === "cannot_resolve") {
                root.setDialogState("cannot_resolve");
            } else if (root.resolutionType === "complex_setup") {
                root.setDialogState("complex_setup");
            } else if (root.resolutionType === "single_command") {
                root.setDialogState("single_command");
            } else {
                root.setDialogState(root.proposedCommand ? "single_command" : "cannot_resolve");
            }

            console.log("[SmartInstall] Resolution received");
            console.log("[SmartInstall] Source:", root.sourceKind);
            console.log("[SmartInstall] Resolution type:", root.resolutionType);
            console.log("[SmartInstall] Command availability:", (root.proposedCommand && root.proposedCommand.length > 0));
        }

        function onSmartInstallAnalysisFailed(name, reason) {
            root.sourceKind = "ai_unavailable";
            root.failureReason = reason || "AI provider request failed";
            root.setDialogState("ai_unavailable");
        }

        function onSmartInstallProgress(name, status, msg) {
            if (name === root.toolName || !root.toolName || root.isInstalling) {
                root.isInstalling = (status === "installing" || status === "post_install_analyzing");
                if (status === "installing") {
                    root.setDialogState("installing");
                } else if (status === "post_install_analyzing") {
                    root.setDialogState("post_install_analyzing");
                }
                root.statusMessage = msg;
                root.installLogs += (msg + "\n");
            }
        }

        function onSmartInstallPostInstallVerified(name, status, msg, retryAct, fp, lang) {
            root.isInstalling = false;
            root.statusMessage = msg;
            root.installLogs += (msg + "\n");

            if (status === "success") {
                root.installationSucceeded = true;
                root.verificationSucceeded = true;
                root.setDialogState("retrying");
                var act = root.retryAction || retryAct;
                var targetFp = root.targetFilePath || fp;
                var targetLang = root.targetLanguageId || lang;
                root.retryRequested(act, targetFp, targetLang);
            } else if (status === "fix_available") {
                root.setDialogState("fix_available");
            } else if (status === "manual_installation_required") {
                root.setDialogState("manual_installation_required");
            } else {
                root.setDialogState("failed");
            }
        }

        function onSmartInstallFixProposed(name, fixCmd, fixExp, retryAct, fp, vCmd, attemptCount) {
            root.suggestedFixCommand = fixCmd;
            root.suggestedFixReason = fixExp || "AI identified a corrective action for the reported error.";
            root.fixAttemptCount = attemptCount || 1;
            root.setDialogState("fix_available");
        }

        function onSmartInstallCompleted(name, success, msg, retryAct) {
            root.isInstalling = false;
            root.statusMessage = msg;
            root.installLogs += (msg + "\n");

            if (success) {
                if (root.dialogState !== "retrying" && root.dialogState !== "success") {
                    root.setDialogState("retrying");
                    var act = root.retryAction || retryAct;
                    var fp = root.targetFilePath;
                    var lang = root.targetLanguageId;
                    root.retryRequested(act, fp, lang);
                }
            } else {
                if (root.dialogState !== "fix_available" && root.dialogState !== "manual_installation_required") {
                    root.setDialogState("failed");
                }
            }
        }
    }

    Rectangle {
        id: modalCard
        width: Math.min(580, parent.width - 32)
        height: Math.min(460, parent.height - 48)
        anchors.centerIn: parent
        radius: 8
        color: theme ? theme.bgSurface : "#1e1e1e"
        border.color: theme ? theme.borderNormal : "#333333"
        border.width: 1
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            // =================================================================
            // 1. Header Row
            // =================================================================
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: 34
                    height: 34
                    radius: 17
                    color: {
                        if (root.dialogState === "success") return "#10b98125";
                        if (root.dialogState === "failed" || root.dialogState === "ai_unavailable") return "#ef444425";
                        if (root.dialogState === "cannot_resolve" || root.dialogState === "manual_installation_required" || root.dialogState === "retry_failed") return "#f59e0b25";
                        if (root.dialogState === "fix_available") return "#a855f725";
                        return (theme ? theme.accent : "#0078d4") + "25";
                    }

                    VectorIcon {
                        anchors.centerIn: parent
                        name: {
                            if (root.dialogState === "success") return "check";
                            if (root.dialogState === "failed" || root.dialogState === "ai_unavailable") return "close";
                            if (root.dialogState === "cannot_resolve" || root.dialogState === "manual_installation_required" || root.dialogState === "retry_failed") return "alert";
                            return "download";
                        }
                        size: 16
                        color: {
                            if (root.dialogState === "success") return "#10b981";
                            if (root.dialogState === "failed" || root.dialogState === "ai_unavailable") return "#ef4444";
                            if (root.dialogState === "cannot_resolve" || root.dialogState === "manual_installation_required" || root.dialogState === "retry_failed") return "#f59e0b";
                            if (root.dialogState === "fix_available") return "#a855f7";
                            return theme ? theme.accent : "#0078d4";
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: {
                            if (root.dialogState === "success") return "Installation Successful";
                            if (root.dialogState === "retry_failed") return "Tool Verified, Operation Failed";
                            if (root.dialogState === "manual_installation_required") return "Manual Installation Required";
                            if (root.dialogState === "fix_available") return "AI Suggested Fix";
                            if (root.dialogState === "post_install_analyzing") return "Verifying Installation with AI...";
                            if (root.dialogState === "retrying") return "Retrying Original Operation...";
                            if (root.dialogState === "installing") return "Installing Developer Tool...";
                            if (root.dialogState === "failed") return "Installation Failed";
                            if (root.dialogState === "ai_unavailable") return "AI Analysis Unavailable";
                            if (root.dialogState === "cannot_resolve") return "Cannot Automatically Resolve";
                            if (root.dialogState === "analyzing") return "Analyzing Issue with AI...";
                            return "Smart Install Developer Tool";
                        }
                        color: theme ? theme.textBright : "#ffffff"
                        font.pixelSize: 14
                        font.bold: true
                        font.family: theme ? theme.fontFamilyUi : "Segoe UI, sans-serif"
                    }

                    Text {
                        text: {
                            if (root.dialogState === "success") return "Tool verified and environment refreshed. Original operation completed.";
                            if (root.dialogState === "retry_failed") return "The tool was installed, but the original operation could not be completed.";
                            if (root.dialogState === "manual_installation_required") return "This installation requires manual setup or administrator privileges.";
                            if (root.dialogState === "fix_available") return "AI identified a safe corrective command for the reported error.";
                            if (root.dialogState === "post_install_analyzing") return "Inspecting execution results and tool availability.";
                            if (root.dialogState === "retrying") return "Executing original operation with refreshed environment.";
                            if (root.dialogState === "installing") return "Executing approved installation command...";
                            if (root.dialogState === "analyzing") return "AI is investigating the failure and available environment.";
                            if (root.dialogState === "ai_unavailable") return "Could not reach AI backend to generate resolution.";
                            if (root.dialogState === "failed") return "Installation or verification could not be completed.";
                            return "Automatic environment setup & dependency resolution";
                        }
                        color: theme ? theme.textMuted : "#888888"
                        font.pixelSize: 11
                        font.family: theme ? theme.fontFamilyUi : "Segoe UI, sans-serif"
                    }
                }

                // Close Button
                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: closeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                    visible: !root.isInstalling && root.dialogState !== "retrying"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "close"
                        size: 10
                        color: theme ? theme.textMuted : "#888888"
                    }

                    MouseArea {
                        id: closeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.isOpen = false;
                            root.cancelled();
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: theme ? theme.borderSubtle : "#282828"
            }

            // =================================================================
            // 2. STATE 1: READY / STATE 2: ANALYZING
            // =================================================================
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.dialogState === "ready" || root.dialogState === "analyzing"
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: readyInfoCol.implicitHeight + 20
                    radius: 6
                    color: theme ? theme.bgPanel : "#141414"
                    border.color: theme ? theme.borderSubtle : "#282828"
                    border.width: 1

                    ColumnLayout {
                        id: readyInfoCol
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        RowLayout {
                            spacing: 8
                            Text {
                                text: "Issue detected in:"
                                color: theme ? theme.textMuted : "#888888"
                                font.pixelSize: 11
                            }
                            Text {
                                text: root.toolName || (root.installContext ? root.installContext.operation : "Operation")
                                color: theme ? theme.textBright : "#ffffff"
                                font.pixelSize: 12
                                font.bold: true
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.descriptionText || (root.installContext ? (root.installContext.errorMessage || root.installContext.operation) : "Investigation ready.")
                            color: theme ? theme.textSecondary : "#aaaaaa"
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                // Analyzing indicator
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: root.dialogState === "analyzing"

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 12

                        BusyIndicator {
                            Layout.alignment: Qt.AlignHCenter
                            running: root.dialogState === "analyzing"
                            width: 36
                            height: 36
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "AI is investigating the failure context..."
                            color: theme ? theme.accent : "#38bdf8"
                            font.pixelSize: 12
                            font.bold: true
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "Inspecting environment, tools, and error output."
                            color: theme ? theme.textMuted : "#888888"
                            font.pixelSize: 11
                        }
                    }
                }

                Item { Layout.fillHeight: true; visible: root.dialogState === "ready" }
            }

            // =================================================================
            // 3. STATE 3: SINGLE COMMAND / STATE 4: COMPLEX SETUP / STATE 5 & 6
            // =================================================================
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.dialogState === "single_command" || root.dialogState === "complex_setup" || root.dialogState === "cannot_resolve" || root.dialogState === "ai_unavailable"
                spacing: 10

                // Diagnosis Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: diagCol.implicitHeight + 16
                    radius: 6
                    color: theme ? theme.bgPanel : "#141414"
                    border.color: theme ? theme.borderSubtle : "#282828"
                    border.width: 1

                    ColumnLayout {
                        id: diagCol
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text {
                                text: "Diagnosis:"
                                color: theme ? theme.textMuted : "#888888"
                                font.pixelSize: 11
                                font.bold: true
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.diagnosisText || root.titleText || "Identified dependency issue"
                                color: theme ? theme.textBright : "#ffffff"
                                font.pixelSize: 11
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }

                            // Source Badge (AI Generated or Built-in Recipe)
                            Rectangle {
                                height: 18
                                width: badgeText.implicitWidth + 12
                                radius: 9
                                color: (root.sourceKind === "ai") ? "#a855f725" : ((root.sourceKind === "built_in_recipe") ? "#0078d425" : "transparent")
                                border.color: (root.sourceKind === "ai") ? "#a855f7" : ((root.sourceKind === "built_in_recipe") ? "#0078d4" : "transparent")
                                border.width: 1
                                visible: root.sourceKind === "ai" || root.sourceKind === "built_in_recipe"

                                Text {
                                    id: badgeText
                                    anchors.centerIn: parent
                                    text: (root.sourceKind === "ai") ? "AI Generated" : "Built-in Recipe"
                                    color: (root.sourceKind === "ai") ? "#c084fc" : "#60a5fa"
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.explanationText || root.descriptionText || "Automated analysis completed."
                            color: theme ? theme.textSecondary : "#aaaaaa"
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                // Proposed Command Box (Single Command)
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.dialogState === "single_command" && root.proposedCommand.length > 0
                    spacing: 4

                    Text {
                        text: "Proposed installation command:"
                        color: theme ? theme.textSecondary : "#cccccc"
                        font.pixelSize: 11
                        font.bold: true
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 52
                        radius: 4
                        color: theme ? theme.bgInput : "#0d0d0d"
                        border.color: theme ? theme.borderNormal : "#333333"
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 8

                            Text {
                                Layout.fillWidth: true
                                text: root.proposedCommand
                                color: theme ? theme.success : "#4ade80"
                                font.pixelSize: 11
                                font.family: theme ? theme.fontFamilyMono : "Consolas, monospace"
                                wrapMode: Text.WrapAnywhere
                                elide: Text.ElideMiddle
                            }

                            Rectangle {
                                width: 26
                                height: 26
                                radius: 3
                                color: copyCmdMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                                VectorIcon {
                                    anchors.centerIn: parent
                                    name: "copy"
                                    size: 12
                                    color: theme ? theme.textSecondary : "#aaaaaa"
                                }

                                MouseArea {
                                    id: copyCmdMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (typeof extensionManager !== "undefined" && extensionManager) {
                                            extensionManager.copy_to_clipboard(root.proposedCommand);
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        visible: root.verifyCommand.length > 0
                        text: "Verification: " + root.verifyCommand
                        color: theme ? theme.textMuted : "#777777"
                        font.pixelSize: 10
                        font.family: theme ? theme.fontFamilyMono : "monospace"
                    }
                }

                // Complex Setup Steps Display
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: root.dialogState === "complex_setup"
                    spacing: 4

                    Text {
                        text: "Setup plan (multiple steps required):"
                        color: theme ? theme.textSecondary : "#cccccc"
                        font.pixelSize: 11
                        font.bold: true
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 4
                        color: theme ? theme.bgInput : "#0d0d0d"
                        border.color: theme ? theme.borderNormal : "#333333"
                        border.width: 1

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: 8
                            clip: true

                            ColumnLayout {
                                width: parent.width
                                spacing: 6

                                Repeater {
                                    model: (root.proposedSteps && root.proposedSteps.length > 0) ? root.proposedSteps : (root.proposedCommand ? root.proposedCommand.split("\n") : [])
                                    delegate: RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Rectangle {
                                            width: 18
                                            height: 18
                                            radius: 9
                                            color: (theme ? theme.accent : "#0078d4") + "30"
                                            Text {
                                                anchors.centerIn: parent
                                                text: (index + 1)
                                                color: theme ? theme.accent : "#38bdf8"
                                                font.pixelSize: 10
                                                font.bold: true
                                            }
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData
                                            color: theme ? theme.textPrimary : "#e2e8f0"
                                            font.pixelSize: 11
                                            font.family: theme ? theme.fontFamilyMono : "monospace"
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Cannot Resolve / AI Unavailable Message Box
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 4
                    color: theme ? theme.bgInput : "#0d0d0d"
                    border.color: theme ? theme.borderNormal : "#333333"
                    border.width: 1
                    visible: root.dialogState === "cannot_resolve" || root.dialogState === "ai_unavailable"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        Text {
                            Layout.fillWidth: true
                            text: (root.dialogState === "ai_unavailable") ? "AI could not analyze this issue." : "This issue cannot be automatically resolved safely."
                            color: theme ? theme.warning : "#f59e0b"
                            font.pixelSize: 12
                            font.bold: true
                        }

                        Text {
                            Layout.fillWidth: true
                            text: (root.dialogState === "ai_unavailable") ? (root.failureReason || "The configured AI service is currently unavailable or returned an unresolvable response.") : "Manual environment configuration or dependency installation is required."
                            color: theme ? theme.textSecondary : "#888888"
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }

                        Item { Layout.fillHeight: true }
                    }
                }

                Item { Layout.fillHeight: true; visible: root.dialogState === "single_command" }
            }

            // =================================================================
            // 4. STATE: FIX AVAILABLE ([FIX] <command>)
            // =================================================================
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.dialogState === "fix_available"
                spacing: 10

                Rectangle {
                    Layout.fillWidth: true
                    height: 34
                    radius: 4
                    color: "#a855f720"
                    border.color: "#a855f7"
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 8

                        VectorIcon {
                            name: "download"
                            size: 14
                            color: "#c084fc"
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "AI Diagnosed a Fixable Issue"
                            color: "#c084fc"
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Text {
                            text: "Fix attempt " + root.fixAttemptCount + " of 2"
                            color: theme ? theme.textMuted : "#888888"
                            font.pixelSize: 10
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: "AI Suggested Fix Command:"
                        color: theme ? theme.textSecondary : "#cccccc"
                        font.pixelSize: 11
                        font.bold: true
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 48
                        radius: 4
                        color: theme ? theme.bgInput : "#0d0d0d"
                        border.color: theme ? theme.borderNormal : "#333333"
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 8

                            Text {
                                Layout.fillWidth: true
                                text: root.suggestedFixCommand
                                color: "#38bdf8"
                                font.pixelSize: 11
                                font.family: theme ? theme.fontFamilyMono : "Consolas, monospace"
                                wrapMode: Text.WrapAnywhere
                                elide: Text.ElideMiddle
                            }

                            Rectangle {
                                width: 26
                                height: 26
                                radius: 3
                                color: copyFixMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                                VectorIcon {
                                    anchors.centerIn: parent
                                    name: "copy"
                                    size: 12
                                    color: theme ? theme.textSecondary : "#aaaaaa"
                                }

                                MouseArea {
                                    id: copyFixMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (typeof extensionManager !== "undefined" && extensionManager) {
                                            extensionManager.copy_to_clipboard(root.suggestedFixCommand);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Fix Reason Explanation
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 4
                    color: theme ? theme.bgPanel : "#141414"
                    border.color: theme ? theme.borderSubtle : "#282828"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6

                        Text {
                            text: "Reason for Fix:"
                            color: theme ? theme.textMuted : "#888888"
                            font.pixelSize: 11
                            font.bold: true
                        }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            Text {
                                width: parent.width
                                text: root.suggestedFixReason || "AI analyzed the real installation output and identified a safe corrective command."
                                color: theme ? theme.textSecondary : "#aaaaaa"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }
                        }

                        Text {
                            text: "Explicit approval is required. DGX will not execute fixes automatically."
                            color: theme ? theme.textMuted : "#666666"
                            font.pixelSize: 10
                            font.italic: true
                        }
                    }
                }
            }

            // =================================================================
            // 5. STATE: MANUAL INSTALLATION REQUIRED
            // =================================================================
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.dialogState === "manual_installation_required"
                spacing: 10

                Rectangle {
                    Layout.fillWidth: true
                    height: 38
                    radius: 4
                    color: "#f59e0b20"
                    border.color: "#f59e0b"
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 8

                        VectorIcon {
                            name: "alert"
                            size: 14
                            color: "#f59e0b"
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "Manual Installation Required"
                            color: "#f59e0b"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 4
                    color: theme ? theme.bgPanel : "#141414"
                    border.color: theme ? theme.borderSubtle : "#282828"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        Text {
                            text: "Why manual installation is required:"
                            color: theme ? theme.textPrimary : "#e2e8f0"
                            font.pixelSize: 11
                            font.bold: true
                        }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            Text {
                                width: parent.width
                                text: root.statusMessage || root.explanationText || "This tool requires administrator privileges, interactive installer setup, or custom system configuration that cannot be safely automated by DGX Studio."
                                color: theme ? theme.textSecondary : "#aaaaaa"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }
                        }

                        Text {
                            text: "Please follow standard installation instructions for your operating system."
                            color: theme ? theme.textMuted : "#777777"
                            font.pixelSize: 10
                        }
                    }
                }
            }

            // =================================================================
            // 6. STATE: RETRYING ORIGINAL OPERATION
            // =================================================================
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.dialogState === "retrying"
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    height: 38
                    radius: 4
                    color: "#10b98120"
                    border.color: "#10b981"
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 8

                        VectorIcon {
                            name: "check"
                            size: 14
                            color: "#10b981"
                        }

                        Text {
                            Layout.fillWidth: true
                            text: (root.toolName || "Tool") + " installed and verified successfully!"
                            color: "#10b981"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 12

                        BusyIndicator {
                            Layout.alignment: Qt.AlignHCenter
                            running: root.dialogState === "retrying"
                            width: 36
                            height: 36
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "Retrying original operation with refreshed environment..."
                            color: theme ? theme.accent : "#38bdf8"
                            font.pixelSize: 12
                            font.bold: true
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "Waiting for real execution result to verify full success."
                            color: theme ? theme.textMuted : "#888888"
                            font.pixelSize: 11
                        }
                    }
                }
            }

            // =================================================================
            // 7. STATE: RETRY FAILED (Tool installed, original op failed)
            // =================================================================
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.dialogState === "retry_failed"
                spacing: 10

                Rectangle {
                    Layout.fillWidth: true
                    height: 38
                    radius: 4
                    color: "#10b98120"
                    border.color: "#10b981"
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 8

                        VectorIcon {
                            name: "check"
                            size: 14
                            color: "#10b981"
                        }

                        Text {
                            Layout.fillWidth: true
                            text: (root.toolName || "Tool") + " was installed and verified successfully."
                            color: "#10b981"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 4
                    color: theme ? theme.bgPanel : "#141414"
                    border.color: "#f59e0b50"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        Text {
                            text: "However, the original operation failed:"
                            color: "#f59e0b"
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 4
                            color: theme ? theme.bgInput : "#0d0d0d"
                            border.color: theme ? theme.borderNormal : "#333333"
                            border.width: 1

                            ScrollView {
                                anchors.fill: parent
                                anchors.margins: 8
                                clip: true

                                Text {
                                    width: parent.width
                                    text: root.originalRetryError || "Operation could not be completed."
                                    color: theme ? theme.textSecondary : "#cccccc"
                                    font.pixelSize: 11
                                    font.family: theme ? theme.fontFamilyMono : "monospace"
                                    wrapMode: Text.WrapAnywhere
                                }
                            }
                        }

                        Text {
                            text: "This is NOT an installation failure. The tool is installed and usable."
                            color: theme ? theme.textMuted : "#777777"
                            font.pixelSize: 10
                            font.italic: true
                        }
                    }
                }
            }

            // =================================================================
            // 8. STATE: INSTALLING / POST-INSTALL ANALYZING / SUCCESS / FAILED
            // =================================================================
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.dialogState === "installing" || root.dialogState === "post_install_analyzing" || root.dialogState === "success" || root.dialogState === "failed"
                spacing: 8

                // Status banner
                Rectangle {
                    Layout.fillWidth: true
                    height: 38
                    radius: 4
                    color: {
                        if (root.dialogState === "success") return "#10b98120";
                        if (root.dialogState === "failed") return "#ef444420";
                        return (theme ? theme.accent : "#0078d4") + "20";
                    }
                    border.color: {
                        if (root.dialogState === "success") return "#10b981";
                        if (root.dialogState === "failed") return "#ef4444";
                        return theme ? theme.accent : "#0078d4";
                    }
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 8

                        VectorIcon {
                            name: (root.dialogState === "success") ? "check" : ((root.dialogState === "failed") ? "close" : "download")
                            size: 14
                            color: (root.dialogState === "success") ? "#10b981" : ((root.dialogState === "failed") ? "#ef4444" : (theme ? theme.accent : "#0078d4"))
                        }

                        Text {
                            Layout.fillWidth: true
                            text: {
                                if (root.dialogState === "success") return "Installation, verification & operation completed successfully!";
                                if (root.dialogState === "post_install_analyzing") return "AI is inspecting real execution results...";
                                if (root.dialogState === "failed") return "Installation or Verification Failed.";
                                return "Executing approved setup...";
                            }
                            color: (root.dialogState === "success") ? "#10b981" : ((root.dialogState === "failed") ? "#ef4444" : (theme ? theme.textBright : "#ffffff"))
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }
                }

                // Live output logs
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 4
                    color: theme ? theme.bgPanel : "#121212"
                    border.color: theme ? theme.borderSubtle : "#252525"
                    border.width: 1

                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 8
                        clip: true

                        Text {
                            width: parent.width
                            text: root.installLogs || root.statusMessage || "Starting installation process..."
                            color: theme ? theme.textSecondary : "#aaaaaa"
                            font.pixelSize: 10
                            font.family: theme ? theme.fontFamilyMono : "monospace"
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }
            }

            // =================================================================
            // 9. Actions Footer
            // =================================================================
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Item { Layout.fillWidth: true }

                // Secondary Button (Cancel / Close)
                Rectangle {
                    width: 80
                    height: 28
                    radius: 3
                    color: cancelMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                    border.color: theme ? theme.borderNormal : "#333333"
                    border.width: 1
                    enabled: !root.isInstalling && root.dialogState !== "retrying" && root.dialogState !== "post_install_analyzing"
                    visible: root.dialogState !== "success" && root.dialogState !== "retry_failed"

                    Text {
                        anchors.centerIn: parent
                        text: (root.dialogState === "cannot_resolve" || root.dialogState === "ai_unavailable" || root.dialogState === "manual_installation_required") ? "Close" : "Cancel"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 11
                    }

                    MouseArea {
                        id: cancelMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.isOpen = false;
                            root.cancelled();
                        }
                    }
                }

                // Analyze with AI Button (shown in 'ready' state)
                Rectangle {
                    width: 120
                    height: 28
                    radius: 3
                    color: analyzeMa.containsMouse ? (theme ? theme.accentHover : "#006cbd") : (theme ? theme.accent : "#0078d4")
                    visible: root.dialogState === "ready"

                    Text {
                        anchors.centerIn: parent
                        text: "Analyze with AI"
                        color: "#ffffff"
                        font.pixelSize: 11
                        font.bold: true
                    }

                    MouseArea {
                        id: analyzeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.setDialogState("analyzing");
                            if (typeof extensionManager !== "undefined" && extensionManager && root.installContext) {
                                extensionManager.start_smart_install_analysis(root.installContext);
                            }
                        }
                    }
                }

                // Run AI Suggested Fix Button (shown in 'fix_available' state)
                Rectangle {
                    width: 100
                    height: 28
                    radius: 3
                    color: runFixMa.containsMouse ? "#9333ea" : "#a855f7"
                    visible: root.dialogState === "fix_available" && root.suggestedFixCommand.length > 0

                    Row {
                        anchors.centerIn: parent
                        spacing: 6

                        VectorIcon {
                            anchors.verticalCenter: parent.verticalCenter
                            name: "download"
                            size: 11
                            color: "#ffffff"
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Run Fix"
                            color: "#ffffff"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: runFixMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            console.log("[SmartInstall] User approved AI fix");
                            root.isInstalling = true;
                            root.setDialogState("installing");
                            root.installLogs += ("Executing AI suggested fix: " + root.suggestedFixCommand + "\n");
                            if (typeof extensionManager !== "undefined" && extensionManager) {
                                extensionManager.execute_smart_install_fix(
                                    root.toolName,
                                    root.suggestedFixCommand,
                                    root.executableName,
                                    root.retryAction,
                                    root.targetFilePath,
                                    root.verifyCommand,
                                    root.fixAttemptCount
                                );
                            }
                        }
                    }
                }

                // Retry Operation Button (shown in 'retry_failed' state)
                Rectangle {
                    width: 120
                    height: 28
                    radius: 3
                    color: retryOpMa.containsMouse ? (theme ? theme.accentHover : "#006cbd") : (theme ? theme.accent : "#0078d4")
                    visible: root.dialogState === "retry_failed"

                    Text {
                        anchors.centerIn: parent
                        text: "Retry Operation"
                        color: "#ffffff"
                        font.pixelSize: 11
                        font.bold: true
                    }

                    MouseArea {
                        id: retryOpMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.setDialogState("retrying");
                            root.retryRequested(root.retryAction, root.targetFilePath, root.targetLanguageId);
                        }
                    }
                }

                // Finish / Close Button (shown in 'retry_failed' or 'success' state)
                Rectangle {
                    width: 80
                    height: 28
                    radius: 3
                    color: finishMa.containsMouse ? "#16a34a" : (theme ? theme.success : "#10b981")
                    visible: root.dialogState === "success" || root.dialogState === "retry_failed"

                    Text {
                        anchors.centerIn: parent
                        text: "Finish"
                        color: "#ffffff"
                        font.pixelSize: 11
                        font.bold: true
                    }

                    MouseArea {
                        id: finishMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.isOpen = false;
                        }
                    }
                }

                // Primary Install Action Button (Install / Approve Setup / Retry Install)
                Rectangle {
                    width: (root.dialogState === "complex_setup") ? 130 : 100
                    height: 28
                    radius: 3
                    color: {
                        if (root.isInstalling || root.dialogState === "retrying" || root.dialogState === "post_install_analyzing") {
                            return theme ? theme.bgSurfaceActive : "#444444";
                        }
                        return confirmMa.containsMouse ? (theme ? theme.accentHover : "#006cbd") : (theme ? theme.accent : "#0078d4");
                    }
                    enabled: (root.dialogState === "failed") || (!root.isInstalling && root.dialogState !== "retrying" && root.dialogState !== "post_install_analyzing" && (root.proposedCommand.length > 0 || (root.proposedSteps && root.proposedSteps.length > 0)))
                    visible: (root.dialogState === "single_command" && root.proposedCommand.length > 0) || (root.dialogState === "complex_setup") || (root.dialogState === "failed")

                    Row {
                        anchors.centerIn: parent
                        spacing: 6

                        VectorIcon {
                            anchors.verticalCenter: parent.verticalCenter
                            name: "download"
                            size: 11
                            color: "#ffffff"
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: {
                                if (root.dialogState === "post_install_analyzing") return "Verifying...";
                                if (root.dialogState === "retrying") return "Retrying...";
                                if (root.isInstalling) return "Installing...";
                                if (root.dialogState === "failed") return "Retry Install";
                                if (root.dialogState === "complex_setup") return "Approve Setup";
                                return "Install";
                            }
                            color: "#ffffff"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: confirmMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (root.isInstalling) return;

                            var execCmd = root.proposedCommand;
                            if (!execCmd && root.proposedSteps && root.proposedSteps.length > 0) {
                                execCmd = root.proposedSteps.join(" && ");
                            }
                            if (!execCmd) return;

                            console.log("[SmartInstall] User approved install");
                            root.isInstalling = true;
                            root.setDialogState("installing");
                            root.installLogs = "Starting installation for " + root.toolName + "...\n";
                            if (typeof extensionManager !== "undefined" && extensionManager) {
                                extensionManager.execute_smart_install_command(
                                    root.toolName,
                                    execCmd,
                                    root.executableName,
                                    root.retryAction,
                                    root.targetFilePath,
                                    root.verifyCommand
                                );
                            }
                            root.confirmed(root.toolName, execCmd, root.executableName, root.retryAction, root.targetFilePath, root.verifyCommand);
                        }
                    }
                }
            }
        }
    }

    function openContext(context) {
        if (!context) return;
        root.installContext = context;
        root.toolName = context.toolName || context.executable || context.detectedMissingDependency || context.operation || "Developer Tool";
        root.toolType = context.operationType || context.toolType || "tool";
        root.executableName = context.executable || "";
        root.descriptionText = context.errorMessage || context.detectedProblem || context.operation || "";
        root.diagnosisText = "";
        root.explanationText = "";
        root.proposedCommand = "";
        root.proposedSteps = [];
        root.verifyCommand = "";
        root.sourceKind = "";
        root.resolutionType = "";
        root.retryAction = context.retryAction || "run";
        root.targetFilePath = context.filePath || "";
        root.targetLanguageId = context.language || context.languageId || "";
        root.isInstalling = false;
        root.statusMessage = "";
        root.installLogs = "";
        root.isOpen = true;

        console.log("[SmartInstall] Entry point opened");
        root.setDialogState("analyzing");

        if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.start_smart_install_analysis) {
            extensionManager.start_smart_install_analysis(context);
        }
    }

    function openProposal(proposal) {
        if (!proposal) return;
        if (!proposal.resolutionType && !proposal.source) {
            openContext(proposal);
            return;
        }
        root.toolName = proposal.toolName || "";
        root.toolType = proposal.toolType || "tool";
        root.executableName = proposal.executable || "";
        root.titleText = proposal.title || ("Install " + root.toolName);
        root.descriptionText = proposal.description || "";
        root.diagnosisText = proposal.diagnosis || "";
        root.explanationText = proposal.explanation || proposal.description || "";
        root.proposedCommand = proposal.command || "";
        root.proposedSteps = proposal.steps || [];
        root.verifyCommand = proposal.verifyCommand || "";
        root.sourceKind = proposal.source || "recipe";
        root.resolutionType = proposal.resolutionType || "single_command";
        root.retryAction = proposal.retryAction || "";
        root.targetFilePath = proposal.filePath || "";
        root.targetLanguageId = proposal.languageId || "";
        root.isInstalling = false;
        root.statusMessage = "";
        root.installLogs = "";
        root.isOpen = true;

        console.log("[SmartInstall] Entry point opened");
        console.log("[SmartInstall] Source:", root.sourceKind);
        console.log("[SmartInstall] Resolution type:", root.resolutionType);
        console.log("[SmartInstall] Command availability:", (root.proposedCommand && root.proposedCommand.length > 0));

        if (root.sourceKind === "ai_unavailable") {
            root.failureReason = root.explanationText || "AI provider unavailable";
            root.setDialogState("ai_unavailable");
        } else if (root.resolutionType === "cannot_resolve") {
            root.setDialogState("cannot_resolve");
        } else if (root.resolutionType === "complex_setup") {
            root.setDialogState("complex_setup");
        } else if (root.resolutionType === "single_command") {
            root.setDialogState("single_command");
        } else {
            root.setDialogState(root.proposedCommand ? "single_command" : "cannot_resolve");
        }
    }
}
