FROM python:3.6
WORKDIR /app
COPY ./blockchain.py /app/blockchain.py
RUN cd /app \
  && pip install Flask==0.12.2 requests==2.18.4
EXPOSE 5000
ENTRYPOINT ["python", "/app/blockchain.py", "--port", "5000"]
