#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import datetime
import logging
import os
import toml
import urllib

import requests

from bugzilla.rhbugzilla import RHBugzilla
from jinja2 import Template

__version__ = "0.2.1"
bzclient = RHBugzilla(
    url="https://bugzilla.redhat.com/xmlrpc.cgi", cookiefile=None
)
# So the bugzilla module has some way to complain
logging.basicConfig()
logger = logging.getLogger("bugzilla")
# logger.setLevel(logging.DEBUG)


class Project:
    """ Simple object representation of a project."""

    def __init__(self):
        self.name = ""
        self.service = ""
        self.url = ""
        self.site = ""
        self.tag = ""


class Ticket:
    """ Simple object representation of a ticket."""

    def __init__(self):
        self.id = ""
        self.url = ""
        self.title = ""
        self.labels = []
        self.assingee = ""
        self.requester = ""
        self.project_url = ""
        self.project = ""
        self.project_site = ""
        self.closed_by = ""
        self.tag = ""


def gather_projects(bz_service=False):
    """ Retrieve all the projects which have subscribed to this idea."""
    projects_path = "projects.toml"
    if not os.path.exists(projects_path):
        print("No projects file is found")
        return 1
    projects_list = toml.load(os.path.join(os.getcwd(), projects_path))
    projects = []
    for service in projects_list['projects']:
        for repo in projects_list['projects'][service]:
            project = Project()
            project.name = repo
            project.service = service
            projects.append(project)
    return projects


def gather_pagure_tickets(project, all_tickets, state):
    """Get the last 100 tickets from the specified state on pagure."""

    project.url = "https://pagure.io/%s/" % (project.name)
    project.site = "pagure.io"
    url = (
            "https://pagure.io/api/0/%s/issues"
            "?status=%s&per_page=100" % (project.name, state.capitalize())
    )
    jsonobj = requests.get(url).json()
    if jsonobj:
        for ticket in jsonobj["issues"]:
            ticketobj = Ticket()
            ticketobj.id = ticket["id"]
            ticketobj.title = ticket["title"]
            ticketobj.url = "https://pagure.io/%s/issue/%s" % (
                project.name,
                ticket["id"],
            )
            ticketobj.labels = ticket["tags"]
            ticketobj.requester = ticket["user"]["name"]
            ticketobj.project_url = project.url
            ticketobj.project = project.name
            ticketobj.project_site = project.site
            if ticket["assignee"]:
                ticketobj.assignee = ticket["assignee"]["fullname"]
            else:
                ticketobj.assignee = None

            all_tickets.append(ticketobj)


def gather_github_tickets(project, all_tickets, state):
    """Get the last 100 tickets from the specified state on github."""
    project.url = "https://github.com/%s/" % (project.name)
    project.site = "github"
    url = (
            "https://api.github.com/repos/%s/issues"
            "?state=%s&per_page=100" % (project.name, state)
    )
    jsonobj = requests.get(url).json()
    if jsonobj and "pull_request" not in jsonobj:
        for ticket in jsonobj:
            ticketobj = Ticket()
            ticketobj.id = ticket["number"]
            ticketobj.title = ticket["title"]
            ticketobj.url = ticket["html_url"]
            ticketobj.requester = ticket["user"]["login"]
            ticketobj.project_url = project.url
            ticketobj.project = project.name
            ticketobj.project_site = project.site
            for label in ticket["labels"]:
                ticketobj.labels.append(label["name"])
            if ticket["assignee"]:
                # GitHub api doesn't give full name of the user
                ticketobj.assignee = ticket["assignee"]["login"]
            else:
                ticketobj.assignee = None

            all_tickets.append(ticketobj)


