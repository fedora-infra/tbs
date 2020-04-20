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

import argparse
import datetime
import json
import logging
import os
import re
import toml

try:
    from urllib2 import urlopen
except:
    from urllib.request import urlopen
from bugzilla.rhbugzilla import RHBugzilla

# Let's import template stuff
from jinja2 import Template
import mwclient

__version__ = "0.2.1"
bzclient = RHBugzilla(
    url="https://bugzilla.redhat.com/xmlrpc.cgi", cookiefile=None
)
# So the bugzilla module has some way to complain
logging.basicConfig()
logger = logging.getLogger("bugzilla")
# logger.setLevel(logging.DEBUG)

RETRIES = 2


class Project(object):
    """ Simple object representation of a project. """

    def __init__(self):
        self.name = ""
        self.service = ""
        self.url = ""
        self.site = ""
        self.owner = ""
        self.tag = ""
        self.tickets = []


class Ticket(object):
    """ Simple object representation of a ticket. """

    def __init__(self):
        self.id = ""
        self.url = ""
        self.title = ""
        self.status = ""
        self.type = ""
        self.component = ""
        self.tag = ""
        self.assingee = ""
        self.requester = ""
        self.project_url = ""
        self.project = ""
        self.project_site = ""
        self.closed_by = ""


def gather_bugzilla_issues(bz_projects):
    """ From the Red Hat bugzilla, retrieve all new tickets with keyword
    """
    full_bz_issues = []
    for bz_project in bz_projects:
        bz_issues = bzclient.query(
            {
                "query_format": "advanced",
                "bug_status": ["NEW", "ASSIGNED"],
                "classification": "Fedora",
                "product": "Fedora",
                "component": bz_project.name
            }
        )
        full_bz_issues += bz_issues
    return full_bz_issues


def gather_projects(bz_service=False):
    """ Retrieve all the projects which have subscribed to this idea.z
    """
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


def parse_arguments():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "--fedmenu-url", help="URL of the fedmenu resources (optional)"
    )
    parser.add_argument(
        "--fedmenu-data-url", help="URL of the fedmenu data source (optional)"
    )
    args = parser.parse_args()
    result = {}
    for key in ["fedmenu_url", "fedmenu_data_url"]:
        if getattr(args, key):
            result[key] = getattr(args, key)
    return result


