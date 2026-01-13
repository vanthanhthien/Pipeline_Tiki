import json 

raw ='{"id":213}'
data =json.loads(raw)
print(data['id'])