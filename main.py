# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

from utils.utils import *

# Just to disable ES warning about hidden indices
import warnings
warnings.filterwarnings("ignore")

# Variables to configure the ES client
elasticsearch_host = "https://localhost:9200"
elasticsearch_ca_path = "/home/c/.elastic-package/profiles/default/certs/elasticsearch/ca-cert.pem"
elasticsearch_user = "elastic"
elasticsearch_pwd = "changeme"

# There NEEDS to be fields with time_series_dimension: true.
data_stream = "metrics-docker.cpu-default"


if __name__ == '__main__':
    # Create the client instance
    client = get_client(elasticsearch_host, elasticsearch_ca_path, elasticsearch_user, elasticsearch_pwd)
    print("You're testing with version {}.\n".format(client.info()["version"]["number"]))

    all_placed = copy_from_data_stream(client, data_stream)

    if not all_placed:
        print("Index for the overwritten documents will be created...")
        create_index_missing_for_docs(client)
        get_missing_docs_info(client)

