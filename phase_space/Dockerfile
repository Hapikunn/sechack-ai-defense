FROM python:3.11-slim

WORKDIR /app

# 共通ライブラリをコピー（database.pyを使うため）
COPY shared/ /app/shared/

COPY phase_space/requirements.txt .
RUN pip install -r requirements.txt

# 共通ライブラリのrequirementsもインストール
RUN pip install -r /app/shared/requirements.txt

COPY phase_space/ /app/

CMD ["python", "-u", "app.py"]