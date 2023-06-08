# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

from utils.utils import *

# Just to disable ES warning about hidden indices
import warnings
warnings.filterwarnings("ignore")

elasticsearch_host = "https://localhost:9200"
elasticsearch_ca_path = "/home/c/.elastic-package/profiles/default/certs/elasticsearch/ca-cert.pem"
elasticsearch_user = "elastic"
elasticsearch_pwd = "changeme"

# This is the standard index with all the documents
source_index = ".ds-metrics-gcp.loadbalancing_metrics-default-2023.06.08-000001"
# This is a copy of the source index.
# Important: we create a copy, so we can have a stable number of documents to make the tests. Otherwise, we might
# be trying to use an index that is still being updated (e.g. integration can still be running)
copy_source_index = source_index + "-copy"

tsdb_index = "index-tsdb-enabled"
tsdb_mappings_path = "tsdb-mappings.json"
tsdb_settings_path = "tsdb-settings.json"

overwritten_docs_index = "tsdb-overwritten-docs"

if __name__ == '__main__':
    # Create the client instance
    client = get_client(elasticsearch_host, elasticsearch_ca_path, elasticsearch_user, elasticsearch_pwd)
    print("You're testing with version {}.\n".format(client.info()["version"]["number"]))

    # Create a copy of the source index
    # Default max number of docs for this function is 3000
    copy_index(client, source_index, copy_source_index, 10)
    # To add a different number (e.g., 1000 docs) just do this:
    # copy_index(client, source_index, copy_source_index, 1000)

    create_index(client, tsdb_index, tsdb_mappings_path, tsdb_settings_path)

    dimensions = get_dimensions(client, tsdb_index)

    # Copy docs from index @copy_source_index to index @tsdb_index
    all_placed = copy_docs_from_to(client, copy_source_index, tsdb_index)

    if not all_placed:
        print("Index for the overwritten documents will be created...")
        create_index_missing_for_docs(client, tsdb_index, overwritten_docs_index)
        get_missing_docs_info(client, overwritten_docs_index, dimensions)



