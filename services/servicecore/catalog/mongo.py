from pymongo import MongoClient

from django.conf import settings


_mongo_client = None


def get_mongo_client():
    global _mongo_client
    if _mongo_client is None:
        config = settings.MONGODB_SETTINGS
        credentials = {}
        if config["USERNAME"] and config["PASSWORD"]:
            credentials = {
                "username": config["USERNAME"],
                "password": config["PASSWORD"],
                "authSource": config["AUTH_SOURCE"],
            }

        _mongo_client = MongoClient(
            host=config["HOST"],
            port=config["PORT"],
            **credentials,
        )
    return _mongo_client


def get_product_collection():
    client = get_mongo_client()
    config = settings.MONGODB_SETTINGS
    database = client[config["NAME"]]
    return database[config["PRODUCT_COLLECTION"]]


def get_catalog_collection():
    client = get_mongo_client()
    config = settings.MONGODB_SETTINGS
    database = client[config["NAME"]]
    return database[config["CATALOG_COLLECTION"]]
