#!/usr/bin/env python3

### stash.py
#   Copyright 2026 Nokia
###

"""
Tested on: SR OS 25.10.R1

This script is an example of a full fledged application implemented to run on an SR OS node.

Stash uses multiple pysros modules to perform actions such as:

- Getting configuration
- Setting configuration
- Converting configuration from pysros format to json
- Converting configuration from json format to pysros
- Printing in SR OS show command tabular format
- Printing dictionary data using printTree
- Building a configuration for installation using YANG elements: Container, Leaf, LeafList
- Handling exceptions

What is Stash?
==============
The stash is an additional datastore in SROS where the operator can "stash" config snippets.
This is useful in many scenarios.

For example, while working on projects, an engineer might need to experiment with different
approaches to solve a problem. It would be useful to be able to stash these to switch between
approaches without having to copy and paste them into an offline file.

Another example is for an operational use. In a running network, sometimes an issue occurs,
or a temporary change of policy is required. In these situations, the configuration in the
network may be changed or deleted. These changes may need to be reverted, either in part or whole.

Having a stash of the original configuration before making changes may help an operator to
get the service back online faster or the service back to its original state.

Installation
============
To install the stash, two steps are required.

1. Copy the stash.py file to the target node's cf3:\\
2. Create a python script:
    ``/configure python python-script "stash" admin-state enable``
    ``/configure python python-script "stash" urls ["cf3:stash.py"]``
    ``/configure python python-script "stash" version python3``
3. Run ``pyexec stash install``

This will create a python-script configuration and an MD-CLI command-alias.
You must log out and log back in to access the command-alias.

Usage
=====
Stash comes with help::

    A:admin@sr-1# stash help
    Syntax: stash <>
        branch          Manage stash branches
        comment         Add a comment to an entry
        commit          Commit a stash entry to configuration
        compare         Compare stash entry to current config
        delete          Delete a stash entry
        entry           Show saved stash entry
        header          Show only header of stash entry
        list            List entries parented here
        list-all        List all entries in branch
        this            Add config at current path to stash
        tree            Tree view of stash entry ids
    stash - The Stash enables the operator to store and retrieve config snippets

Some commands under stash need arguments, such as ``stash commit``::

    A:admin@sr-1# stash commit
    This command requires an argument.

    Syntax: stash commit <id>
        id              Id of stash entry

To begin using stash, enter a configuration candidate datastore and navigate to a path.
Then, issue the ``stash this`` command to create a stash entry::

    (gl)[/configure router "Base" interface "system"]
    A:admin@sr-1# stash this
    ===============================================================================
    Stash Entry
    ===============================================================================
    Branch    : global
    Id        : 1
    Comment   : n/a
    Path      : configure router "Base" interface "system"
    Parent    : configure router "Base"
    ===============================================================================

The stash now has a copy of the configuration committed under this path. You can view
this configuration using ``stash entry <id>``::

    A:admin@sr-1# stash entry 1
    ===============================================================================
    Stash Entry
    ===============================================================================
    Branch    : global
    Id        : 1
    Comment   : n/a
    Path      : configure router "Base" interface "system"
    Parent    : configure router "Base"
    ===============================================================================
    Data:
    -------------------------------------------------------------------------------
    +-- interface-name: system
    `-- ipv4:
        `-- primary:
            +-- prefix-length: 32
            `-- address: 10.0.0.1
    ===============================================================================

Structure of the Application
============================
This application is broken in different parts using classes. The classes are:

- Node - handles operations to the node like get and set
- JSONInstancePath - handles operations on json-instance-path string
- StashDataStore - handles storage of stash data
- StashDataViewer - used for accessing stored data in the stash and printing it
- StashInstall - operations to install stash into a system
- StashApplication - implements the user interface and command routing

"""

import json
import os
import sys

from pysros.management import (
    InvalidPathError,
    ModelProcessingError,
    SrosMgmtError,
    connect,
)
from pysros.pprint import KeyValueTable, Table, printTree
from pysros.wrappers import Container, Leaf, LeafList


class Node:
    """
    The class uses pysros modules to interact with the node configuration.
    """

    def __init__(self):
        """
        Initialize a connection to the node. If an exception is raised, the application stops with
        an exit.
        """
        try:
            self.connection = connect()
        except RuntimeError as error:
            print("Failed to connect.  Error: {}".format(error))
            sys.exit(-1)
        except ModelProcessingError as error:
            print(
                "Failed to create model-driven schema. Error: {}".format(error)
            )
            sys.exit(-2)

    def get(self, path: str) -> dict:
        """
        Given a json-instance-path, this method returns pysros format dictionary data.
        If the path has no running configuration, a None is returned.

        :param path: json-instance-path to query
        :type path: str
        :return: Running configuration as this path (if any)
        :rtype: dict
        """
        try:
            data = self.connection.running.get(path)
        except LookupError:
            data = None
        return data

    def set(self, path: str, data: dict, commit: bool) -> bool:
        """
        Used for modifying the configuration within a candidate datastore on the node.
        There is an option on whether to commit at the same time or not.

        :param path: json-instance-path to modify at
        :type path: str
        :param data: pysros format data to update at given path
        :type data: dict
        :param commit: To commit the candidate or not
        :type commit: bool
        :return: Success or Failure of the operation
        :rtype: bool
        """
        try:
            self.connection.candidate.set(path=path, value=data, commit=commit)
            return True
        except InvalidPathError as error:
            print(
                "Path is not valid for set operation. Error: {}".format(error)
            )
            return False
        except SrosMgmtError as error:
            print("Unable to set data. Error: {}".format(error))
            return False

    def discard(self):
        """
        Clears the candidate datastore
        """
        try:
            self.connection.candidate.discard()
        except SrosMgmtError:
            print("Unable to discard from candidate datastore.")

    def compare(self) -> str:
        """
        Executes a compare of the candidate datastore against the running configuration and return
        the output in md-cli format.

        :return: md-cli output of the operation
        :rtype: str
        """
        return self.connection.candidate.compare(output_format="md-cli")

    def convert_to_json(self, path: str, pysros_data: dict) -> dict:
        """
        Given pysros format data at a given path, return in json format

        :param path: json-instance-path instance
        :type path: str
        :param pysros_data: Description
        :type pysros_data: dict
        :return: Description
        :rtype: dict
        """
        return self.connection.convert(
            path=path,
            payload=pysros_data,
            source_format="pysros",
            destination_format="json",
        )

    def convert_to_pysros(self, path: str, json_data: dict) -> dict:
        """
        Given json format data at a given path, return in pysros format

        :param path: json-instance-path instance
        :type path: str
        :param json_data: Description
        :type json_data: dict
        :return: Description
        :rtype: dict
        """
        return self.connection.convert(
            path=path,
            payload=json_data,
            source_format="json",
            destination_format="pysros",
        )

    def disconnect(self):
        self.connection.disconnect()


