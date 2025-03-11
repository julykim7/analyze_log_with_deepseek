import logging
import configparser
from elasticsearch_utils import ElasticsearchClient
from feishu_utils import FeishuClient
import requests
import json
import time

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

es_host = config.get('elasticsearch', 'host')
es_port = config.getint('elasticsearch', 'port')
es_username = config.get('elasticsearch', 'username')
es_password = config.get('elasticsearch', 'password')
deepseek_api_url = config.get('deepseek', 'api_url', fallback="https://api.deepseek.com/chat/completions")

# 初始化 Elasticsearch 客户端
es_client = ElasticsearchClient(es_host, es_port, es_username, es_password)

# 初始化飞书客户端
feishu_client = FeishuClient(config.get('feishu', 'webhook_url'))

# 模拟历史故障匹配,内容仅作为举例使用。
historical_fault_db = {
    "Redis连接池耗尽": ["redis connection pool exhausted", "redis pool full"],
    "数据库连接超时": ["database connection timeout", "db connect timed out"],
    "2024年10月28日 网络连接异常历史故障匹配验证": ["网络连接异常","故障根因：专线丢包，交换机版本bug"]
}


def analyze_logs_with_deepseek(logs):
    headers = {
        "Authorization": f"Bearer {config.get('deepseek', 'api_key')}",
        "Content-Type": "application/json"
    }
    combined_logs = "\n".join(logs)
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": f"作为拥有20年经验的资深运维专家,把日志按照故障类型'数据库异常'、'程序异常'、'网络异常'、'redis异常'、'mq异常'等进行分类,并整体评估影响范围(P0-P3)给出建议：\n{combined_logs}"
            }
        ]
    }
    max_retries = 3
    retries = 0
    while retries < max_retries:
        try:
            response = requests.post(deepseek_api_url, headers=headers, json=data)
            response.raise_for_status()  # 检查 HTTP 状态码，如果不是 200，抛出异常
            result = response.json()
            return result
        except requests.RequestException as e:
            logging.error(f"请求出错: {e}")
            retries += 1
            time.sleep(2)  # 等待 2 秒后重试
        except json.JSONDecodeError as e:
            logging.error(f"JSON 解析出错: {e}")
            break
        except requests.HTTPError as e:
            if response.status_code == 401:
                logging.error("权限验证失败，请检查授权密钥。")
                break
            elif response.status_code == 400:
                logging.error("请求参数有误，请检查请求数据。")
                break
            else:
                logging.error(f"请求出错，状态码: {response.status_code}，响应内容: {response.text}")
                retries += 1
                time.sleep(2)  # 等待 2 秒后重试
    return None


def match_with_historical_db(logs):
    """
    将日志与历史故障库进行匹配
    :param logs: 日志列表
    :return: 匹配结果
    """
    matches = []
    for log in logs:
        for fault, keywords in historical_fault_db.items():
            for keyword in keywords:
                if keyword.lower() in log.lower():
                    matches.append((log, fault))
    return matches


# 主函数
def main():
    index_name = config.get('elasticsearch_index', 'index_name')
    logs = es_client.get_logs_from_es(index_name)
    if logs:
        # 用 deepseek 分类打标
        result = analyze_logs_with_deepseek(logs)
        if result:
            try:
                message = result["choices"][0]["message"]["content"]
                logging.info(f"整合日志分析结果: {message}")
                # 与历史故障库进行匹配
                historical_matches = match_with_historical_db(logs)

                historical_match_message = ""
                if historical_matches:
                    historical_match_message = "<font color='red'>**历史故障库匹配结果:**</font>\n"
                    for log, fault in historical_matches:
                        historical_match_message += f"日志内容: {log}\n 匹配故障: <font color='red'>**{fault}**</font>\n"
                else:
                    historical_match_message = "未找到与历史故障库匹配的日志。"

                logging.info(historical_match_message)

                # 整合 deepseek 分析结果和历史故障匹配结果
                full_message = f"整合日志分类:\n{message}\n\n{historical_match_message}"

                feishu_client.send_message("整合日志分析结果", full_message)
            except KeyError as e:
                logging.error(f"返回结果中缺少必要的键: {e}")
        else:
            logging.error("日志分析失败。")
    else:
        logging.warning("未从Elasticsearch获取到日志。")


if __name__ == "__main__":
    main()
