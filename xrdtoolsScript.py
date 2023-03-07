import xrdtools

Nom='2tom_def15B220XC.xrdml'
data = xrdtools.read_xrdml(Nom)
print()
print("dictionnaire associe a: ",Nom)
print()
print(data)
index=0
print()
print("...balayage dictionnaire")
for key,value in data.items():
    print()
    print("index =",index)
    print(" key  =",key)
    print(" value=",value)
    index+=1
print(len(data['data']))
print(len(data['x']))