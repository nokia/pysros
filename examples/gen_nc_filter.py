#!/usr/bin/env python3
### gen_nc_filter.py
#   Copyright 2021-2026 Nokia
###

"""
Convert YANG instance paths to NETCONF XML filter content.

Tested on SR OS 25.10.R1 and 26.3.R1

This script reads a YANG data path from standard input and converts it
to a NETCONF XML filter.  It is designed to work with the output of the
pwc json-instance-path command on SR OS, which provides YANG paths
for configuration and state data.

It can be used with any NETCONF client that requires subtree filters,
such as ncclient and Ansible automation modules.

It can be executed on an SR OS device using the pyexec command as an
output modifier to the pwc json-instance-path command.

Usage:

    echo "/nokia-conf:configure/system" | python3 gen_nc_filter.py

SR OS Usage:

    Place this script into the cf3:/bin directory on the SR OS device.

    Configure the python-script to reference the script filename.

    /configure python { python-script "gen_nc_filter" admin-state enable }
    /configure python { python-script "gen_nc_filter" urls ["cf3:/bin/gen_nc_filter.py"] }
    /configure python { python-script "gen_nc_filter" version python3 }

    Then use the script as an output modifier to the pwc json-instance-path command:

    pwc json-instance-path | pyexec gen_nc_filter

Example Output:

    <configure xmlns="urn:nokia.com:sros:ns:yang:sr:conf">
      <router>
        <router-name>Base</router-name>
        <bgp>
          <neighbor>
            <ip-address>192.168.1.1</ip-address>
          </neighbor>
        </bgp>
      </router>
    </configure>

"""

import sys


def escape_xml(text):
    """
    Escape special XML characters required by XML 1.0 specification.

    References:
    - W3C XML 1.0 Specification, Section 2.4 "Character References"
      https://www.w3.org/TR/xml/#sec-references
    - W3C XML 1.0 Specification, Section 4.6 "Predefined Entities"
      https://www.w3.org/TR/xml/#sec-predefined-ent
    - RFC 3470: Guidelines for the Use of Extensible Markup Language (XML)
      within IETF Protocols, Section 4.13 "Entity Declarations and Entity References"
      https://www.rfc-editor.org/rfc/rfc3470.html#section-4.13

    XML has five standard predefined entity references:
    - & (ampersand) -> &amp;       [MUST in all contexts - escape FIRST]
    - < (less-than) -> &lt;        [MUST in element content]
    - > (greater-than) -> &gt;     [MUST in element content when preceded by ]]
    - " (quotation mark) -> &quot; [MUST in attribute values]
    - ' (apostrophe) -> &apos;     [OPTIONAL - in attribute values]

    Critical: & MUST be escaped first to avoid double-escaping of other entities.
    """
    text = str(text)
    # Ampersand MUST be first - prevents double-escaping of other entities
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def validate_yang_path(path_string):
    """
    Validate that input is a valid YANG instance path format.

    YANG paths must:
    - Not be empty or None
    - Start with '/'
    - Contain valid namespace prefixes (format: namespace:element)
    - Have balanced brackets for predicates
    - Have properly quoted predicate values (must use double quotes)
    - Follow format: /namespace:element[predicate="value"]/...

    Raises ValueError with descriptive message if validation fails.
    Returns: tuple (is_config_path: bool, is_state_path: bool)
    """
    # Check for empty/null input
    if not path_string or not isinstance(path_string, str):
        raise ValueError(
            "Invalid input: expected non-empty string, got {}".format(
                type(path_string).__name__
            )
        )

    path_string = path_string.strip()

    # Must start with /
    if not path_string.startswith("/"):
        raise ValueError(
            "Invalid YANG path: must start with '/', got: {}".format(
                path_string[:20]
            )
        )

    # Check for balanced brackets
    bracket_count = 0
    for i, char in enumerate(path_string):
        if char == "[":
            bracket_count += 1
        elif char == "]":
            bracket_count -= 1

        if bracket_count < 0:
            raise ValueError(
                "Invalid YANG path: unmatched ']' at position {}".format(i)
            )

    if bracket_count != 0:
        raise ValueError("Invalid YANG path: unmatched '[' bracket(s)")

    # Validate predicates have quoted values
    pos = 0
    while True:
        bracket_start = path_string.find("[", pos)
        if bracket_start == -1:
            break
        bracket_end = path_string.find("]", bracket_start)
        if bracket_end == -1:
            break

        # Extract content between brackets (skipping the '[')
        pred_start = bracket_start + 1
        pred_content = path_string[pred_start:bracket_end]
        eq_pos = pred_content.find("=")
        if eq_pos != -1:
            # Extract value after '=' (skipping the '=')
            value_start = eq_pos + 1
            pred_value = pred_content[value_start:].strip()
            if not (pred_value.startswith('"') and pred_value.endswith('"')):
                raise ValueError(
                    "Invalid predicate value (must be quoted): {}".format(
                        pred_content
                    )
                )

        pos = bracket_end + 1

    # Check for valid namespace prefix in first element
    colon_pos = path_string.find(":")
    slash_pos = path_string.find("/", 1)  # Find second /

    if colon_pos == -1:
        raise ValueError(
            "Invalid YANG path: missing namespace prefix, got: {}".format(
                path_string[:30]
            )
        )

    # Extract first element to validate namespace
    if slash_pos == -1:
        first_element = path_string[1:]  # Everything after first /
    else:
        first_element = path_string[1:slash_pos]

    # Remove predicate part if present
    bracket_pos = first_element.find("[")
    if bracket_pos != -1:
        first_element = first_element[:bracket_pos]

    # Check namespace prefix format
    is_config_path = False
    is_state_path = False

    if ":" in first_element:
        namespace, element = first_element.split(":", 1)

        # Validate namespace is one of expected SR OS namespaces
        if namespace == "nokia-conf":
            is_config_path = True
            if element != "configure":
                raise ValueError(
                    "Invalid SR OS config path: expected 'nokia-conf:configure', "
                    "got 'nokia-conf:{}'".format(element)
                )
        elif namespace == "nokia-state":
            is_state_path = True
            if element != "state":
                raise ValueError(
                    "Invalid SR OS state path: expected 'nokia-state:state', "
                    "got 'nokia-state:{}'".format(element)
                )
        # Allow other namespaces for future extensibility

    return is_config_path, is_state_path


