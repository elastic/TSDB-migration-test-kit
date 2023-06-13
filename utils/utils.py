import json
import os.path

from elasticsearch import Elasticsearch
from elasticsearch.client import IngestClient

# The TSDB index
tsdb_index = "tsdb-index-enabled"
# This is the index in which we will store the documents that were overwritten - ie, the ones that caused us
# to lose data
overwritten_docs_index = "tsdb-overwritten-docs"


# Create ElasticSearch client
def get_client(elasticsearch_host, elasticsearch_ca_path, elasticsearch_user, elasticsearch_pwd, cloud_id: str,
               elastic_pwd: str):
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


# Get the content of JSON file
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


# Some settings cause an error as they are not known to ElasticSearch Python client.
# This function discards the ones that were causing me error (there might be more!).
def discard_unknown_settings(content_settings: []):
    settings = content_settings["settings"]
    settings["index"].pop("provided_name", None)
    settings["index"].pop("uuid", None)
    settings["index"].pop("creation_date", None)
    if "version" in settings["index"]:
        settings["index"]["version"].pop("created", None)
    return settings


# Given a JSON file, add the document to the index
def add_doc_from_file(client: Elasticsearch, index_name: str, doc_path: str):
    file = open(doc_path)
    content = json.load(file)
    file.close()
    client.index(index=index_name, document=content)


# Place all documents from a folder @folder_docs to the index @index_name
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


def create_index(client: Elasticsearch, index_name: str, mappings: {} = {}, settings: {} = {}):
    print("Creating index {}...".format(index_name))
    if client.indices.exists(index=index_name):
        print("\tIndex", index_name, "exists and will be deleted.")
        client.indices.delete(index=index_name)
    client.indices.create(index=index_name, mappings=mappings, settings=settings)
    print("Index {name} successfully created.\n".format(name=index_name))


# Create an index @overwritten_docs_index to store all the documents that were overwritten on index @tsdb_index
def create_index_missing_for_docs(client: Elasticsearch):
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


def get_missing_docs_info(client: Elasticsearch, max_docs: int = 10):
    body = {'size': max_docs, 'query': {'match_all': {}}}
    res = client.search(index=overwritten_docs_index, body=body)
    dimensions = get_dimensions(client)

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


def get_dimensions(client: Elasticsearch):
    settings = client.indices.get_settings(index=tsdb_index)
    if "routing_path" in settings[tsdb_index]['settings']['index']:
        dimensions = settings[tsdb_index]['settings']['index']['routing_path']
        return dimensions
    else:
        print("Dimensions are not defined for index {}. Program will end.".format(tsdb_index))
        exit(0)


# Append some entry to an object. Needed to add the index mode to the index settings.
def add_entry_to_json(template: {}, settings: {}):
    for key in settings:
        if key in template:
            if len(settings) == 1:
                template[key] = settings[key]
            else:
                add_entry_to_json(template[key], settings[key])
        else:
            template[key] = settings[key]


