// SnippetManager.js - Built-in Code Snippet Expansion Engine for DGX Studio

.pragma library

var SNIPPETS = {
    "python": [
        { label: "def", insertText: "def ${1:function_name}(${2:args}):\n    \"\"\"${3:docstring}\"\"\"\n    ${0:pass}", detail: "def function_name(args):" },
        { label: "class", insertText: "class ${1:ClassName}:\n    def __init__(self${2:, args}):\n        ${0:pass}", detail: "class ClassName:" },
        { label: "main", insertText: "if __name__ == '__main__':\n    ${0:main()}", detail: "if __name__ == '__main__':" },
        { label: "try", insertText: "try:\n    ${1:pass}\nexcept ${2:Exception} as ${3:e}:\n    ${0:print(e)}", detail: "try ... except Exception:" },
        { label: "for", insertText: "for ${1:item} in ${2:items}:\n    ${0:pass}", detail: "for item in items:" },
        { label: "lambda", insertText: "lambda ${1:x}: ${0:x * 2}", detail: "lambda x: ..." },
        { label: "import", insertText: "import ${1:os}\nimport ${0:sys}", detail: "import module" },
        { label: "print", insertText: "print(f\"${1:value}: {${2:value}}\")", detail: "print(f'...')" }
    ],
    "javascript": [
        { label: "clg", insertText: "console.log('${1:label}:', ${2:value});", detail: "console.log(value)" },
        { label: "fn", insertText: "function ${1:name}(${2:params}) {\n    ${0}\n}", detail: "function name(params)" },
        { label: "afn", insertText: "const ${1:name} = async (${2:params}) => {\n    ${0}\n};", detail: "const name = async () =>" },
        { label: "fori", insertText: "for (let ${1:i} = 0; ${1:i} < ${2:array}.length; ${1:i}++) {\n    const ${3:item} = ${2:array}[${1:i}];\n    ${0}\n}", detail: "for (let i = 0; i < len; i++)" },
        { label: "try", insertText: "try {\n    ${1}\n} catch (${2:err}) {\n    console.error(${2:err});\n}", detail: "try ... catch (err)" },
        { label: "fetch", insertText: "const response = await fetch('${1:url}', {\n    method: '${2:GET}',\n    headers: { 'Content-Type': 'application/json' }\n});\nconst data = await response.json();", detail: "fetch API request" },
        { label: "import", insertText: "import { ${1:module} } from '${2:package}';", detail: "import { ... } from '...'" },
        { label: "export", insertText: "export const ${1:name} = ${2:value};", detail: "export const" }
    ],
    "typescript": [
        { label: "interface", insertText: "export interface ${1:InterfaceName} {\n    ${2:id}: ${3:string};\n    ${0}\n}", detail: "interface InterfaceName" },
        { label: "type", insertText: "export type ${1:TypeName} = ${2:string};", detail: "type TypeName" },
        { label: "clg", insertText: "console.log('${1:label}:', ${2:value});", detail: "console.log(value)" },
        { label: "afn", insertText: "export const ${1:name} = async (${2:params}: ${3:any}): Promise<${4:void}> => {\n    ${0}\n};", detail: "const name = async (): Promise<>" }
    ],
    "html": [
        { label: "html5", insertText: "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>${1:Document}</title>\n</head>\n<body>\n    <h1>${2:Hello World}</h1>\n    ${0}\n</body>\n</html>", detail: "HTML5 Boilerplate Document" },
        { label: "div", insertText: "<div class=\"${1:container}\">\n    ${0}\n</div>", detail: "<div class='...'> ... </div>" },
        { label: "span", insertText: "<span>${0}</span>", detail: "<span> ... </span>" },
        { label: "p", insertText: "<p>${0}</p>", detail: "<p> ... </p>" },
        { label: "a", insertText: "<a href=\"${1:#}\">${0:Link}</a>", detail: "<a href='...'> ... </a>" },
        { label: "button", insertText: "<button class=\"${1:btn}\">${0:Click Me}</button>", detail: "<button> ... </button>" },
        { label: "btn", insertText: "<button class=\"${1:btn}\" onclick=\"${2:handleClick()}\">${0:Click Me}</button>", detail: "<button onclick='...'>" },
        { label: "input", insertText: "<input type=\"${1:text}\" placeholder=\"${2:Enter text...}\" />", detail: "<input type='...' />" },
        { label: "form", insertText: "<form action=\"${1:#}\" method=\"${2:post}\">\n    ${0}\n</form>", detail: "<form> ... </form>" },
        { label: "img", insertText: "<img src=\"${1:image.png}\" alt=\"${2:image description}\" />", detail: "<img src='...' />" },
        { label: "ul", insertText: "<ul>\n    <li>${0:Item 1}</li>\n</ul>", detail: "<ul> <li> ... </li> </ul>" },
        { label: "ol", insertText: "<ol>\n    <li>${0:Item 1}</li>\n</ol>", detail: "<ol> <li> ... </li> </ol>" },
        { label: "li", insertText: "<li>${0}</li>", detail: "<li> ... </li>" },
        { label: "table", insertText: "<table>\n    <thead>\n        <tr>\n            <th>${1:Header}</th>\n        </tr>\n    </thead>\n    <tbody>\n        <tr>\n            <td>${0:Data}</td>\n        </tr>\n    </tbody>\n</table>", detail: "<table> ... </table>" },
        { label: "section", insertText: "<section class=\"${1:section}\">\n    ${0}\n</section>", detail: "<section> ... </section>" },
        { label: "header", insertText: "<header>\n    ${0}\n</header>", detail: "<header> ... </header>" },
        { label: "footer", insertText: "<footer>\n    ${0}\n</footer>", detail: "<footer> ... </footer>" },
        { label: "nav", insertText: "<nav>\n    ${0}\n</nav>", detail: "<nav> ... </nav>" },
        { label: "main", insertText: "<main>\n    ${0}\n</main>", detail: "<main> ... </main>" },
        { label: "h1", insertText: "<h1>${0}</h1>", detail: "<h1> ... </h1>" },
        { label: "h2", insertText: "<h2>${0}</h2>", detail: "<h2> ... </h2>" },
        { label: "h3", insertText: "<h3>${0}</h3>", detail: "<h3> ... </h3>" },
        { label: "script", insertText: "<script src=\"${1:app.js}\"></script>", detail: "<script src='...'>" },
        { label: "link", insertText: "<link rel=\"stylesheet\" href=\"${1:style.css}\">", detail: "<link rel='stylesheet'>" },
        { label: "style", insertText: "<style>\n    ${0}\n</style>", detail: "<style> ... </style>" }
    ],
    "css": [
        { label: "flex", insertText: "display: flex;\nalign-items: center;\njustify-content: center;", detail: "Flexbox Centering" },
        { label: "grid", insertText: "display: grid;\ngrid-template-columns: repeat(auto-fit, minmax(200px, 1fr));\ngap: 16px;", detail: "CSS Grid Responsive" },
        { label: "gradient", insertText: "background: linear-gradient(135deg, ${1:#0078d4} 0%, ${2:#a855f7} 100%);", detail: "linear-gradient" }
    ],
    "cpp": [
        { label: "main", insertText: "#include <iostream>\n\nint main(int argc, char* argv[]) {\n    std::cout << \"${1:Hello, World!}\" << std::endl;\n    return 0;\n}", detail: "int main() { ... }" },
        { label: "cout", insertText: "std::cout << \"${1:message}\" << std::endl;", detail: "std::cout" },
        { label: "fori", insertText: "for (size_t ${1:i} = 0; ${1:i} < ${2:count}; ++${1:i}) {\n    ${0}\n}", detail: "for loop" }
    ],
    "qml": [
        { label: "rect", insertText: "Rectangle {\n    id: ${1:rect}\n    width: ${2:100}; height: ${3:100}\n    color: \"${4:#0078d4}\"\n    radius: 4\n}", detail: "Rectangle { ... }" },
        { label: "item", insertText: "Item {\n    id: ${1:root}\n    anchors.fill: parent\n}", detail: "Item { ... }" },
        { label: "row", insertText: "RowLayout {\n    anchors.fill: parent\n    spacing: 8\n}", detail: "RowLayout { ... }" },
        { label: "ma", insertText: "MouseArea {\n    anchors.fill: parent\n    cursorShape: Qt.PointingHandCursor\n    onClicked: {\n        ${0}\n    }\n}", detail: "MouseArea { ... }" }
    ]
};

