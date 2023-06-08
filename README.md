## Algorithm

1. Create a new index with the same mappings as the source index, ie, 
the one with TSDB disabled:
```python

```
> **Note**: This newly index is a copy of the source index. We need to create it
> so we can have a fixed number of documents to make the tests.
> Otherwise, we might be trying to use an index that is still being updated 
> (e.g. integration can still be running).

2. Place all documents from the source index in the newly created one:
```python

```


## Troubleshoot

```python
elasticsearch.BadRequestError: BadRequestError(400, "{'took': 1, 'timed_out': False, 'total': 1, 'updated': 0, 'created': 0, 'deleted': 0, 'batches': 1, 'version_conflicts': 0, 'noops': 0, 'retries': {'bulk': 0, 'search': 0}, 'throttled_millis': 0, 'requests_per_second': -1.0, 'throttled_until_millis': 0, 'failures': [{'index': 'index-tsdb-enabled', 'cause': {'type': 'document_parsing_exception', 'reason': '[1:2513] failed to parse: time series index @timestamp value [2023-06-07T12:48:00Z] must be larger than 2023-06-07T14:30:45Z', 'caused_by': {'type': 'illegal_argument_exception', 'reason': 'time series index @timestamp value [2023-06-07T12:48:00Z] must be larger than 2023-06-07T14:30:45Z'}}, 'status': 400}]}")
```
Check this part of the file:
```json
        "time_series": {
          "end_time": "2023-06-07T18:30:45.000Z",
          "start_time": "2023-06-07T14:30:45.000Z"
        },
```

Update it.