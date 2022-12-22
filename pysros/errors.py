# Copyright 2021 Nokia

from .exceptions import *
from .exceptions import make_exception

__doc__ = """This module contains error definitions for pySROS.

.. reviewed by PLM 20211201
.. reviewed by TechComms 21211202
"""

pysros_err_action_subtree_not_supported = (SrosMgmtError, """Md-compare subtree-path is not supported in action method, use compare method instead""")
pysros_err_arg_must_be_string = (TypeError, """Argument "module" must be a string""")
pysros_err_attr_cannot_be_deleted = (AttributeError, "'{obj}' object attribute '{attribute}' cannot be deleted")
pysros_err_attr_is_read_only = (AttributeError, "'{obj:.50}' object attribute '{attribute:.100}' is read-only")
pysros_err_can_check_state_from_running_only = (SrosMgmtError, "State can be checked from running datastore only")
pysros_err_can_get_state_from_running_only = (LookupError, "State can be retrieved from running datastore only")
pysros_err_can_have_one_semicolon = (InvalidPathError, "Identifier can contain only one ':'")
pysros_err_can_not_find_yang = (ModelProcessingError, "Cannot find yang '{yang_name}'")
pysros_err_cannot_call_go_to_parent = (InvalidPathError, "Cannot call go_to_parent on root")
pysros_err_cannot_delete_from_state = (SrosMgmtError, "Cannot delete from state tree")
pysros_err_cannot_find_module_set_id_or_content_id = (RuntimeError, "Cannot find module-set-id or content-id")
pysros_err_cannot_lock_and_unlock_running = (SrosMgmtError, "Cannot lock and unlock running config")
pysros_err_cannot_modify_config = (SrosMgmtError, "Cannot modify running config")
pysros_err_cannot_modify_state = (SrosMgmtError, "Cannot modify state tree")
pysros_err_cannot_pars_path = (ModelProcessingError, "Cannot parse path {path!r}")
pysros_err_cannot_remove_node = (ModelProcessingError, "Cannot remove {node}")
pysros_err_cannot_specify_non_key_leaf = (InvalidPathError, "Cannot specify non-key leaf as path attribute")
pysros_err_commit_conflicts_detected = (SrosConfigConflictError, "Commit failed - conflict detected, configuration changes cleared")
pysros_err_could_not_create_conn = (RuntimeError, "Cannot create connection - {reason}")
pysros_err_data_missing = (SrosMgmtError, "Entry does not exist")
pysros_err_depth_must_be_positive = (ValueError, "Depth must be > 0")
pysros_err_duplicate_found = (SrosMgmtError, "Entry cannot contain duplicates - {duplicate}")
pysros_err_empty_path = (InvalidPathError, "Empty path")
pysros_err_entry_does_not_exists = (KeyError, "Entry does not exist")
pysros_err_even_num_of_columns_required = (ValueError, "Even number of data columns required")
pysros_err_expected_end_bracket = (InvalidPathError, "Expected ']'")
pysros_err_expected_equal_operator = (InvalidPathError, "Expected '='")
pysros_err_filter_empty_string = (SrosMgmtError, "Cannot filter by an empty string")
pysros_err_filter_not_supported_on_leaves = (InvalidPathError, "Filter is not supported for leaves")
pysros_err_filter_should_be_dict = (TypeError, "Filter argument should be a dict")
pysros_err_filter_wrong_leaf_value = (TypeError, "Unsupported leaf filter for '{leaf_name}'")
pysros_err_incorrect_leaf_value = (SrosMgmtError, "Invalid value for leaf {leaf_name}")
pysros_err_invalid_align = (ValueError, "Invalid align: '{align}'")
pysros_err_invalid_col_description = (TypeError, "Invalid column description")
pysros_err_invalid_config = (ModelProcessingError, "Invalid config statement")
pysros_err_invalid_identifier = (InvalidPathError, "Invalid identifier")
pysros_err_invalid_json_structure = (ValueError, "Invalid JSON structure")
pysros_err_invalid_key_in_path = (SrosMgmtError, "Invalid key value in path")
pysros_err_invalid_module_set_id_or_content_id = (RuntimeError, "Invalid module-set-id")
pysros_err_invalid_operation_on_key = (InvalidPathError, "Operation cannot be performed on key")
pysros_err_invalid_operation_on_leaflist = (InvalidPathError, "Operation cannot be performed on leaflist")
pysros_err_invalid_path_operation_missing_keys = (InvalidPathError, "Cannot perform operation on list without specifying keys")
pysros_err_invalid_target = (ValueError, "Invalid target")
pysros_err_invalid_transport = (TypeError, "Currently only NETCONF transport is supported")
pysros_err_invalid_value = (TypeError, "MO contents not a dict '{data}'")
pysros_err_invalid_value_for_type = (TypeError, "Invalid value for {type}: {value}")
pysros_err_invalid_yang_path = (ModelProcessingError, "Invalid path {path!r}")
pysros_err_invalid_xml_element = (ValueError, 'XML element {element} can be empty or contain another XML element')
pysros_err_invalid_xml_root = (ValueError, 'XML root element can be empty or contain another XML element')
pysros_err_key_val_mismatch = (SrosMgmtError, "Cannot change value of key-leaf '{key_name}'")
pysros_err_leaflist_should_be_list = (TypeError, "expected list object but got {type_name}")
pysros_err_malformed_keys = (TypeError, "Malformed keys for '{full_path}' with value '{value}'")
pysros_err_missing_keys = (InvalidPathError, "Missing keys on element '{element}'")
pysros_err_no_data_found = (LookupError, "No data found")
pysros_err_not_connected = (RuntimeError, "Not connected")
pysros_err_not_found_slash_before_name = (InvalidPathError, "'/' not found before element name")
pysros_err_path_should_be_string = (TypeError, "path argument should be a string")
pysros_err_prefix_does_not_have_ns = (LookupError, "prefix '{prefix}' of '{name}' does not have corresponding namespace")
pysros_err_root_path = (InvalidPathError, "Operation cannot be performed on root")
pysros_err_server_dos_not_have_required_yang_lib = (RuntimeError, "NETCONF server does not have required yang-library")
pysros_err_server_dos_not_have_yang_lib = (RuntimeError, "NETCONF server does not have yang-library capability")
pysros_err_target_should_be_list = (InvalidPathError, "Target should be a list")
pysros_err_type_must_be = (TypeError, "must be {expected:.50s}, not {actual:.50s}")
pysros_err_unended_quoted_string = (InvalidPathError, "Unended quoted string")
pysros_err_unexpected_change_of_path_ctx = (ModelProcessingError, "Unexpected change of path ctx")
pysros_err_unexpected_end_of_yang = (ModelProcessingError, "Unexpected end of YANG")
pysros_err_unexpected_token = (ModelProcessingError, "Unexpected token {token}")
pysros_err_unexpected_value_of_type = (TypeError, "Unexpected value of type '{val_type}' in '{type}'")
pysros_err_unknown_child = (SrosMgmtError, "Cannot find child with name '{child_name}' in path '{path}'")
pysros_err_unknown_dds = (InternalError, "Unknown data definition statement type {dds}")
pysros_err_unknown_dev_statement = (ModelProcessingError, "Unknown deviate statement: {stmt!r}'")
pysros_err_unknown_element = (InvalidPathError, "Unknown element '{element}'")
pysros_err_unknown_identityref = (ModelProcessingError, "Unknown identityref {identifier}")
pysros_err_unknown_key = (InvalidPathError, "Unknown key '{key_name}'")
pysros_err_unknown_prefix_for_name = (ModelProcessingError, "Unknown prefix '{prefix}' for '{name}'")
pysros_err_unresolved_augment = (InternalError, "Augments cannot be resolved")
pysros_err_unresolved_leafref = (InternalError, "Unresolved leafref {type}")
pysros_err_unresolved_type = (InternalError, "Unresolved type in schema: {type}")
pysros_err_unsupported_set_method = (SrosMgmtError, "Unsupported set method")
pysros_err_unsupported_type_for_wrapper = (TypeError, "Unsupported type for {wrapper_name} data")
pysros_err_use_deepcopy = (NotImplementedError, "Use '.deepcopy' instead")
pysros_err_wrong_netconf_response = (SrosMgmtError, "Wrong NETCONF response")
pysros_err_wrong_rhs = (ModelProcessingError, "Invalid argument to the right of the plus symbol")
pysros_err_unsupported_compare_method = (SrosMgmtError, "Unsupported compare method")
pysros_err_unsupported_compare_datastore = (SrosMgmtError, "Compare is only supported against the candidate datastore")
pysros_err_unsupported_compare_endpoint = (InvalidPathError, "Unsupported compare path endpoint")
pysros_err_unsupported_action_path = (InvalidPathError, "Path does not point to an action")
pysros_err_unsupported_convert_method = (SrosMgmtError, "Unsupported convert method")
pysros_err_unsupported_action_io = (SrosMgmtError, "Unsupported value of argument action_io")
pysros_err_invalid_rd_state = (InternalError, "Invalid database state")
pysros_err_convert_root_not_support_pysros = (SrosMgmtError, "'pysros' format is not supported for root")
pysros_err_convert_wrong_payload_type = (TypeError, "Invalid payload type for convert")
pysros_err_wrong_json_root = (JsonDecodeError, "JSON root must be object")
pysros_err_malformed_xml = (ValueError, "Malformed XML")
pysros_err_multiple_occurences_of_node = (SrosMgmtError, "Multiple occurrences of node")
pysros_err_multiple_occurences_of_entry = (SrosMgmtError, "Multiple occurrences of list entry")
pysros_err_convert_invalid_value_for_type = (SrosMgmtError, "Invalid value for {name}")
