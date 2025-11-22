FROM python:3.11

WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "/usr/src/app/entrypoint.sh"]
