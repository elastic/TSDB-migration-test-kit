"""
All functions related to the ES client are placed here.
"""

from elasticsearch import Elasticsearch
from elasticsearch.client import IngestClient

import json
import os.path

from utils.tsdb import *


def get_client(elasticsearch_host, elasticsearch_ca_path, elasticsearch_user, elasticsearch_pwd, cloud_id="",
               elastic_pwd=""):
    """
    Create ES client.
    If cloud values are provided, they will take priority over the local deployment.
    :param elasticsearch_host: ES host.
    :param elasticsearch_ca_path: Path to ES certificate.
    :param elasticsearch_user: Name of the ES user.
    :param elasticsearch_pwd: Password for ES.
    :param cloud_id: Cloud ID. Default is empty.
    :param elastic_pwd: Password for the elastic cloud. Default is empty.
    :return: ES client.
    """
    if cloud_id != "" and elastic_pwd != "":
        print("Client will connect to the cloud.\n")
        return Elasticsearch(
            cloud_id=cloud_id,
            basic_auth=("elastic", elastic_pwd)
        )
    return Elasticsearch(
        hosts=elasticsearch_host,
        ca_certs=elasticsearch_ca_path,
        basic_auth=(elasticsearch_user, elasticsearch_pwd)
    )


def add_doc_from_file(client: Elasticsearch, index_name: str, doc_path: str):
    """
    Given a JSON file, add the document to the index.
    This function does not check if the file exists, since that requirement was already
    checked before it was called.
    :param client: ES client.
    :param index_name: name of the index to place the document.
    :param doc_path: path to the document to add.
    """
    file = open(doc_path)
    content = json.load(file)
    file.close()
    client.index(index=index_name, document=content)


def place_documents(client: Elasticsearch, index_name: str, folder_docs: str):
    """
    Place all documents from folder to an index.
    :param client: ES client.
    :param index_name: name of the index to add the documents.
    :param folder_docs: path to the folder with the documents to add.
    """
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


def create_index(client: Elasticsearch, index_name: str, mappings: {} = {}, settings: {} = {}):
    """
    Create new ES index. If the index already exists, it will be deleted and a new one created.
    :param client: ES client.
    :param index_name: name of the index.
    :param mappings: mappings to be used for the new index. If not specified, default ones will be used.
    :param settings: settings to be used for the new index. If not specified, default ones will be used.
    """
    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)
    client.indices.create(index=index_name, mappings=mappings, settings=settings)
    print("Index {name} successfully created.\n".format(name=index_name))


def create_index_missing_for_docs(client: Elasticsearch):
    """
    Create an index to place all the documents that were updated at least one time.
    :param client: ES client.
    """
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


def build_query(dimensions: {}):
    """
    Build query to retrieve document based on the dimensions.
    :param dimensions: Dictionary containing field and field value.
    :return: query.
    """
    query = {
        "bool": {
            "must": []
        }
    }
    for field in dimensions:
        term = {
            "term": {
                field: dimensions[field]
            }
        }
        query["bool"]["must"].append(term)

    return query


def get_and_place_documents(client: Elasticsearch, data_stream: str, dir_name: str, dimensions_values: {}, n: int, number_of_docs):
    """
    Given the dimensions, place the documents in the directory.
    :param client: ES client.
    :param dir_name: Name of the parent directory.
    :param dimensions_values:
    :param n: Number of the directory inside the parent directory. Example: 1 would create dir_name/1.
    :param number_of_docs: Number of documents to get with that set of dimensions.
    :param index_name: Index name in which documents are stored.
    """
    query = build_query(dimensions_values)

    res = client.search(index=data_stream, query=query, sort={"@timestamp": "asc"}, size=number_of_docs)

    dir_for_docs = os.path.join(dir_name, str(n))
    os.mkdir(dir_for_docs)

    for doc in res["hits"]["hits"]:
        name = doc["_id"] + ".json"
        with open(os.path.join(dir_for_docs, name), 'w') as file:
            json.dump(doc, file, indent=4)


def get_missing_docs_info(client: Elasticsearch, data_stream: str, display_docs: int = 10, dir: str = "",
                          get_overlapping_files: bool = False,
                          copy_docs_per_dimension: int = 2):
    """
    Display the dimensions of the first @display_docs documents.
    If @get_overlapping_files is set to True, then @copy_docs_per_dimension documents will be placed in a directory
    (if the directory does not exist!).
    :param client: ES client.
    :param display_docs: number of documents to display.
    :param dir: name of the directory.
    :param get_overlapping_files: true if you want to place fields in the directory, false otherwise.
    :param copy_docs_per_dimension: number of documents to get for a set of dimensions.
    :param docs_index: name of the index with the documents.
    """
    if get_overlapping_files:
        if os.path.exists(dir):
            print("WARNING: The directory {} exists. Please delete it. Documents will not be placed.\n".format(dir))
            get_overlapping_files = False
        else:
            os.mkdir(dir)
            n = 1

    body = {'size': display_docs, 'query': {'match_all': {}}}
    res = client.search(index=overwritten_docs_index, body=body)
    dimensions = time_series_fields["dimension"]

    print("The timestamp and dimensions of the first {} overwritten documents are:".format(display_docs))
    for doc in res["hits"]["hits"]:
        if get_overlapping_files:
            dimensions_values = {"@timestamp": doc["_source"]["@timestamp"]}

        print("- Timestamp {}:".format(doc["_source"]["@timestamp"]))
        for dimension in dimensions:
            el = doc["_source"]
            keys = dimension.split(".")
            for key in keys:
                if key not in el:
                    el = "(Missing value)"
                    break
                el = el[key]
            print("\t{}: {}".format(dimension, el))
            if el != "(Missing value)" and get_overlapping_files:
                dimensions_values[dimension] = el

        if get_overlapping_files:
            get_and_place_documents(client, data_stream, dir, dimensions_values, n, copy_docs_per_dimension)
            n += 1


