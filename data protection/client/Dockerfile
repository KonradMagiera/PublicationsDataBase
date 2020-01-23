FROM python:3.7-alpine
RUN apk update && apk add gcc libc-dev make git libffi-dev openssl-dev python3-dev libxml2-dev libxslt-dev
EXPOSE 5000
WORKDIR /var/www
RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
ENV FLASK_APP app.py
ENV FLASK_RUN_HOST 0.0.0.0
CMD ["sh", "-c", "flask run --cert=cert.pem --key=key.pem"]