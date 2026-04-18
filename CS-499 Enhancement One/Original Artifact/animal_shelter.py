from pymongo import MongoClient

class AnimalShelter(object):
    """ CRUD operations for Animal collection in MongoDB """

    def __init__(self, username, password):
        # Initializing the MongoClient. This helps to 
        # access the MongoDB databases and collections.
        # This is hard-wired to use the aac database, the 
        # animals collection, and the aac user.
        # Definitions of the connection string variables are
        # unique to the individual Apporto environment.
        #
        # You must edit the connection variables below to reflect
        # your own instance of MongoDB!
        #
        # Connection Variables
        #

        
        HOST = 'nv-desktop-services.apporto.com'
        PORT = 30767
        DB = 'AAC'
        COL = 'animals'

        self.client = MongoClient(f'mongodb://{username}:{password}@{HOST}:{PORT}/?authSource=admin')
        self.database = self.client[DB]
        self.collection = self.database[COL]

    def create(self, data):
        if data is not None:
            result = self.collection.insert_one(data)
            return result.acknowledged
        else:
            raise Exception("Nothing to save, because data parameter is empty")

    def read(self, query):
        return list(self.collection.find(query))
        
    def update(self, query, updates):
        result = self.collection.update_many(query, {'$set': updates})
        return result.modified_count    
    
    def delete(self, query):
        if query:
            return self.collection.delete_many(query).deleted_count
        else:
            raise Exception("Delete query not valid")

    
