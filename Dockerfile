FROM debian:trixie

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
      python3 \
      python3-flask \
      python3-folium \
      python3-flask-sqlalchemy \
      python3-gunicorn

COPY app /app/
WORKDIR /app/

CMD ["python3", "-m", "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]
