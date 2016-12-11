def get_db():
    from pymongo import MongoClient
    client = MongoClient('0.0.0.0:27017')
    db = client.renoted
    return db

def add_annotation(db,renoted_id):
    db.annotations.insert({"renoted_id" : renoted_id,"processed" : False, "initialtags":[],"addedtags":[]})
    
def get_country(db):
    return db.countries.find_one()



def annotation_main(renoted_id):
     db = get_db()
     add_annotation(db,renoted_id)
if __name__ == "__main__":

    db = get_db() 
    add_country(db)
    print get_country(db)