def gather_gitlab_tickets(project, all_tickets, state):
    """Get the last 100 tickets from the specified state on gitlab."""
    # https://docs.gitlab.com/ee/api/issues.html#list-project-issues
    project.url = "https://gitlab.com/%s/" % (project.name)
    project.site = "gitlab.com"
    url = (
            "https://gitlab.com/api/v4/projects/%s/issues?state=%s&per_page=100"
            % (urllib.parse.quote(project.name, safe=""), state)
    )
    jsonobj = requests.get(url).json()
    if jsonobj:
        for ticket in jsonobj:
            ticketobj = Ticket()
            ticketobj.id = ticket["id"]
            ticketobj.title = ticket["title"]
            ticketobj.url = ticket["web_url"]
            ticketobj.labels = ticket["labels"]
            ticketobj.requester = ""
            ticketobj.project_url = project.url
            ticketobj.project = project.name
            ticketobj.project_site = project.site
            if ticket["assignee"]:
                ticketobj.assignee = ticket["assignee"]["name"]
            else:
                ticketobj.assignee = None

            all_tickets.append(ticketobj)


def gather_bugzilla_tickets(project, all_tickets):
    """"Get the bugzilla tickets for a component"""
    project.tag = "bugzillaTag"
    project.url = "https://bugzilla.redhat.com/buglist.cgi"\
                  "?bug_status=NEW&bug_status=ASSIGNED&component=%s&product=Fedora"\
                  % (project.name)
    project.site = "bugzilla.redhat.com"
    bz_list = bzclient.query(
        {
            "query_format": "advanced",
            "bug_status": ["NEW", "ASSIGNED"],
            "classification": "Fedora",
            "product": "Fedora",
            "component": project.name
        })
    for ticket in bz_list:
        ticketobj = Ticket()
        ticketobj.id = ticket.bug_id
        ticketobj.title = ticket.short_desc
        ticketobj.url = "https://bugzilla.redhat.com/%s" % (
            ticket.bug_id)
        ticketobj.labels = []
        ticketobj.requester = ticket.creator
        ticketobj.project_url = project.url
        ticketobj.project = project.name
        ticketobj.project_site = project.site
    if ticket.assigned_to:
        ticketobj.assignee = ticket.assigned_to
    else:
        ticketobj.assignee = None
    all_tickets.append(ticketobj)


def main():
    """ For each projects which have suscribed in the correct place
    (fedoraproject wiki page), gather all the tickets containing the
    provided keyword.
    """

    template = "./template.html"
    if not os.path.exists(template):
        print("No template found")
        return 1

    projects = gather_projects()

    all_tickets = []
    closed_tickets = []
    state = 'open'
    for project in projects:
        print(f"Fetching issues for {project.name}")
        if project.service == 'github':
            gather_github_tickets(project, all_tickets, state)
        elif project.service == "pagure":
            gather_pagure_tickets(project, all_tickets, state)
        elif project.service == "gitlab":
            gather_gitlab_tickets(project, all_tickets, state)
        elif project.service == "bugzilla":
            gather_bugzilla_tickets(project, all_tickets)

    tickets_groomed = []
    tickets_in_progress = []
    tickets_blocked = []
    tickets_untaged = []
    for ticket in all_tickets:
        if ticket.assignee:
            if "blocked" in ticket.labels:
                tickets_blocked.append(ticket)
            else:
                tickets_in_progress.append(ticket)
            continue
        for label in ticket.labels:
            if label == "groomed":
                tickets_groomed.append(ticket)
            else:
                tickets_untaged.append(ticket)

    try:
        # Read in template
        stream = open(template, "r")
        tplfile = stream.read()
        stream.close()
        # Fill the template
        mytemplate = Template(tplfile)
        html = mytemplate.render(
            projects=projects,
            all_tickets=all_tickets,
            tickets_groomed=tickets_groomed,
            tickets_in_progress=tickets_in_progress,
            tickets_blocked=tickets_blocked,
            tickets_untaged=tickets_untaged,
            closed_tickets=closed_tickets,
            date=datetime.datetime.now().strftime("%a %b %d %Y %H:%M"),
        )
        # Write down the page
        stream = open("index.html", "w")
        stream.write(html)
        stream.close()

    except IOError as err:
        print("ERROR: %s" % err)


if __name__ == "__main__":
    main()
