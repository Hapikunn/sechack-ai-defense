FROM python:3.11-slim

WORKDIR /app

# 共通ライブラリをインストール
COPY shared/requirements.txt /app/shared/
RUN pip install -r /app/shared/requirements.txt

# Blue AIのコードをコピー
COPY blue_ai/ /app/

CMD ["python", "-u", "main.py"]