import json
import os
from json import JSONEncoder

# subclass JSONEncoder
class setEncoder(JSONEncoder):
        def default(self, obj):
            return list(obj)
data= {"ULUS10565": "C:/PPSPP games/Tactics Ogre - Let Us Cling Together (USA).iso"}
with open('game_map.json', 'w', encoding='utf-8') as f:
    jsonData = json.dump(data, f, indent=4, cls=setEncoder)
    print(jsonData)


