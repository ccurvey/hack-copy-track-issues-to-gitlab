import re
from re import MULTILINE
import xmlrpclib
import gitlab
"""
What
=====

 This script migrates issues from trac to gitlab.
 * Component & Issue-Type are converted to labels
 * Milestones are ignored (or: I did not get the script to set my one single milestone, so I set it manually)
 * Comments to issues are copied over
 * Wiki Syntax in comments/descriptions is sanitized for my basic usage


How
====

 Usage: configure the following variables in in ```migrate.py````

Source
-------

 * ```trac_url``` - xmlrpc url to trac, e.g. ``https://user:secret@www.example.com/projects/taskninja/login/xmlrpc```

Target
-------

 * ```gitlab_url``` - e.g. ```https://www.exmple.com/gitlab/api/v3```
 * ```gitlab_access_token``` - the access token of the user creating all the issues. Found on the account page,  e.g. ```secretsecretsecret```
 * ```dest_project_name``` - the destination project including the paths to it. Basically the rest of the clone url minus the ".git". E.g. ```jens.neuhalfen/task-ninja```.
 * ```milestone_map``` - Maps milestones from trac to gitlab. Milestones have to exist in gitlab prior to running the script (_CAVE_: Assigning milestones does not work.)

License
========

 License: http://www.wtfpl.net/

Requirements
==============

 * ```Python 2.7, xmlrpclib, requests```
 * Trac with xmlrpc plugin enabled
 * Gitlab

"""
trac_url = "https://user:secret@www.example.com/projects/taskninja/login/xmlrpc"

gitlab_url = "https://www.exmple.com/gitlab/api/v3"
gitlab_access_token = "secretsecretsecret"



dest_project_name ="jens.neuhalfen/task-ninja"
milestone_map = {"M1 - build and tests":"M1 - build and tests" }
"------"



def fix_wiki_syntax(markup):
    markup = re.sub(r'#!CommitTicketReference.*\n',"",markup, flags=MULTILINE)

    markup = markup.replace("{{{\n","\n```text\n")
    markup = markup.replace("{{{","```")
    markup = markup.replace("}}}","```")

    # [changeset:"afsd38..2fs/taskninja"] or [changeset:"afsd38..2fs"]
    markup = re.sub(r'\[changeset:"([^"/]+?)(?:/[^"]+)?"]',r"changeset \1",markup)

    return markup

def get_dest_project_id(dest_project_name):
    dest_project = dest.project_by_name(dest_project_name)
    if not dest_project: raise ValueError("Project '%s' not found under '%s'" % (dest_project_name, gitlab_url))
    return dest_project["id"]

def get_dest_milestone_id(dest_project_id,milestone_name):
    dest_milestone_id = dest.milestone_by_name(dest_project_id,milestone_name )
    if not dest_milestone_id: raise ValueError("Milestone '%s' of project '%s' not found under '%s'" % (milestone_name,dest_project_name, gitlab_url))
    return dest_milestone_id["id"]



#if __name__ == "__main__":
#   for v  in ['[changeset:"7609b4a46141a61d8f1e4a3e9c9d4f013e0388f8"]:','[changeset:"7609b4a46141a61d8f1e4a3e9c9d4f013e0388f8/taskninja"]:']:
#    print(v, fix_wiki_syntax(v))

if __name__ == "__main__":
    dest = gitlab.Connection(gitlab_url,gitlab_access_token)
    source = xmlrpclib.ServerProxy(trac_url)

    dest_project_id = get_dest_project_id(dest_project_name)
    milestone_map_id={}
    for mstracname, msgitlabname in milestone_map.iteritems():
        milestone_map_id[mstracname]=get_dest_milestone_id(dest_project_id, msgitlabname)



    get_all_tickets = xmlrpclib.MultiCall(source)

    for ticket in source.ticket.query("max=0"):
        get_all_tickets.ticket.get(ticket)


    for src_ticket in get_all_tickets():
        src_ticket_id = src_ticket[0]
        src_ticket_data = src_ticket[3]

        is_closed =  src_ticket_data['status'] == "closed"
        new_ticket_data = {
            "title" : src_ticket_data['summary'],
            "description" : fix_wiki_syntax( src_ticket_data['description']),
            "closed" : 1 if is_closed else 0,
            "labels" : ",".join( [src_ticket_data['type'], src_ticket_data['component']] )
        }

        milestone = src_ticket_data['milestone']
        if milestone and milestone_map_id[milestone]:
            new_ticket_data["milestone"] = milestone_map_id[milestone]

        new_ticket = dest.create_issue(dest_project_id, new_ticket_data)
        new_ticket_id  = new_ticket["id"]
        # setting closed in create does not work -- bug in gitlab
        if is_closed: dest.close_issue(dest_project_id,new_ticket_id)

        # same for milestone
        if new_ticket_data.has_key("milestone"): dest.set_issue_milestone(dest_project_id,new_ticket_id,new_ticket_data["milestone"])


        changelog = source.ticket.changeLog(src_ticket_id)
        for change in changelog:
            change_type = change[2]
            if (change_type == "comment"):
                comment = fix_wiki_syntax( change[4])
                dest.comment_issue(dest_project_id,new_ticket_id,comment)



