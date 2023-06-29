from utils.es import *

elasticsearch_host = "https://localhost:9200"
elasticsearch_ca_path = "/home/c/.elastic-package/profiles/default/certs/elasticsearch/ca-cert.pem"
elasticsearch_user = "elastic"
elasticsearch_pwd = "changeme"

sample_index_template_name = "test-tsdb-template-sample"
template_path = "templates/index-template.json"

# !! Do NOT change this name. The index pattern is matching the one from the sample template.
data_stream_name = "test-tsdb-sample"

documents_path = "sampleDocs"


def get_file_content(file_name: str):
    """
    Get the content of JSON file.
    """
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


def prepare_set_up(client: Elasticsearch, data_stream_name: str, index_template_name: str, index_template_path: str):
    """
    Create new data stream and place documents in the data stream.
    :param client: ES client.
    :param data_stream_name: name of the data stream.
    :param index_template_name: name of the index template.
    :param index_template_path: path to the index template.
    """
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


if __name__ == '__main__':
    # Create the client instance
    client = get_client(elasticsearch_host, elasticsearch_ca_path, elasticsearch_user, elasticsearch_pwd)
    print("You're testing with version {}.\n".format(client.info()["version"]["number"]))

    # To reproduce something similar to what we need to test,
    # we will create a new index template @sample_index_template_name based on the file @template_path.
    # After that we create a new data stream that will have the same index pattern as the index template expects.
    prepare_set_up(client, data_stream_name, sample_index_template_name, template_path)

    # Now we copy all documents from the folder @documents_path to the data_stream @data_stream_name
    place_documents(client, data_stream_name, documents_path)

    all_placed = copy_from_data_stream(client, data_stream_name)

    if not all_placed:
        print("Overwritten documents will be placed in new index.")
        create_index_missing_for_docs(client)
        get_missing_docs_info(client)