def copy_docs_from_to(client: Elasticsearch, source_index: str, dest_index: str, max_docs: int):
    """
    Copy documents from one index to the other.
    :param client: ES client.
    :param source_index: source index with the documents to be copied to a new index.
    :param dest_index: destination index for the documents.
    :param max_docs: max number of documents to copy.
    :return: True if the number of documents is the same in the new index as it was in the old index.
    """
    print("Copying documents from {} to {}...".format(source_index, dest_index))
    if not client.indices.exists(index=source_index):
        print("Source index {name} does not exist. Program will end.".format(name=source_index))
        exit(0)

    if max_docs != -1:
        resp = client.reindex(source={"index": source_index}, dest={"index": dest_index}, refresh=True,
                              max_docs=max_docs)
    else:
        resp = client.reindex(source={"index": source_index}, dest={"index": dest_index}, refresh=True)
    if resp["updated"] > 0:
        print("WARNING: Out of {} documents from the index {}, {} of them were discarded.\n".format(resp["total"],
                                                                                                    source_index,
                                                                                                    resp[
                                                                                                        "updated"]))
        return False
    else:
        print(
            "All {} documents taken from index {} were successfully placed to index {}.\n".format(resp["total"],
                                                                                                  source_index,
                                                                                                  dest_index))
        return True


def get_tsdb_config(client: Elasticsearch, data_stream_name: str, docs_index: int, settings_mappings_index: int):
    """
    Get the index name where documents are placed, and mappings and settings for the new TSDB index.
    :param client: ES client.
    :param data_stream_name:
    :param docs_index: number of the index in the data stream with the documents to be moved to the TSDB index.
    :param settings_mappings_index: number of the index for the settings and mappings for the TSDB index.
    :return: documents index name, settings and mappings for the TSDB index.
    """
    data_stream = client.indices.get_data_stream(name=data_stream_name)
    n_indexes = len(data_stream["data_streams"][0]["indices"])

    # Get the index to use for document retrieval
    if docs_index == -1:
        docs_index = 0
    elif docs_index >= n_indexes:
        print("ERROR: Data stream {} has {} indexes. Documents index number {} is not valid.".format(data_stream_name,
                                                                                                     n_indexes,
                                                                                                     docs_index))
        exit(0)

    # Get index to use for settings/mappings
    if settings_mappings_index == -1:
        settings_mappings_index = n_indexes - 1
    elif settings_mappings_index >= n_indexes:
        print("ERROR: Data stream {} has {} indexes. Settings/mappings index number {} is not valid.".format(
            data_stream_name, n_indexes, settings_mappings_index))
        exit(0)

    docs_index_name = data_stream["data_streams"][0]["indices"][docs_index]["index_name"]
    settings_mappings_index_name = data_stream["data_streams"][0]["indices"][settings_mappings_index]["index_name"]

    print("Index being used for the documents is {}.".format(docs_index_name))
    print("Index being used for the settings and mappings is {}.".format(settings_mappings_index_name))
    print()

    mappings = client.indices.get_mapping(index=settings_mappings_index_name)[settings_mappings_index_name]["mappings"]
    settings = client.indices.get_settings(index=settings_mappings_index_name)[settings_mappings_index_name]["settings"]

    settings = get_tsdb_settings(mappings, settings)

    return docs_index_name, mappings, settings


def copy_from_data_stream(client: Elasticsearch, data_stream_name: str, docs_index: int = -1,
                          settings_mappings_index: int = -1, max_docs: int = -1):
    """
    Given a data stream, it copies the documents retrieved from the given index and places them in a new
    index with TSDB enabled.
    :param client: ES client.
    :param data_stream_name: name of the data stream.
    :param docs_index: number of the index to use to retrieve the documents.
    :param settings_mappings_index: number of the index to use to get the mappings and settings for the TSDB index.
    :param max_docs:
    :return: True if the number of documents placed to the TSDB index remained the same. False otherwise.
    """
    print("Testing data stream {}.".format(data_stream_name))

    if not client.indices.exists(index=data_stream_name):
        print("\tData stream {} does not exist. Program will end.".format(data_stream_name))
        exit(0)

    source_index, mappings, settings = get_tsdb_config(client, data_stream_name, docs_index, settings_mappings_index)

    create_index(client, tsdb_index, mappings, settings)

    return copy_docs_from_to(client, source_index, tsdb_index, max_docs)
