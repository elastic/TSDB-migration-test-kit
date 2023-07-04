from utils.es import *
import argparse

program_defaults = {
    # Variables to configure the ES client:
    "elasticsearch_host": "https://localhost:9200",
    "elasticsearch_ca_path": "/home/c/.elastic-package/profiles/default/certs/elasticsearch/ca-cert.pem",
    "elasticsearch_user": "elastic",
    "elasticsearch_pwd": "changeme",

    # If you are running on cloud, you should set these two. If they are not empty, then the client will connect
    # to the cloud using these variables, instead of the ones above.
    "cloud_pwd": "",
    "cloud_id": "",

    # Name of the data stream to test
    "data_stream": "metrics-aws.usage-default",

    # docs_index: number of the index to use to retrieve the documents. -1 indicates the default will be used,
    # which would be 0 - indicating the first index of the data stream
    # settings_mappings_index: number of the index to use to get the mappings and settings for the TSDB index.
    # -1 indicates the default will be used, which is the last index of the data stream.
    # Note: We use -1 because we do not know how many indices a data stream has at this moment. Even though
    # we could set the default of docs_index to 0 because it is guaranteed that the default (first index) exists,
    # we use -1 to keep consistency.
    # Important: count starts at 0.
    # Example: an index 000001, has the index 0; an index 000002, has the index 1, and so on.
    "docs_index": -1,
    "settings_mappings_index": -1,

    # Maximum documents to be reindexed to the new TSDB index. -1 indicates that we should reindex all documents.
    # Tip: Is reindexing too slow or encountering a timeout? Set this value.
    "max_docs": -1

}

program_defaults |= {
    # Name of the directory to place files.
    "directory_overlapping_files": "overwritten-docs" + "-" + program_defaults["data_stream"],

    # Do you want to get in your @directory_overlapping_files the files that are overlapping?
    # Set this to True and delete the directory named directory_overlapping_files if it already exists!
    "get_overlapping_files": True,

    # How many sets of dimensions do you want to print that are causing loss of data?
    # This value also indicates how many directories will be created in case get_overlapping_files is set to True.
    "display_docs": 10,
    # How many documents you want to retrieve per set of dimensions causing a loss of data?
    "copy_docs_per_dimension": 2
}


