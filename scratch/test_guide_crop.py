import sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine, QQmlComponent

app = QGuiApplication(sys.argv)
engine = QQmlEngine()
comp = QQmlComponent(engine, "qml/components/EditorArea.qml")
editor = comp.create()

snippet = """vector<string> strs = {"aa", "ab"} ;

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
    }
}
"""
segs = editor.computeGuideSegmentsForText(snippet).toVariant()
print("Segments for snippet (count = {}):".format(len(segs)))
for s in segs:
    print(" ", s)