def main():
    """ For each projects which have suscribed in the correct place
    (fedoraproject wiki page), gather all the tickets containing the
    provided keyword.
    """

    extra_kwargs = parse_arguments()

    template = "/etc/tbs/template.html"
    if not os.path.exists(template):
        template = "./template.html"
    if not os.path.exists(template):
        print("No template found")
        return 1

    projects = gather_projects()

    labels = ['groomed', 'in-progress', '']
    states = ['open', 'closed']
    ticket_num = 0
    all_tickets = []
    closed_tickets = []
    for project in projects:
        # print('Project: %s' % project.name)
        tickets = []
        if project.service == 'github':
            for state in states:
                for label in labels:
                    project.tag = label
                    project.url = "https://github.com/%s/" % (project.name)
                    project.site = "github"
                    url = (
                        "https://api.github.com/repos/%s/issues"
                        "?labels=%s&state=%s" % (project.name, label, state)
                    )
                    stream = urlopen(url)
                    output = stream.read()
                    jsonobj = json.loads(output)
                    if jsonobj:
                        for ticket in jsonobj:
                            ticket_num = ticket_num + 1
                            ticketobj = Ticket()
                            ticketobj.id = ticket["number"]
                            ticketobj.title = ticket["title"]
                            ticketobj.url = ticket["html_url"]
                            ticketobj.status = ticket["state"]
                            ticketobj.tag = label
                            ticketobj.requester = ticket["user"]["login"]
                            ticketobj.project_url = project.url
                            ticketobj.project = project.name
                            ticketobj.project_site = project.site
                            if ticket["assignee"]:
                                # GitHub api doesn't give full name of the user
                                ticketobj.assignee = ticket["assignee"]["login"]
                            else:
                                ticketobj.assignee = None
                                                        
                            if ticket["closed_at"]:
                               closed_tickets.append(ticketobj)
                            else:
                               all_tickets.append(ticketobj)

                            tickets.append(ticketobj)
        elif project.service == "pagure":
            for state in states:
                for label in labels:
                    project.tag = label
                    project.url = "https://pagure.io/%s/" % (project.name)
                    project.site = "pagure.io"
                    url = (
                        "https://pagure.io/api/0/%s/issues"
                        "?status=%s&tags=%s" % (project.name, state.capitalize(), label)
                    )
                    stream = urlopen(url)
                    output = stream.read()
                    jsonobj = json.loads(output)
                    if jsonobj:
                        for ticket in jsonobj["issues"]:
                            ticket_num = ticket_num + 1
                            ticketobj = Ticket()
                            ticketobj.id = ticket["id"]
                            ticketobj.title = ticket["title"]
                            ticketobj.url = "https://pagure.io/%s/issue/%s" % (
                                project.name,
                                ticket["id"],
                            )
                            ticketobj.status = ticket["status"]
                            ticketobj.tag = label
                            ticketobj.requester = ticket["user"]["name"]
                            ticketobj.project_url = project.url
                            ticketobj.project = project.name
                            ticketobj.project_site = project.site
                            if ticket["assignee"]:
                                ticketobj.assignee = ticket["assignee"]["fullname"]
                            else:
                                ticketobj.assignee = None

                            if ticket["closed_at"]:
                               closed_tickets.append(ticketobj)
                            else:
                               all_tickets.append(ticketobj)

                            tickets.append(ticketobj)

        elif project.service == "gitlab":
            for state in states:
                for label in labels:
                    project.tag = label
                    # https://docs.gitlab.com/ee/api/issues.html#list-project-issues
                    project.url = "https://gitlab.com/%s/" % (project.name)
                    project.site = "gitlab.com"
                    url = (
                        "https://gitlab.com/api/v4/projects/%s/issues"
                        "?state=%s&labels=%s"
                        % (urllib2.quote(project.name, safe=""), state, label)
                    )
                    stream = urlopen(url)
                    output = stream.read()
                    jsonobj = json.loads(output)
                    if jsonobj:
                        for ticket in jsonobj:
                            ticket_num = ticket_num + 1
                            ticketobj = Ticket()
                            ticketobj.id = ticket["id"]
                            ticketobj.title = ticket["title"]
                            ticketobj.url = ticket["web_url"]
                            ticketobj.status = ticket["state"]
                            ticketobj.tag = label
                            ticketobj.requester = ""
                            ticketobj.project_url = project.url
                            ticketobj.project = project.name
                            ticketobj.project_site = project.site
                            if ticket["assignee"]:
                                ticketobj.assignee = ticket["assignee"]["name"]
                            else:
                                ticketobj.assignee = None
                            tickets.append(ticketobj)
                            all_tickets.append(ticketobj)
        elif project.service == "bugzilla":
            project.tag = "bugzillaTag"
            # https://docs.gitlab.com/ee/api/issues.html#list-project-issues
            project.url = "https://bugzilla.redhat.com/buglist.cgi?bug_status=NEW&bug_status=ASSIGNED&component=%s&product=Fedora" % (
                project.name)
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
                ticket_num = ticket_num + 1
                ticketobj = Ticket()
                ticketobj.id = ticket.bug_id
                ticketobj.title = ticket.short_desc
                ticketobj.url = "https://bugzilla.redhat.com/%s" % (
                    ticket.bug_id)
                ticketobj.status = ticket.status
                ticketobj.tag = "in-progress" if ticket.bug_status == "ASSIGNED" else ""
                ticketobj.requester = ticket.creator
                ticketobj.project_url = project.url
                ticketobj.project = project.name
                ticketobj.project_site = project.site
                if ticket.assigned_to:
                    ticketobj.assignee = ticket.assigned_to
                else:
                    ticketobj.assignee = None
                tickets.append(ticketobj)
                all_tickets.append(ticketobj)
        project.tickets = tickets

    tickets_groomed = []
    tickets_in_progress = []
    tickets_untaged = []
    for ticket in all_tickets:
        if ticket.tag == "in-progress":
            tickets_in_progress.append(ticket)
        elif ticket.tag == "groomed":
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
            ticket_num=ticket_num,
            tickets_groomed=tickets_groomed,
            tickets_in_progress=tickets_in_progress,
            tickets_untaged=tickets_untaged,
            closed_tickets=closed_tickets,
            date=datetime.datetime.now().strftime("%a %b %d %Y %H:%M"),
            **extra_kwargs
        )
        # Write down the page
        stream = open("index.html", "w")
        stream.write(html)
        stream.close()
    except IOError as err:
        print("ERROR: %s" % err)


if __name__ == "__main__":
    main()
