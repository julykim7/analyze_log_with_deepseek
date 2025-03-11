import logging
from elasticsearch import Elasticsearch


class ElasticsearchClient:
    def __init__(self, host, port, username, password):
        # 指定scheme为http
        self.es = Elasticsearch([{'host': host, 'port': port, 'scheme': 'http'}], http_auth=(username, password))

    def get_logs_from_es(self, index_name, size=10):
        # 限定查询范围，最近1h，最新10条，可以根据需要调整
        query = {
            "query": {
                # "match_all": {}
                "range": {
                    "@timestamp": {
                        "gte": "now-5h",
                        "lt": "now"
                    }
                }
            },
            "sort": [
                {
                    "@timestamp": {
                        "order": "desc"
                    }
                }
            ],
            "size": size
        }
        try:
            result = self.es.search(index=index_name, body=query)
            logs = [hit["_source"]["message"] for hit in result["hits"]["hits"]]
            return logs
        except Exception as e:
            logging.error(f"从Elasticsearch获取日志出错: {e}")
            return []
