import json
import os.path

from elasticsearch import Elasticsearch
from elasticsearch.client import IngestClient


def get_client(elasticsearch_host, elasticsearch_ca_path, elasticsearch_user, elasticsearch_pwd):
    return Elasticsearch(
        hosts=elasticsearch_host,
        ca_certs=elasticsearch_ca_path,
        basic_auth=(elasticsearch_user, elasticsearch_pwd)
    )


def get_file_content(file_name: str):
    if file_name != "" and not os.path.exists(file_name):
        print("\tFile", file_name, "for index mappings/settings does not exist. Program will end.")
        exit(0)
    if file_name != "":
        file = open(file_name)
        content = json.load(file)
        file.close()
    else:
        content = {}
    return content


# Create index name @index_name, with the mappings from the file @file_mappings and settings from @file_settings.
def create_index(client: Elasticsearch, index_name: str, file_mappings: str = "", file_settings: str = ""):
    print("Creating index {}...".format(index_name))
    if client.indices.exists(index=index_name):
        print("\tIndex", index_name, "exists and will be deleted.")
        client.indices.delete(index=index_name)

    content_mappings = get_file_content(file_mappings)
    content_settings = get_file_content(file_settings)

    if "mappings" in content_mappings:
        mappings = content_mappings["mappings"]
    else:
        print("\tNo mappings were defined for index {name}. Default mappings will be used.".format(name=index_name))
        mappings = {}

    if "settings" in content_settings:
        settings = content_settings["settings"]
        settings["index"].pop("provided_name", None)
        settings["index"].pop("uuid", None)
        settings["index"].pop("creation_date", None)
        settings["index"]["version"].pop("created", None)
    else:
        print("\tNo settings were defined for index {name}. Default settings will be used.".format(name=index_name))
        settings = {}

    client.indices.create(index=index_name, mappings=mappings, settings=settings)
    print("Index {name} successfully created.\n".format(name=index_name))


def add_doc_from_file(client: Elasticsearch, index_name: str, doc_path: str):
    file = open(doc_path)
    content = json.load(file)
    file.close()
    client.index(index=index_name, document=content)
    # print("\t Document {} was added to index {}.".format(os.path.basename(doc_path), index_name))


def place_documents(client: Elasticsearch, index_name: str, folder_docs: str):
    print("Placing documents on the index {name}...".format(name=index_name))
    if not client.indices.exists(index=index_name):
        print("Index {name} does not exist. Program will end.".format(name=index_name))
        exit(0)

    if not os.path.isdir(folder_docs):
        print("Folder {} does not exist. Documents cannot be placed. Program will end.".format(folder_docs))
        exit(0)

    for doc in os.listdir(folder_docs):
        doc_path = os.path.join(folder_docs, doc)
        if os.path.isfile(doc_path):
            add_doc_from_file(client, index_name, doc_path)

    # From Elastic docs: Use the refresh API to explicitly make all operations performed on one or more indices since
    # the last refresh available for search. If the request targets a data stream, it refreshes the stream’s backing
    # indices.
    client.indices.refresh(index=index_name)
    resp = client.search(index=index_name, query={"match_all": {}})
    n_docs = resp['hits']['total']['value']
    print("Successfully placed {} documents on the index {name}.\n".format(n_docs, name=index_name))


def copy_docs_from_to(client: Elasticsearch, source_index: str, dest_index: str):
    print("Copying documents from {} to {}...".format(source_index, dest_index))
    if not client.indices.exists(index=source_index):
        print("Source index {name} does not exist. Program will end.".format(name=source_index))
        exit(0)
    if not client.indices.exists(index=dest_index):
        print("Destination index {name} does not exist. Program will end.".format(name=dest_index))
        exit(0)

    resp = client.reindex(source={"index": source_index}, dest={"index": dest_index}, refresh=True)
    if resp["updated"] > 0:
        print("WARNING: Out of {} documents from the index {}, {} of them was/were discarded.\n".format(resp["total"],
                                                                                                        source_index,
                                                                                                        resp[
                                                                                                            "updated"]))
        return False
    else:
        print(
            "All {} documents from index {} were successfully placed to index {}.\n".format(resp["total"], source_index,
                                                                                            dest_index))
        return True


def create_index_missing_for_docs(client: Elasticsearch, tsdb_index: str, overwritten_docs_index: str):
    create_index(client, overwritten_docs_index)

    pipelines = IngestClient(client)
    pipeline_name = 'get-missing-docs'
    pipelines.put_pipeline(id=pipeline_name, body={
        'description': "Drop all documents that were not overwritten.",
        "processors": [
            {
                "drop": {
                    "if": "ctx._version == 1"
                }
            }
        ]
    })

    dest = {
        "index": overwritten_docs_index,
        "version_type": "external",
        "pipeline": pipeline_name
    }

    client.reindex(source={"index": tsdb_index}, dest=dest, refresh=True)


def get_missing_docs_info(client: Elasticsearch, index_name: str, dimensions: [], max_docs: int = 10):
    body = {
        'size': max_docs,
        'query': {
            'match_all': {}
        }
    }

    res = client.search(index=index_name, body=body)
    print("The timestamp and dimensions of the first {} overwritten documents are:".format(max_docs))
    for doc in res["hits"]["hits"]:
        print("- Timestamp {}:".format(doc["_source"]["@timestamp"]))
        for dimension in dimensions:
            el = doc["_source"]
            keys = dimension.split(".")
            for key in keys:
                if key not in el:
                    el = "(Missing value)"
                    break
                el = el[key]
            print("\t{} = {}".format(dimension, el))

        #for dimension in dimensions:
        #    print("\t{} = {}".format(dimension, doc["_source"][dimension]))


def get_dimensions(client: Elasticsearch, tsdb_index: str):
    settings = client.indices.get_settings(index=tsdb_index)
    if "routing_path" in settings[tsdb_index]['settings']['index']:
        dimensions = settings[tsdb_index]['settings']['index']['routing_path']
        print("Dimensions of the index {} are {}.".format(tsdb_index, dimensions))
        return dimensions
    else:
        print("Dimensions are not defined for index {}. Program will end.".format(tsdb_index))
        exit(0)


def copy_index(client: Elasticsearch, original_index: str, copy_index: str, max_docs: int = 3000):
    if not client.indices.exists(index=original_index):
        print("\tIndex", original_index, "does not exist. Program will end.")
        exit(0)

    print("Creating index {}...".format(copy_index))
    if client.indices.exists(index=copy_index):
        print("\tIndex", copy_index, "exists and will be deleted.")
        client.indices.delete(index=copy_index)

    content = client.indices.get_mapping(index=original_index)
    mappings = content[original_index]["mappings"]
    client.indices.create(index=copy_index, mappings=mappings)
    print("Index {name} successfully created.".format(name=copy_index))

    resp = client.reindex(source={"index": original_index}, dest={"index": copy_index}, refresh=True, max_docs=max_docs)
    print("Copied {} documents to index {name}.\n".format(resp["created"], name=copy_index))