class StashInstall:
    @staticmethod
    def install():
        """
        Installs configuration to mount stash into md-cli.
        """
        print("Install Stash to this system.")
        node = Node()
        StashInstall.update_python_script(node)
        StashInstall.create_command_alias(node)
        print("Installation complete.")

    @staticmethod
    def update_python_script(node: Node):
        """
        Updates the python script to include a description.

        :param node: Node instance
        :type node: Node
        """
        print("Updating Python Script..")
        path = '/nokia-conf:configure/python/python-script[name="stash"]'
        data = {
            "version": Leaf("python3"),
            "name": Leaf("stash"),
            "description": Leaf(
                "Stash via https://github.com/nokia/pysros/tree/main/examples"
            ),
            "admin-state": Leaf("enable"),
            "urls": LeafList(["cf3:stash.py"]),
        }
        success = node.set(path=path, data=data, commit=True)
        if success:
            print("Python Script updated.")
        else:
            sys.exit(-5)

    @staticmethod
    def create_command_alias(node: Node):
        """
        Adds a command alias into the configuration datastore.

        :param node: Node instance
        :type node: Node
        """
        print("Adding Command Alias...")
        path = "/nokia-conf:configure/system/management-interface/cli/md-cli/environment/command-alias"
        data = {
            "alias": {
                "stash": Container(
                    {
                        "description": Leaf(
                            "Stash allows you to store and retrieve configuration snippets"
                        ),
                        "mount-point": {
                            "global": Container({"path": Leaf("global")})
                        },
                        "admin-state": Leaf("enable"),
                        "alias-name": Leaf("stash"),
                        "cli-command": Leaf(
                            'pwc json-instance-path | pyexec "stash"'
                        ),
                    }
                )
            }
        }
        success = node.set(path=path, data=data, commit=True)
        if success:
            print(
                "For the command-alias to take effect, log out and log back in."
            )
        else:
            sys.exit(-6)


class JSONInstancePath:
    """
    Handles operations on the output of pwc json-instance-path. This path looks like::

        A:admin@sr-1# pwc json-instance-path
        Present Working Context:
        /nokia-conf:configure/router[router-name="Base"]

    """

    def __init__(self, json_instance_path: str, from_pwc: bool = False):
        """
        Initialise the class instance

        :param json_instance_path: Output of pwc json-instance-path
        :type json_instance_path: str
        :param from_pwc: True if raw multi-line output, False if just the path string
        :type from_pwc: bool
        """
        if from_pwc:
            self.path = json_instance_path[1].strip().replace("\n", "")
        else:
            self.path = json_instance_path

    def string(self) -> str:
        """
        String the path string

        :return: The json-instance-path string
        :rtype: str
        """

        return self.path

    def __str__(self) -> str:
        """
        Allows this instance to be printed

        :return: The json-instance-path string
        :rtype: str
        """
        return self.path

    def is_configure(self) -> bool:
        """
        Checks whether the json instance path starts with configure

        :return: True if path starts with configure
        :rtype: bool
        """
        return self.path.startswith("/nokia-conf:configure")

    def split(self) -> list[str]:
        """
        A json-instance-path is made of / and quoted string. This method splits these parts.
        For example ``/nokia-conf:configure/router[router-name="Base"]`` is split where the ``/`` is into:
        ['','nokia-conf:configure', 'router[router-name="Base"]']

        :return: List of string parts of the json-instance-path
        :rtype: list
        """
        parts = []
        next_part = ""
        in_quotes = False
        path_str = self.path
        for i in range(0, len(path_str)):
            if path_str[i] == '"':
                in_quotes = not in_quotes

            if not in_quotes and path_str[i] == "/":
                parts.append(next_part)
                next_part = ""
            else:
                next_part += path_str[i]
        if len(next_part) != 0:
            parts.append(next_part)
        return parts

    def convert_to_cli(self) -> str:
        """
        Used to convert a json-instance-path like ``/nokia-conf:configure/router[router-name="Base"]``
        to "configure router base"

        :return: A configuration string
        :rtype: str
        """
        parts = self.split()[2:]
        cli_path = "configure"
        for part in parts:
            cli_path += " " + self.extract_node(part)
        return cli_path

    def extract_node(self, part: str) -> str:
        """
        When given a single part of the json-instance-path, it breaks values like ``user[user-name="admin"]``
        into ``user admin``

        :param part: A single part of the json-instance-path
        :type part: str
        :return: one or two values depending on part
        :rtype: str
        """
        # Break these into node and value if present: user[user-name="admin"]
        if "[" in part:
            index = part.find("[")
            node = part[0:index]
            key_start = index + 1
            key = part[key_start:-1]

            value_index = key.find('"')
            value = key[value_index:]

            return node + " " + value
        # Else, the node is just a single value: security
        else:
            return part

    def convert_to_cli_wrapped(self, length: int) -> list[str]:
        """
        Converts the json-instance-path of this instance into a wrapped CLI command string.
        Useful when the output is too wide and needs to be wrapped at a word boundary.

        :param length: Maximum length before wrapping
        :type length: int
        :return: Lines of text
        :rtype: list
        """
        converted = self.convert_to_cli()
        wrapped = self.wrap(converted, length)
        return wrapped

    def wrap(self, content: str, length: int) -> list[str]:
        """
        Wraps the given string into multiple lines given the maximum length.

        :param content: The string to wrap
        :type content: str
        :param length: Maximum length before wrapping
        :type length: int
        :return: Lines of text
        :rtype: list
        """
        parts = content.split(" ")
        lines = []
        running_string = ""
        for part in parts:
            if len(running_string) + len(part) > length:
                lines.append(running_string)
                running_string = ""
            if len(running_string) > 0:
                running_string += " "
            running_string += part
        lines.append(running_string)
        return lines

    def get_parent_path(self):
        """
        Generates a new JSONInstancePath instance for the parent path.

        :return: Parent path
        :rtype: JSONInstancePath
        """
        parts = self.split()
        parts = parts[:-1]  # drop last level
        parent_path = "/".join(parts)
        return JSONInstancePath(parent_path)


