**This program was build and tested with Python version 3.10.**

This repository contains the code to a new approach for testing
TSDB migration. 

## Table of Contents

* [Installation](#installation)
* [Requirements](#requirements)
* [Set up](#set-up)
* [Run](#run)
* [Algorithm](#algorithm)
* [Understanding the program](#understanding-the-program)
* [Realistic output example](#realistic-output-example)
* [Testing the dashboard](#testing-the-dashboard)
* [Other questions](#other-questions)


## Installation

You need to install the [Python client for ElasticSearch](https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/installation.html):
```console
python -m pip install elasticsearch
```


## Requirements

1. You need to be running Elasticsearch.
2. You need a data stream with at least one field set as dimension.


## Set up

This set up is only to set the default values through the `main.py` file. If
you rather do this through the command line, skip this and refer to [run](#run).

You need to set the variables in the `main.py` file for the ES python client:

```python
# Variables to configure the ES client:
"elasticsearch_host": "https://localhost:9200",
"elasticsearch_ca_path": "/home/c/.elastic-package/profiles/default/certs/elasticsearch/ca-cert.pem",
"elasticsearch_user": "elastic",
"elasticsearch_pwd": "changeme",

# If you are running on cloud, you should set these two. If they are not empty, then the client will connect
# to the cloud using these variables, instead of the ones above.
"cloud_pwd": "",
"cloud_id": "",
```

You also need to set the name of the data stream you want to test:
```python
# Name of the data stream to test
"data_stream": "metrics-aws.s3_storage_lens-default",
```

Additionally, the `main.py` has defaults for:
- The number of documents you want to copy from the TSDB disabled index. Change
 the parameter `max_docs`:
   ```python
   "max_docs": 10000
   ```
  `-1` indicates that all documents from the index must be placed to the TSDB index.
    > **Note**: If you are trying to copy many documents, you migh run into this error:
    > ```console
    > elastic_transport.ConnectionTimeout: Connection timed out
    > ```
    > This happens because the elasticsearch python client has a default timeout
    that was not changed in this testing kit. Setting `max_docs` to a lower value
    will be enough to make that error disappear.
- The index number from the data stream you want to use to retrieve the documents,
and the index number for the index you want to use for the settings and mappings:
   ```python
   "docs_index": 1,
   "settings_mappings_index": 3,
  ```
  
   Confused by this? Imagine a data stream with two indices:

   ![img_2.png](images/img_2.png)

   By default, the first index of the data stream is always used as the one
   that has the documents. The last index is the default for the settings/mappings.
   This way, if you changed the data stream to include one existent field as dimension,
   you will not have to restart sending the documents, and can just use the data
   that is already there. In the program, these defaults are, for both parameters,
    indicated by `-1`.




- Do you want to get in a local directory some of the files that are being overwritten?
Set these variables:
    ```python
    # Name of the directory to place files.
    "directory_overlapping_files": "overwritten-docs" + "-" + program_defaults["data_stream"],

    # Do you want to get in your @directory_overlapping_files the files that are overlapping?
    # Set this to True and delete the directory named directory_overlapping_files if it already exists!
    "get_overlapping_files": True,
    ```
  > **Note**: The directory should not exist! Otherwise, the files will not be placed, since we are
not deleting the directory. A warning will be shown indicating that the files
were not placed:
    > ```commandline
    > WARNING: The directory overwritten-docs exists. Please delete it. Documents will not be placed.
    > ```
  If the documents are placed, your project structure will be
similar to this:
![img.png](images/img.png)
    
    And then you can just compare the files and see which fields should habe
been set as dimension!

    > **Note**: By default, the program will only create 10 folders
for the first 10 set of dimensions causing loss of data. For each of
these folders, it will only get two documents that are overlapping - this
does not mean that there are no more documents overlapping for those
set of dimensions. If you want to change these default values, have a look at:
    > ```python
    > # How many sets of dimensions do you want to print that are causing loss of data?
    > # This value also indicates how many directories will be created in case get_overlapping_files is set to True.
    > "display_docs": 10,
    > # How many documents you want to retrieve per set of dimensions causing a loss of data?
    > "copy_docs_per_dimension": 2
    > ```
    
    


## Run

After settings the values for all the variables, just run the python program:

```python
python main.py
```

If you prefer to set the parameters values through the command line run:

```python
python main.py --help
```

To see the options. The default values are also displayed.

Example:

```python
python main.py --get_overlapping_files False --max_docs 40000
```

## Algorithm


![img.png](images/algorithm.png)

The algorithm for the program is as follows:
1. Given the data stream name, we get all its indices.
2. Given the documents index number provided by the user (or the default, 0), we obtain the index
name from the list we got on step 1.
3. Given the settings/mappings index number provided by the user (or the default,
the last index available in the data stream),
we obtain the index name from the list we got on step 1.
4. We retrieve the mappings and settings from the index we got on step 3.
5. We update those same settings so TSDB is enabled.
6. We create a new index given the settings and mappings. This index has
TSDB enabled.
7. We place the documents in index obtained on step 2 on our
TSDB enabled new index.
8. We compare if the number of files placed in the TSDB index is the same
as the number of files we retrieved from the documents index.
9. If it is the same, the program ends.
10. Otherwise, we will place all updated documents in a new index.
11. The dimensions and timestamp of the documents in this new index
will be displayed in the output.


## Understanding the program

Please refer to the [sample](sample/README.md) to understand the basics of it.

## Realistic output example

<details>
<summary>
In case TSDB migration was successful, ie, no loss of data occurred.
</summary>

```console
You're testing with version 8.8.0-SNAPSHOT.

Testing data stream metrics-aws.usage-default.
Index being used for the documents is .ds-metrics-aws.usage-default-2023.06.29-000001.
Index being used for the settings and mappings is .ds-metrics-aws.usage-default-2023.06.29-000001.

The time series fields for the TSDB index are: 
	- dimension (7 fields):
		- agent.id
		- aws.dimensions.Class
		- aws.dimensions.Resource
		- aws.dimensions.Service
		- aws.dimensions.Type
		- cloud.account.id
		- cloud.region
	- gauge (2 fields):
		- aws.usage.metrics.CallCount.sum
		- aws.usage.metrics.ResourceCount.sum
	- routing_path (7 fields):
		- agent.id
		- aws.dimensions.Class
		- aws.dimensions.Resource
		- aws.dimensions.Service
		- aws.dimensions.Type
		- cloud.account.id
		- cloud.region

Index tsdb-index-enabled successfully created.

Copying documents from .ds-metrics-aws.usage-default-2023.06.29-000001 to tsdb-index-enabled...
All 5000 documents taken from index .ds-metrics-aws.usage-default-2023.06.29-000001 were successfully placed to index tsdb-index-enabled.
```
</details>

<details>
<summary>
In case TSDB migration was not successful.
</summary>

```console
You're testing with version 8.8.0-SNAPSHOT.

Testing data stream metrics-aws.usage-default.
Index being used for the documents is .ds-metrics-aws.usage-default-2023.06.29-000001.
Index being used for the settings and mappings is .ds-metrics-aws.usage-default-2023.06.29-000001.

The time series fields for the TSDB index are: 
	- dimension (7 fields):
		- agent.id
		- aws.dimensions.Class
		- aws.dimensions.Resource
		- aws.dimensions.Service
		- aws.dimensions.Type
		- cloud.account.id
		- cloud.region
	- gauge (2 fields):
		- aws.usage.metrics.CallCount.sum
		- aws.usage.metrics.ResourceCount.sum
	- routing_path (7 fields):
		- agent.id
		- aws.dimensions.Class
		- aws.dimensions.Resource
		- aws.dimensions.Service
		- aws.dimensions.Type
		- cloud.account.id
		- cloud.region

Index tsdb-index-enabled successfully created.

Copying documents from .ds-metrics-aws.usage-default-2023.06.29-000001 to tsdb-index-enabled...
WARNING: Out of 10000 documents from the index .ds-metrics-aws.usage-default-2023.06.29-000001, 152 of them were discarded.

Overwritten documents will be placed in new index.
Index tsdb-overwritten-docs successfully created.

The timestamp and dimensions of the first 10 overwritten documents are:
- Timestamp 2023-06-29T13:24:00.000Z:
	agent.id: 178edbcb-2132-497d-b6da-e8c7d8095a90
	aws.dimensions.Class: None
	aws.dimensions.Resource: Spot
	aws.dimensions.Service: Fargate
	aws.dimensions.Type: Resource
	cloud.account.id: 627286350134
	cloud.region: eu-north-1
- Timestamp 2023-06-29T13:24:00.000Z:
	agent.id: 178edbcb-2132-497d-b6da-e8c7d8095a90
	aws.dimensions.Class: None
	aws.dimensions.Resource: Spot
	aws.dimensions.Service: Fargate
	aws.dimensions.Type: Resource
	cloud.account.id: 627286350134
	cloud.region: ap-southeast-1
- Timestamp 2023-06-29T13:24:00.000Z:
	agent.id: 178edbcb-2132-497d-b6da-e8c7d8095a90
	aws.dimensions.Class: None
	aws.dimensions.Resource: OnDemand
	aws.dimensions.Service: Fargate
	aws.dimensions.Type: Resource
	cloud.account.id: 627286350134
	cloud.region: us-east-2
- Timestamp 2023-06-29T13:24:00.000Z:
	agent.id: 178edbcb-2132-497d-b6da-e8c7d8095a90
	aws.dimensions.Class: None
	aws.dimensions.Resource: OnDemand
	aws.dimensions.Service: Fargate
	aws.dimensions.Type: Resource
	cloud.account.id: 627286350134
	cloud.region: eu-north-1
- Timestamp 2023-06-29T13:24:00.000Z:
	agent.id: 178edbcb-2132-497d-b6da-e8c7d8095a90
	aws.dimensions.Class: None
	aws.dimensions.Resource: OnDemand
	aws.dimensions.Service: Fargate
	aws.dimensions.Type: Resource
	cloud.account.id: 627286350134
	cloud.region: ap-southeast-1
- Timestamp 2023-06-29T13:24:00.000Z:
	agent.id: 178edbcb-2132-497d-b6da-e8c7d8095a90
	aws.dimensions.Class: None
	aws.dimensions.Resource: TableCount
	aws.dimensions.Service: DynamoDB
	aws.dimensions.Type: Resource
	cloud.account.id: 627286350134
	cloud.region: us-east-1
- Timestamp 2023-06-29T13:24:00.000Z:
	agent.id: 178edbcb-2132-497d-b6da-e8c7d8095a90
	aws.dimensions.Class: None
	aws.dimensions.Resource: ListMetrics
	aws.dimensions.Service: CloudWatch
	aws.dimensions.Type: API
	cloud.account.id: 627286350134
	cloud.region: eu-west-1
- Timestamp 2023-06-29T13:24:00.000Z:
	agent.id: 178edbcb-2132-497d-b6da-e8c7d8095a90
	aws.dimensions.Class: None
	aws.dimensions.Resource: ListMetrics
	aws.dimensions.Service: CloudWatch
	aws.dimensions.Type: API
	cloud.account.id: 627286350134
	cloud.region: eu-west-2
- Timestamp 2023-06-29T13:24:00.000Z:
	agent.id: 178edbcb-2132-497d-b6da-e8c7d8095a90
	aws.dimensions.Class: None
	aws.dimensions.Resource: ListMetrics
	aws.dimensions.Service: CloudWatch
	aws.dimensions.Type: API
	cloud.account.id: 627286350134
	cloud.region: eu-west-3
- Timestamp 2023-06-29T13:24:00.000Z:
	agent.id: 178edbcb-2132-497d-b6da-e8c7d8095a90
	aws.dimensions.Class: None
	aws.dimensions.Resource: ListMetrics
	aws.dimensions.Service: CloudWatch
	aws.dimensions.Type: API
	cloud.account.id: 627286350134
	cloud.region: sa-east-1
```

</details>


## Testing the dashboard

Are you sure you want to test a dashboard?...

Unfortunately, there is no automation for a dashboard.
You have a tiring and repetitive process in front of you:

1. Create a data view for the TSDB index:

  ![img.png](images/img_3.png)

> **Note**: The TSDB index will be deleted and recreated every time you
> run the program. It is also a hidden index, in case you are having
> trouble finding it.


2. Go to the dashboard you wish to text, and for every visualization
change the data view to the one you just created:

   ![img.png](images/img_1.png)


## Other questions

**Is TSDB enabled in the index I use for the documents?**

The index you use for documents is obtained in this line:
```python
all_placed = copy_from_data_stream(...)
```
In this, it would be the default, which is 0. If you set your own
`docs_index`, then that one will be used.

It does not matter if TSDB is enabled or not. The program will only
use this index to retrieve documents, so as long as there is data,
nothing should go wrong.

However, does it make sense to use an index with TSDB enabled to retrieve
the documents? If you are testing the dimensions, then the overlap
of data already occurred as soon as the documents were placed in the
index.


**Is TSDB enabled in the index I use for the settings/mappings?**

It does not matter, as long as you have dimensions valid to be part of
the routing path.


**What is the name of the index where we are placing the documents
with TSDB enabled?**

The index is named `tsdb-index-enabled`. You should be able to see this information
in the output messages.


**What is the name of the index where we are placing the overwritten
documents?**

The index is named `tsdb-overwritten-docs`. You should be able to see this information
in the output messages.


**Where are the defaults for every index created and everything else
related to TSDB?**

The defaults are in `utils/tsdb.py`. Each one has a comment that
should be clear enough to understand.



