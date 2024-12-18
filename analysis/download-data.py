import opensearchpy
from datetime import datetime
import os
import logging
from logging.handlers import RotatingFileHandler
import csv
import json
from tqdm import tqdm


def setup_logging(log_level=logging.DEBUG):
    """Setup logging configuration"""
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('opensearch_downloader')
    logger.setLevel(log_level)
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    
    file_handler = RotatingFileHandler(
        'logs/opensearch_download.log',
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class OpenSearchDownloader:
    def __init__(self, host, port, username, password, index_name, batch_size=10000):
        self.logger = logging.getLogger('opensearch_downloader')
        self.client = opensearchpy.OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=(username, password),
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        self.index_name = index_name
        self.batch_size = batch_size
        self.logger.info(f"Initialized downloader for index: {index_name} with batch size: {batch_size}")

    def get_total_docs(self, query):
        self.logger.debug("Executing count query...")
        count_query = {
            "query": query["query"]
        }
        result = self.client.count(index=self.index_name, body=count_query)
        total = result['count']
        self.logger.info(f"Total documents matching query: {total}")
        return total

    def flatten_dict(self, d, parent_key='', sep='.'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, (list, tuple)):
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
        return dict(items)

    def get_all_fields(self, query, sample_size=1000):
        self.logger.info(f"Scanning {sample_size} documents to determine all possible fields...")
        
        sample_query = query.copy()
        sample_query['size'] = min(sample_size, self.batch_size)
        
        response = self.client.search(
            index=self.index_name,
            body=sample_query,
            scroll='5m'
        )
        
        scroll_id = response['_scroll_id']
        all_fields = set()
        docs_scanned = 0
        
        # Create progress bar for field scanning
        pbar = tqdm(total=sample_size, desc="Scanning fields")
        
        try:
            while docs_scanned < sample_size:
                hits = response['hits']['hits']
                if not hits:
                    break
                
                for hit in hits:
                    flat_data = self.flatten_dict(hit['_source'])
                    all_fields.update(flat_data.keys())
                
                batch_size = len(hits)
                docs_scanned += batch_size
                pbar.update(batch_size)
                
                if docs_scanned < sample_size:
                    response = self.client.scroll(scroll_id=scroll_id, scroll='5m')
                    scroll_id = response['_scroll_id']
                
        finally:
            pbar.close()
            try:
                self.client.clear_scroll(scroll_id=scroll_id)
            except Exception as e:
                self.logger.warning(f"Error clearing scroll during field scanning: {str(e)}")
        
        self.logger.info(f"Found {len(all_fields)} unique fields in {docs_scanned} documents")
        return sorted(list(all_fields))

    def stream_to_csv(self, query, csv_writer, fieldnames, scroll_timeout='5m'):
        self.logger.info("Starting scroll download process")
        
        total_docs = self.get_total_docs(query)
        documents_processed = 0
        
        query['size'] = self.batch_size
        
        response = self.client.search(
            index=self.index_name,
            body=query,
            scroll=scroll_timeout
        )
        
        scroll_id = response['_scroll_id']
        header_written = False
        batch_count = 1

        # Create progress bar for main download
        pbar = tqdm(total=total_docs, desc="Downloading")
        
        try:
            while True:
                hits = response['hits']['hits']
                if not hits:
                    break

                for hit in hits:
                    flat_data = self.flatten_dict(hit['_source'])
                    
                    if not header_written:
                        csv_writer.writeheader()
                        header_written = True
                    
                    row = {field: flat_data.get(field, '') for field in fieldnames}
                    csv_writer.writerow(row)
                
                batch_size = len(hits)
                documents_processed += batch_size
                pbar.update(batch_size)
                
                response = self.client.scroll(
                    scroll_id=scroll_id,
                    scroll=scroll_timeout
                )
                scroll_id = response['_scroll_id']
                batch_count += 1
                
        except Exception as e:
            self.logger.error(f"Error during scroll: {str(e)}", exc_info=True)
            raise
        finally:
            pbar.close()
            try:
                self.client.clear_scroll(scroll_id=scroll_id)
            except Exception as e:
                self.logger.warning(f"Error clearing scroll: {str(e)}")
            
        return documents_processed

if __name__ == "__main__":
    # Setup logging
    logger = setup_logging()
    logger.info("Starting OpenSearch data download script")
    
    # Get configuration from environment variables
    HOST = os.getenv('OPENSEARCH_HOST')
    PORT = int(os.getenv('OPENSEARCH_PORT', '443'))
    USERNAME = os.getenv('OPENSEARCH_USERNAME')
    PASSWORD = os.getenv('OPENSEARCH_PASSWORD')
    INDEX_NAME = "benchmark-metrics*"
    
    logger.info(f"Using host: {HOST}:{PORT} and index: {INDEX_NAME}")
    
    required_vars = ['OPENSEARCH_HOST', 'OPENSEARCH_USERNAME', 'OPENSEARCH_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    QUERY = {
        "size": 500,
        "stored_fields": ["*"],
        "script_fields": {},
        "_source": {"excludes": []},
        "query": {
            "bool": {
                "must": [],
                "filter": [
                    {"match_all": {}},
                    {"match_phrase": {"meta.tag_run-type": "official"}},
                    {"match_phrase": {"meta.tag_ci": "scheduled"}},
                    {"match_phrase": {"name": "service_time"}},
                    {
                        "range": {
                            "test-execution-timestamp": {
                                "gte": "2024-11-30T00:00:00.000Z",
                                "lte": "2024-12-11T00:00:00.000Z",
                                "format": "strict_date_optional_time",
                            }
                        }
                    },
                ],
                "should": [],
                "must_not": [],
            }
        }
    }
    
    try:
        # Initialize downloader
        downloader = OpenSearchDownloader(
            host=HOST,
            port=PORT,
            username=USERNAME,
            password=PASSWORD,
            index_name=INDEX_NAME,
            batch_size=10000
        )
        
        # Create output filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f'opensearch_data_{timestamp}.csv'
        
        # Get all possible fields first
        all_fields = downloader.get_all_fields(QUERY)
        
        # Stream download to CSV file
        logger.info(f"Starting download process, streaming to {output_filename}")
        with open(output_filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_fields)
            total_processed = downloader.stream_to_csv(QUERY, writer, all_fields)
            
            logger.info(f"Download complete. Processed {total_processed} documents.")
            logger.info(f"Data saved to {output_filename}")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("Script execution completed")
