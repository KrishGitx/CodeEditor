import subprocess

test_code = '''vector<string> strs = {"aa", "ab"} ;

int count,i = 0, j = strs.size() - 1 ,k=0; //j == 1
cout<<"j:"<<strs[1]<<endl;
string lngstring = strs[0];

while (i != j)// 0 != 1
{
    if(lngstring[k] == strs[j][k]){ //a == a
        if(k < strs[j].size() - 1) //0 < 1
            k++; //1
}else if (lngstring[k] != strs[j][k] ){ //a != b
    lngstring = lngstring.substr(0,k);
    if(j>0){j--;}
    k=0;
}
else{
    return 0;
}'''

with open('scratch/temp_code.txt', 'w', encoding='utf-8') as f:
    f.write(test_code)

runner = f"""
const fs = require('fs');
const theme = {{ tabSize: 4 }};
"""
with open('qml/components/EditorArea.qml', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('function computeGuideSegmentsForText(docText)')
end = content.find('function recomputeScopes(docText)')
js_code = content[start:end]

runner += js_code + """
const testDoc = fs.readFileSync('scratch/temp_code.txt', 'utf8');
console.log(JSON.stringify(computeGuideSegmentsForText(testDoc), null, 2));
"""

with open('scratch/temp_runner2.js', 'w', encoding='utf-8') as f:
    f.write(runner)

res = subprocess.run(['node', 'scratch/temp_runner2.js'], capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print('ERR:', res.stderr)

