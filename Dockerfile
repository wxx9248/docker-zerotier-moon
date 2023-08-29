FROM zerotier/zerotier:1.12.1

LABEL maintainer="wxx9248 <wxx9248@wxx9248.top>"

RUN rm -f /entrypoint.sh
RUN apt-get install -y python3
COPY entrypoint.py /entrypoint.py
COPY healthcheck.sh /healthcheck.sh
RUN chmod 755 /entrypoint.py
RUN chmod 755 /healthcheck.sh
ENTRYPOINT ["/entrypoint.py"]
HEALTHCHECK --interval=1s CMD /healthcheck.sh

EXPOSE 9993/udp
