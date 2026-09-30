.pragma library

var LANGUAGES = [
    {
        id: "python",
        name: "Python",
        extensions: [".py", ".pyw"],
        keywords: [
            "def", "class", "import", "from", "return", "if", "elif", "else",
            "while", "for", "in", "try", "except", "finally", "with", "as",
            "pass", "break", "continue", "yield", "lambda", "global", "nonlocal",
            "raise", "assert", "async", "await", "None", "True", "False", "is",
            "not", "and", "or", "self", "print", "len", "range", "dict", "list",
            "set", "tuple", "int", "str", "float", "bool", "enumerate", "zip",
            "open", "super", "isinstance", "type", "sum", "min", "max", "sorted",
            "any", "all", "map", "filter", "reversed", "abs", "round", "dir",
            "getattr", "setattr", "hasattr", "input", "format", "iter", "next",
            "__init__", "__main__", "__name__", "__str__", "__repr__", "__call__",
            "append", "extend", "insert", "remove", "pop", "clear", "index", "count",
            "sort", "reverse", "keys", "values", "items", "get", "update", "split",
            "join", "replace", "strip", "lower", "upper", "startswith", "endswith"
        ]
    },
    {
        id: "javascript",
        name: "JavaScript",
        extensions: [".js", ".mjs", ".cjs", ".jsx"],
        keywords: [
            "function", "const", "let", "var", "return", "if", "else", "for",
            "while", "do", "switch", "case", "default", "break", "continue",
            "try", "catch", "finally", "throw", "class", "extends", "super",
            "this", "new", "import", "export", "from", "as", "default", "async",
            "await", "yield", "typeof", "instanceof", "void", "delete", "null",
            "undefined", "true", "false", "console", "log", "warn", "error",
            "document", "window", "Promise", "Array", "Object", "String", "Number",
            "Boolean", "Math", "JSON", "Date", "RegExp", "Map", "Set", "Symbol",
            "setTimeout", "setInterval", "clearTimeout", "clearInterval", "fetch",
            "push", "pop", "shift", "unshift", "splice", "slice", "concat",
            "forEach", "map", "filter", "reduce", "find", "findIndex", "includes",
            "indexOf", "join", "split", "replace", "trim", "toLowerCase", "toUpperCase"
        ]
    },
    {
        id: "typescript",
        name: "TypeScript",
        extensions: [".ts", ".tsx", ".d.ts"],
        keywords: [
            "interface", "type", "enum", "implements", "declare", "namespace",
            "abstract", "readonly", "public", "private", "protected", "static",
            "override", "keyof", "typeof", "as", "is", "never", "unknown", "any",
            "function", "const", "let", "return", "if", "else", "for", "while",
            "class", "extends", "super", "this", "new", "import", "export", "async",
            "await", "Promise", "Array", "Record", "Partial", "Required", "Pick",
            "Omit", "Exclude", "Extract", "NonNullable", "Parameters", "ReturnType",
            "console", "log", "string", "number", "boolean", "void", "object"
        ]
    },
    {
        id: "cpp",
        name: "C++",
        extensions: [".cpp", ".hpp", ".cc", ".cxx", ".c++", ".h++"],
        keywords: [
            "int", "float", "double", "char", "void", "bool", "auto", "const",
            "class", "struct", "template", "typename", "public", "private", "protected",
            "namespace", "using", "std", "vector", "string", "cout", "cin", "endl",
            "return", "if", "else", "for", "while", "do", "switch", "case", "break",
            "continue", "new", "delete", "nullptr", "virtual", "override", "constexpr",
            "include", "static_cast", "dynamic_cast", "reinterpret_cast", "sizeof",
            "pair", "map", "unordered_map", "set", "unordered_set", "queue", "stack",
            "push_back", "emplace_back", "begin", "end", "size", "empty", "clear"
        ]
    },
    {
        id: "c",
        name: "C",
        extensions: [".c", ".h"],
        keywords: [
            "int", "char", "float", "double", "void", "short", "long", "unsigned",
            "signed", "struct", "union", "enum", "typedef", "sizeof", "static",
            "extern", "const", "volatile", "return", "if", "else", "for", "while",
            "do", "switch", "case", "default", "break", "continue", "goto", "printf",
            "scanf", "malloc", "free", "calloc", "realloc", "memcpy", "memset", "NULL", "include"
        ]
    },
    {
        id: "csharp",
        name: "C#",
        extensions: [".cs"],
        keywords: [
            // Standard C# Keywords
            "using", "namespace", "class", "struct", "interface", "enum", "public",
            "private", "protected", "internal", "static", "readonly", "override",
            "virtual", "abstract", "sealed", "async", "await", "Task", "void", "int",
            "float", "double", "decimal", "string", "bool", "byte", "char", "object",
            "var", "return", "if", "else", "for", "foreach", "while", "do", "switch",
            "case", "default", "break", "continue", "new", "this", "base", "get", "set",
            "init", "try", "catch", "finally", "throw", "null", "true", "false", "in", "out",
            "ref", "is", "as", "typeof", "sizeof", "lock", "yield", "delegate", "event",
            "Console", "WriteLine", "List", "Dictionary", "HashSet", "Queue", "Stack",
            "IEnumerable", "IEnumerator", "Math", "Convert", "Action", "Func",

            // Unity Engine Core Classes & Components
            "MonoBehaviour", "ScriptableObject", "GameObject", "Transform", "RectTransform",
            "Component", "Object", "Behaviour", "Camera", "Light", "AudioSource", "AudioClip",
            "AudioListener", "Renderer", "MeshRenderer", "SkinnedMeshRenderer", "MeshFilter",
            "Material", "Shader", "Texture", "Texture2D", "Sprite", "SpriteRenderer",
            "Canvas", "CanvasGroup", "CanvasScaler", "GraphicRaycaster",

            // Unity Engine Math, Vectors & Structs
            "Vector2", "Vector3", "Vector4", "Vector2Int", "Vector3Int",
            "Quaternion", "Matrix4x4", "Color", "Color32", "Mathf", "Bounds", "Rect",
            "Ray", "Ray2D", "RaycastHit", "RaycastHit2D", "Plane",

            // Unity Engine Physics & Colliders
            "Rigidbody", "Rigidbody2D", "Collider", "Collider2D", "BoxCollider", "BoxCollider2D",
            "SphereCollider", "CapsuleCollider", "CapsuleCollider2D", "MeshCollider",
            "CharacterController", "Physics", "Physics2D", "PhysicsMaterial2D", "PhysicMaterial",
            "Collision", "Collision2D", "ContactPoint", "Joint", "HingeJoint",

            // Unity Engine Lifecycle & Event Methods
            "Awake", "Start", "Update", "FixedUpdate", "LateUpdate", "OnEnable", "OnDisable",
            "OnDestroy", "OnTriggerEnter", "OnTriggerStay", "OnTriggerExit",
            "OnTriggerEnter2D", "OnTriggerStay2D", "OnTriggerExit2D",
            "OnCollisionEnter", "OnCollisionStay", "OnCollisionExit",
            "OnCollisionEnter2D", "OnCollisionStay2D", "OnCollisionExit2D",
            "OnGUI", "OnDrawGizmos", "OnDrawGizmosSelected", "OnValidate",
            "OnBecameVisible", "OnBecameInvisible", "OnApplicationQuit", "OnApplicationPause",

            // Unity Engine APIs & Methods
            "Instantiate", "Destroy", "DestroyImmediate", "GetComponent", "GetComponents",
            "GetComponentInChildren", "GetComponentsInChildren", "GetComponentInParent",
            "GetComponentsInParent", "TryGetComponent", "AddComponent",
            "FindObjectOfType", "FindObjectsOfType", "FindWithTag", "FindGameObjectsWithTag",
            "CompareTag", "SendMessage", "BroadcastMessage", "SetActive",
            "Translate", "Rotate", "RotateAround", "LookAt",
            "StartCoroutine", "StopCoroutine", "StopAllCoroutines",
            "WaitForSeconds", "WaitForSecondsRealtime", "WaitForEndOfFrame", "WaitForFixedUpdate", "WaitUntil", "WaitWhile",

            // Unity Engine Subsystems (Input, Time, SceneManagement, UI, Audio, Debug)
            "Time", "deltaTime", "fixedDeltaTime", "timeScale",
            "Input", "GetAxis", "GetAxisRaw", "GetButton", "GetButtonDown", "GetButtonUp",
            "GetKey", "GetKeyDown", "GetKeyUp", "mousePosition", "touchCount", "touches", "KeyCode",
            "Debug", "Log", "LogWarning", "LogError", "LogException", "DrawRay", "DrawLine", "Break",
            "SceneManager", "LoadScene", "LoadSceneAsync", "GetActiveScene", "Scene",
            "Application", "targetFrameRate", "persistentDataPath", "dataPath", "streamingAssetsPath", "Quit",
            "Screen", "width", "height", "dpi", "fullScreen",
            "PlayerPrefs", "SetInt", "GetInt", "SetFloat", "GetFloat", "SetString", "GetString", "Save", "HasKey",
            "Resources", "Load", "LoadAsync", "LoadAll", "UnloadUnusedAssets",
            "Gizmos", "color", "DrawWireSphere", "DrawWireCube", "DrawSphere", "DrawCube",
            "Random", "Range", "value", "insideUnitSphere", "insideUnitCircle", "rotation",

            // Unity UI & TextMeshPro
            "Button", "Image", "RawImage", "Text", "Slider", "Toggle", "Scrollbar", "Dropdown",
            "InputField", "TMP_Text", "TextMeshPro", "TextMeshProUGUI", "TMP_InputField", "TMP_Dropdown",

            // Unity Animation & Navigation
            "Animation", "Animator", "AnimatorStateInfo", "Play", "SetTrigger", "ResetTrigger",
            "SetBool", "GetBool", "SetFloat", "GetFloat", "SetInteger", "GetInteger",
            "NavMesh", "NavMeshAgent", "NavMeshObstacle", "SetDestination",

            // Unity Attributes
            "SerializeField", "HideInInspector", "Header", "Tooltip", "Range", "Space",
            "RequireComponent", "DisallowMultipleComponent", "ExecuteInEditMode", "ExecuteAlways",
            "CreateAssetMenu", "ContextMenu", "ContextMenuItem", "Serializable"
        ]
    },
    {
        id: "java",
        name: "Java",
        extensions: [".java"],
        keywords: [
            "public", "private", "protected", "class", "interface", "extends",
            "implements", "package", "import", "void", "int", "boolean", "String",
            "static", "final", "abstract", "return", "if", "else", "for", "while",
            "try", "catch", "finally", "throw", "throws", "new", "this", "super",
            "System", "out", "println", "null", "true", "false", "override",
            "ArrayList", "HashMap", "HashSet", "List", "Map", "Set", "length", "size"
        ]
    },
    {
        id: "rust",
        name: "Rust",
        extensions: [".rs"],
        keywords: [
            "fn", "let", "mut", "pub", "struct", "enum", "impl", "trait", "use",
            "mod", "match", "if", "else", "while", "loop", "for", "in", "return",
            "break", "continue", "self", "Self", "const", "static", "unsafe", "async",
            "await", "where", "Some", "None", "Ok", "Err", "String", "Vec", "Option",
            "Result", "i32", "i64", "u32", "u64", "f64", "bool", "println", "format",
            "unwrap", "expect", "clone", "as_ref", "into", "from", "push", "iter"
        ]
    },
    {
        id: "go",
        name: "Go",
        extensions: [".go"],
        keywords: [
            "package", "import", "func", "return", "var", "const", "type", "struct",
            "interface", "if", "else", "for", "range", "switch", "case", "default",
            "select", "go", "defer", "chan", "map", "make", "new", "len", "cap",
            "append", "nil", "true", "false", "int", "string", "bool", "error", "fmt",
            "Println", "Printf", "Sprintf", "Error"
        ]
    },
    {
        id: "qml",
        name: "QML",
        extensions: [".qml"],
        keywords: [
            "import", "QtQuick", "Item", "Rectangle", "Text", "TextInput", "TextArea",
            "ListView", "ColumnLayout", "RowLayout", "GridLayout", "ScrollView",
            "MouseArea", "Button", "property", "signal", "alias", "id", "width",
            "height", "anchors", "fill", "centerIn", "color", "visible", "onClicked",
            "function", "Component", "onCompleted", "Connections", "Timer", "Window",
            "font", "pixelSize", "bold", "radius", "border", "spacing", "margins"
        ]
    },
    {
        id: "html",
        name: "HTML",
        extensions: [".html", ".htm"],
        keywords: [
            "<!DOCTYPE html>", "html", "head", "title", "meta", "link", "script",
            "body", "header", "nav", "main", "section", "article", "aside", "footer",
            "div", "span", "p", "h1", "h2", "h3", "h4", "ul", "ol", "li", "a",
            "button", "input", "form", "table", "tr", "td", "th", "img", "class", "id",
            "style", "src", "href", "alt", "placeholder", "type", "value"
        ]
    },
    {
        id: "css",
        name: "CSS",
        extensions: [".css"],
        keywords: [
            "display", "flex", "grid", "position", "relative", "absolute", "fixed",
            "margin", "padding", "width", "height", "color", "background", "border",
            "border-radius", "font-family", "font-size", "font-weight", "align-items",
            "justify-content", "flex-direction", "gap", "overflow", "cursor", "z-index",
            "box-shadow", "transition", "transform", "opacity", "none", "block", "inline"
        ]
    },
    {
        id: "scss",
        name: "SCSS",
        extensions: [".scss", ".sass"],
        keywords: [
            "@import", "@include", "@mixin", "@extend", "@use", "@forward", "@if",
            "@else", "@each", "@for", "$variable", "display", "margin", "padding"
        ]
    },
    {
        id: "json",
        name: "JSON",
        extensions: [".json"],
        keywords: ["true", "false", "null", "\"name\"", "\"version\"", "\"description\"", "\"main\"", "\"scripts\"", "\"dependencies\"", "\"devDependencies\""]
    },
    {
        id: "xml",
        name: "XML",
        extensions: [".xml", ".svg"],
        keywords: ["version", "encoding", "xml", "root", "node", "item", "svg", "path", "viewBox"]
    },
    {
        id: "yaml",
        name: "YAML",
        extensions: [".yaml", ".yml"],
        keywords: ["true", "false", "null", "version:", "name:", "services:", "image:", "ports:", "environment:"]
    },
    {
        id: "sql",
        name: "SQL",
        extensions: [".sql"],
        keywords: [
            "SELECT", "FROM", "WHERE", "INSERT", "INTO", "UPDATE", "SET", "DELETE",
            "JOIN", "LEFT JOIN", "INNER JOIN", "GROUP BY", "ORDER BY", "HAVING",
            "LIMIT", "CREATE TABLE", "DROP TABLE", "ALTER TABLE", "PRIMARY KEY",
            "FOREIGN KEY", "AND", "OR", "NOT", "NULL", "AS", "DISTINCT", "COUNT"
        ]
    },
    {
        id: "shell",
        name: "Shell",
        extensions: [".sh", ".bash", ".ps1", ".bat", ".cmd"],
        keywords: [
            "echo", "if", "then", "else", "fi", "for", "in", "do", "done", "while",
            "case", "esac", "function", "return", "exit", "export", "set", "cd", "ls", "mkdir", "rm"
        ]
    },
    {
        id: "markdown",
        name: "Markdown",
        extensions: [".md", ".markdown"],
        keywords: ["# Header", "## Subheader", "### Section", "```code```", "- item", "[link]()", "**bold**", "*italic*"]
    }
];

function detectLanguage(fileName) {
    if (!fileName) return { id: "text", name: "Plain Text", keywords: [] };
    var lower = fileName.toLowerCase();
    for (var i = 0; i < LANGUAGES.length; i++) {
        var lang = LANGUAGES[i];
        for (var e = 0; e < lang.extensions.length; e++) {
            if (lower.endsWith(lang.extensions[e])) {
                return lang;
            }
        }
    }
    return { id: "text", name: "Plain Text", keywords: [] };
}

function getKeywords(langId) {
    if (!langId) return [];
    for (var i = 0; i < LANGUAGES.length; i++) {
        if (LANGUAGES[i].id === langId) {
            return LANGUAGES[i].keywords || [];
        }
    }
    return [];
}

function getCompletionsForLanguage(langId, prefix) {
    var p = (prefix || "").toLowerCase();
    var list = [];
    var kws = getKeywords(langId);
    for (var k = 0; k < kws.length; k++) {
        if (!p || kws[k].toLowerCase().startsWith(p) || kws[k].toLowerCase().indexOf(p) !== -1) {
            list.push({
                label: kws[k],
                insertText: kws[k],
                type: "keyword"
            });
        }
    }
    return list;
}