function getSnippetsForLanguage(langId) {
    var id = (langId || "").toLowerCase();
    if (id === "py" || id === "python") return SNIPPETS["python"];
    if (id === "js" || id === "javascript") return SNIPPETS["javascript"];
    if (id === "ts" || id === "typescript") return SNIPPETS["typescript"];
    if (id === "html" || id === "htm" || id === "xml") return SNIPPETS["html"];
    if (id === "css" || id === "scss") return SNIPPETS["css"];
    if (id === "cpp" || id === "c++" || id === "c") return SNIPPETS["cpp"];
    if (id === "qml") return SNIPPETS["qml"];
    return SNIPPETS["javascript"];
}

function expandSnippetTemplate(template) {
    var marker = "___CURSOR_MARKER___";
    var replaced = template;

    if (replaced.indexOf("${0}") !== -1) {
        replaced = replaced.replace("${0}", marker);
    } else if (/\$\{\d+:([^}]+)\}/.test(replaced)) {
        replaced = replaced.replace(/\$\{\d+:([^}]+)\}/, "$1" + marker);
    }

    // Strip tabstop markers e.g. ${1:name} -> name, ${0} -> ""
    replaced = replaced.replace(/\$\{\d+:([^}]+)\}/g, "$1");
    replaced = replaced.replace(/\$\{\d+\}/g, "");
    replaced = replaced.replace(/\$\d+/g, "");

    var cursorOffset = replaced.indexOf(marker);
    if (cursorOffset !== -1) {
        replaced = replaced.replace(marker, "");
    } else {
        cursorOffset = replaced.length;
    }

    return { text: replaced, cursorOffset: cursorOffset };
}