def parse_yang_path(path):
    """
    Parse YANG instance identifier path and build XML structure.

    Handles:
    - Simple elements: /nokia-conf:configure/system
    - Predicates: /nokia-conf:configure/router[router-name="Base"]
    - Multiple levels: /nokia-conf:configure/router[router-name="Base"]/bgp/neighbor[ip-address="192.168.1.1"]

    Returns dict with 'namespace', 'elements', 'error'
    """
    if not path or not path.startswith("/"):
        return {"error": "Path must start with /"}

    path = path.strip()
    elements = []
    current_pos = 1
    namespace = None

    while current_pos < len(path):
        # Find next slash or end of string
        next_slash = path.find("/", current_pos)
        if next_slash == -1:
            segment = path[current_pos:]
            current_pos = len(path)
        else:
            segment = path[current_pos:next_slash]
            current_pos = next_slash + 1

        if not segment:
            continue

        # Parse segment: element[predicate="value"] or just element
        bracket_pos = segment.find("[")
        if bracket_pos == -1:
            element_name = segment
            predicate = None
        else:
            element_name = segment[:bracket_pos]
            # Extract predicate content
            bracket_end = segment.find("]", bracket_pos)
            if bracket_end == -1:
                return {"error": "Unmatched bracket in: {}".format(segment)}
            pred_start = bracket_pos + 1
            predicate = segment[pred_start:bracket_end]

        # Extract namespace from first element
        if ":" in element_name:
            ns, elem = element_name.split(":", 1)
            if not namespace:
                namespace = ns
            element_name = elem

        elements.append({"name": element_name, "predicate": predicate})

    if not namespace:
        return {"error": "No namespace found in path"}

    return {"namespace": namespace, "elements": elements, "error": None}


def parse_predicate(predicate):
    """
    Parse predicate string: key="value" or key='value'
    Returns tuple (key, value)
    """
    eq_pos = predicate.find("=")
    if eq_pos == -1:
        return None, None

    key = predicate[:eq_pos].strip()
    value_start = eq_pos + 1
    value_part = predicate[value_start:].strip()

    # Remove quotes
    if (value_part.startswith('"') and value_part.endswith('"')) or (
        value_part.startswith("'") and value_part.endswith("'")
    ):
        value = value_part[1:-1]
    else:
        value = value_part

    return key, value


def build_xml(namespace, elements):
    """
    Build properly nested XML structure from parsed YANG path.

    Returns just the inner content (no XML declaration, no filter wrapper).
    Correctly nests all elements in hierarchy and closes them at the end.
    """
    # Map namespace to xmlns
    ns_map = {
        "nokia-conf": "urn:nokia.com:sros:ns:yang:sr:conf",
        "nokia-state": "urn:nokia.com:sros:ns:yang:sr:state",
    }

    if namespace not in ns_map:
        return None, "Unknown namespace: {}".format(namespace)

    lines = []

    # Open all elements
    for i, elem_data in enumerate(elements):
        indent = "  " * i
        elem_name = elem_data["name"]
        predicate = elem_data["predicate"]

        # Open the element
        lines.append("{}<{}>".format(indent, elem_name))

        # Add predicate as child element if present
        if predicate:
            key, value = parse_predicate(predicate)
            if key and value:
                inner_indent = "  " * (i + 1)
                lines.append(
                    "{}<{}>{}</{}>".format(
                        inner_indent, key, escape_xml(value), key
                    )
                )

    # Close all elements in reverse order
    for i in range(len(elements) - 1, -1, -1):
        indent = "  " * i
        elem_name = elements[i]["name"]
        lines.append("{}</{}>".format(indent, elem_name))

    return "\n".join(lines), None


def main():
    """Main entry point."""
    try:
        # Read from stdin
        input_text = sys.stdin.read().strip()

        if not input_text:
            sys.stderr.write("Error: No input provided\n")
            sys.exit(1)

        # Extract YANG path from input
        # Handle SR OS pwc output which includes status lines like "Present Working Context"
        yang_path = None
        for line in input_text.split("\n"):
            line = line.strip()
            # YANG paths start with /
            if line.startswith("/"):
                yang_path = line
                break

        if not yang_path:
            sys.stderr.write("Error: No YANG path found in input\n")
            sys.exit(1)

        # Validate YANG path
        is_config, is_state = validate_yang_path(yang_path)

        # Parse path
        parsed = parse_yang_path(yang_path)
        if parsed.get("error"):
            sys.stderr.write("Error: {}\n".format(parsed["error"]))
            sys.exit(1)

        # Build XML
        xml_content, error = build_xml(parsed["namespace"], parsed["elements"])

        if error:
            sys.stderr.write("Error: {}\n".format(error))
            sys.exit(1)

        # Output just the inner content (no XML declaration, no filter wrapper)
        print(xml_content)

    except Exception as e:
        sys.stderr.write("Error: {}\n".format(str(e)))
        sys.exit(1)


if __name__ == "__main__":
    main()
