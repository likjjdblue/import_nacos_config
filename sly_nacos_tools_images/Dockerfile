FROM centos:7
WORKDIR /TRS
ADD ./import_nacos_config.py /TRS
RUN chmod 777 /TRS/import_nacos_config.py

CMD ["python", "./import_nacos_config.py"]