def get_cmd_arguments():
    parser = argparse.ArgumentParser(description='Process command line arguments.',
                                     formatter_class=argparse.RawTextHelpFormatter)

    # ES variables
    parser.add_argument('--elasticsearch_host', action="store", dest='elasticsearch_host',
                        default=program_defaults["elasticsearch_host"],
                        help="Elasticsearch host.\nDefault: " + program_defaults["elasticsearch_host"])

    parser.add_argument('--elasticsearch_ca_path', action="store", dest='elasticsearch_ca_path',
                        default=program_defaults["elasticsearch_ca_path"],
                        help="Location of the Elasticsearch certificate.\nDefault: "
                             + program_defaults["elasticsearch_ca_path"])
    parser.add_argument('--elasticsearch_user', action="store", dest='elasticsearch_user',
                        default=program_defaults["elasticsearch_user"],
                        help="Name of the Elasticsearch user.\nDefault: " + program_defaults["elasticsearch_user"])
    parser.add_argument('--elasticsearch_pwd', action="store", dest='elasticsearch_pwd',
                        default=program_defaults["elasticsearch_pwd"],
                        help="Elasticsearch password.\nDefault: " + program_defaults["elasticsearch_pwd"])

    # Cloud variables
    parser.add_argument('--cloud_id', action="store", dest='cloud_id', default=program_defaults["cloud_id"],
                        help="The ID for Elastic Cloud. If set, it will overwrite every elasticsearch_* argument."
                             "\nDefault: " + program_defaults["cloud_id"])
    parser.add_argument('--cloud_pwd', action="store", dest='cloud_pwd', default=program_defaults["cloud_pwd"],
                        help="The password for Elastic Cloud. If set, it will overwrite every elasticsearch_* argument."
                             "\nDefault: " + program_defaults["cloud_pwd"])

    # Data stream name
    parser.add_argument('--data_stream', action="store", dest='data_stream', default=program_defaults["data_stream"],
                        help="The name of the data stream to migrate to TSDB.\nDefault: "
                             + program_defaults["data_stream"])

    # Reindex variables
    if program_defaults["docs_index"] == -1:
        default = "First index of the data stream"
    else:
        default = str(program_defaults["docs_index"])
    parser.add_argument('--docs_index', action="store", dest='docs_index', default=program_defaults["docs_index"],
                        help="The data stream index number to be used to retrieve the documents. "
                             "Count starts at 0. This means the index 0001 has docs_index 0, index 0002 has"
                             "the docs_index 1 and so on.\nDefault: " + default)

    if program_defaults["settings_mappings_index"] == -1:
        default = "Last index of the data stream"
    else:
        default = str(program_defaults["settings_mappings_index"])
    parser.add_argument('--settings_mappings_index', action="store", dest='settings_mappings_index',
                        default=program_defaults["settings_mappings_index"],
                        help="The data stream index number to be used to retrieve the mappings and settings. "
                             "Count starts at 0. This means the index 0001 has settings_mappings_index 0, index 0002 "
                             "has the settings_mappings_index 1 and so on.\nDefault: " + default)

    if program_defaults["max_docs"] == -1:
        default = "All documents from the data stream index docs_index."
    else:
        default = str(program_defaults["max_docs"])
    parser.add_argument('--max_docs', action="store", dest='max_docs', default=program_defaults["max_docs"],
                        help="The number of documents to retrieve from the index and reindex to the TSDB one."
                             "\nDefault: " + default)

    # Overlapping files configuration
    parser.add_argument('--get_overlapping_files', action="store", dest='get_overlapping_files',
                        default=program_defaults["get_overlapping_files"],
                        help="Flag to place the overwritten documents: documents will be placed if True, otherwise"
                             " if False.\nDefault: " + str(program_defaults["get_overlapping_files"]))
    parser.add_argument('--directory_overlapping_files', action="store", dest='directory_overlapping_files',
                        default=program_defaults["directory_overlapping_files"],
                        help="The directory path to place the overwritten documents.\nDefault: "
                             + program_defaults["directory_overlapping_files"])
    parser.add_argument('--display_docs', action="store", dest='display_docs',
                        default=program_defaults["display_docs"],
                        help="Number of documents overlapping used to display the dimensions."
                             "\nDefault: " + str(program_defaults["display_docs"]))
    parser.add_argument('--copy_docs_per_dimension', action="store", dest='copy_docs_per_dimension',
                        default=program_defaults["copy_docs_per_dimension"],
                        help="Number of documents to retrieve per set of dimensions that caused loss of data."
                             "\nDefault: " + str(program_defaults["copy_docs_per_dimension"]))

    args, unknown = parser.parse_known_args()
    if len(unknown) > 0:
        parser.print_help()
        print("\nUser provided unknown flags:", unknown)
        print("Program will end.")
        exit(0)
    return args


if __name__ == '__main__':
    args = get_cmd_arguments()

    print("Values being used:")
    for arg in vars(args):
        if arg.startswith("elasticsearch_"):
            if args.cloud_id != "" and args.cloud_pwd != "":
                continue
        if arg.startswith("cloud_"):
            if args.cloud_id == "" or args.cloud_pwd == "":
                continue

        if arg == "docs_index" and getattr(args, arg) == -1:
            print("\t{} = {}".format(arg, "First index of the data stream"))
            continue
        if arg == "settings_mappings_index" and getattr(args, arg) == -1:
            print("\t{} = {}".format(arg, "Last index of the data stream"))
            continue
        if arg == "max_docs" and getattr(args, arg) == -1:
            print("\t{} = {}".format(arg, "All documents"))
            continue
        print("\t{} = {}".format(arg, getattr(args, arg)))

    print()

    # Create the client instance
    client = get_client(args.elasticsearch_host, args.elasticsearch_ca_path, args.elasticsearch_user,
                        args.elasticsearch_pwd, args.cloud_id, args.cloud_pwd)
    print("You're testing with version {}.\n".format(client.info()["version"]["number"]))

    # Create TSDB index and place documents
    all_placed = copy_from_data_stream(client, args.data_stream, int(args.docs_index), int(args.settings_mappings_index),
                                       int(args.max_docs))

    # Get overwritten documents information
    if not all_placed:
        print("Overwritten documents will be placed in new index.")
        create_index_missing_for_docs(client)
        get_missing_docs_info(client, args.data_stream, int(args.display_docs), args.directory_overlapping_files,
                              bool(args.get_overlapping_files), int(args.copy_docs_per_dimension))

