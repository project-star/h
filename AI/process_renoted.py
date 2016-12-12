#import extracttext
#import wordsfrequency
#import gethypothesisvalues
#import tagstoupdate
#import updatetagselasticsearch
#import updatepostgres
import time
import getTags
import subprocess
def get_db():
    from pymongo import MongoClient
    client = MongoClient('0.0.0.0:27017')
    db = client.renoted
    return db

def get_annotations(db):
    collection=db.annotations.find({"processed": False})
    for item in collection:
        #print item["renoted_id"]
        getTags.callOpenCalais(item["annotation_id"])
  
        overalldata=getTags.extractTags(item["annotation_id"])
        data=process_results(overalldata)
        #print overalldata        
        #topwords=wordsfrequency.topwords(item["renoted_id"])
        #print topwords
        #existingvalues=gethypothesisvalues.getExistingInfo(item["renoted_id"])
        #print existingvalues
        #finaltags=tagstoupdate.tagstoupdate(topwords,existingvalues)
        #print finaltags
        #updatetagselasticsearch.updatetags(finaltags,item["renoted_id"])
        #updatepostgres.updatetags(finaltags,item["renoted_id"])
        db.annotations.update_one({'_id': item['_id']},{'$set':{"processed": True,"addedtags" : data["socialtags"], "topics":data["topics"]}}, upsert=False)
    return db.annotations.find({"processed": False})

def process_results(overalldata):
    topics=[]
    socialtags=[]
    doc={}
    print overalldata["topics"]    
    print overalldata["socialtags"]
    for item in overalldata["topics"]:
        topics.append(item["name"])
    for item in overalldata["socialtags"]:    
        socialtags.append(item["name"])
    doc["topics"] = topics
    doc["socialtags"] = socialtags
    return doc


def annotation_main(renoted_id):
     db = get_db()
     add_annotation(db,renoted_id)
if __name__ == "__main__":
    db=get_db()
    while(True):

        print get_annotations(db)
        time.sleep(20)
