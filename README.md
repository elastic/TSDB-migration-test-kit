## Installation

You need to install the [Python client for ElasticSearch](https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/installation.html):
```console
python -m pip install elasticsearch
```

## Requirements

1. You need to be running ElasticSearch.
2. You need a data stream with at least one field setted as dimension.


## Set up

You need to set the variables in the `main.py` file:

```python
# Variables to configure the ES client
elasticsearch_host = "https://localhost:9200"
elasticsearch_ca_path = "/home/c/.elastic-package/profiles/default/certs/elasticsearch/ca-cert.pem"
elasticsearch_user = "elastic"
elasticsearch_pwd = "changeme"

# There NEEDS to be fields with time_series_dimension: true.
data_stream = "metrics-docker.cpu-default"
```

The program should be ready to run after.

## Example

Refer to [sample](sample/README.md).