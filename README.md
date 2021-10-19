# README

## tl;dw (too long; didn't write one yet)

```shell
# setup our env variables
cp .docker-env-dist .docker-env

# cat environment variables to see if anything is missing
cat .docker-env

# to build
DOCKER_BUILDKIT=1 docker-compose build

# to start
docker-compose up --detach

# to stop
docker-compose down
```