class StashDataStore:
    """
    Stash is a collection of Branches of stashed entries under a path tree.
    This datastore class manages this structure.
    """

    def __init__(self, filename: str):
        """
        Initialize the datastore for the stash. If the stash file exists, load it. Otherwise, create
        a new stash file.

        :param filename: Location to store the stash such as ``cf3:stash.json``
        :type filename: str
        """
        self.filename = filename
        if os.path.exists(filename):
            self.load()
        else:
            self.create_new_stash()

    def load(self):
        """
        Load from the stash json file.
        """
        with open(self.filename) as infile:
            self.stash = json.load(infile)
        self.activate_branch()

    def save(self):
        """
        Saves the stash datastore into the json file specified during instance creation.
        """
        with open(self.filename, "w") as outfile:
            json.dump(self.stash, outfile)

    def create_new_stash(self):
        """
        Generate a new stash datastore with an empty branch called ``global``.
        """
        self.stash = {"version": 2.0, "branches": {}}
        self.add_branch("global", "Global default branch")
        self.set_active_branch("global")
        self.activate_branch()

    def add_branch(self, name: str, description: str):
        """
        Adds a stash branch to the datastore

        :param name: Name of branch
        :type name: str
        :param description: Description of branch
        :type description: str
        """
        self.stash["branches"][name] = {
            "description": description,
            "stash": {},
            "next-id": 1,
            "paths": {},
        }
        self.save()

    def delete_branch(self, name: str):
        """
        Deletes a branch from the stash - including all stashed entries

        :param name: Name of branch
        :type name: str
        """
        self.stash["branches"].pop(name)
        self.save()

    def clean_branch(self, name: str):
        """
        Clean branch is used to remove all entries. This is effectively just overriding the branch with
        its initial setting. Therefore, this method points to the add_branch method while passing it the
        name of the branch given and the description of the branch currenly in the datastore.

        :param name: Name of branch
        :type name: str
        """
        branch = name
        description = self.stash["branches"][name]["description"]
        self.add_branch(branch, description)

    def set_active_branch(self, name: str):
        """
        Change the active branch

        :param name: Name of branch
        :type name: str
        """
        if name in self.stash["branches"]:
            self.stash["active-branch"] = name

    def activate_branch(self):
        """
        Activate the branch for stash operations
        """
        branch = self.stash["active-branch"]
        self.active_branch = self.stash["branches"][branch]
        self.save()

    def get_active_branch(self) -> str:
        """
        Returns the currently active branch.

        :return: Active Branch name
        :rtype: str
        """

        return self.stash["active-branch"]

    def get_branch_list(self) -> list[str]:
        """
        Gets the list of branches available

        :return: List of branch names
        :rtype: list[str]
        """
        return list(self.stash["branches"].keys())

    def get_branch_description(self, branch) -> str:
        """
        Returns the description of the named branch

        :param branch: Name of branch
        :return: Description of branch
        :rtype: str
        """
        return self.stash["branches"][branch]["description"]

    def get_branch_item_count(self, branch) -> int:
        """
        Returns the count of stashed entries in the given branch

        :param branch: Name of branch
        :return: Count of Entries
        :rtype: int
        """
        return len(self.stash["branches"][branch]["stash"])

    def has_branch(self, branch) -> bool:
        """
        Check whether the given branch exists

        :param branch: Name of branch
        :return: True if branch exists
        :rtype: bool
        """
        return branch in self.stash["branches"]

    def add_entry(self, path: JSONInstancePath, json_data: dict) -> str:
        """
        Adds a stash entry into the currently active branch

        :param path: json-instance-path object
        :type path: JSONInstancePath
        :param json_data: json format data
        :type json_data: dict
        :return: Id of the entry
        :rtype: int
        """
        id = self.get_next_id()
        self.active_branch["stash"][id] = {
            "path": path.string(),
            "data": json_data,
        }
        self.add_to_path(path, id)
        self.save()
        return id

    def has_id(self, id: str) -> bool:
        """
        Used to check whether the given entry id exists

        :param id: Id of the entry
        :type id: str
        :return: True if it exists
        :rtype: bool
        """
        return id in self.active_branch["stash"]

    def get_next_id(self) -> str:
        """
        Stash tracks a counter under each branch to allocate a unique id to each entry.
        This method is used to get the next id to use.

        :return: Entry Id
        :rtype: str
        """
        id = self.active_branch["next-id"]
        self.active_branch["next-id"] += 1
        return str(id)

    def add_to_path(self, path: JSONInstancePath, id: str):
        """
        Associates the given stash entry id to the json-instance-path

        :param path: json-instance-path object
        :type path: JSONInstancePath
        :param id: Entry Id
        :type id: str
        """
        path_chain = path.split()
        path_chain = path_chain[1:-1]  # attach up to parent link only

        segment = self.active_branch["paths"]
        for link in path_chain:
            if link not in segment:
                segment[link] = {}
            segment = segment[link]
        if "stash" not in segment:
            segment["stash"] = []
        segment["stash"].append(id)
        self.save()

    def delete_entry(self, id: str):
        """
        Deletes a stash entry.

        :param id: Entry Id
        :type id: str
        """
        entry = self.get_entry(id)
        path = JSONInstancePath(entry["path"])
        self.unlink_path(path, id)
        self.active_branch["stash"].pop(id)
        self.save()

    def unlink_path(self, path: JSONInstancePath, id: str):
        """
        When an entry is removed, its association to the json-instance-path is
        also removed.

        :param path: json-instance-path object
        :type path: JSONInstancePath
        :param id: Entry Id
        :type id: str
        """
        path_chain = path.split()
        path_chain = path_chain[1:-1]  # attach up to parent link only

        # Navigate to the path and remove the stash entry id
        segment = self.active_branch["paths"]
        segments = [segment]
        for link in path_chain:
            segment = segment[link]
            segments.append(segment)
        segment["stash"].remove(id)

        # Prune path tree as a clean up exercise
        for segment in reversed(segments):
            empty_keys = []
            for key in segment:
                if len(segment[key]) == 0:
                    empty_keys.append(key)
            for key in empty_keys:
                segment.pop(key)

    def add_comment_to_entry(self, id: str, comment: str):
        """
        Update the comment of a stash entry

        :param id: Entry Id
        :type id: str
        :param comment: Comment string
        :type comment: str
        """
        entry = self.get_entry(id)
        entry["comment"] = comment
        self.save()

    def get_entry(self, id: str) -> dict:
        """
        Get a stash entry by id.

        :param id: Entry Id
        :type id: str
        :return: Dictionary of the Stash Entry
        :rtype: dict
        """
        return self.active_branch["stash"][id]

    def get_all_entry_ids(self) -> list[str]:
        """
        Get all stash entries in the active branch

        :return: List of Entry Ids
        :rtype: list[str]
        """
        return list(self.active_branch["stash"].keys())

    def get_entries_from_path(self, path: JSONInstancePath) -> list[str]:
        """
        Get all stash entries in the active branch under given json-instance-path

        :param path: json-instance-path object
        :type path: JSONInstancePath
        :return: List of Entry Ids
        :rtype: list[str]
        """
        path_chain = path.split()[1:]
        segment = self.active_branch["paths"]
        for link in path_chain:
            if link in segment:
                segment = segment[link]
            else:
                return []  # Nothing found in stash
        if "stash" in segment:
            return segment["stash"].copy()
        return []  # Nothing found in stash

    def get_path_tree(self, path: JSONInstancePath) -> dict[str, str]:
        """
        Navigate to given json-instance-path

        :param path: json-instance-path object
        :type path: JSONInstancePath
        :return: Tree like dict with Entry Ids
        :rtype: dict
        """
        path_chain = path.split()[1:]
        segment = self.active_branch["paths"]
        for link in path_chain:
            if link in segment:
                segment = segment[link]
            else:
                return {}  # Nothing found in stash
        return segment


