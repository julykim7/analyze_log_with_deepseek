import logging
import requests

class FeishuClient:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_message(self, log, analysis_result):
        headers = {
            "Content-Type": "application/json"
        }
        # 飞书消息纯文本格式，markdown展示不友好
        #text = f"日志内容: {log}\n分析结果: {analysis_result}"
        #data = {
        #    "msg_type": "text",
        #    "content": {
        #        "text": text
        #    }
        #}
        # 调整使用飞书消息卡片格式，可以展示更丰富的内容和交互
        data = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "DeepSeek日志分析告警推送"
                    }
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**来自Deepseek的消息**:\n{log}"
                        }
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**deepseek分析结果**:\n{analysis_result}"
                        }
                    }
                ]
            }
        }
        try:
            response = requests.post(self.webhook_url, headers=headers, json=data)
            response.raise_for_status()
            logging.info("消息已成功发送到飞书。")
        except requests.RequestException as e:
            logging.error(f"请求出错: {e}")
        except requests.HTTPError as e:
            logging.error(f"发送消息到飞书失败，状态码: {response.status_code}，响应内容: {response.text}")
