# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

from utils.utils import *

# Just to disable ES warning about hidden indices
import warnings

warnings.filterwarnings("ignore")

# Variables to configure the ES client:
elasticsearch_host = "https://localhost:9200"
elasticsearch_ca_path = "/home/c/.elastic-package/profiles/default/certs/elasticsearch/ca-cert.pem"
elasticsearch_user = "elastic"
elasticsearch_pwd = "changeme"

# If you are running on cloud, you should set these two. If they are not empty, then the client will connect
# to the cloud using these variables, instead of the above ones.
elastic_pwd = ""
cloud_id = ""

# There NEEDS to be fields with time_series_dimension: true.
data_stream = "metrics-istio.istiod_metrics-default"  # metrics-docker.cpu-default"

if __name__ == '__main__':
    # Create the client instance
    client = get_client(elasticsearch_host, elasticsearch_ca_path, elasticsearch_user, elasticsearch_pwd, cloud_id, elastic_pwd)
    print("You're testing with version {}.\n".format(client.info()["version"]["number"]))

    all_placed = copy_from_data_stream(client, data_stream)

    ## Is running this function too slow? Please set the number of max documents as this:
    ## all_placed = copy_from_data_stream(client, data_stream, max_docs=5000)

    # Did you change the mappings of the data stream and still want to use the documents from one index
    # but the settings/mappings of the other? You can set the index for each one like this:
    # all_placed = copy_from_data_stream(client, data_stream, docs_index=0,settings_index=1)
    # Note: an index 000001, has the docs_index has 0; an index 000002, has the docs_index 1, and so on.

    if not all_placed:
        print("Index for the overwritten documents will be created...")
        create_index_missing_for_docs(client)
        get_missing_docs_info(client)