class StashDataViewer:
    """
    Used to print information in the stash datastore.
    """

    def __init__(self, datastore: StashDataStore, node: Node):
        """
        Docstring for __init__

        :param datastore: Datastore instance reference
        :type datastore: StashDataStore
        :param node: Node instance reference
        :type node: Node
        """
        self.datastore = datastore
        self.node = node

    def validate_id(self, id: str):
        """
        This method validates the provided id against the stash datastore.

        :param id: Id of the stash entry
        :type id: str
        """
        if not self.datastore.has_id(id):
            print(
                "The current active branch <{}> does not have an entry with id <{}>.".format(
                    self.datastore.get_active_branch(), id
                )
            )
            return False
        return True

    def print_entry(self, id: str):
        """
        This method will print an entry from the stash.

        :param id: Id of the stash entry
        :type id: str
        """
        self.print_entry_header(id)
        self.print_entry_data(id)

    def print_entry_header(self, id: str):
        """
        This method will print a formatted header of the stash entry including:
        branch, id, path, and parent.

        :param id: Id of the stash entry
        :type id: str
        """
        # Extract values to present in output
        branch = self.datastore.get_active_branch()
        entry = self.datastore.get_entry(id)
        comment = entry.get("comment", "n/a")
        path = JSONInstancePath(entry["path"])
        parent_path = path.get_parent_path()

        # Wrapped cli path strings
        path_lines = path.convert_to_cli_wrapped(68)
        parent_lines = parent_path.convert_to_cli_wrapped(68)

        # Prepare table for display
        table = KeyValueTable("Stash Entry", [(10, None), (68, None)])
        data = [["Branch", branch], ["Id", id], ["Comment", comment]]
        data.extend(self.get_kv_table_multi_line_entries("Path", path_lines))
        data.extend(
            self.get_kv_table_multi_line_entries("Parent", parent_lines)
        )

        # Print info table
        table.print(data)

    def get_kv_table_multi_line_entries(self, title: str, lines: list):
        """
        Returns a multi-line KV list where the first Key is set to title while the
        rest are set to empty string.
        To be used for building data into a KeyValueTable instance.

        :param title: Key for the KeyValueTable
        :type title: str
        :param lines: Lines to associate to Key
        :type lines: list
        """
        data = []
        first_line = True
        for line in lines:
            if first_line:
                data.append([title, line])
                first_line = False
            else:
                data.append(["", line])
        return data

    def print_entry_data(self, id: str):
        """
        Print data associated with a stored stash entry.

        :param id: Id of the stash entry
        :type id: str
        """
        entry = self.datastore.get_entry(id)
        path = entry["path"]
        json_data = entry["data"]
        data = self.node.convert_to_pysros(path, json_data)
        print("Data:")
        print("-" * 79)
        printTree(data)
        print("=" * 79)

    def print_entries_from_path(self, path: JSONInstancePath):
        """
        Print all entries under given path (if any)

        :param path: json-instance-path object
        :type path: JSONInstancePath
        """
        entries = self.datastore.get_entries_from_path(path)
        if len(entries) == 0:
            print(
                "There are no stash entries at this present working context."
            )
        else:
            for id in entries:
                self.print_entry(id)

    def print_entry_headers_from_path(self, path: JSONInstancePath):
        """
        Print just the headers of all entries under given path (if any)

        :param path: json-instance-path object
        :type path: JSONInstancePath
        """
        entries = self.datastore.get_entries_from_path(path)
        if len(entries) == 0:
            print(
                "There are no stash entries at this present working context."
            )
        else:
            for id in entries:
                self.print_entry_header(id)

    def print_all_entries(self):
        """
        Prints all the entries in the active branch.
        """
        branch = self.datastore.get_active_branch()
        entries = self.datastore.get_all_entry_ids()
        if len(entries) == 0:
            print(
                "There are no stashed entries in branch <{}>.".format(branch)
            )
        else:
            for id in sorted(entries):
                self.print_entry(id)

    def print_tree_from_path(self, path: JSONInstancePath):
        """
        Given a json-instance-path, retrieve and print the stash entry ids in tree format.

        :param path: json-instance-path object
        :type path: JSONInstancePath
        """
        tree = self.datastore.get_path_tree(path)
        print("=" * 79)
        print("Stash Tree View with stash entry IDs")
        print("-" * 79)
        if len(tree) > 0:
            printTree(tree)
        else:
            print("Nothing stashed at or below this current context level.")
        print("=" * 79)

    def print_branches(self):
        """
        Prints a tabular form of the branches in the stash
        """
        branches = self.datastore.get_branch_list()

        columns = [(16, "Name"), (54, "Description"), (7, "Entries", ">")]
        rows = []
        count = 0
        for branch in sorted(branches):
            rows.append(
                [
                    branch,
                    self.datastore.get_branch_description(branch),
                    self.datastore.get_branch_item_count(branch),
                ]
            )
            count += 1

        summary = "The active stash branch is <{}>".format(
            self.datastore.get_active_branch()
        )

        table = Table(
            "Stash Branches",
            columns=columns,
            showCount="Branches",
            summary=summary,
            width=79,
        )
        table.print(rows)


