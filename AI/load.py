import sys
import json

json_data=open(sys.argv[1]).read()
#print json_data
data = json.loads(json_data)
typegroup=""
topics=[]
socialtags=[]
entities=[]
relations=[]
industry=[]
for keys in data:
#    print keys
#    print ("+++++++data in keys+++++")
    if (keys != "doc"):
#        print data[keys]["_typeGroup"]
        if (data[keys]["_typeGroup"] == "topics"):
             topicval={}
             topicval["name"]=data[keys]["name"]
             topicval["score"]=data[keys]["score"]
             topics.append(topicval)
#             socialtags.append(socialTagval)
#             print data[keys]

        if (data[keys]["_typeGroup"] == "socialTag"):
             socialTagval={}
             socialTagval["name"]=data[keys]["name"]
             socialTagval["importance"]=data[keys]["importance"]
             socialtags.append(socialTagval)
#             print data[keys]
#             print socialtags
        if (data[keys]["_typeGroup"] == "entities"):
            entitiesval={}
            entitiesval["name"]=data[keys]["name"]
            entitiesval["_type"]=data[keys]["_type"]
            entitiesval["relevance"]=data[keys]["relevance"]
            entities.append(entitiesval)

        if (data[keys]["_typeGroup"] == "industry"):
            industryval={}
            industryval["name"]=data[keys]["name"]
#            industryval["_type"]=data[keys]["_type"]
            industryval["relevance"]=data[keys]["relevance"]
            industry.append(industryval)
#        if (data[keys]["_typeGroup"] == "relations"):
#            relations.append(data[keys]["_type"])

doc={}
doc["topics"]=topics
doc["socialtags"]=socialtags
doc["entities"]=entities
doc["industry"]=industry
print json.dumps(doc)


#            print data[keys]
#             print data[keys]["importance"]
#    datains = json.loads
# print(data)
