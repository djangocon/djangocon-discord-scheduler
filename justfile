set dotenv-load := false

alias build := docker-compose-build
alias down := docker-compose-down
alias logs := docker-compose-logs
alias ps := docker-compose-ps
alias up := docker-compose-up

@_default:
    just --list

@docker-compose-build:
    docker-compose build

@docker-compose-down:
    docker-compose down

@docker-compose-logs +ARGS="":
    docker-compose logs {{ ARGS }}

@docker-compose-ps:
    docker-compose ps

@docker-compose-up +ARGS="--detach":
    docker-compose up {{ ARGS }}

@fmt:
    just --fmt --unstable

@pip-compile:
    -rm -rf requirements.txt
    pip install --upgrade --requirement=requirements.in
    pip-compile -r requirements.in
