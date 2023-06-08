## Example explained

There are three documents that will be used in this example:

![img.png](img.png)

The field `name` will be set as dimension for the TSDB index and `age` will be set as counter.
Since two of the documents are identified by the same dimension (`name: Joana`), only two
of the three documents will be part of the TSDB index.


## Algorithm

1. Create index in standard mode, ie, TSDB disabled:
```python
create_index(client, source_index, source_mappings_path)
```
> **Note**: there is no need to delete this index if running the function multiple times.
Before the index is created, the function checks if there is an index with that name
and deletes it if the case. This way we make sure we are always testing with an empty
index with the custom mappings.

2. Place the three sample documents in the newly created index:
```
place_documents(client, source_index, documents_path)
```

3. Create new index in TSDB mode:
```
create_index(client, dest_index, dest_mappings_path)
```
> **Note**: same as explained in point 1.

4. Copy documents from standard index to TSDB index:
```
copy_docs_from_to(client, source_index, dest_index)
```
> **Note**: we need to know the document version to know if a document was overwritten or not.
> Unfortunately, the version field is not searchable, so we will have to create yet a new index.

5. **If documents were overwritten**, ie, lost, then a new index is created and all the overwritten
documents IDs will be printed:
```
create_index_missing_for_docs(client, dest_index, overwritten_docs_index)
get_docs_ids(client, overwritten_docs_index)
```

## Example results

> **Note**: I have the three indexes created, so they will all be deleted and newly recreated.
> I am also using ES version `8.8.0-SNAPSHOT`, so this will all be viewed in the printed lines.

Running the `main.py` file will produce a result similar to this one:

```console
You're testing with version 8.8.0-SNAPSHOT.

Creating index source-tsdb-disabled...
	Index source-tsdb-disabled exists and will be deleted.
	No settings were defined for index source-tsdb-disabled. Default settings will be used.
Index source-tsdb-disabled successfully created.

Placing documents on the index source-tsdb-disabled...
Successfully placed 3 documents on the index source-tsdb-disabled.

Creating index dest-tsdb-enabled...
	Index dest-tsdb-enabled exists and will be deleted.
Index dest-tsdb-enabled successfully created.

Copying documents from source-tsdb-disabled to dest-tsdb-enabled...
WARNING: Out of 3 documents from the index source-tsdb-disabled, 1 of them was/were discarded.

Index for the overwritten documents will be created...
Creating index overwritten-docs...
	No mappings were defined for index overwritten-docs. Default mappings will be used.
	No settings were defined for index overwritten-docs. Default settings will be used.
Index overwritten-docs successfully created.

The ID of the first 10 overwritten documents is:
 - V2uiLWxxhlgtT1jmAAADuj2ODQA
```




