import urllib
import sys
import subprocess
import json
def callOpenCalais(id):

    filepath= id+".txt"
    ret_code=subprocess.call("python opencalais.py " + filepath + " . " + "pjqwAWv7pJfyPFGh3WNUf8ACDDazT4QU", shell=True) 

def extractTags(id):
    filepath = id + ".txt.xml"   
    json_data=open(filepath).read()
    #print json_data
    data = json.loads(json_data)
    typegroup=""
    topics=[]
    socialtags=[]
    entities=[]
    relations=[]
    industry=[]
    for keys in data:
        if (keys != "doc"):
            if (data[keys]["_typeGroup"] == "topics"):
                topicval={}
                topicval["name"]=data[keys]["name"]
                topicval["score"]=data[keys]["score"]
                topics.append(topicval)

            if (data[keys]["_typeGroup"] == "socialTag"):
                socialTagval={}
                socialTagval["name"]=data[keys]["name"]
                socialTagval["importance"]=data[keys]["importance"]
                socialtags.append(socialTagval)
            if (data[keys]["_typeGroup"] == "entities"):
                entitiesval={}
                entitiesval["name"]=data[keys]["name"]
                entitiesval["_type"]=data[keys]["_type"]
                entitiesval["relevance"]=data[keys]["relevance"]
                entities.append(entitiesval)

            if (data[keys]["_typeGroup"] == "industry"):
                industryval={}
                industryval["name"]=data[keys]["name"]
                industryval["relevance"]=data[keys]["relevance"]
                industry.append(industryval)

    doc={}
    doc["topics"]=topics
    doc["socialtags"]=socialtags
    doc["entities"]=entities
    doc["industry"]=industry
    return doc
