# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

from utils.utils import *

elasticsearch_host = "https://localhost:9200"
elasticsearch_ca_path = "/home/c/.elastic-package/profiles/default/certs/elasticsearch/ca-cert.pem"
elasticsearch_user = "elastic"
elasticsearch_pwd = "changeme"

source_index = "source-tsdb-disabled"
source_mappings_path = "mappings/source-mappings.json"
documents_path = "sampleDocs"

dest_index = "dest-tsdb-enabled"
dest_mappings_path = "mappings/dest-mappings.json"
dest_settings_path = "mappings/dest-settings.json"

overwritten_docs_index = "overwritten-docs"

# 1. Create source index given name @source_index and mappings/settings from @source_mappings_path.
# 2. Place documents from folder @documents_path in the source index.
# 3. Delete (if exists) and create destination index named @dest_index with mappings/settings from @dest_mappings_path.
# 4. Get X files from source index.
# 5. Put documents in the destination index.
# 6. Compare the number of documents between the two indices.
if __name__ == '__main__':
    # Create the client instance
    client = get_client(elasticsearch_host,elasticsearch_ca_path, elasticsearch_user, elasticsearch_pwd)
    print("You're testing with version {}.\n".format(client.info()["version"]["number"]))

    # Create source index given name @source_index and mappings/settings from @source_mappings_path.
    create_index(client, source_index, source_mappings_path)

    # Place documents from folder @documents_path in the source index.
    place_documents(client, source_index, documents_path)

    # Delete (if exists) and create destination index named @dest_index with mappings/settings from @dest_mappings_path.
    create_index(client, dest_index, dest_mappings_path, dest_settings_path)

    dimensions = get_dimensions(client, dest_index)

    # Copy docs from index @source_index to index @dest_index
    all_placed = copy_docs_from_to(client, source_index, dest_index)

    if not all_placed:
        print("Index for the overwritten documents will be created...")
        create_index_missing_for_docs(client, dest_index, overwritten_docs_index)
        get_missing_docs_info(client, overwritten_docs_index, dimensions)

