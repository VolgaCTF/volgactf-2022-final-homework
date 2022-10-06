FROM python:3.7.14-slim
ADD src VERSION /dist/
WORKDIR /dist

# setup the services
RUN pip install --requirement aesthetic/requirements.txt
RUN pip install --requirement editor/requirements.txt
RUN pip install --requirement jinnice/requirements.txt
RUN pip install --requirement myblog/requirements.txt

# start game simulation
CMD ["python", "-u", "main.py"]