class StashApplication:
    @staticmethod
    def run():
        """
        Runs the stash application. It first prepares the environment with instances to the node,
        the json-instance-path, the datastore, and the dataviewer.

        Then it reads the arguments passed it and dispatches the commands to methods that implement
        each command operation.
        """
        node = Node()
        pwc_output = sys.stdin.readlines()
        path = JSONInstancePath(pwc_output, from_pwc=True)
        datastore = StashDataStore("cf3:\\stash.json")
        dataviewer = StashDataViewer(datastore, node)
        args = sys.argv

        # Dispatch
        if len(args) == 1:  # Python script called with no parameters
            StashApplication.print_stash_help()
        else:
            command = args[1]
            parameters = args[2:]
            if command == "install":
                StashInstall.install()
            elif command == "this":
                StashApplication.stash_this(
                    parameters, path, node, datastore, dataviewer
                )
            elif command == "comment":
                StashApplication.stash_comment(
                    parameters, datastore, dataviewer
                )
            elif command == "entry":
                StashApplication.stash_entry(parameters, dataviewer)
            elif command == "header":
                StashApplication.stash_header(parameters, dataviewer)
            elif command == "data":
                StashApplication.stash_data(parameters, dataviewer)
            elif command == "list":
                StashApplication.stash_list(path, dataviewer)
                if parameters[0] == "all":
                    StashApplication.stash_list_all(dataviewer)
            elif command == "list-all":
                StashApplication.stash_list_all(dataviewer)
            elif command == "tree":
                StashApplication.stash_tree(path, dataviewer)
            elif command == "delete":
                StashApplication.stash_delete(parameters, datastore)
            elif command == "compare":
                StashApplication.stash_compare(
                    parameters, node, datastore, dataviewer
                )
            elif command == "commit":
                StashApplication.stash_commit(
                    parameters, node, datastore, dataviewer
                )
            elif command == "branch":
                if len(args) < 3:
                    StashApplication.print_stash_branch_help()
                else:
                    branch_command = args[2]
                    parameters = args[3:]
                    if branch_command == "list":
                        StashApplication.stash_branch_list(dataviewer)
                    elif branch_command == "add":
                        StashApplication.stash_branch_add(
                            parameters, datastore
                        )
                    elif branch_command == "activate":
                        StashApplication.stash_branch_activate(
                            parameters, datastore
                        )
                    elif branch_command == "delete":
                        StashApplication.stash_branch_delete(
                            parameters, datastore
                        )
                    elif branch_command == "clean":
                        StashApplication.stash_branch_clean(
                            parameters, datastore
                        )
                    else:
                        StashApplication.print_stash_branch_help()
            else:
                StashApplication.print_stash_help()
        node.disconnect()

    @staticmethod
    def print_stash_help():
        """
        Prints a help string for stash operations
        """
        print("Syntax: stash <>")
        commands = {
            "this": "Add config at current path to stash",
            "comment": "Add a comment to an entry",
            "entry": "Show saved stash entry",
            "header": "Show only header of stash entry",
            "data": "Show saved configuration data in a stash entry",
            "list": "List entries parented here",
            "list-all": "List all entries in branch",
            "tree": "Tree view of stash entry ids",
            "delete": "Delete a stash entry",
            "compare": "Compare stash entry to current config",
            "commit": "Commit a stash entry to configuration",
            "branch": "Manage stash branches",
            "install": "Installs python script and command alias",
        }
        for command in sorted(commands):
            print("    {:<16}{}".format(command, commands[command]))

        print(
            "stash - The Stash enables the operator to store and retrieve config snippets"
        )

    @staticmethod
    def stash_this(
        args: list[str],
        path: JSONInstancePath,
        node: Node,
        datastore: StashDataStore,
        dataviewer: StashDataViewer,
    ):
        """
        Implements the ``stash this`` command that add a new stash entry into the datastore.

        :param args: Args passed to this command
        :type args: list[str]
        :param path: json-instance-path object
        :type path: JSONInstancePath
        :param node: node object
        :type node: Node
        :param datastore: datastore object
        :type datastore: StashDataStore
        :param dataviewer: dataviewer object
        :type dataviewer: StashDataViewer
        """
        # Only permit stash this from a configuration datastore.
        if not path.is_configure():
            print(
                "This method can only be used while in a configuration datastore."
            )
        else:
            data = node.get(path.string())  # Get data at path
            if data:
                # Convert to storable format
                json_data = node.convert_to_json(path.string(), data)
                id = datastore.add_entry(path, json_data)

                # Add comment if passed
                if len(args) > 0:
                    comment = " ".join(args)
                    datastore.add_comment_to_entry(id, comment)
                dataviewer.print_entry_header(id)
            else:
                print("No committed configuration found.")

    @staticmethod
    def stash_comment(
        args: list[str], datastore: StashDataStore, dataviewer: StashDataViewer
    ):
        """
        Implements the ``stash comment`` command that is used to associate a comment to a stash entry.

        :param args: Args passed to this command
        :type args: list[str]
        :param datastore: datastore object
        :type datastore: StashDataStore
        :param dataviewer: dataviewer object
        :type dataviewer: StashDataViewer
        """
        # Verify that required arguments have been passed
        args_required = {
            "id": "Id of stash entry",
            "comment": "Text of up to 255 characters (in quotes)",
        }
        if len(args) != len(args_required):
            StashApplication.print_command_syntax(
                "stash comment", args_required
            )
        else:
            id = args[0]
            if dataviewer.validate_id(id):
                comment = args[1]
                datastore.add_comment_to_entry(id, comment)
                print("Comment saved.")

    @staticmethod
    def stash_entry(args: list[str], dataviewer: StashDataViewer):
        """
        Implements the ``stash entry`` command that is used to print the contents of a stash entry.

        :param args: Args passed to this command
        :type args: list[str]
        :param dataviewer: dataviewer object
        :type dataviewer: StashDataViewer
        """
        # Verify that required arguments have been passed
        args_required = {"id": "Id of stash entry"}
        if len(args) != len(args_required):
            StashApplication.print_command_syntax("stash entry", args_required)
        else:
            id = args[0]
            if dataviewer.validate_id(id):
                dataviewer.print_entry(id)

    @staticmethod
    def stash_header(args: list[str], dataviewer: StashDataViewer):
        """
        Implements the ``stash header`` command that is used to print just the header of a stash entry.

        :param args: Args passed to this command
        :type args: list[str]
        :param dataviewer: dataviewer object
        :type dataviewer: StashDataViewer
        """
        # Verify that required arguments have been passed
        args_required = {"id": "Id of stash entry"}
        if len(args) != len(args_required):
            StashApplication.print_command_syntax(
                "stash header", args_required
            )
        else:
            id = args[0]
            if dataviewer.validate_id(id):
                dataviewer.print_entry_header(id)

    @staticmethod
    def stash_data(args: list[str], dataviewer: StashDataViewer):
        """
        Implements the ``stash data`` command that is used to print only the saved configuration data
        stored in a stash entry.

        :param args: Args passed to this command
        :type args: list[str]
        :param dataviewer: dataviewer object
        :type dataviewer: StashDataViewer
        """
        # Verify that required arguments have been passed
        args_required = {"id": "Id of stash entry"}
        if len(args) != len(args_required):
            StashApplication.print_command_syntax("stash data", args_required)
        else:
            id = args[0]
            if dataviewer.validate_id(id):
                dataviewer.print_entry_data(id)

    @staticmethod
    def stash_list(path: JSONInstancePath, dataviewer: StashDataViewer):
        """
        Implements the ``stash list`` command that is used to print all entries at current path.

        :param path: json-instance-path object
        :type path: JSONInstancePath
        :param dataviewer: dataviewer object
        :type dataviewer: StashDataViewer
        """
        dataviewer.print_entries_from_path(path)

    @staticmethod
    def stash_list_all(dataviewer: StashDataViewer):
        """
        Implements the ``stash list-all`` command that is used to print all entries in
        current stash branch.

        :param dataviewer: dataviewer object
        :type dataviewer: StashDataViewer
        """
        dataviewer.print_all_entries()

    @staticmethod
    def stash_tree(path: JSONInstancePath, dataviewer: StashDataViewer):
        """
        Implements the ``stash tree`` command that is used to print a tree view of stash
        entries at the current path or deeper.

        :param path: json-instance-path object
        :type path: JSONInstancePath
        :param dataviewer: dataviewer object
        :type dataviewer: StashDataViewer
        """
        dataviewer.print_tree_from_path(path)

    @staticmethod
    def stash_delete(args: list[str], datastore: StashDataStore):
        """
        Implements the ``stash delete`` command that is used to delete a saved stash entry.

        :param args: List of args passed to this command
        :type args: list[str]
        :param datastore: datastore object
        :type datastore: StashDataStore
        """
        # Verify that required arguments have been passed
        args_required = {"id": "Id of stash entry"}
        if len(args) != len(args_required):
            StashApplication.print_command_syntax(
                "stash delete", args_required
            )
        else:
            id = args[0]
            if datastore.has_id(id):
                branch = datastore.get_active_branch()
                datastore.delete_entry(id)
                print(
                    "Stash entry <{}> removed from branch <{}>.".format(
                        id, branch
                    )
                )

    @staticmethod
    def stash_compare(
        args: list[str],
        node: Node,
        datastore: StashDataStore,
        dataviewer: StashDataViewer,
    ):
        """
        Implements the ``stash compare`` command that is used to compare a saved stash entry
        against the running configuration of the node.

        :param args: List of args passed to this command
        :type args: list[str]
        :param node: node object
        :type node: Node
        :param datastore: datastore object
        :type datastore: StashDataStore
        :param dataviewer: dataviewer object
        :type dataviewer: StashDataViewer
        """
        # Verify that required arguments have been passed
        args_required = {"id": "Id of stash entry"}
        if len(args) != len(args_required):
            StashApplication.print_command_syntax(
                "stash compare", args_required
            )
        else:
            id = args[0]
            if datastore.has_id(id):
                # Extract values to present in output
                entry = datastore.get_entry(id)
                path = JSONInstancePath(entry["path"])
                data = entry["data"]
                data = node.convert_to_pysros(path.string(), data)

                # Set configuration into candidate without commit and run a compare
                success = node.set(path.string(), data, commit=False)
                if success:
                    dataviewer.print_entry_header(id)
                    result = node.compare()
                    if len(result) > 0:
                        print(result)
                    else:
                        print("No difference found.")
                    print("-" * 79)
                    node.discard()

    @staticmethod
    def stash_commit(
        args: list[str],
        node: Node,
        datastore: StashDataStore,
        dataviewer: StashDataViewer,
    ):
        """
        Implements the ``stash commit`` command that is used to apply the saved data in a stash entry
        in the running configuration.

        :param args: List of args passed to this command
        :type args: list[str]
        :param node: node object
        :type node: Node
        :param datastore: datastore object
        :type datastore: StashDataStore
        :param dataviewer: dataviewer object
        :type dataviewer: StashDataViewer
        """
        # Verify that required arguments have been passed
        args_required = {"id": "Id of stash entry"}
        if len(args) != len(args_required):
            StashApplication.print_command_syntax(
                "stash commit", args_required
            )
        else:
            id = args[0]
            if datastore.has_id(id):
                # Extract values to present in output
                entry = datastore.get_entry(id)
                path = JSONInstancePath(entry["path"])
                data = entry["data"]
                data = node.convert_to_pysros(path.string(), data)
                # Set the configuration into candidate and commit it
                success = node.set(path.string(), data, commit=True)
                if success:
                    dataviewer.print_entry_header(id)
                    print("Committed")

    @staticmethod
    def print_stash_branch_help():
        """
        Print help text for ``stash branch``.
        """
        print("Syntax: stash branch <>")
        commands = {
            "list": "List available branches",
            "add": "Add a new branch",
            "activate": "Activate a branch for stash operations",
            "delete": "Delete a branch (stash entries are lost)",
            "clean": "Clean all entries and reset stash branch",
        }
        for command in sorted(commands):
            print("    {:<16}{}".format(command, commands[command]))

        print("Branches allows for stash entry organization.")

    @staticmethod
    def stash_branch_list(dataviewer: StashDataViewer):
        """
        Implements the ``stash branch list`` command that is used to print a table of stash branches.

        :param dataviewer: dataviewer object
        :type dataviewer: StashDataViewer
        """
        dataviewer.print_branches()

    @staticmethod
    def stash_branch_add(args: list[str], datastore: StashDataStore):
        """
        Implements the ``stash branch add`` command that is used to add a new branch to stash.

        :param args: List of arguments passed to this command
        :type args: list[str]
        :param datastore: datastore object
        :type datastore: StashDataStore
        """
        # Verify that required arguments have been passed
        args_required = {
            "name": "Branch name; maximum 16 characters",
            "description": "Branch description; maximum 80 characters",
        }
        if len(args) != len(args_required):
            StashApplication.print_command_syntax(
                "stash branch add", args_required
            )
        else:
            new_branch_name = args[0][
                0:16
            ].lower()  # Trim to max 16 characters
            new_branch_description = args[1][0:80]  # Trim to max 80 characters

            if datastore.has_branch(new_branch_name):
                print("Branch <{}> already exists.".format(new_branch_name))
            else:
                datastore.add_branch(new_branch_name, new_branch_description)
                print("Branch <{}> created.".format(new_branch_name))

    @staticmethod
    def stash_branch_activate(args: list[str], datastore: StashDataStore):
        """
        Implements the ``stash branch activate`` command that is used to choose which
        branch accepts stash operations.

        :param args: List of arguments passed to this command
        :type args: list[str]
        :param datastore: datastore object
        :type datastore: StashDataStore
        """
        # Verify that required arguments have been passed
        args_required = {"name": "Branch name; maximum 16 characters"}
        if len(args) != len(args_required):
            StashApplication.print_command_syntax(
                "stash branch activate", args_required
            )
        else:
            branch_name = args[0][0:16].lower()  # Trim to max 16 characters
            if datastore.has_branch(branch_name):
                datastore.set_active_branch(branch_name)
                datastore.activate_branch()
                print("Branch <{}> activated.".format(branch_name))
            else:
                print("The branch <{}> does not exist.".format(branch_name))

    @staticmethod
    def stash_branch_delete(args: list[str], datastore: StashDataStore):
        """
        Implements the ``stash branch delete`` command that is used to delete a branch
        from the stash.

        :param args: List of arguments passed to this command
        :type args: list[str]
        :param datastore: datastore object
        :type datastore: StashDataStore
        """
        # Verify that required arguments have been passed
        args_required = {"name": "Branch name; maximum 16 characters"}
        if len(args) != len(args_required):
            StashApplication.print_command_syntax(
                "stash branch delete", args_required
            )
        else:
            branch_name = args[0][0:16].lower()  # Trim to max 16 characters
            active_branch = datastore.get_active_branch()
            if datastore.has_branch(branch_name):
                if branch_name == active_branch:
                    print(
                        "Cannot delete active branch <{}>.".format(branch_name)
                    )
                else:
                    datastore.delete_branch(branch_name)
                    print("Branch <{}> has been deleted.".format(branch_name))
            else:
                print("The branch <{}> does not exist.".format(branch_name))

    @staticmethod
    def stash_branch_clean(args: list[str], datastore: StashDataStore):
        """
        Implements the ``stash branch clean`` command that is remove all entries in a stash branch
        but not delete it. The id counter for the branch is also reset to 1.

        :param args: List of arguments passed to this command
        :type args: list[str]
        :param datastore: datastore object
        :type datastore: StashDataStore
        """
        # Verify that required arguments have been passed
        args_required = {"name": "Branch name; maximum 16 characters"}
        if len(args) != len(args_required):
            StashApplication.print_command_syntax(
                "stash branch clean", args_required
            )
        else:
            branch_name = args[0][0:16].lower()  # Trim to max 16 characters
            if datastore.has_branch(branch_name):
                datastore.clean_branch(branch_name)
                print(
                    "The branch <{}> has been cleaned and reset.".format(
                        branch_name
                    )
                )
            else:
                print("The branch <{}> does not exist.".format(branch_name))

    @staticmethod
    def print_command_syntax(command: str, args_required: dict):
        """
        Print syntax for a command.

        For example, this method could be called with:
        .. code-block:: usage
            args_required = {
                "name": "Branch name; maximum 16 characters",
                "description": "Branch description; maximum 80 characters",
            }
            StashApplication.print_command_syntax("stash branch add", args_required)

        In this case, the method will print:
        .. code-block:: output
            This command requires 2 arguments

            Syntax: stash branch add <name> <description>
                name            Branch name; maximum 16 characters
                description     Branch description; maximum 80 characters

        :param command: Command string the syntax is for
        :type command: str
        :param args_required: Key/Value pairs of arguments and their descriptions
        :type args_required: dict
        """
        # Message line for number of args passed
        count = len(args_required)
        if count == 1:
            print("This command requires an argument.")
        else:
            print("This command requires {} arguments".format(count))

        # Syntax Line
        print()
        print("Syntax: {}".format(command), end="")
        for key in args_required:
            print(" <{}>".format(key), end="")
        print()

        # Description of each argument
        for key, value in args_required.items():
            print("    {:<16}{}".format(key, value))
        print()


def main():
    """
    This is the main entry into the application. Two high level options are available: to install, or, use the stash.
    """
    if len(sys.argv) == 2 and sys.argv[1] == "install":
        StashInstall.install()
    else:
        StashApplication.run()


if __name__ == "__main__":
    main()