def copy_docs_from_to(client: Elasticsearch, source_index: str, dest_index: str, max_docs: int):
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
        print("WARNING: Out of {} documents from the index {}, {} of them was/were discarded.\n".format(resp["total"],
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


# Given a data stream, we copy the mappings and settings and modify them for the TSDB index.
def get_tsdb_config(client: Elasticsearch, data_stream_name: str, docs_index: int, settings_index: int):
    tsdb_config_index = "do-not-use"
    clone_template = "clone-template"

    if client.indices.exists(index=tsdb_config_index):
        client.indices.delete_data_stream(tsdb_config_index)

    data_stream = client.indices.get_data_stream(name=data_stream_name)
    n_indexes = len(data_stream["data_streams"][0]["indices"])

    # Get the index from the data stream. We need it to get the settings and mappings.

    if docs_index == -1:
        docs_index = 0
    else:
        if docs_index >= n_indexes:
            print("\tWARNING: Data stream {} has {} indexes. The document index used will be 0 "
                  "instead of the given {}.".format(data_stream_name, n_indexes, docs_index))
            docs_index = 0
        else:
            docs_index = 0

    if settings_index == -1:
        settings_index = n_indexes - 1
    elif settings_index >= n_indexes:
        print("\tWARNING: Data stream {} has {} indexes. The settings index used will be 0 "
              "instead of the given {}.".format(data_stream_name, n_indexes, settings_index))
        settings_index = n_indexes - 1

    docs_index_name = data_stream["data_streams"][0]["indices"][docs_index]["index_name"]
    settings_index_name = data_stream["data_streams"][0]["indices"][settings_index]["index_name"]

    print("\tThe index {} will be used as the standard index for the mappings/settings.".format(settings_index_name))
    mappings = client.indices.get_mapping(index=settings_index_name)[settings_index_name]
    settings = client.indices.get_settings(index=settings_index_name)[settings_index_name]

    # Some settings cause an error on the ES client. This function removes them.
    discard_unknown_settings(settings)
    # Add the time_series mode
    settings["settings"]["index"] |= {"mode": "time_series"}

    # Create a new index template, similar to the standard index template but with TSDB enable
    if client.indices.exists_index_template(name=clone_template):
        client.indices.delete_index_template(name=clone_template)
    client.indices.put_index_template(name=clone_template,
                                      index_patterns=[tsdb_config_index],
                                      data_stream={"allow_custom_routing": "false"},
                                      template=mappings | settings)

    # Create a data stream to obtain the full mappings and settings of the TSDB index.
    # We need this workaround to get the routing_path (ie, the list of our dimensions)
    # since the template cannot determine the value of this field.
    client.indices.create_data_stream(name=tsdb_config_index)
    mappings = client.indices.get_mapping(index=tsdb_config_index)
    settings = client.indices.get_settings(index=tsdb_config_index)
    for key in mappings:
        mappings = mappings[key]["mappings"]
        settings = discard_unknown_settings(settings[key])
        break

    # We change the TSDB time window, just so we don't run into errors.
    time_series = {
        "time_series": {
            "end_time": "2100-06-08T14:41:54.000Z",
            "start_time": "1900-06-08T09:54:18.000Z"
        }
    }
    settings["index"] |= time_series
    add_entry_to_json(settings, time_series)

    # Now that we have the settings and mappings for the TSDB index, we delete the data stream.
    # We won't use our newly created index (and after this line deleted) because it causes
    # problems with conflicts and with reindex.
    client.indices.delete_data_stream(name=tsdb_config_index)
    client.indices.delete_index_template(name=clone_template)

    return docs_index_name, mappings, settings


def copy_from_data_stream(client: Elasticsearch, data_stream_name: str, docs_index: int = -1,
                          settings_index: int = -1, max_docs: int = -1):
    print("Using data stream {} to create new TSDB index {}...".format(data_stream_name, tsdb_index))

    if not client.indices.exists(index=data_stream_name):
        print("\tData stream {} does not exist. Program will end.".format(data_stream_name))
        exit(0)

    # Get the name of the index with the documents, and the mappings and settings for the new TSDB index
    source_index, mappings, settings = get_tsdb_config(client, data_stream_name, docs_index, settings_index)

    # Create the TSDB index
    create_index(client, tsdb_index, mappings, settings)

    # Copy the documents from one index to the other
    return copy_docs_from_to(client, source_index, tsdb_index, max_docs)


# A new index template @index_template_name based on the configuration from the file @index_template_path
# will be created. After that, the data_stream @data_stream_name with the same index pattern is created.
def prepare_set_up(client: Elasticsearch, data_stream_name: str, index_template_name: str, index_template_path: str):
    print("Preparing the setup...")

    print("\tPreparing index template {} from file {}...".format(index_template_name, index_template_path))
    if client.indices.exists_index_template(name=index_template_name):
        print("\t\tIndex template", index_template_name, "exists and will be deleted, along with all its data streams.")
        info = client.indices.get_index_template(name=index_template_name)
        data_streams = info["index_templates"][0]["index_template"]["index_patterns"]
        for data_stream in data_streams:
            client.indices.delete_data_stream(name=data_stream, expand_wildcards="all")
        client.indices.delete_index_template(name=index_template_name)

    print("\tPreparing data stream {}...".format(data_stream_name))
    if client.indices.exists(index=data_stream_name):
        print("\t\tIndices from data stream ", data_stream_name, "exist and will be deleted.")
        client.indices.delete_data_stream(name=data_stream_name, expand_wildcards="all")

    content = get_file_content(index_template_path)
    client.indices.put_index_template(name=index_template_name, body=content)
    print("\tIndex template", index_template_name, "successfully created.")

    client.indices.create_data_stream(name=data_stream_name)
    print("\tData stream", data_stream_name, "successfully created.")
    print("Ready to start.\n")
