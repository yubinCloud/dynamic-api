FROM python:3.10-alpine

WORKDIR /src

EXPOSE 7100

ENV ENV_FOR_DYNACONF=production

COPY requirements.txt requirements.txt

COPY replaced_py/fastapi_routing.py /usr/local/lib/python3.10/site-packages/fastapi/routing.py
COPY replaced_py/starlette_routing.py /usr/local/lib/python3.10/site-packages/starlette/routing.py

RUN pip install --no-cache-dir --upgrade -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

ADD ./dynamicapi ./

RUN ls

CMD ["python", "main.py"]
#CMD ["/bin/sh"]