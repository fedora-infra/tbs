# tbs
Ticket Board System

# Hacking

Setup a virtual environment

```
$ python3 -m venv .venv
$ source .venv/bin/activate
```

Install the dependencies

```
$ pip install -r requirements.txt
```

Run the script

```
$ python tbs.py
```

# Adding a new project to tbs

Simply edit `projects.toml` and add the project.

# TBS workflow

## Groomed

Every ticket that is ready to be work on. To mark ticket groomed, add label `groomed`.

## In progress

Tickets that are being work on. To mark ticket in progress, assign someone to it.

## Blocked

Tickets that are currently blocked. To mark ticket blocked, add label `blocked`.
