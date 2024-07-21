import logging
from datetime import date as d

import boto3
import yaml

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class ReloadHivePartition:
    """"Class to reload hive partition by table
    """

    _yaml_config = None         # type: dict
    _s3_path = None             # type: list
    _s3_partition = []          # type: list
    _athena_partition = None    # type: list
    _folder = None              # type: str
    _part_year_month = None     # type: str
    _kwargs = None              # type: dict
    _bucket = None              # type: str

    def __init__(self, **kwargs):
        logger.info("Initialize class to Reload Hive Partition")
        self._kwargs = kwargs
        self._read_yaml_file()
        self._set_bucket()

    def reload(self) -> None:
        """"Public method to call the execution order reload partition process

        Return:
            None
        """
        self._get_year_month()

        if self._kwargs:
            prefix = self._kwargs.get('prefix')
            self._process_reload_partition(prefix)
        else:
            prefix = self._yaml_config['prefix']
            self._get_root_prefix(prefix)
            self._process_reload_partition()

    def _process_reload_partition(self) -> None:
        """"Method to execute all the process to reload partition base on the prefix

        Return:
            None
        """

        table = self._yaml_config['table']
        db = table.split(".")[0]
        self._get_s3_prefix_partition()
        if self._s3_partition:
            query = f"SHOW PARTITIONS {table}"
            logger.info(f"Got Partition for {table}")
            response = self._run_query(query, db)
            query_status = self._get_status_query(response['QueryExecutionId'])
            if query_status:
                self._get_athena_partition()
                self._add_athena_partition(table, db)


    def _set_bucket(self) -> None:
        """" get the values from Kwargs , if the bucket are not in arguments, set bucket value from yaml file
         and store in the class variable _bucket take the value from yaml config file.

        Raise:
            Exception: if the bucket is not in the yaml config file

        Return:
            None
        """
        bucket = self._yaml_config['bucket']

        if not bucket:
            raise Exception(f"Bucket not define in yaml file")

        self._bucket = bucket

    def _get_year_month(self) -> None:
        """"get current year and month and put in class variable  _part_year_month

        Return:
            None
        """
        tmp_date = d.today().strftime("%Y/%m/%d")
        date = tmp_date.split('/')
        year, month = date[0], date[1]
        part_year_month = f"year={year}"

        if part_year_month:
            self._part_year_month = part_year_month

    def _add_athena_partition(self, table: str, database: str) -> None:
        """""add partition to athena table in case that partition exists in s3 but don't exists in athena
        Args:
            table(str): table name to add partitions
            database(str): database name

        Return:
            None
        """
        if self._s3_partition:
            for partition in self._s3_partition:
                if partition not in self._athena_partition:
                    logger.info(f"adding partition {partition} to table {table} in database: {database}")
                    query = f"ALTER TABLE {table} ADD IF NOT EXISTS PARTITION ({partition}) "
                    query = query.replace("/", ", ")
                    self._run_query(query, database)

    def _get_root_prefix(self, prefix: str) -> None:
        """"Get all the folder structure inside a root prefix, to get all the data bases and tables
        for athena and execute the process to compare athena partition and s3 partition
        Args:
            prefix(str): root prefix

        Return:
            None
        """
        args = {
            'Bucket': self._bucket,
            'Delimiter': '/',
            'Prefix': prefix
            }
        paginator = self.s3_client().get_paginator("list_objects_v2")
        for page in paginator.paginate(**args):
            for prefix in page.get('CommonPrefixes'):
                args['Prefix'] = prefix.get('Prefix')
                for sub_pages in paginator.paginate(**args):
                    if sub_pages.get('CommonPrefixes') or sub_pages.get("Prefix"):
                        if sub_pages.get("Prefix"):
                            prefix = sub_pages.get('Prefix')

                        self._s3_partition.append(prefix)

    def _read_yaml_file(self) -> None:
        """Read the Yaml file configuration and put in the class variable _yaml_config

        Return:
            None
        """
        yaml_file = 'config.yml'
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        if data:
            self._yaml_config = data

    def _get_s3_prefix_partition(self, prefix=None) -> None:
        """"Get all the partition base on the prefix with the format year=2020/month06/day=02
        only if the prefix have a file with ext json.gz and put in class variable _s3_partition.

        Args:
            prefix(str): prefix to get the s3 partition

        Return:
            None
        """

        list_partition = []
        for item in self._s3_partition:
            key = item.split('/')[-2]
            if key not in list_partition:
                list_partition.append(key)

        if list_partition:
            self._s3_partition = list_partition

    def _run_query(self, query: str, database: str) -> dict:
        """""execute query in athena
        Args:
            query(str): Query to execute
            database(str): Name of the database

        Return:
            response(dict)
        """
        client = self.athena_client()
        athena_result = self._yaml_config['athena_query_result']

        config = {
            'OutputLocation': athena_result,
            'EncryptionConfiguration': {'EncryptionOption': 'SSE_S3'}
            }
        context = {'Database': database}

        response = client.start_query_execution(QueryString=query, QueryExecutionContext=context,
                                                ResultConfiguration=config)

        return response

    def _get_status_query(self, query_id: str) -> bool:
        """"Get status from Athena Query and put the output location value in the class variable
        _s3_path
        Args:
            query_id(str): id for the query executed

        Return:
            bool
        """
        client = self.athena_client()
        state = 'RUNNING'

        while state in ['RUNNING', 'QUEUED']:
            response = client.get_query_execution(QueryExecutionId=query_id)
            if 'QueryExecution' in response and 'Status' in response['QueryExecution'] and 'State' in \
                    response['QueryExecution']['Status']:
                state = response['QueryExecution']['Status']['State']
                if state == 'FAILED':
                    logger.error(f"Query Execution Failed, "
                                 f"Error: {response['QueryExecution']['Status']['StateChangeReason']}")
                    return False
                elif state == 'SUCCEEDED':
                    s3_path = response['QueryExecution']['ResultConfiguration']['OutputLocation']

                    self._s3_path = s3_path
                    return True

    def _get_athena_partition(self) -> None:
        """"Read athena  partition output files from s3 and put  in the class variable _athena_partition
        Return:
            None
        """
        if self._s3_path:
            s3_path = self._s3_path.split('/')
            response = self.s3_client().get_object(Bucket=s3_path[-2], Key=s3_path[-1])
            file_data = response['Body'].read()
            file_data = file_data.decode('utf-8')
            athena_list = file_data.splitlines()

            if athena_list:
                self._athena_partition = athena_list

    @staticmethod
    def athena_client() -> boto3.client:
        """"Athena client

        Return:
             athena client: (boto3.client)
        """
        athena = boto3.client('athena')

        return athena

    @staticmethod
    def s3_client() -> boto3.client:
        """" S3 client
        Return:
             s3 client: (boto3.client)
        """
        s3 = boto3.client('s3')

        return s3

