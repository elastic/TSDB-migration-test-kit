from utils.utils import *

elasticsearch_host = "https://localhost:9200"
elasticsearch_ca_path = "/home/c/.elastic-package/profiles/default/certs/elasticsearch/ca-cert.pem"
elasticsearch_user = "elastic"
elasticsearch_pwd = "changeme"

sample_index_template_name = "test-tsdb-template-sample"
template_path = "templates/index-template.json"

# !! Do NOT change this name. The index pattern is matching the one from the sample template.
data_stream_name = "test-tsdb-sample"

documents_path = "sampleDocs"

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
        print("Index for the overwritten documents will be created...")
        create_index_missing_for_docs(client)
        get_missing_docs_info(client)
