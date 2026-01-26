FROM debian:trixie

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
      python3 \
      python3-pip
RUN pip3 install --break-system-packages \
      flask \
      uwsgi \
      folium \
      Flask-SQLAlchemy

COPY app /app/
WORKDIR /app/

CMD ["flask", "run", "-h", "0.0.0.0"]
#CMD ["uwsgi", "--http", ":5000", "--module", "app:app"]
#CMD ["uwsgi", "--http", "0.0.0.0:5000", "--chdir", "/app", "--wsgi-file", "app.py", "--callable", "app", "--need-app"]
